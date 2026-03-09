#!/usr/bin/env python3
"""
Phase 1: Fetch all AppSheet data to local JSON files.
No PostgreSQL needed — just downloads data.
"""
import json
import os
import sys
import time
import urllib.request
import urllib.error
import urllib.parse

APPSHEET_APP_ID = "cfc7574f-e4ec-4cf4-8a63-f04d84d347d4"
APPSHEET_API_KEY = "V2-vnqyX-ZhkYA-kCDLU-narl7-gMXiz-h9vit-L8hNP-I037X"

RATE_LIMIT = 46

TABLES = [
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
    ("operacional", "BBDD PACIENTES"),
    ("operacional", "BBDD LEADS"),
    ("operacional", "BBDD TARIFARIO"),
    ("operacional", "BBDD ALINEADORES"),
    ("operacional", "BBDD PROFESIONALES"),
    ("operacional", "BBDD PROVEEDORES"),
    ("operacional", "BBDD CONCILIACION"),
    ("operacional", "BBDD INSUMOS y STOCK"),
    ("operacional", "BBDD SESIONES"),
    ("operacional", "BBDD PAGOS"),
    ("operacional", "BBDD PRESUPUESTOS"),
    ("operacional", "BBDD NOTAS"),
    ("operacional", "BBDD ORDENES"),
    ("operacional", "BBDD FACTURAS"),
    ("operacional", "BBDD GASTOS"),
    ("operacional", "BBDD PRODUCCION"),
]


def fetch_appsheet(table_name):
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
                    print(f"    Empty JSON, retry in 50s...")
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


def main():
    out_dir = os.path.join(os.path.dirname(__file__), "..", "data", "appsheet_export")
    os.makedirs(out_dir, exist_ok=True)

    print(f"Fetching {len(TABLES)} tables from AppSheet")
    print(f"Rate limit: {RATE_LIMIT}s between calls")
    print(f"Output: {out_dir}")
    print(f"Estimated time: ~{len(TABLES) * RATE_LIMIT // 60} minutes\n")

    start = time.time()
    total_rows = 0

    for i, (schema, table) in enumerate(TABLES):
        if i > 0:
            print(f"  Waiting {RATE_LIMIT}s...", end=" ", flush=True)
            time.sleep(RATE_LIMIT)
            print("ok")

        elapsed = time.time() - start
        remaining = (len(TABLES) - i) * RATE_LIMIT
        print(f"[{i+1}/{len(TABLES)}] {schema}.'{table}' "
              f"({elapsed/60:.0f}m elapsed, ~{remaining/60:.0f}m left)")

        rows = fetch_appsheet(table)
        count = len(rows)
        total_rows += count

        # Save to JSON
        safe_name = table.replace(" ", "_").replace("|", "_").replace("/", "_")
        filename = f"{schema}__{safe_name}.json"
        filepath = os.path.join(out_dir, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump({"schema": schema, "table": table, "rows": rows}, f, ensure_ascii=False)

        print(f"  -> {count} rows saved to {filename}")

    elapsed = time.time() - start
    print(f"\n{'='*50}")
    print(f"FETCH COMPLETE")
    print(f"Total rows: {total_rows:,}")
    print(f"Files: {len(TABLES)} JSON files in {out_dir}")
    print(f"Time: {elapsed/60:.1f} minutes")
    print(f"{'='*50}")


if __name__ == "__main__":
    main()
