#!/usr/bin/env python3
"""
Phase 2: Import AppSheet data (from .json.gz) into Cloud SQL PostgreSQL.
Run from Cloud Shell after uploading appsheet_data.json.gz.

Usage:
    1. Upload appsheet_data.json.gz and this script to Cloud Shell
    2. Start proxy: cloud-sql-proxy nexus-clinic-os:southamerica-east1:stick-db --port=5432 &
    3. pip install psycopg2-binary
    4. python import_to_pg.py
"""
import json
import gzip
import sys
import time
import os

try:
    import psycopg2
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "psycopg2-binary", "-q"])
    import psycopg2

# ============================================================
# CONFIGURATION
# ============================================================
PG_HOST = "127.0.0.1"
PG_PORT = 5432
PG_DB = "nexus_clinic_os"
PG_USER = "postgres"
PG_PASS = "Frahat27"

DATA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "appsheet_data.json.gz")

# FK constraints to drop before import and recreate after
FK_CONSTRAINTS = [
    ('operacional', 'BBDD SESIONES', 'BBDD SESIONES_ID PACIENTE_fkey'),
    ('operacional', 'BBDD PAGOS', 'BBDD PAGOS_ID PACIENTE_fkey'),
    ('operacional', 'BBDD PRESUPUESTOS', 'BBDD PRESUPUESTOS_ID Paciente_fkey'),
    ('operacional', 'BBDD NOTAS', 'BBDD NOTAS_ID Paciente_fkey'),
    ('operacional', 'BBDD ORDENES', 'BBDD ORDENES_ID Paciente_fkey'),
]

FK_RECREATE = [
    ('operacional', 'BBDD SESIONES', 'BBDD SESIONES_ID PACIENTE_fkey',
     '"ID PACIENTE"', 'operacional."BBDD PACIENTES"("ID Paciente")'),
    ('operacional', 'BBDD PAGOS', 'BBDD PAGOS_ID PACIENTE_fkey',
     '"ID PACIENTE"', 'operacional."BBDD PACIENTES"("ID Paciente")'),
    ('operacional', 'BBDD PRESUPUESTOS', 'BBDD PRESUPUESTOS_ID Paciente_fkey',
     '"ID Paciente"', 'operacional."BBDD PACIENTES"("ID Paciente")'),
    ('operacional', 'BBDD NOTAS', 'BBDD NOTAS_ID Paciente_fkey',
     '"ID Paciente"', 'operacional."BBDD PACIENTES"("ID Paciente")'),
    ('operacional', 'BBDD ORDENES', 'BBDD ORDENES_ID Paciente_fkey',
     '"ID Paciente"', 'operacional."BBDD PACIENTES"("ID Paciente")'),
]


def transform(value, pg_type):
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
            parts = v.split("/")
            if len(parts) == 3 and len(parts[2]) == 4:
                try:
                    return f"{parts[2]}-{parts[0].zfill(2)}-{parts[1].zfill(2)}"
                except Exception:
                    pass
            if len(v) == 10 and v[4] == "-":
                return v
            return None
        return value
    if pg_type in ("time", "timetz"):
        return value.strip() if isinstance(value, str) and value.strip() else None
    if pg_type == "interval":
        return value.strip() if isinstance(value, str) and value.strip() else None
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
    return str(value) if value is not None else None


def get_pg_columns(cur, schema, table):
    cur.execute("""
        SELECT column_name, udt_name
        FROM information_schema.columns
        WHERE table_schema = %s AND table_name = %s
        ORDER BY ordinal_position
    """, (schema, table))
    return {row[0]: row[1] for row in cur.fetchall()}


def import_table(cur, schema, table, rows):
    pg_cols = get_pg_columns(cur, schema, table)
    if not pg_cols:
        print(f"  WARNING: No columns in PG for {schema}.'{table}' - skipping")
        return 0, 0

    print(f"  Rows to import: {len(rows)} | PG cols: {len(pg_cols)}")

    inserted = 0
    errors = 0

    for row in rows:
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
            if errors <= 3:
                print(f"    Row error: {str(e)[:150]}")
            cur.connection.rollback()

    cur.connection.commit()
    return inserted, errors


def main():
    # Load data
    if not os.path.exists(DATA_FILE):
        print(f"ERROR: {DATA_FILE} not found!")
        print("Make sure appsheet_data.json.gz is in the same directory as this script.")
        sys.exit(1)

    print(f"Loading {DATA_FILE}...")
    with gzip.open(DATA_FILE, "rb") as gz:
        all_tables = json.loads(gz.read().decode())

    total_rows = sum(len(t["rows"]) for t in all_tables)
    print(f"Tables: {len(all_tables)}")
    print(f"Total rows: {total_rows:,}\n")

    # Connect to PG
    print(f"Connecting to {PG_HOST}:{PG_PORT}/{PG_DB}...")
    conn = psycopg2.connect(
        host=PG_HOST, port=PG_PORT,
        dbname=PG_DB, user=PG_USER, password=PG_PASS,
        sslmode="prefer",
    )
    conn.autocommit = False
    cur = conn.cursor()
    print("Connected OK\n")

    # Step 1: Truncate all tables (clean slate from previous partial import)
    print("Step 1: Cleaning existing data...")
    for tbl in all_tables:
        schema = tbl["schema"]
        table = tbl["table"]
        try:
            cur.execute(f'TRUNCATE {schema}."{table}" CASCADE')
        except Exception as e:
            print(f"  Truncate {schema}.'{table}': {e}")
            conn.rollback()
    conn.commit()
    print("  Done\n")

    # Step 2: Drop FK constraints
    print("Step 2: Dropping FK constraints...")
    for schema, table, constraint in FK_CONSTRAINTS:
        try:
            cur.execute(f'ALTER TABLE {schema}."{table}" DROP CONSTRAINT IF EXISTS "{constraint}"')
            print(f"  Dropped: {table}.{constraint}")
        except Exception as e:
            print(f"  Skip: {constraint} ({e})")
            conn.rollback()
    conn.commit()
    print()

    # Step 3: Import all data
    print("Step 3: Importing data...")
    start = time.time()
    total_ins = 0
    total_err = 0

    for i, tbl in enumerate(all_tables):
        schema = tbl["schema"]
        table = tbl["table"]
        rows = tbl["rows"]

        print(f"[{i+1}/{len(all_tables)}] {schema}.'{table}'")

        if not rows:
            print(f"  (empty)")
            continue

        ins, err = import_table(cur, schema, table, rows)
        total_ins += ins
        total_err += err
        print(f"  -> Inserted: {ins}, Errors: {err}")

    # Step 4: Recreate FK constraints
    print(f"\nStep 4: Recreating FK constraints...")
    for schema, table, constraint, col, ref in FK_RECREATE:
        try:
            sql = f'ALTER TABLE {schema}."{table}" ADD CONSTRAINT "{constraint}" FOREIGN KEY ({col}) REFERENCES {ref}'
            cur.execute(sql)
            conn.commit()
            print(f"  OK: {table}.{constraint}")
        except Exception as e:
            print(f"  WARN: {constraint} - {str(e)[:100]}")
            conn.rollback()

    cur.close()
    conn.close()

    elapsed = time.time() - start
    print(f"\n{'='*50}")
    print(f"IMPORT COMPLETE")
    print(f"Rows inserted: {total_ins:,}")
    print(f"Errors: {total_err}")
    print(f"Time: {elapsed:.1f} seconds")
    print(f"{'='*50}")


if __name__ == "__main__":
    main()
