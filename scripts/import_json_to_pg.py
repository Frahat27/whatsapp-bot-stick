#!/usr/bin/env python3
"""
Phase 2: Import JSON files into Cloud SQL PostgreSQL.
Run from Cloud Shell after uploading the JSON files.

Usage:
    pip install psycopg2-binary
    python import_to_pg.py
"""
import json
import glob
import os
import sys
import time

try:
    import psycopg2
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "psycopg2-binary", "-q"])
    import psycopg2

# ============================================================
# CONFIGURATION
# ============================================================
PG_HOST = "127.0.0.1"  # Via Cloud SQL Auth Proxy
PG_PORT = 5432
PG_DB = "nexus_clinic_os"
PG_USER = "postgres"
PG_PASS = "Frahat27"

# Directory containing the JSON files
DATA_DIR = os.path.join(os.path.dirname(__file__), "appsheet_export")


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
        print(f"  No columns in PG - skipping")
        return 0, 0

    print(f"  Rows: {len(rows)} | PG cols: {len(pg_cols)}")

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
                print(f"    Error: {e}")
            cur.connection.rollback()

    cur.connection.commit()
    return inserted, errors


def main():
    # Find JSON files
    json_files = sorted(glob.glob(os.path.join(DATA_DIR, "*.json")))
    if not json_files:
        print(f"No JSON files found in {DATA_DIR}")
        print("Make sure appsheet_export/ directory is in the same folder as this script")
        sys.exit(1)

    print(f"Found {len(json_files)} JSON files in {DATA_DIR}")
    print(f"PostgreSQL: {PG_HOST}:{PG_PORT}/{PG_DB}\n")

    # Connect
    conn = psycopg2.connect(
        host=PG_HOST, port=PG_PORT,
        dbname=PG_DB, user=PG_USER, password=PG_PASS,
        sslmode="prefer",
    )
    conn.autocommit = False
    cur = conn.cursor()
    print("Connected to PostgreSQL OK\n")

    start = time.time()
    total_ins = 0
    total_err = 0

    for i, filepath in enumerate(json_files):
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)

        schema = data["schema"]
        table = data["table"]
        rows = data["rows"]

        print(f"[{i+1}/{len(json_files)}] {schema}.'{table}'")

        if not rows:
            print(f"  (empty)")
            continue

        ins, err = import_table(cur, schema, table, rows)
        total_ins += ins
        total_err += err
        print(f"  -> Inserted: {ins}, Errors: {err}")

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
