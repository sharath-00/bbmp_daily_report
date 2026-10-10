import sys
import io
import time
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from config import Config
from tb_client import ThingsBoardClient

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

client = ThingsBoardClient()
if not client.login():
    print("Failed to authenticate with ThingsBoard.")
    sys.exit(1)

BBMP_CUSTOMER_ID = "e2119df0-45c3-11f0-94dc-77130b2f47e9"

print("Fetching all devices under Customer Bangalore (BBMP)...")

bbmp_devices = []
page = 0
while True:
    url = f"{client.host}/api/customer/{BBMP_CUSTOMER_ID}/deviceInfos?pageSize=1000&page={page}"
    res = client.session.get(url, timeout=20)
    if res.status_code != 200:
        url = f"{client.host}/api/customer/{BBMP_CUSTOMER_ID}/devices?pageSize=1000&page={page}"
        res = client.session.get(url, timeout=20)
        
    if res.status_code == 200:
        data = res.json()
        devs = data.get("data", [])
        bbmp_devices.extend(devs)
        if not data.get("hasNext", False) or len(devs) == 0:
            break
        page += 1
    else:
        break

print(f"Retrieved {len(bbmp_devices)} BBMP devices. Checking online/offline status using 30 parallel workers...")

# Define East sub-zones
EAST_SUBZONES = [
    "sarvagnanagar", "cvramannagar", "pulakeshinagar", "shivajinagar", 
    "hebbal", "shanthinagar", "east", "cvrn", "sn", "pn", "svjr", "heb", "sntr"
]

def check_device_status(dev):
    dev_id = dev.get("id", {}).get("id")
    dev_name = dev.get("name", "")
    dev_label = dev.get("label", "")
    
    region = "OTHER"
    zone_name = ""
    ward_name = ""
    is_active = False

    try:
        res_attr = client.session.get(f"{client.host}/api/plugins/telemetry/DEVICE/{dev_id}/values/attributes", timeout=5)
        if res_attr.status_code == 200:
            for item in res_attr.json():
                k = item.get("key")
                v = item.get("value")
                if k == "active":
                    is_active = (str(v).lower() in ("true", "1", "online"))
                elif k == "region":
                    region = str(v).upper()
                elif k == "zoneName":
                    zone_name = str(v)
                elif k == "wardName":
                    ward_name = str(v)
    except Exception:
        pass

    is_bom = "BOMMANAHALLI" in region or "BOMMANAHALI" in region or "BMH" in zone_name.upper() or "BMH" in ward_name.upper()
    is_east = "EAST" in region or any(kw in zone_name.upper() for kw in ["SARVAGNA", "CVRAMAN", "PULAKESHI", "SHIVAJI", "HEBBAL", "SHANTHI"])

    category = "other"
    if is_bom:
        category = "bommanahalli"
    elif is_east:
        category = "east"

    return category, is_active

stats = {
    "bommanahalli": {"online": 0, "offline": 0, "total": 0},
    "east": {"online": 0, "offline": 0, "total": 0},
    "other": {"online": 0, "offline": 0, "total": 0}
}

with ThreadPoolExecutor(max_workers=30) as executor:
    futures = [executor.submit(check_device_status, dev) for dev in bbmp_devices]
    for future in as_completed(futures):
        category, is_active = future.result()
        stats[category]["total"] += 1
        if is_active:
            stats[category]["online"] += 1
        else:
            stats[category]["offline"] += 1

print("\n" + "="*85)
print(f"⚡ BANGALORE (BBMP) PANEL ONLINE / OFFLINE STATUS REPORT")
print(f" Execution Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("="*85)
print(f"{'Region / Zone':<28} | {'Online Panels':<16} | {'Offline Panels':<16} | {'Total Panels':<12}")
print("-" * 85)

bom = stats["bommanahalli"]
east = stats["east"]
oth = stats["other"]

tot_online = bom["online"] + east["online"] + oth["online"]
tot_offline = bom["offline"] + east["offline"] + oth["offline"]
tot_panels = len(bbmp_devices)

print(f"{'Bommanahalli Region':<28} | {bom['online']:<16} | {bom['offline']:<16} | {bom['total']:<12}")
print(f"{'EAST Region':<28} | {east['online']:<16} | {east['offline']:<16} | {east['total']:<12}")
print("-" * 85)
print(f"{'COMBINED (Bommanahalli+EAST)':<28} | {bom['online']+east['online']:<16} | {bom['offline']+east['offline']:<16} | {bom['total']+east['total']:<12}")
print(f"{'GRAND TOTAL BBMP':<28} | {tot_online:<16} | {tot_offline:<16} | {tot_panels:<12}")
print("="*85 + "\n")
