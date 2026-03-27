#!/usr/bin/env python3
"""
HWStream Uploader — reads HWiNFO64 CSV log and streams to your public dashboard.

Setup:
  1. In HWiNFO64: Sensors → Settings → Enable CSV logging, set interval to 2000ms
  2. pip install requests watchdog
  3. python hwstream.py --csv "C:/path/to/hwinfo.csv" --token YOUR_TOKEN --server https://your-server.com

"""

import argparse
import csv
import json
import os
import sys
import time
import requests
from pathlib import Path

# ─── Sensor categorization ───────────────────────────────────────────────────

CATEGORY_RULES = [
    ("cpu",     ["cpu", "core", "package", "tdie", "tctl"]),
    ("gpu",     ["gpu", "vram", "video", "graphics", "hot spot"]),
    ("ram",     ["ram", "memory", "dram", "mem used", "mem load"]),
    ("fan",     ["fan", "rpm", "cooler"]),
    ("voltage", ["volt", "vcore", "vdd", "vsoc", "v+", "v-", "+12", "+5", "+3.3"]),
    ("storage", ["drive", "disk", "nvme", "ssd", "hdd", "nand"]),
]

def categorize(label: str) -> str:
    low = label.lower()
    for cat, keywords in CATEGORY_RULES:
        if any(k in low for k in keywords):
            return cat
    return "other"

def parse_unit(label: str) -> str:
    low = label.lower()
    if "temp" in low or "°c" in low or "celsius" in low: return "°C"
    if "rpm" in low: return "RPM"
    if "%" in low or "load" in low or "usage" in low: return "%"
    if "volt" in low or label.startswith("V"): return "V"
    if "watt" in low or " w" in low: return "W"
    if "mhz" in low or "clock" in low: return "MHz"
    if "mb" in low and ("mem" in low or "ram" in low or "vram" in low): return "MB"
    if "gb" in low: return "GB"
    return ""

# ─── CSV parsing ─────────────────────────────────────────────────────────────

def read_latest_row(csv_path: str) -> dict | None:
    """Read the last data row from HWiNFO64 CSV log."""
    try:
        with open(csv_path, "r", encoding="utf-8-sig", errors="replace") as f:
            lines = f.readlines()

        if len(lines) < 3:
            return None

        # HWiNFO CSV: row 0 = sensor labels, row 1 = units, rows 2+ = data
        labels = next(csv.reader([lines[0]]))
        units_row = next(csv.reader([lines[1]]))
        data_row  = next(csv.reader([lines[-1]]))

        if len(data_row) < 2:
            return None

        sensors = []
        for i, (label, unit, value) in enumerate(zip(labels, units_row, data_row)):
            label = label.strip()
            if not label or label.lower() in ("date", "time"):
                continue
            try:
                val = float(value.strip())
            except ValueError:
                continue

            u = unit.strip() or parse_unit(label)
            sensors.append({
                "id": i,
                "label": label,
                "value": round(val, 2),
                "unit": u,
                "category": categorize(label),
            })

        return {"sensors": sensors}

    except Exception as e:
        print(f"[parse error] {e}")
        return None

# ─── Upload loop ──────────────────────────────────────────────────────────────

def upload_loop(csv_path: str, token: str, server: str, interval: int):
    url = f"{server.rstrip('/')}/api/upload/{token}"
    dashboard = f"{server.rstrip('/')}/dashboard/{token}"

    print(f"\n  HWStream Uploader")
    print(f"  CSV : {csv_path}")
    print(f"  Live: {dashboard}\n")

    last_size = -1
    errors = 0

    while True:
        try:
            size = os.path.getsize(csv_path)
            if size != last_size:
                data = read_latest_row(csv_path)
                if data and data["sensors"]:
                    r = requests.post(url, json=data, timeout=5)
                    if r.status_code == 200:
                        j = r.json()
                        print(f"  ✓  {len(data['sensors'])} sensors → {j.get('clients', 0)} viewer(s) live", end="\r")
                        errors = 0
                    else:
                        print(f"  ✗  Server error {r.status_code}")
                    last_size = size
        except requests.exceptions.ConnectionError:
            errors += 1
            if errors == 1:
                print(f"\n  ✗  Cannot reach {server} — retrying...")
        except FileNotFoundError:
            print(f"\n  ✗  CSV not found: {csv_path}")
            print("     Make sure HWiNFO64 CSV logging is enabled.")
            sys.exit(1)
        except KeyboardInterrupt:
            print("\n\n  Stopped.")
            sys.exit(0)
        except Exception as e:
            print(f"\n  error: {e}")

        time.sleep(interval / 1000)

# ─── CLI ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Stream HWiNFO64 CSV to HWStream dashboard")
    parser.add_argument("--csv",    required=True,  help="Path to HWiNFO64 CSV log file")
    parser.add_argument("--token",  required=True,  help="Your unique dashboard token")
    parser.add_argument("--server", required=True,  help="Dashboard server URL (e.g. https://hwstream.up.railway.app)")
    parser.add_argument("--interval", type=int, default=2000, help="Upload interval in ms (default: 2000)")
    args = parser.parse_args()

    if not Path(args.csv).exists():
        print(f"Error: CSV file not found: {args.csv}")
        print("Enable CSV logging in HWiNFO64: Sensors → Settings → Log all values to CSV")
        sys.exit(1)

    upload_loop(args.csv, args.token, args.server, args.interval)

if __name__ == "__main__":
    main()
