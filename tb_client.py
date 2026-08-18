import time
from datetime import datetime, date, timedelta, timezone, time as time_obj
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

    def get_tenant_customers(self, page_size: int = 1000) -> List[Dict[str, Any]]:
        """Fetch list of all customers for the authenticated tenant."""
        self._ensure_authenticated()
        url = f"{self.host}/api/customers"
        params = {"pageSize": page_size, "page": 0}
        try:
            res = self.session.get(url, params=params, timeout=15)
            if res.status_code != 200:
                url = f"{self.host}/api/tenant/customers"
                res = self.session.get(url, params=params, timeout=15)
            if res.status_code == 200:
                data = res.json()
                return data.get("data", []) if isinstance(data, dict) else data
            else:
                logger.warning(f"Failed to fetch customers: HTTP {res.status_code} - {res.text}")
                return []
        except Exception as e:
            logger.error(f"Error fetching customers: {e}")
            return []

    def find_customer_by_name(self, name_query: str) -> Optional[Dict[str, Any]]:
        """Find customer matching a search query string."""
        customers = self.get_tenant_customers()
        query_upper = name_query.upper().strip()
        for cust in customers:
            title = str(cust.get("title", cust.get("name", ""))).upper()
            if query_upper in title:
                logger.info(f"Found matching ThingsBoard customer for '{name_query}': {cust.get('title')} (ID: {cust.get('id', {}).get('id')})")
                return cust
        return None

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

    def fetch_panel_installation_report(self, customer_id: Optional[str] = None, project_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Fetches Panel Installation Report data for specified customer and project (BBMP or 5B Innovation).
        """
        self._ensure_authenticated()
        
        proj_name = project_name or Config.PROJECT_NAME or "BBMP"
        target_cust_id = customer_id

        if not target_cust_id:
            if "5B" in proj_name.upper() or "INNOVATION" in proj_name.upper():
                target_cust_id = Config.TB_CUSTOMER_ID_5B
                if not target_cust_id:
                    matched_cust = self.find_customer_by_name("5B") or self.find_customer_by_name("Innovation")
                    if matched_cust:
                        target_cust_id = matched_cust.get("id", {}).get("id")
            if not target_cust_id:
                target_cust_id = Config.TB_CUSTOMER_ID
        
        # 1. Fetch devices under customer
        devices = []
        page = 0
        while True:
            url = f"{self.host}/api/customer/{target_cust_id}/deviceInfos?pageSize=1000&page={page}"
            res = None
            for attempt in range(3):
                try:
                    res = self.session.get(url, timeout=60)
                    break
                except Exception as e:
                    logger.warning(f"Attempt {attempt+1} failed to fetch page {page}: {e}")
                    time.sleep(2)
            if not res or res.status_code != 200:
                url = f"{self.host}/api/customer/{target_cust_id}/devices?pageSize=1000&page={page}"
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
                
        ist = timezone(timedelta(hours=5, minutes=30))
        now_dt = datetime.now(ist)
        today_start_dt = datetime(now_dt.year, now_dt.month, now_dt.day, 0, 0, 0, tzinfo=ist)
        today_start_ts_ms = int(today_start_dt.timestamp() * 1000)

        bom_online = 0
        bom_offline = 0
        bom_offline_pf_today = 0
        bom_offline_pf_prior = 0
        bom_total = 0

        east_online = 0
        east_offline = 0
        east_offline_pf_today = 0
        east_offline_pf_prior = 0
        east_total = 0

        other_online = 0
        other_offline = 0
        other_offline_pf_today = 0
        other_offline_pf_prior = 0
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
            "panel_door_open": 0,
            "offline_gt_7_days": 0,
            "offline_pf_gt_7_days": 0
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
            systime_val = None
            pkt_val = None
            pkt_ts = 0
            fault_val = None

            try:
                r_ts = self.session.get(f"{self.host}/api/plugins/telemetry/DEVICE/{dev_id}/values/timeseries?keys=systime,pkt,fault", timeout=5)
                if r_ts.status_code == 200:
                    ts_data = r_ts.json()
                    if isinstance(ts_data, dict):
                        systime_list = ts_data.get("systime")
                        if isinstance(systime_list, list) and len(systime_list) > 0 and isinstance(systime_list[0], dict):
                            systime_val = systime_list[0].get("value")

                        pkt_list = ts_data.get("pkt")
                        if isinstance(pkt_list, list) and len(pkt_list) > 0 and isinstance(pkt_list[0], dict):
                            pkt_entry = pkt_list[0]
                            pkt_val = pkt_entry.get("value")
                            pkt_ts = pkt_entry.get("ts", 0)

                        fault_list = ts_data.get("fault")
                        if isinstance(fault_list, list) and len(fault_list) > 0 and isinstance(fault_list[0], dict):
                            fault_val = fault_list[0].get("value")
                    
                    # EXACT DASHBOARD JAVASCRIPT FORMULA FROM O&M DASHBOARD
                    if str(pkt_val) == "8":
                        dev_issues["power_failure"] = True
                        if pkt_ts >= today_start_ts_ms:
                            status = "OFFLINE_PF_TODAY"
                        else:
                            status = "OFFLINE_PF_PRIOR"
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

            region_attr = ""
            zone_attr = ""
            ward_attr = ""
            slat_attr = ""
            slon_attr = ""
            lat_attr = ""
            lon_attr = ""
            # 2. Fetch region, zoneName, wardName, slatitude, slongitude, latitude, longitude attributes for categorization and report
            try:
                r_attr = self.session.get(f"{self.host}/api/plugins/telemetry/DEVICE/{dev_id}/values/attributes?keys=region,zoneName,wardName,slatitude,slongitude,latitude,longitude,slat,slon,lat,lon", timeout=5)
                if r_attr.status_code == 200:
                    for item in r_attr.json():
                        k = item.get("key")
                        v = item.get("value")
                        if k == "region":
                            region_attr = str(v)
                        elif k == "zoneName":
                            zone_attr = str(v)
                        elif k == "wardName":
                            ward_attr = str(v)
                        elif k in ("slatitude", "slat") and v is not None:
                            slat_attr = str(v)
                        elif k in ("slongitude", "slon") and v is not None:
                            slon_attr = str(v)
                        elif k in ("latitude", "lat") and v is not None:
                            lat_attr = str(v)
                        elif k in ("longitude", "lon") and v is not None:
                            lon_attr = str(v)
                        if k in ("region", "zoneName", "wardName") and v:
                            combined_str += " " + str(v).upper()
            except Exception:
                pass

            # If surveyed slatitude / slongitude not on device attributes, check related ASSET
            if not slat_attr or not slon_attr:
                try:
                    r_rel = self.session.get(f"{self.host}/api/relations/info?toId={dev_id}&toType=DEVICE", timeout=3)
                    if r_rel.status_code == 200:
                        for rel in r_rel.json():
                            if rel.get("from", {}).get("entityType") == "ASSET":
                                aid = rel.get("from", {}).get("id")
                                r_aattr = self.session.get(f"{self.host}/api/plugins/telemetry/ASSET/{aid}/values/attributes?keys=slatitude,slongitude,slat,slon,latitude,longitude", timeout=3)
                                if r_aattr.status_code == 200:
                                    for item in r_aattr.json():
                                        k = item.get("key")
                                        v = item.get("value")
                                        if k in ("slatitude", "slat") and v is not None and not slat_attr:
                                            slat_attr = str(v)
                                        elif k in ("slongitude", "slon") and v is not None and not slon_attr:
                                            slon_attr = str(v)
                                        elif k in ("latitude", "lat") and v is not None and not lat_attr:
                                            lat_attr = str(v)
                                        elif k in ("longitude", "lon") and v is not None and not lon_attr:
                                            lon_attr = str(v)
                                break
                except Exception:
                    pass

            final_lat = slat_attr if slat_attr else lat_attr
            final_lon = slon_attr if slon_attr else lon_attr
            lat_lon_str = f"{final_lat}, {final_lon}" if (final_lat and final_lon) else "-"

            display_region = region_attr if region_attr else (zone_attr if zone_attr else "")
            
            is_bbmp_project = (proj_name == "BBMP")
            is_bom = is_bbmp_project and ("BOMMANAHALLI" in combined_str or "BOMMANAHALI" in combined_str or "BMH" in combined_str)
            is_east = is_bbmp_project and ("EAST" in combined_str or any(kw in combined_str for kw in ["SARVAGNA", "CVRAMAN", "PULAKESHI", "SHIVAJI", "HEBBAL", "SHANTHI"]))

            if is_bom:
                category = "bommanahalli"
                region_name = "Bommanahalli Region"
            elif is_east:
                category = "east"
                region_name = "EAST Region"
            elif display_region:
                category = display_region.lower().replace(" ", "_")
                region_name = display_region.title() if not display_region.isupper() else display_region
            else:
                category = "general"
                region_name = f"{proj_name} Region"

            is_offline_gt_7 = False
            is_offline_pf_gt_7 = False

            # Determine last received timestamp for data date
            last_ts_sec = None
            if status in ("OFFLINE_PF_TODAY", "OFFLINE_PF_PRIOR") and pkt_ts > 0:
                last_ts_sec = pkt_ts / 1000.0
            elif systime_val is not None:
                try:
                    last_ts_sec = float(systime_val)
                except Exception:
                    pass
            if (last_ts_sec is None or last_ts_sec <= 0) and pkt_ts > 0:
                last_ts_sec = pkt_ts / 1000.0

            if last_ts_sec and last_ts_sec > 0:
                last_received_date = datetime.fromtimestamp(last_ts_sec).strftime("%Y-%m-%d %H:%M:%S")
            else:
                last_received_date = "-"

            # Calculate rounded offline duration
            offline_days_str = "-" if status == "ONLINE" else "-"
            if status != "ONLINE":
                if last_ts_sec and last_ts_sec > 0:
                    diff_sec = max(0, now_ts_sec - last_ts_sec)
                    offline_days_val = diff_sec / 86400.0
                    rounded_days = int(round(offline_days_val))
                    if rounded_days == 0:
                        hours = max(1, int(diff_sec // 3600))
                        offline_days_str = f"{hours} Hours"
                    else:
                        offline_days_str = f"{rounded_days} Days"

                    if offline_days_val > 7.0:
                        if status == "OFFLINE":
                            is_offline_gt_7 = True
                        elif status in ("OFFLINE_PF_TODAY", "OFFLINE_PF_PRIOR"):
                            is_offline_pf_gt_7 = True
                else:
                    offline_days_str = "1+ Days" if status == "OFFLINE_PF_PRIOR" else "Today"

            SCREENSHOT_ISSUES_MAP = {
                "low_voltage": "Low Voltage",
                "high_voltage": "High Voltage",
                "high_current": "High Current / Power Theft",
                "low_current": "Low Current",
                "mcb_trip": "MCB Trip",
                "relay_failure": "Relay Failure",
                "meter_comm_failure": "MeterComm Failure"
            }
            active_issues_list = [label for key, label in SCREENSHOT_ISSUES_MAP.items() if dev_issues.get(key)]
            if is_offline_gt_7:
                active_issues_list.append("Offline (>7 Days)")
            if is_offline_pf_gt_7:
                active_issues_list.append("Offline PF (>7 Days)")

            panel_info = {
                "id": dev_id,
                "name": str(dev.get("name", "")),
                "label": str(dev.get("label", "")),
                "region": region_attr if region_attr else region_name,
                "region_name": region_name,
                "zone": zone_attr if zone_attr else "-",
                "ward": ward_attr if ward_attr else "-",
                "status": status,
                "last_received_date": last_received_date,
                "days_offline": offline_days_str,
                "active_issues": active_issues_list,
                "lat_lon": lat_lon_str,
                "dev_issues": dev_issues
            }

            return category, region_name, status, dev_issues, panel_info, is_offline_gt_7, is_offline_pf_gt_7

        logger.info(f"Processing {len(devices)} devices using 30 parallel workers with exact Dashboard formula...")

        affected_panels = []
        offline_gt_7_count = 0
        offline_pf_gt_7_count = 0
        dynamic_regions = {}

        with ThreadPoolExecutor(max_workers=30) as executor:
            futures = [executor.submit(process_device, dev) for dev in devices]
            for future in as_completed(futures):
                category, region_name, status, dev_issues, panel_info, is_off_gt_7, is_off_pf_gt_7 = future.result()

                if is_off_gt_7:
                    offline_gt_7_count += 1
                if is_off_pf_gt_7:
                    offline_pf_gt_7_count += 1

                for k, has_issue in dev_issues.items():
                    if has_issue:
                        issues_summary[k] += 1

                if panel_info["active_issues"]:
                    affected_panels.append(panel_info)

                cat_key = category
                if cat_key not in dynamic_regions:
                    dynamic_regions[cat_key] = {
                        "name": region_name,
                        "online": 0,
                        "offline": 0,
                        "offline_pf_today": 0,
                        "offline_pf_prior": 0,
                        "offline_pf": 0,
                        "total": 0
                    }
                r_stat = dynamic_regions[cat_key]
                r_stat["total"] += 1
                if status == "ONLINE":
                    r_stat["online"] += 1
                elif status == "OFFLINE_PF_TODAY":
                    r_stat["offline_pf_today"] += 1
                elif status == "OFFLINE_PF_PRIOR":
                    r_stat["offline_pf_prior"] += 1
                else:
                    r_stat["offline"] += 1

        for r_stat in dynamic_regions.values():
            r_stat["offline_pf"] = r_stat["offline_pf_today"] + r_stat["offline_pf_prior"]

        combined_online = sum(r["online"] for r in dynamic_regions.values())
        combined_offline = sum(r["offline"] for r in dynamic_regions.values())
        combined_offline_pf_today = sum(r["offline_pf_today"] for r in dynamic_regions.values())
        combined_offline_pf_prior = sum(r["offline_pf_prior"] for r in dynamic_regions.values())
        combined_offline_pf = combined_offline_pf_today + combined_offline_pf_prior
        combined_total = len(devices)

        total_offline_excl_pf = combined_offline
        total_high_current = issues_summary.get("high_current", 0)
        total_mcb_trip = issues_summary.get("mcb_trip", 0)
        total_meter_comm = issues_summary.get("meter_comm_failure", 0)
        total_panels_count = len(devices)

        # Penalty points calculation excluding offline(pf)
        penalty_points = (total_offline_excl_pf * 1) + (total_high_current * 10) + (total_mcb_trip * 5) + (total_meter_comm * 5)
        penalty_pct = (penalty_points / total_panels_count * 100.0) if total_panels_count > 0 else 0.0
        kpi_score = max(0.0, round(100.0 - penalty_pct, 2))

        # Panel Performance Score: (online panels + offline (pf) that occurred today) / total panels * 100
        performance_score = round(((combined_online + combined_offline_pf_today) / combined_total * 100.0), 2) if combined_total > 0 else 0.0

        issues_summary["offline_gt_7_days"] = offline_gt_7_count
        issues_summary["offline_pf_gt_7_days"] = offline_pf_gt_7_count

        regions_list = list(dynamic_regions.values())
        bom_stat = dynamic_regions.get("bommanahalli", {"online": 0, "offline": 0, "offline_pf": 0, "offline_pf_today": 0, "offline_pf_prior": 0, "total": 0})
        east_stat = dynamic_regions.get("east", {"online": 0, "offline": 0, "offline_pf": 0, "offline_pf_today": 0, "offline_pf_prior": 0, "total": 0})

        return {
            "customer": proj_name,
            "project_name": proj_name,
            "performance_score": performance_score,
            "panel_performance_score": performance_score,
            "kpi_score": kpi_score,
            "penalty_points": penalty_points,
            "offline_gt_7_days": offline_gt_7_count,
            "offline_pf_gt_7_days": offline_pf_gt_7_count,
            "regions": regions_list,
            "bommanahalli": bom_stat,
            "east": east_stat,
            "combined": {
                "online": combined_online,
                "offline": combined_offline,
                "offline_pf": combined_offline_pf,
                "offline_pf_today": combined_offline_pf_today,
                "offline_pf_prior": combined_offline_pf_prior,
                "total": combined_total
            },
            "issues": issues_summary,
            "affected_panels": affected_panels,
            "total_panels": len(devices)
        }

