#!/usr/bin/env python3
"""
Migration: AppSheet → Cloud SQL PostgreSQL
Reads all data from AppSheet API, writes to PostgreSQL.

Usage:
    python scripts/migrate_to_postgres.py
    python scripts/migrate_to_postgres.py --app-id XXXXX   # override App ID
    python scripts/migrate_to_postgres.py --dry-run         # fetch only, don't insert

Requires in .env:
    APPSHEET_APP_ID=...
    APPSHEET_API_KEY=...
    CLINIC_DATABASE_URL=postgresql://postgres:PASSWORD@IP:5432/nexus_clinic_os
"""
from __future__ import annotations

import argparse
import asyncio
import os
import sys
import time
from datetime import datetime, date

import asyncpg
import httpx
from dotenv import load_dotenv

load_dotenv()

RATE_LIMIT_SECONDS = 46

# Tables in insertion order (parents before children)
TABLES: list[tuple[str, str]] = [
    # --- Config tables (no FKs) ---
    ("config", "LISTA A | tipo tratamientos"),
    ("config", "LISTA B | FUENTE CAPTACION"),
    ("config", "LISTA C | STATUS LEAD"),
    ("config", "LISTA D | Estado Paciente"),
    ("config", "LISTA E | TIPO DE ENCUESTA"),
    ("config", "LISTA F | TIPO DE GASTO"),
    ("config", "LISTA G | Metodo de Pago"),
    ("config", "LISTA G1 | Estado de Pago"),
    ("config", "LISTA H | Unidad de medida"),
    ("config", "LISTA I | Estado de Tratamiento"),
    ("config", "LISTA J | Estado de Sesion"),
    ("config", "Lista L | Insumos y Packaging"),
    ("config", "LISTA M | CATEGORIA DE PAGOS"),
    ("config", "LISTA N | UNIDAD DE NEGOCIO"),
    ("config", "LISTA O | HORARIOS DE ATENCION"),
    # --- Operacional: independent tables first ---
    ("operacional", "BBDD PACIENTES"),
    ("operacional", "BBDD LEADS"),
    ("operacional", "BBDD TARIFARIO"),
    ("operacional", "BBDD ALINEADORES"),
    ("operacional", "BBDD PROFESIONALES"),
    ("operacional", "BBDD PROVEEDORES"),
    ("operacional", "BBDD CONCILIACION"),
    ("operacional", "BBDD INSUMOS y STOCK"),
    # --- Operacional: tables with FK → PACIENTES ---
    ("operacional", "BBDD SESIONES"),
    ("operacional", "BBDD PAGOS"),
    ("operacional", "BBDD PRESUPUESTOS"),
    ("operacional", "BBDD NOTAS"),
    ("operacional", "BBDD ORDENES"),
    # --- Operacional: remaining tables ---
    ("operacional", "BBDD FACTURAS"),
    ("operacional", "BBDD GASTOS"),
    ("operacional", "BBDD PRODUCCION"),
]


async def get_pg_columns(conn: asyncpg.Connection, schema: str, table: str) -> dict[str, str]:
    """Get {column_name: udt_name} from PostgreSQL table."""
    rows = await conn.fetch("""
        SELECT column_name, udt_name
        FROM information_schema.columns
        WHERE table_schema = $1 AND table_name = $2
        ORDER BY ordinal_position
    """, schema, table)
    return {r["column_name"]: r["udt_name"] for r in rows}


async def fetch_appsheet_rows(
    client: httpx.AsyncClient, app_id: str, api_key: str, table_name: str
) -> list[dict]:
    """Fetch all rows from AppSheet table via API."""
    url = f"https://api.appsheet.com/api/v2/apps/{app_id}/tables/{table_name}/Action"
    body = {"Action": "Find", "Properties": {}, "Rows": []}
    headers = {
        "ApplicationAccessKey": api_key,
        "Content-Type": "application/json",
    }

    for attempt in range(3):
        try:
            resp = await client.post(url, json=body, headers=headers, timeout=60.0)
            if resp.status_code == 200:
                data = resp.json()
                if isinstance(data, list):
                    return data
                # Empty body = rate limited, retry
                if not data:
                    print(f"    Empty response (rate limited?), retry in 50s...")
                    await asyncio.sleep(50)
                    continue
                return []
            else:
                print(f"    HTTP {resp.status_code}: {resp.text[:200]}")
                return []
        except Exception as e:
            print(f"    Network error (attempt {attempt+1}): {e}")
            await asyncio.sleep(10)

    return []


def transform_value(value, pg_type: str):
    """Transform AppSheet value → PostgreSQL-compatible value."""
    if value is None or value == "":
        return None

    # Boolean
    if pg_type == "bool":
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.strip().upper() in ("Y", "YES", "TRUE", "1", "N/A")
        return bool(value)

    # Date: AppSheet returns MM/DD/YYYY
    if pg_type == "date":
        if isinstance(value, str):
            for fmt in ("%m/%d/%Y", "%Y-%m-%d", "%d/%m/%Y"):
                try:
                    return datetime.strptime(value.strip(), fmt).date()
                except ValueError:
                    continue
            return None
        return value

    # Time
    if pg_type in ("time", "timetz"):
        if isinstance(value, str) and value.strip():
            return value.strip()
        return None

    # Interval (Duration)
    if pg_type == "interval":
        if isinstance(value, str) and value.strip():
            return value.strip()
        return None

    # Numeric types
    if pg_type in ("numeric", "float8", "float4", "int4", "int8", "int2"):
        if isinstance(value, (int, float)):
            return value
        if isinstance(value, str):
            cleaned = value.replace("$", "").replace(",", "").replace(" ", "").strip()
            if not cleaned or cleaned == "-":
                return None
            try:
                if pg_type in ("int4", "int8", "int2"):
                    return int(float(cleaned))
                return float(cleaned)
            except ValueError:
                return None
        return value

    # Text: stringify
    if value is not None:
        return str(value)
    return None


async def migrate_table(
    conn: asyncpg.Connection,
    client: httpx.AsyncClient,
    app_id: str,
    api_key: str,
    schema: str,
    table: str,
    dry_run: bool = False,
) -> tuple[int, int]:
    """Migrate one table. Returns (inserted, errors)."""
    # 1. Get PG column definitions
    pg_cols = await get_pg_columns(conn, schema, table)
    if not pg_cols:
        print(f"  ⚠ No columns in PG — skipping")
        return 0, 0

    # 2. Fetch data from AppSheet
    rows = await fetch_appsheet_rows(client, app_id, api_key, table)
    if not rows:
        print(f"  (empty or not accessible)")
        return 0, 0

    print(f"  AppSheet: {len(rows)} rows → PG columns: {len(pg_cols)}")

    if dry_run:
        print(f"  [DRY RUN] Would insert {len(rows)} rows")
        return len(rows), 0

    # 3. Insert rows
    inserted = 0
    errors = 0

    for row in rows:
        # Filter to only PG columns
        filtered = {}
        for col_name, pg_type in pg_cols.items():
            if col_name in row:
                filtered[col_name] = transform_value(row[col_name], pg_type)

        if not filtered:
            continue

        cols = list(filtered.keys())
        values = [filtered[c] for c in cols]
        col_str = ", ".join(f'"{c}"' for c in cols)
        ph_str = ", ".join(f"${i+1}" for i in range(len(cols)))

        query = f'{schema}."{table}" ({col_str}) VALUES ({ph_str})'

        try:
            await conn.execute(f"INSERT INTO {query} ON CONFLICT DO NOTHING", *values)
            inserted += 1
        except Exception as e:
            errors += 1
            if errors <= 5:
                print(f"    ✗ Row error: {e}")

    return inserted, errors


async def main():
    parser = argparse.ArgumentParser(description="Migrate AppSheet → PostgreSQL")
    parser.add_argument("--app-id", help="Override APPSHEET_APP_ID from .env")
    parser.add_argument("--api-key", help="Override APPSHEET_API_KEY from .env")
    parser.add_argument("--dry-run", action="store_true", help="Fetch data but don't insert")
    args = parser.parse_args()

    app_id = args.app_id or os.getenv("APPSHEET_APP_ID", "")
    api_key = args.api_key or os.getenv("APPSHEET_API_KEY", "")
    db_url = os.getenv("CLINIC_DATABASE_URL", "")

    if not app_id or not api_key:
        print("ERROR: Set APPSHEET_APP_ID and APPSHEET_API_KEY in .env")
        print("  (or use --app-id to override)")
        sys.exit(1)

    if not db_url:
        print("ERROR: Set CLINIC_DATABASE_URL in .env")
        print("  Format: postgresql://postgres:PASSWORD@IP:5432/nexus_clinic_os")
        sys.exit(1)

    # Show config
    db_display = db_url.split("@")[1] if "@" in db_url else "configured"
    print(f"AppSheet App ID: {app_id[:8]}...")
    print(f"PostgreSQL: {db_display}")
    print(f"Tables: {len(TABLES)}")
    print(f"Rate limit: {RATE_LIMIT_SECONDS}s between API calls")
    est_min = len(TABLES) * RATE_LIMIT_SECONDS // 60
    print(f"Estimated time: ~{est_min} minutes")
    if args.dry_run:
        print("MODE: DRY RUN (no inserts)")
    print()

    # Connect
    conn = await asyncpg.connect(db_url)
    print("Connected to PostgreSQL ✓")

    # Disable FK checks for bulk load
    await conn.execute("SET session_replication_role = 'replica'")
    print("FK checks disabled for migration ✓\n")

    start_time = time.time()
    total_inserted = 0
    total_errors = 0

    async with httpx.AsyncClient() as client:
        for i, (schema, table) in enumerate(TABLES):
            # Rate limit (skip first)
            if i > 0:
                wait = RATE_LIMIT_SECONDS
                print(f"\n  ⏳ Waiting {wait}s (rate limit)... ", end="", flush=True)
                await asyncio.sleep(wait)
                print("done")

            elapsed = time.time() - start_time
            remaining = (len(TABLES) - i) * RATE_LIMIT_SECONDS
            print(f"\n[{i+1}/{len(TABLES)}] {schema}.'{table}' "
                  f"(elapsed: {elapsed/60:.0f}m, ~{remaining/60:.0f}m left)")

            inserted, errors = await migrate_table(
                conn, client, app_id, api_key, schema, table, args.dry_run
            )
            total_inserted += inserted
            total_errors += errors

    # Re-enable FK checks
    await conn.execute("SET session_replication_role = 'origin'")
    print("\nFK checks re-enabled ✓")

    await conn.close()

    elapsed = time.time() - start_time
    print(f"\n{'='*60}")
    print(f"MIGRATION COMPLETE")
    print(f"Total rows inserted: {total_inserted:,}")
    print(f"Total errors: {total_errors}")
    print(f"Time: {elapsed/60:.1f} minutes")
    print(f"{'='*60}")


if __name__ == "__main__":
    asyncio.run(main())
