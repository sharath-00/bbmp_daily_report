import sys
import io
import json
from config import Config
from tb_client import ThingsBoardClient

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

client = ThingsBoardClient()
if not client.login():
    sys.exit(1)

BBMP_CUSTOMER_ID = "e2119df0-45c3-11f0-94dc-77130b2f47e9"

res = client.session.get(f"{client.host}/api/customer/{BBMP_CUSTOMER_ID}/deviceInfos?pageSize=50&page=0", timeout=15)
devs = res.json().get("data", [])

print("Inspecting Comm Status attributes for sample BBMP devices...")

comm_status_keys = {}

for dev in devs:
    dev_id = dev.get("id", {}).get("id")
    res_attr = client.session.get(f"{client.host}/api/plugins/telemetry/DEVICE/{dev_id}/values/attributes", timeout=5)
    if res_attr.status_code == 200:
        for item in res_attr.json():
            k = item.get("key")
            v = str(item.get("value"))
            if any(term in k.lower() or term in v.lower() for term in ["comm", "relay", "pf", "power", "status"]):
                comm_status_keys[f"{k}:{v}"] = comm_status_keys.get(f"{k}:{v}", 0) + 1

print("\nFound Comm / Relay Status attributes:")
for k, v in comm_status_keys.items():
    print(f"  • {k} (count: {v})")
