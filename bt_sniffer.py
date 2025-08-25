import argparse
import asyncio
import csv
import json
import sys
import time
import platform
from datetime import datetime, timezone


def utc_now_iso():
    return datetime.now(timezone.utc).isoformat()

class DeviceRecord:
    def __init__(self, address, transport):
        self.address = address
        self.transport = transport  # "BLE" or "Classic"
        self.name = None
        self.rssi = None
        self.tx_power = None
        self.appearance = None
        self.connectable = None
        self.address_type = None
        self.service_uuids = set()
        self.service_data = {}      # uuid -> hex string
        self.manufacturer_data = {} # company_id(int) -> hex string
        self.device_class = None    # Classic CoD integer if available
        self.first_seen = utc_now_iso()
        self.last_seen = self.first_seen
        self.sightings = 0

    def update_last_seen(self):
        self.last_seen = utc_now_iso()
        self.sightings += 1
    
#This method return a flat dictionary that is suitable for CSV/JOSN.
    def to_row(self):
        return {
            "address": self.address,
            "transport": self.transport,
            "name": self.name,
            "rssi": self.rssi,
            "tx_power": self.tx_power,
            "appearance": self.appearance,
            "connectable": self.connectable,
            "address_type": self.address_type,
            "device_class": self.device_class,
            "service_uuids": sorted(list(self.service_uuids)) if self.service_uuids else None,
            "service_data": self.service_data or None,
            "manufacturer_data": self.manufacturer_data or None,
            "first_seen": self.first_seen,
            "last_seen": self.last_seen,
            "sightings": self.sightings,
        }

#BLE scan implementation (bleak)

async def scan_ble(duration, adapter, verbose=False):
    try:
        from bleak import BleakScanner
        from bleak.backends.scanner import AdvertisementData
    except Exception as e:
        print("[!] BLE scan requested but 'bleak' is not installed or failed to import.", file=sys.stderr)
        print("    pip install bleak", file=sys.stderr)
        return {}

    records = {}

    def on_detect(device, adv_data: 'AdvertisementData'):
        addr = getattr(device, "address", None) or getattr(device, "mac_address", None) or "UNKNOWN"
        rec = records.get(addr)
        if rec is None:
            rec = DeviceRecord(addr, "BLE")
            records[addr] = rec

        # Update high-level fields
        rec.name = device.name or adv_data.local_name or rec.name
        rec.rssi = getattr(adv_data, "rssi", None) if getattr(adv_data, "rssi", None) is not None else getattr(device, "rssi", None)
        rec.tx_power = getattr(adv_data, "tx_power", None)
        rec.appearance = getattr(adv_data, "appearance", None)
        rec.connectable = getattr(adv_data, "connectable", None)
        rec.address_type = getattr(adv_data, "address_type", None)

        # Service UUIDs
        if getattr(adv_data, "service_uuids", None):
            for u in adv_data.service_uuids:
                rec.service_uuids.add(u)

        # Service data (uuid -> hex)
        if getattr(adv_data, "service_data", None):
            for u, b in adv_data.service_data.items():
                rec.service_data[u] = b.hex()

        # Manufacturer data (company_id -> hex)
        if getattr(adv_data, "manufacturer_data", None):
            for cid, b in adv_data.manufacturer_data.items():
                try:
                    key = int(cid)
                except Exception:
                    key = cid
                rec.manufacturer_data[key] = b.hex()

        rec.update_last_seen()
        if verbose:
            print(f"[BLE] {rec.address}  RSSI={rec.rssi}  Name={rec.name}  Services={len(rec.service_uuids)}")

    kwargs = {}
    # Adapter selection (Linux 'hci0', macOS None, Windows None)
    if adapter:
        kwargs["adapter"] = adapter

    try:
        scanner = BleakScanner(detection_callback=on_detect, **kwargs)
        await scanner.start()
        await asyncio.sleep(duration)
        await scanner.stop()
    except Exception as e:
        print(f"[!] BLE scan error: {e}", file=sys.stderr)

    return records

# Classic scan implementation (PyBluez)

def scan_classic(duration, verbose=False):
    try:
        import bluetooth  # PyBluez
    except Exception as e:
        print("[!] Classic scan requested but 'pybluez' is not installed or failed to import.", file=sys.stderr)
        print("    pip install pybluez", file=sys.stderr)
        return {}

    records = {}

    try:
        # The duration parameter is advisory; some platforms ignore/approximate it.
        devices = bluetooth.discover_devices(duration=duration, lookup_names=True, flush_cache=True, lookup_class=True)
    except TypeError:
        # Older PyBluez versions may not support lookup_class
        devices = bluetooth.discover_devices(duration=duration, lookup_names=True, flush_cache=True)
        devices = [(addr, name, None) for addr, name in devices]

    for item in devices:
        if len(item) == 3:
            addr, name, dev_class = item
        else:
            # Fallback tuple shape
            addr, name = item[0], item[1] if len(item) > 1 else None
            dev_class = None

        rec = records.get(addr)
        if rec is None:
            rec = DeviceRecord(addr, "Classic")
            records[addr] = rec

        rec.name = name or rec.name
        rec.device_class = dev_class
        rec.update_last_seen()
        if verbose:
            print(f"[BR/EDR] {rec.address}  Name={rec.name}  CoD={rec.device_class}")

    return records

#Output helpers

def write_json(path, records):
    with open(path, "w", encoding="utf-8") as f:
        json.dump([r.to_row() for r in records.values()], f, ensure_ascii=False, indent=2)

def write_csv(path, records):
    rows = [r.to_row() for r in records.values()]
    # Expand sets/lists/dicts to JSON strings for CSV
    for r in rows:
        if isinstance(r.get("service_uuids"), list):
            r["service_uuids"] = json.dumps(r["service_uuids"])
        if isinstance(r.get("service_data"), dict):
            r["service_data"] = json.dumps(r["service_data"])
        if isinstance(r.get("manufacturer_data"), dict):
            r["manufacturer_data"] = json.dumps(r["manufacturer_data"])

    fieldnames = [
        "address","transport","name","rssi","tx_power","appearance","connectable",
        "address_type","device_class","service_uuids","service_data","manufacturer_data",
        "first_seen","last_seen","sightings"
    ]
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow(r)

#CLI Design for the program.

def parse_args():
    p = argparse.ArgumentParser(description="Bluetooth sniffer/logger for BLE and Classic (Inquiry).")
    p.add_argument("--mode", choices=["ble","classic","both"], default="ble",
                   help="What to scan: BLE advertisements, Classic Inquiry, or both (default: ble).")
    p.add_argument("--seconds", type=int, default=20, help="Scan duration per mode (default: 20).")
    p.add_argument("--adapter", type=str, default=None,
                   help="Adapter/interface name (e.g., 'hci0' on Linux). Optional on Windows/macOS.")
    p.add_argument("--json", dest="json_path", type=str, default=None, help="Write results to JSON file path.")
    p.add_argument("--csv", dest="csv_path", type=str, default=None, help="Write results to CSV file path.")
    p.add_argument("--verbose", action="store_true", help="Print sightings as they arrive.")
    return p.parse_args()

async def main_async():
    args = parse_args()
    all_records = {}

    print(f"[i] Platform: {platform.system()}  Python: {platform.python_version()}")
    print(f"[i] Mode: {args.mode}  Duration: {args.seconds}s per mode  Adapter: {args.adapter or '(default)'}")
    print(f"[i] Started at: {utc_now_iso()}")

    if args.mode in ("ble", "both"):
        print("[i] Starting BLE scan...")
        ble_records = await scan_ble(args.seconds, args.adapter, verbose=args.verbose)
        all_records.update(ble_records)
        print(f"[i] BLE scan complete: {len(ble_records)} device(s)")

    if args.mode in ("classic", "both"):
        print("[i] Starting Classic Inquiry scan...")
        classic_records = await asyncio.to_thread(scan_classic, args.seconds, args.verbose)
        # Merge: prefer BLE fields when same MAC appears (rare across transports but possible on some stacks)
        for addr, rec in classic_records.items():
            if addr in all_records:
                # Preserve existing BLE info; keep classic-specific fields
                existing = all_records[addr]
                existing.device_class = existing.device_class or rec.device_class
                existing.update_last_seen()
            else:
                all_records[addr] = rec
        print(f"[i] Classic scan complete: {len(classic_records)} device(s)")

    if not all_records:
        print("[i] No devices discovered.")
    else:
        print(f"[i] Total unique devices: {len(all_records)}")

    # Outputs
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    if args.json_path:
        write_json(args.json_path, all_records)
        print(f"[✓] Wrote JSON: {args.json_path}")
    if args.csv_path:
        write_csv(args.csv_path, all_records)
        print(f"[✓] Wrote CSV:  {args.csv_path}")
    if not args.json_path and not args.csv_path:
        # Default to writing a timestamped JSON for convenience
        default_json = f"bt_scan_{ts}.json"
        write_json(default_json, all_records)
        print(f"[i] No output path provided. Wrote default JSON: {default_json}")

if __name__ == "__main__":
    try:
        asyncio.run(main_async())
    except KeyboardInterrupt:
        print("\n[!] Interrupted by user.")
