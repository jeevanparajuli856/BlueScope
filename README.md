# Bluetooth Sniffer & Logger

A cross-platform Python tool to scan **nearby Bluetooth devices** (BLE & Classic), log their details, and export results to **JSON** or **CSV**.  
It’s designed for research, troubleshooting, and educational purposes, not for intercepting or decrypting traffic.

## Features
- **BLE Scanning** (via [Bleak](https://github.com/hbldh/bleak)):
  - Logs device address, name (if advertised), RSSI, TX power, appearance, connectable flag, address type
  - Captures service UUIDs, service data, and manufacturer data (hex format)
- **Classic Scanning** (via [PyBluez2](https://github.com/pybluez/pybluez)):
  - Logs device address, friendly name, and Class of Device (CoD)
- **Aggregation**
  - Tracks first seen, last seen, and sightings count per device
- **Cross-platform**
  - BLE: Linux, Windows, macOS
  - Classic: Linux & Windows (not supported on macOS)
- **Output**
  - Export results as JSON or CSV
  - Includes timestamp and detailed metadata

## Installation

Make sure you have Python 3.9+ installed. Then:

```bash
git clone https://github.com/<your-username>/bluetooth-sniffer.git
cd bluetooth-sniffer
pip install -r requirements.txt
```

### Dependencies
- [`bleak`](https://pypi.org/project/bleak/) – for BLE scanning
- [`pybluez2`](https://pypi.org/project/pybluez2/) – for Classic Bluetooth (use `pybluez` on Linux if supported)

> On Linux you may also need Bluetooth headers:
```bash
sudo apt-get install bluetooth libbluetooth-dev python3-dev
```

---

## Usage

Basic BLE scan for 20 seconds:
```bash
python bt_sniffer.py --mode ble --seconds 20 --csv ble_scan.csv
```

Classic Bluetooth scan (Windows/Linux):
```bash
python bt_sniffer.py --mode classic --seconds 25 --json classic_scan.json
```

Scan both BLE & Classic:
```bash
python bt_sniffer.py --mode both --seconds 30 --csv scan.csv --json scan.json
```

Optional flags:
- `--adapter` → Specify adapter name (e.g., `hci0` on Linux)
- `--verbose` → Print live sightings to terminal
- `--json` / `--csv` → Save output files (if not provided, defaults to JSON with timestamp)

---

## Example Output

**JSON (per device):**
```json
{
  "address": "AA:BB:CC:DD:EE:FF",
  "transport": "BLE",
  "name": "Tile Tracker",
  "rssi": -62,
  "tx_power": -4,
  "appearance": 512,
  "connectable": true,
  "address_type": "public",
  "device_class": null,
  "service_uuids": ["0000180f-0000-1000-8000-00805f9b34fb"],
  "service_data": {"feaa": "200104031122"},
  "manufacturer_data": {"76": "1aff7605..."},
  "first_seen": "2025-08-24T23:18:01.123456+00:00",
  "last_seen":  "2025-08-24T23:18:07.987654+00:00",
  "sightings": 5
}
```

---

## Disclaimer
This tool only captures **advertisement and inquiry data** that devices broadcast publicly.  
It does **not** decrypt or intercept private communications.  
Use responsibly and in compliance with your local laws, regulations, and organizational policies.

---

## License
MIT License © 2025 Jeevan Parajuli
