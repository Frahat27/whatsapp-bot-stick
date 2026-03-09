#!/usr/bin/env python3
"""
Import ONLY the 5 remaining tables into Cloud SQL PostgreSQL.
Order: PROFESIONALES, TARIFARIO, PRODUCCION, SESIONES, PAGOS
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

PG_HOST = "127.0.0.1"
PG_PORT = 5432
PG_DB = "nexus_clinic_os"
PG_USER = "postgres"
PG_PASS = "Frahat27"

DATA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "appsheet_data.json.gz")

# Only these 5 tables, in this order
REMAINING = [
    "BBDD PROFESIONALES",
    "BBDD TARIFARIO",
    "BBDD PRODUCCION",
    "BBDD SESIONES",
    "BBDD PAGOS",
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
            if errors <= 5:
                print(f"    Row error: {str(e)[:200]}")
            cur.connection.rollback()

    cur.connection.commit()
    return inserted, errors


def main():
    if not os.path.exists(DATA_FILE):
        print(f"ERROR: {DATA_FILE} not found!")
        sys.exit(1)

    print(f"Loading data...")
    with gzip.open(DATA_FILE, "rb") as gz:
        all_tables = json.loads(gz.read().decode())

    # Build lookup by table name
    lookup = {t["table"]: t for t in all_tables}

    print(f"Connecting to {PG_HOST}:{PG_PORT}/{PG_DB}...")
    conn = psycopg2.connect(
        host=PG_HOST, port=PG_PORT,
        dbname=PG_DB, user=PG_USER, password=PG_PASS,
        sslmode="prefer",
    )
    conn.autocommit = False
    cur = conn.cursor()
    print("Connected OK\n")

    # Drop FK constraints for SESIONES and PAGOS (they reference PACIENTES)
    print("Dropping FK constraints...")
    fks_to_drop = [
        ('BBDD SESIONES', 'BBDD SESIONES_ID PACIENTE_fkey'),
        ('BBDD PAGOS', 'BBDD PAGOS_ID PACIENTE_fkey'),
    ]
    for table, constraint in fks_to_drop:
        try:
            cur.execute(f'ALTER TABLE operacional."{table}" DROP CONSTRAINT IF EXISTS "{constraint}"')
            print(f"  Dropped: {constraint}")
        except Exception as e:
            print(f"  Skip: {e}")
            conn.rollback()
    conn.commit()
    print()

    start = time.time()
    total_ins = 0
    total_err = 0

    for i, table_name in enumerate(REMAINING):
        print(f"[{i+1}/{len(REMAINING)}] operacional.'{table_name}'")

        tbl = lookup.get(table_name)
        if not tbl:
            print(f"  NOT FOUND in data file - skipping")
            continue

        rows = tbl["rows"]
        if not rows:
            print(f"  (empty)")
            continue

        ins, err = import_table(cur, "operacional", table_name, rows)
        total_ins += ins
        total_err += err
        print(f"  -> Inserted: {ins}, Errors: {err}")

    # Recreate FK constraints
    print(f"\nRecreating FK constraints...")
    fks_to_create = [
        ('BBDD SESIONES', 'BBDD SESIONES_ID PACIENTE_fkey',
         '"ID PACIENTE"', 'operacional."BBDD PACIENTES"("ID Paciente")'),
        ('BBDD PAGOS', 'BBDD PAGOS_ID PACIENTE_fkey',
         '"ID PACIENTE"', 'operacional."BBDD PACIENTES"("ID Paciente")'),
    ]
    for table, constraint, col, ref in fks_to_create:
        try:
            cur.execute(f'ALTER TABLE operacional."{table}" ADD CONSTRAINT "{constraint}" FOREIGN KEY ({col}) REFERENCES {ref}')
            conn.commit()
            print(f"  OK: {constraint}")
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
