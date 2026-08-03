import time
from datetime import datetime, date, timedelta, time as time_obj
import logging
from typing import Dict, Any, List, Optional
import requests
from config import Config

logger = logging.getLogger("BBMP_Panel_Report.TBClient")


class ThingsBoardClient:
    """ThingsBoard REST API Client for authentication, device listing, telemetry, and alarms."""

    def __init__(self, host: Optional[str] = None, username: Optional[str] = None, password: Optional[str] = None):
        self.host = (host or Config.TB_HOST).rstrip("/")
        self.username = username or Config.TB_USERNAME
        self.password = password or Config.TB_PASSWORD
        self.token: Optional[str] = None
        self.session = requests.Session()
        adapter = requests.adapters.HTTPAdapter(pool_connections=35, pool_maxsize=35)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)

    def login(self) -> bool:
        """Authenticate with ThingsBoard REST API and retrieve JWT token."""
        url = f"{self.host}/api/auth/login"
        payload = {
            "username": self.username,
            "password": self.password
        }
        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        
        logger.info(f"Connecting to ThingsBoard at {self.host}...")
        try:
            response = self.session.post(url, json=payload, headers=headers, timeout=15)
            if response.status_code == 200:
                data = response.json()
                self.token = data.get("token")
                self.refresh_token = data.get("refreshToken")
                self.session.headers.update({"X-Authorization": f"Bearer {self.token}"})
                logger.info("Successfully authenticated with ThingsBoard API.")
                return True
            else:
                logger.error(f"Login failed (HTTP {response.status_code}): {response.text}")
                return False
        except Exception as e:
            logger.error(f"Failed to connect to ThingsBoard at {url}: {e}")
            return False

    def _ensure_authenticated(self):
        if not self.token:
            if not self.login():
                raise ConnectionError("Could not authenticate with ThingsBoard API.")

    def get_tenant_devices(self, page_size: int = 100, page: int = 0) -> List[Dict[str, Any]]:
        """Fetch list of tenant devices."""
        self._ensure_authenticated()
        url = f"{self.host}/api/tenant/devices"
        params = {"pageSize": page_size, "page": page}
        try:
            res = self.session.get(url, params=params, timeout=15)
            if res.status_code == 200:
                data = res.json()
                return data.get("data", [])
            else:
                logger.error(f"Failed to fetch tenant devices: HTTP {res.status_code} - {res.text}")
                return []
        except Exception as e:
            logger.error(f"Error fetching tenant devices: {e}")
            return []

    def get_latest_telemetry(self, entity_type: str, entity_id: str, keys: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Fetch latest telemetry values for a given entity (DEVICE, ASSET, etc.).
        Returns dict of {key: [{'ts': timestamp, 'value': val}]}
        """
        self._ensure_authenticated()
        url = f"{self.host}/api/plugins/telemetry/{entity_type}/{entity_id}/values/timeseries"
        params = {}
        if keys:
            params["keys"] = ",".join(keys)
            
        try:
            res = self.session.get(url, params=params, timeout=15)
            if res.status_code == 200:
                return res.json()
            else:
                logger.warning(f"Telemetry request for {entity_type} {entity_id} failed: HTTP {res.status_code}")
                return {}
        except Exception as e:
            logger.error(f"Error fetching telemetry for {entity_id}: {e}")
            return {}

    def get_active_alarms(self, entity_type: Optional[str] = None, entity_id: Optional[str] = None, page_size: int = 100) -> List[Dict[str, Any]]:
        """Fetch active alarms."""
        self._ensure_authenticated()
        url = f"{self.host}/api/alarms"
        params = {"pageSize": page_size, "page": 0, "status": "ACTIVE_UNACK"}
        if entity_type and entity_id:
            url = f"{self.host}/api/alarm/{entity_type}/{entity_id}"
            
        try:
            res = self.session.get(url, params=params, timeout=15)
            if res.status_code == 200:
                data = res.json()
                return data.get("data", []) if isinstance(data, dict) else data
            return []
        except Exception as e:
            logger.error(f"Error fetching alarms: {e}")
            return []

    def fetch_all_panel_data(self, target_entity_id: Optional[str] = None, target_entity_type: str = "DEVICE", keys: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        High-level helper to gather summary data across all panels/devices or a single panel.
        """
        keys_to_fetch = keys or Config.TB_KEYS

        if target_entity_id:
            # Single Device Mode
            telemetry = self.get_latest_telemetry(target_entity_type, target_entity_id, keys=keys_to_fetch)
            alarms = self.get_active_alarms(target_entity_type, target_entity_id)
            parsed_telemetry = {k: v[0]["value"] if v else None for k, v in telemetry.items()}
            return {
                "summary": {
                    "total_devices": 1,
                    "online_devices": 1 if parsed_telemetry.get("active") != "false" else 0,
                    "offline_devices": 1 if parsed_telemetry.get("active") == "false" else 0,
                    "active_alarms": len(alarms)
                },
                "devices": [{
                    "id": target_entity_id,
                    "name": f"Panel-{target_entity_id[:8]}",
                    "type": target_entity_type,
                    "telemetry": parsed_telemetry,
                    "alarms": alarms
                }]
            }
        else:
            # Multi-Device Mode (All Tenant Devices)
            devices = self.get_tenant_devices()
            device_reports = []
            online_count = 0
            offline_count = 0
            total_alarms = 0

            now_dt = datetime.now()
            today_start_ts = int(datetime.combine(now_dt.date(), time_obj.min).timestamp() * 1000)
            week_start_ts = today_start_ts - (7 * 24 * 60 * 60 * 1000)

            installed_today_count = 0
            installed_week_count = 0

            for dev in devices:
                dev_id = dev.get("id", {}).get("id")
                dev_name = dev.get("name", "Unknown Device")
                dev_label = dev.get("label", dev_name)
                dev_type = dev.get("type", "Light Panel")
                created_ts = dev.get("createdTime", 0)

                if created_ts >= today_start_ts:
                    installed_today_count += 1
                if created_ts >= week_start_ts:
                    installed_week_count += 1

                if dev_id:
                    telemetry = self.get_latest_telemetry("DEVICE", dev_id, keys=keys_to_fetch)
                    parsed_telemetry = {}
                    for k, vals in telemetry.items():
                        if vals and isinstance(vals, list) and len(vals) > 0:
                            parsed_telemetry[k] = vals[0].get("value")

                    # Check online status
                    active_val = str(parsed_telemetry.get("active", "true")).lower()
                    is_online = active_val not in ("false", "0", "offline")
                    if is_online:
                        online_count += 1
                    else:
                        offline_count += 1

                    device_reports.append({
                        "id": dev_id,
                        "name": dev_name,
                        "label": dev_label,
                        "type": dev_type,
                        "is_online": is_online,
                        "telemetry": parsed_telemetry
                    })

            alarms = self.get_active_alarms()
            total_alarms = len(alarms)

            return {
                "summary": {
                    "total_devices": len(devices),
                    "online_devices": online_count,
                    "offline_devices": offline_count,
                    "installed_today": installed_today_count,
                    "installed_this_week": installed_week_count,
                    "active_alarms": total_alarms
                },
                "devices": device_reports,
                "alarms": alarms
            }

    def fetch_panel_installation_report(self, customer_id: str = "e2119df0-45c3-11f0-94dc-77130b2f47e9") -> Dict[str, Any]:
        """
        Fetches exact Panel Installation Report data for Customer Bangalore (BBMP)
        filtering for Bommanahalli and East regions.
        """
        self._ensure_authenticated()
        
        # 1. Fetch devices under customer
        devices = []
        page = 0
        while True:
            url = f"{self.host}/api/customer/{customer_id}/deviceInfos?pageSize=1000&page={page}"
            res = None
            for attempt in range(3):
                try:
                    res = self.session.get(url, timeout=60)
                    break
                except Exception as e:
                    logger.warning(f"Attempt {attempt+1} failed to fetch page {page}: {e}")
                    time.sleep(2)
            if not res or res.status_code != 200:
                url = f"{self.host}/api/customer/{customer_id}/devices?pageSize=1000&page={page}"
                for attempt in range(3):
                    try:
                        res = self.session.get(url, timeout=60)
                        break
                    except Exception as e:
                        logger.warning(f"Attempt {attempt+1} failed to fetch fallback page {page}: {e}")
                        time.sleep(2)
            if res and res.status_code == 200:
                data = res.json()
                devs = data.get("data", [])
                devices.extend(devs)
                if not data.get("hasNext", False) or len(devs) == 0:
                    break
                page += 1
            else:
                break
                
        bom_online = 0
        bom_offline = 0
        bom_offline_pf = 0
        bom_total = 0

        east_online = 0
        east_offline = 0
        east_offline_pf = 0
        east_total = 0

        other_online = 0
        other_offline = 0
        other_offline_pf = 0
        other_total = 0
        now_ts_sec = time.time()
        THRESHOLD_SEC = 14400  # 4 Hours (14,400s)

        issues_summary = {
            "low_voltage": 0,
            "high_voltage": 0,
            "power_failure": 0,
            "high_current": 0,
            "low_current": 0,
            "mcb_trip": 0,
            "relay_failure": 0,
            "meter_comm_failure": 0,
            "manual_operation": 0,
            "panel_door_open": 0
        }

        def decode_fault_alerts(fault_val):
            if not fault_val:
                return set()
            try:
                fault_int = int(fault_val)
            except Exception:
                return set()
            
            fault_types = [
                'RVL','RVH','YVL','YVH','BVL','BVH',
                'RCL','RCH','YCL','YCH','BCL','BCH',
                'RPL','RPH','YPL','YPH','BPL','BPH',
                'MTR','RTC','RIC','YIC','BIC','ROC',
                'YOC','BOC','TPR','RCF','YCF','BCF',
                'MCB','BPS','EARL','CURR','NEUD','TEMR',
                'MTRC','REL','PWR','MR','TOD','LIV','OVR','SERVO',
                'PREV','res','res','res','res','res','MODR'
            ]
            
            alerts = set()
            for i in range(len(fault_types)):
                if (fault_int >> i) & 1:
                    alerts.add(fault_types[i])
            return alerts

        from concurrent.futures import ThreadPoolExecutor, as_completed

        def process_device(dev):
            dev_id = dev.get("id", {}).get("id")
            
            # Extract group names, dev name, dev label
            groups = dev.get("groups", [])
            group_names = [g.get("name", "").upper() for g in groups if isinstance(g, dict)]
            group_str = " ".join(group_names)
            
            dev_name = str(dev.get("name", "")).upper()
            dev_label = str(dev.get("label", "")).upper()
            combined_str = f"{group_str} {dev_name} {dev_label}"
            
            status = "OFFLINE"  # Default
            dev_issues = {
                "low_voltage": False,
                "high_voltage": False,
                "power_failure": False,
                "high_current": False,
                "low_current": False,
                "mcb_trip": False,
                "relay_failure": False,
                "meter_comm_failure": False,
                "manual_operation": False,
                "panel_door_open": False
            }
            
            # 1. Fetch exact dashboard timeseries keys (systime, pkt, fault) for 100% dashboard match
            try:
                r_ts = self.session.get(f"{self.host}/api/plugins/telemetry/DEVICE/{dev_id}/values/timeseries?keys=systime,pkt,fault", timeout=5)
                if r_ts.status_code == 200:
                    ts_data = r_ts.json()
                    systime_val = ts_data.get("systime", [{}])[0].get("value") if "systime" in ts_data else None
                    pkt_val = ts_data.get("pkt", [{}])[0].get("value") if "pkt" in ts_data else None
                    fault_val = ts_data.get("fault", [{}])[0].get("value") if "fault" in ts_data else None
                    
                    # EXACT DASHBOARD JAVASCRIPT FORMULA FROM O&M DASHBOARD
                    if str(pkt_val) == "8":
                        status = "OFFLINE_PF"
                        dev_issues["power_failure"] = True
                    elif systime_val is not None:
                        try:
                            sys_sec = float(systime_val)
                            if (now_ts_sec - sys_sec) < THRESHOLD_SEC:
                                status = "ONLINE"
                            else:
                                status = "OFFLINE"
                        except Exception:
                            pass

                    alerts = decode_fault_alerts(fault_val)
                    dev_issues["low_voltage"] = bool(alerts & {"RVL", "YVL", "BVL"})
                    dev_issues["high_voltage"] = bool(alerts & {"RVH", "YVH", "BVH"})
                    dev_issues["high_current"] = bool(alerts & {"RCH", "YCH", "BCH"})
                    dev_issues["low_current"] = bool(alerts & {"RCL", "YCL", "BCL"})
                    dev_issues["mcb_trip"] = "MCB" in alerts
                    dev_issues["relay_failure"] = bool(alerts & {"RCF", "YCF", "BCF"})
                    dev_issues["meter_comm_failure"] = "MTR" in alerts
                    dev_issues["manual_operation"] = "BPS" in alerts
                    dev_issues["panel_door_open"] = "TPR" in alerts
            except Exception:
                pass

            # 2. Fetch region, zoneName, wardName attributes for categorization
            try:
                r_attr = self.session.get(f"{self.host}/api/plugins/telemetry/DEVICE/{dev_id}/values/attributes?keys=region,zoneName,wardName", timeout=5)
                if r_attr.status_code == 200:
                    for item in r_attr.json():
                        k = item.get("key")
                        v = item.get("value")
                        if k in ("region", "zoneName", "wardName") and v:
                            combined_str += " " + str(v).upper()
            except Exception:
                pass

            is_bom = "BOMMANAHALLI" in combined_str or "BOMMANAHALI" in combined_str or "BMH" in combined_str
            is_east = "EAST" in combined_str or any(kw in combined_str for kw in ["SARVAGNA", "CVRAMAN", "PULAKESHI", "SHIVAJI", "HEBBAL", "SHANTHI"])

            category = "other"
            if is_bom:
                category = "bommanahalli"
            elif is_east:
                category = "east"

            return category, status, dev_issues

        logger.info(f"Processing {len(devices)} devices using 30 parallel workers with exact Dashboard formula...")

        with ThreadPoolExecutor(max_workers=30) as executor:
            futures = [executor.submit(process_device, dev) for dev in devices]
            for future in as_completed(futures):
                category, status, dev_issues = future.result()

                for k, has_issue in dev_issues.items():
                    if has_issue:
                        issues_summary[k] += 1

                if category == "bommanahalli":
                    bom_total += 1
                    if status == "ONLINE":
                        bom_online += 1
                    elif status == "OFFLINE_PF":
                        bom_offline_pf += 1
                    else:
                        bom_offline += 1
                elif category == "east":
                    east_total += 1
                    if status == "ONLINE":
                        east_online += 1
                    elif status == "OFFLINE_PF":
                        east_offline_pf += 1
                    else:
                        east_offline += 1
                else:
                    other_total += 1
                    if status == "ONLINE":
                        other_online += 1
                    elif status == "OFFLINE_PF":
                        other_offline_pf += 1
                    else:
                        other_offline += 1

        total_offline = (bom_offline + bom_offline_pf) + (east_offline + east_offline_pf) + (other_offline + other_offline_pf)
        total_high_current = issues_summary.get("high_current", 0)
        total_mcb_trip = issues_summary.get("mcb_trip", 0)
        total_meter_comm = issues_summary.get("meter_comm_failure", 0)
        total_panels_count = len(devices)

        penalty_points = (total_offline * 1) + (total_high_current * 10) + (total_mcb_trip * 5) + (total_meter_comm * 5)
        penalty_pct = (penalty_points / total_panels_count * 100.0) if total_panels_count > 0 else 0.0
        performance_score = max(0.0, round(100.0 - penalty_pct, 2))

        return {
            "customer": "Bangalore (BBMP)",
            "performance_score": performance_score,
            "penalty_points": penalty_points,
            "bommanahalli": {"online": bom_online, "offline": bom_offline, "offline_pf": bom_offline_pf, "total": bom_total},
            "east": {"online": east_online, "offline": east_offline, "offline_pf": east_offline_pf, "total": east_total},
            "combined": {
                "online": bom_online + east_online,
                "offline": bom_offline + east_offline,
                "offline_pf": bom_offline_pf + east_offline_pf,
                "total": bom_total + east_total
            },
            "issues": issues_summary,
            "total_panels": len(devices)
        }

