#!/usr/bin/env python3
"""
Migration: AppSheet -> Cloud SQL PostgreSQL
Standalone script — only needs psycopg2-binary

Usage:
    pip install psycopg2-binary
    python migrate.py
"""
import json
import sys
import time
import urllib.request
import urllib.error
import urllib.parse

# Try psycopg2, if not available suggest install
try:
    import psycopg2
    import psycopg2.extras
except ImportError:
    print("Installing psycopg2-binary...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "psycopg2-binary", "-q"])
    import psycopg2
    import psycopg2.extras

# ============================================================
# CONFIGURATION — Edit these values
# ============================================================
APPSHEET_APP_ID = "cfc7574f-e4ec-4cf4-8a63-f04d84d347d4"
APPSHEET_API_KEY = "V2-vnqyX-ZhkYA-kCDLU-narl7-gMXiz-h9vit-L8hNP-I037X"

PG_HOST = "34.95.178.117"
PG_PORT = 5432
PG_DB = "nexus_clinic_os"
PG_USER = "postgres"
PG_PASS = "Frahat27"

RATE_LIMIT = 46  # seconds between AppSheet API calls

# ============================================================
# TABLE LIST (ordered: parents before children)
# ============================================================
TABLES = [
    # Config (no FKs)
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
    # Operacional: independent first
    ("operacional", "BBDD PACIENTES"),
    ("operacional", "BBDD LEADS"),
    ("operacional", "BBDD TARIFARIO"),
    ("operacional", "BBDD ALINEADORES"),
    ("operacional", "BBDD PROFESIONALES"),
    ("operacional", "BBDD PROVEEDORES"),
    ("operacional", "BBDD CONCILIACION"),
    ("operacional", "BBDD INSUMOS y STOCK"),
    # Operacional: FK -> PACIENTES
    ("operacional", "BBDD SESIONES"),
    ("operacional", "BBDD PAGOS"),
    ("operacional", "BBDD PRESUPUESTOS"),
    ("operacional", "BBDD NOTAS"),
    ("operacional", "BBDD ORDENES"),
    # Operacional: remaining
    ("operacional", "BBDD FACTURAS"),
    ("operacional", "BBDD GASTOS"),
    ("operacional", "BBDD PRODUCCION"),
]


def fetch_appsheet(table_name):
    """Fetch all rows from AppSheet table using urllib."""
    encoded_name = urllib.parse.quote(table_name)
    url = f"https://api.appsheet.com/api/v2/apps/{APPSHEET_APP_ID}/tables/{encoded_name}/Action"
    body = json.dumps({"Action": "Find", "Properties": {}, "Rows": []}).encode()
    headers = {
        "ApplicationAccessKey": APPSHEET_API_KEY,
        "Content-Type": "application/json",
    }

    for attempt in range(3):
        try:
            req = urllib.request.Request(url, data=body, headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=60) as resp:
                raw = resp.read().decode()
                if not raw:
                    print(f"    Empty response (rate limited?), retry in 50s...")
                    time.sleep(50)
                    continue
                data = json.loads(raw)
                if isinstance(data, list):
                    return data
                if not data:
                    print(f"    Empty JSON (rate limited?), retry in 50s...")
                    time.sleep(50)
                    continue
                return []
        except urllib.error.HTTPError as e:
            print(f"    HTTP {e.code}: {e.read().decode()[:200]}")
            return []
        except Exception as e:
            print(f"    Error (attempt {attempt+1}): {e}")
            time.sleep(10)

    return []


def get_pg_columns(cur, schema, table):
    """Get {column_name: data_type} from PG."""
    cur.execute("""
        SELECT column_name, udt_name
        FROM information_schema.columns
        WHERE table_schema = %s AND table_name = %s
        ORDER BY ordinal_position
    """, (schema, table))
    return {row[0]: row[1] for row in cur.fetchall()}


def transform(value, pg_type):
    """Transform AppSheet value for PostgreSQL."""
    if value is None or value == "" or value == "N/A":
        return None

    if pg_type == "bool":
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.strip().upper() in ("Y", "YES", "TRUE", "1")
        return bool(value)

    if pg_type == "date":
        if isinstance(value, str):
            v = value.strip()
            # Try MM/DD/YYYY (AppSheet format)
            parts = v.split("/")
            if len(parts) == 3 and len(parts[2]) == 4:
                try:
                    return f"{parts[2]}-{parts[0].zfill(2)}-{parts[1].zfill(2)}"
                except Exception:
                    pass
            # Already YYYY-MM-DD?
            if len(v) == 10 and v[4] == "-":
                return v
            return None
        return value

    if pg_type in ("time", "timetz"):
        if isinstance(value, str) and value.strip():
            return value.strip()
        return None

    if pg_type == "interval":
        if isinstance(value, str) and value.strip():
            return value.strip()
        return None

    if pg_type in ("numeric", "float8", "float4"):
        if isinstance(value, (int, float)):
            return value
        if isinstance(value, str):
            cleaned = value.replace("$", "").replace(",", "").strip()
            if not cleaned or cleaned == "-":
                return None
            try:
                return float(cleaned)
            except ValueError:
                return None
        return value

    if pg_type in ("int4", "int8", "int2"):
        if isinstance(value, (int, float)):
            return int(value)
        if isinstance(value, str):
            cleaned = value.replace(",", "").strip()
            if not cleaned or cleaned == "-":
                return None
            try:
                return int(float(cleaned))
            except ValueError:
                return None
        return value

    # Text
    return str(value) if value is not None else None


def migrate_table(cur, schema, table):
    """Migrate one table. Returns (inserted, errors)."""
    # Get PG columns
    pg_cols = get_pg_columns(cur, schema, table)
    if not pg_cols:
        print(f"  No columns in PG - skipping")
        return 0, 0

    # Fetch from AppSheet
    rows = fetch_appsheet(table)
    if not rows:
        print(f"  (empty or not accessible)")
        return 0, 0

    print(f"  AppSheet: {len(rows)} rows | PG cols: {len(pg_cols)}")

    inserted = 0
    errors = 0

    for row in rows:
        # Filter to PG columns only
        filtered = {}
        for col, pg_type in pg_cols.items():
            if col in row:
                filtered[col] = transform(row[col], pg_type)

        if not filtered:
            continue

        cols = list(filtered.keys())
        values = [filtered[c] for c in cols]
        col_str = ", ".join(f'"{c}"' for c in cols)
        ph_str = ", ".join(["%s"] * len(cols))

        sql = f'INSERT INTO {schema}."{table}" ({col_str}) VALUES ({ph_str}) ON CONFLICT DO NOTHING'

        try:
            cur.execute(sql, values)
            inserted += 1
        except Exception as e:
            errors += 1
            if errors <= 5:
                print(f"    Error: {e}")
            cur.connection.rollback()

    cur.connection.commit()
    return inserted, errors


def main():
    print(f"AppSheet App: {APPSHEET_APP_ID[:8]}...")
    print(f"PostgreSQL: {PG_HOST}:{PG_PORT}/{PG_DB}")
    print(f"Tables: {len(TABLES)}")
    print(f"Rate limit: {RATE_LIMIT}s between API calls")
    print(f"Estimated time: ~{len(TABLES) * RATE_LIMIT // 60} minutes")
    print()

    # Connect
    conn = psycopg2.connect(
        host=PG_HOST, port=PG_PORT,
        dbname=PG_DB, user=PG_USER, password=PG_PASS,
        sslmode="prefer",
    )
    conn.autocommit = False
    cur = conn.cursor()
    print("Connected to PostgreSQL OK")

    # Tables are ordered parents-first, so FK constraints are satisfied naturally
    print("Starting migration...\n")

    start = time.time()
    total_ins = 0
    total_err = 0

    for i, (schema, table) in enumerate(TABLES):
        if i > 0:
            print(f"\n  Waiting {RATE_LIMIT}s (rate limit)...", end=" ", flush=True)
            time.sleep(RATE_LIMIT)
            print("ok")

        elapsed = time.time() - start
        remaining = (len(TABLES) - i) * RATE_LIMIT
        print(f"\n[{i+1}/{len(TABLES)}] {schema}.'{table}' "
              f"({elapsed/60:.0f}m elapsed, ~{remaining/60:.0f}m left)")

        ins, err = migrate_table(cur, schema, table)
        total_ins += ins
        total_err += err
        print(f"  -> Inserted: {ins}, Errors: {err}")

    cur.close()
    conn.close()

    elapsed = time.time() - start
    print(f"\n{'='*50}")
    print(f"MIGRATION COMPLETE")
    print(f"Rows inserted: {total_ins:,}")
    print(f"Errors: {total_err}")
    print(f"Time: {elapsed/60:.1f} minutes")
    print(f"{'='*50}")


if __name__ == "__main__":
    main()
