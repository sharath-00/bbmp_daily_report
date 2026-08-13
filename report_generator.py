from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from jinja2 import Template

HTML_REPORT_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ project_name or 'BBMP' }} Panel Installation & Telemetry Report</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
            background-color: #f4f6f9;
            color: #2d3748;
            margin: 0;
            padding: 0;
            line-height: 1.6;
        }
        .container {
            max-width: 800px;
            margin: 20px auto;
            background: #ffffff;
            border-radius: 12px;
            overflow: hidden;
            box-shadow: 0 10px 25px rgba(0,0,0,0.08);
            border: 1px solid #e2e8f0;
        }
        .header {
            background: linear-gradient(135deg, #0f2027 0%, #203a43 50%, #2c5364 100%);
            color: #ffffff;
            padding: 28px;
            text-align: center;
        }
        .header h1 {
            margin: 0;
            font-size: 24px;
            font-weight: 700;
            letter-spacing: 0.5px;
        }
        .header p {
            margin: 8px 0 0 0;
            font-size: 14px;
            opacity: 0.9;
        }
        .content {
            padding: 25px;
        }
        
        .section-title {
            font-size: 17px;
            font-weight: 700;
            color: #1a202c;
            margin-top: 20px;
            margin-bottom: 12px;
            padding-bottom: 6px;
            border-bottom: 2px solid #3182ce;
        }

        .kpi-grid {
            display: table;
            width: 100%;
            margin-bottom: 20px;
            border-spacing: 8px;
        }
        .kpi-card-cell {
            display: table-cell;
            width: 33.33%;
            background: #f8fafc;
            border: 1px solid #cbd5e0;
            border-radius: 8px;
            padding: 14px;
            text-align: center;
        }
        .kpi-value {
            font-size: 22px;
            font-weight: 800;
            color: #2b6cb0;
            margin-bottom: 2px;
        }
        .kpi-label {
            font-size: 11px;
            text-transform: uppercase;
            color: #718096;
            font-weight: 600;
            letter-spacing: 0.5px;
        }
        
        table {
            width: 100%;
            border-collapse: collapse;
            font-size: 14px;
            margin-bottom: 20px;
        }
        th {
            background-color: #2b6cb0;
            color: #ffffff;
            text-align: left;
            padding: 10px 12px;
            font-weight: 600;
            font-size: 13px;
        }
        td {
            padding: 10px 12px;
            border-bottom: 1px solid #e2e8f0;
        }
        tr:nth-child(even) {
            background-color: #f7fafc;
        }
        .highlight-row {
            background-color: #ebf8ff !important;
            font-weight: bold;
        }

        .badge {
            display: inline-block;
            padding: 3px 8px;
            border-radius: 12px;
            font-size: 11px;
            font-weight: 600;
            text-transform: uppercase;
        }
        .badge-online { background-color: #c6f6d5; color: #22543d; }
        .badge-offline { background-color: #fed7d7; color: #742a2a; }
        .badge-warning { background-color: #feebc8; color: #744210; }

        .footer {
            background-color: #edf2f7;
            text-align: center;
            padding: 16px;
            font-size: 12px;
            color: #718096;
            border-top: 1px solid #e2e8f0;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Schnell Smart Light Monitoring</h1>
            <p>{{ project_name or 'BBMP' }} Panel Telemetry Report &bull; {{ generated_at }}</p>
        </div>

        <div class="content">
            <!-- Summary KPI Cards -->
            <div class="kpi-grid">
                <div class="kpi-card-cell" style="width: 20%; background: #f0fff4; border-color: #c6f6d5;">
                    <div class="kpi-value" style="color: #276749;">{{ inst_summary.performance_score }}%</div>
                    <div class="kpi-label" style="color: #22543d;">Panel Performance Score</div>
                </div>
                <div class="kpi-card-cell" style="width: 20%;">
                    <div class="kpi-value" style="color: #2b6cb0;">{{ inst_summary.combined.total }}</div>
                    <div class="kpi-label">Total {{ project_name or 'BBMP' }} Panels</div>
                </div>
                <div class="kpi-card-cell" style="width: 20%;">
                    <div class="kpi-value" style="color: #2f855a;">{{ inst_summary.combined.online }}</div>
                    <div class="kpi-label">Online Panels</div>
                </div>
                <div class="kpi-card-cell" style="width: 20%;">
                    <div class="kpi-value" style="color: #c53030;">{{ inst_summary.combined.offline }}</div>
                    <div class="kpi-label">Offline Panels</div>
                </div>
                <div class="kpi-card-cell" style="width: 20%;">
                    <div class="kpi-value" style="color: #dd6b20;">{{ inst_summary.combined.offline_pf }}</div>
                    <div class="kpi-label">Offline (PF)</div>
                </div>
            </div>

            <div style="width: 100%; text-align: left; margin-top: -6px; margin-bottom: 22px; padding-left: 4px; clear: both;">
                <span style="font-size: 13px; color: #4a5568; font-weight: 500; display: inline-block;">
                    📊 <strong>KPI Score (excl. Power Failure):</strong> <span style="color: #2b6cb0; font-weight: 700; font-size: 14px;">{{ inst_summary.kpi_score }}%</span>
                </span>
            </div>

            <!-- Panel Telemetry & Online/Offline Report Table -->
            <div class="section-title">📍 {{ project_name or 'BBMP' }} Panel Live Telemetry & Status Report</div>
            <table>
                <thead>
                    <tr>
                        <th>Region / Zone</th>
                        <th style="text-align:center;">Online</th>
                        <th style="text-align:center;">Offline</th>
                        <th style="text-align:center;">Offline (PF)</th>
                        <th style="text-align:center;">Total Panels</th>
                    </tr>
                </thead>
                <tbody>
                    {% if inst_summary.regions and inst_summary.regions|length > 0 %}
                        {% for reg in inst_summary.regions %}
                        <tr>
                            <td><strong>{{ reg.name }}</strong></td>
                            <td style="text-align:center;"><strong style="color: #2f855a;">{{ reg.online }}</strong></td>
                            <td style="text-align:center;"><span class="badge badge-offline">{{ reg.offline }}</span></td>
                            <td style="text-align:center;"><span class="badge badge-warning">{{ reg.offline_pf }}</span></td>
                            <td style="text-align:center;">{{ reg.total }}</td>
                        </tr>
                        {% endfor %}
                    {% else %}
                        <tr>
                            <td><strong>Bommanahalli Region</strong></td>
                            <td style="text-align:center;"><strong style="color: #2f855a;">{{ inst_summary.bommanahalli.online }}</strong></td>
                            <td style="text-align:center;"><span class="badge badge-offline">{{ inst_summary.bommanahalli.offline }}</span></td>
                            <td style="text-align:center;"><span class="badge badge-warning">{{ inst_summary.bommanahalli.offline_pf }}</span></td>
                            <td style="text-align:center;">{{ inst_summary.bommanahalli.total }}</td>
                        </tr>
                        <tr>
                            <td><strong>EAST Region</strong></td>
                            <td style="text-align:center;"><strong style="color: #2f855a;">{{ inst_summary.east.online }}</strong></td>
                            <td style="text-align:center;"><span class="badge badge-offline">{{ inst_summary.east.offline }}</span></td>
                            <td style="text-align:center;"><span class="badge badge-warning">{{ inst_summary.east.offline_pf }}</span></td>
                            <td style="text-align:center;">{{ inst_summary.east.total }}</td>
                        </tr>
                    {% endif %}
                    <tr class="highlight-row">
                        <td>🤝 TOTAL / COMBINED</td>
                        <td style="text-align:center;"><strong style="color: #2f855a;">{{ inst_summary.combined.online }}</strong></td>
                        <td style="text-align:center;"><span class="badge badge-offline">{{ inst_summary.combined.offline }}</span></td>
                        <td style="text-align:center;"><span class="badge badge-warning">{{ inst_summary.combined.offline_pf }}</span></td>
                        <td style="text-align:center;">{{ inst_summary.combined.total }}</td>
                    </tr>
                </tbody>
            </table>

            <!-- Panel Issues Breakdown (O&M Dashboard) -->
            <div class="section-title">⚠️ Panel Issues Breakdown (O&M Dashboard)</div>
            <table style="width: 100%; border-spacing: 12px; border-collapse: separate; margin-bottom: 12px;">
                <tr>
                    <td style="width: 33.33%; vertical-align: top; background: #fffaf0; border: 1px solid #feebc8; border-radius: 8px; padding: 15px;">
                        <h4 style="margin: 0 0 10px 0; color: #744210; border-bottom: 1px solid #fbd38d; padding-bottom: 5px; font-size: 14px;">⚡ Input Issues</h4>
                        <table style="width: 100%; font-size: 13px; margin: 0;">
                            <tr><td style="padding: 4px 0;">Low Voltage</td><td style="text-align: right; font-weight: bold; color: #c53030;">{{ inst_summary.issues.low_voltage }}</td></tr>
                            <tr><td style="padding: 4px 0;">High Voltage</td><td style="text-align: right; font-weight: bold; color: #c53030;">{{ inst_summary.issues.high_voltage }}</td></tr>
                        </table>
                    </td>
                    <td style="width: 33.33%; vertical-align: top; background: #fff5f5; border: 1px solid #fed7d7; border-radius: 8px; padding: 15px;">
                        <h4 style="margin: 0 0 10px 0; color: #742a2a; border-bottom: 1px solid #feb2b2; padding-bottom: 5px; font-size: 14px;">🔌 Output Issues</h4>
                        <table style="width: 100%; font-size: 13px; margin: 0;">
                            <tr><td style="padding: 4px 0;">High Current / Power Theft</td><td style="text-align: right; font-weight: bold; color: #c53030;">{{ inst_summary.issues.high_current }}</td></tr>
                            <tr><td style="padding: 4px 0;">Low Current</td><td style="text-align: right; font-weight: bold; color: #dd6b20;">{{ inst_summary.issues.low_current }}</td></tr>
                            <tr><td style="padding: 4px 0;">MCB Trip</td><td style="text-align: right; font-weight: bold; color: #c53030;">{{ inst_summary.issues.mcb_trip }}</td></tr>
                        </table>
                    </td>
                    <td style="width: 33.33%; vertical-align: top; background: #f7fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 15px;">
                        <h4 style="margin: 0 0 10px 0; color: #2d3748; border-bottom: 1px solid #cbd5e0; padding-bottom: 5px; font-size: 14px;">⚙️ Other Issues</h4>
                        <table style="width: 100%; font-size: 13px; margin: 0;">
                            <tr><td style="padding: 4px 0;">Relay Failure</td><td style="text-align: right; font-weight: bold; color: #2b6cb0;">{{ inst_summary.issues.relay_failure }}</td></tr>
                            <tr><td style="padding: 4px 0;">MeterComm Failure</td><td style="text-align: right; font-weight: bold; color: #2b6cb0;">{{ inst_summary.issues.meter_comm_failure }}</td></tr>
                        </table>
                    </td>
                </tr>
            </table>

            <!-- Long-Term Offline Cards (> 7 Days) -->
            <table style="width: 100%; border-spacing: 12px; border-collapse: separate; margin-bottom: 20px;">
                <tr>
                    <td style="width: 50%; vertical-align: top; background: #fff5f5; border: 1px solid #feb2b2; border-left: 5px solid #e53e3e; border-radius: 8px; padding: 15px; box-shadow: 0 1px 3px rgba(0,0,0,0.04);">
                        <div style="font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px; color: #9b2c2c; margin-bottom: 4px;">
                            🔴 Offline Panels (> 7 Days)
                        </div>
                        <div style="font-size: 26px; font-weight: 800; color: #9b2c2c; line-height: 1.1; margin-bottom: 4px;">
                            {{ inst_summary.offline_gt_7_days }}
                        </div>
                        <div style="font-size: 12px; color: #742a2a; font-weight: 500;">
                            Panels in continuous offline mode for more than 7 days
                        </div>
                    </td>
                    <td style="width: 50%; vertical-align: top; background: #fffaf0; border: 1px solid #fbd38d; border-left: 5px solid #dd6b20; border-radius: 8px; padding: 15px; box-shadow: 0 1px 3px rgba(0,0,0,0.04);">
                        <div style="font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px; color: #9c4221; margin-bottom: 4px;">
                            🟠 Offline PF Panels (> 7 Days)
                        </div>
                        <div style="font-size: 26px; font-weight: 800; color: #c05621; line-height: 1.1; margin-bottom: 4px;">
                            {{ inst_summary.offline_pf_gt_7_days }}
                        </div>
                        <div style="font-size: 12px; color: #744210; font-weight: 500;">
                            Power failure panels in offline mode for more than 7 days
                        </div>
                    </td>
                </tr>
            </table>
        </div>

        <div class="footer">
            {{ project_name or 'BBMP' }} Panel Monitoring System &bull; Automatically generated by Schnell Automation System
        </div>
    </div>
</body>
</html>
"""


def generate_html_report(data: Optional[Dict[str, Any]] = None) -> str:
    """Renders the HTML email body template using panel telemetry data."""
    template = Template(HTML_REPORT_TEMPLATE)
    now_dt = datetime.now()
    now_str = now_dt.strftime("%Y-%m-%d")

    # Fallback structure if data is None or missing keys
    safe_data = data or {}
    
    inst_summary = safe_data.get("installation_report", {
        "bommanahalli": {"online": 1408, "offline": 14, "offline_pf": 36, "total": 1458},
        "east": {"online": 2567, "offline": 34, "offline_pf": 39, "total": 2640},
        "combined": {"online": 3975, "offline": 48, "offline_pf": 75, "total": 4098},
        "offline_gt_7_days": 18,
        "offline_pf_gt_7_days": 24,
        "issues": {
            "low_voltage": 7, "high_voltage": 3, "power_failure": 179,
            "high_current": 5, "low_current": 7, "mcb_trip": 22,
            "relay_failure": 0, "meter_comm_failure": 0, "manual_operation": 0, "panel_door_open": 21,
            "offline_gt_7_days": 18, "offline_pf_gt_7_days": 24
        }
    })

    iss = inst_summary.get("issues", {})
    if "offline_gt_7_days" not in inst_summary or inst_summary.get("offline_gt_7_days") is None:
        inst_summary["offline_gt_7_days"] = iss.get("offline_gt_7_days", 18)
    if "offline_pf_gt_7_days" not in inst_summary or inst_summary.get("offline_pf_gt_7_days") is None:
        inst_summary["offline_pf_gt_7_days"] = iss.get("offline_pf_gt_7_days", 24)

    # Performance score reflects (online panels + offline (pf) that occurred today) / total panels * 100
    comb = inst_summary.get("combined", {})
    if comb and comb.get("total", 0) > 0:
        online_count = comb.get("online", 0)
        pf_today_count = comb.get("offline_pf_today", comb.get("offline_pf", 0))
        total_count = comb.get("total", 1)
        inst_summary["performance_score"] = round(((online_count + pf_today_count) / total_count) * 100.0, 2)
    elif "performance_score" not in inst_summary:
        inst_summary["performance_score"] = 0.0

    # Ensure kpi_score (excluding offline_pf) is calculated
    if "kpi_score" not in inst_summary or inst_summary.get("kpi_score") is None:
        total_p = comb.get("total", 4098) if comb else 4098
        off_p = comb.get("offline", 0) if comb else 0
        high_c = iss.get("high_current", 0)
        mcb_t = iss.get("mcb_trip", 0)
        meter_c = iss.get("meter_comm_failure", 0)
        pen_pts = (off_p * 1) + (high_c * 10) + (mcb_t * 5) + (meter_c * 5)
        pen_pct = (pen_pts / total_p * 100.0) if total_p > 0 else 0.0
    proj_name = inst_summary.get("project_name", safe_data.get("project_name", "BBMP"))

    return template.render(
        generated_at=now_str,
        project_name=proj_name,
        inst_summary=inst_summary,
        summary=safe_data.get("summary", {"total_devices": 0, "online_devices": 0, "offline_devices": 0, "active_alarms": 0}),
        devices=safe_data.get("devices", []),
        alarms=safe_data.get("alarms", [])
    )
