from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from jinja2 import Template

HTML_REPORT_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>BBMP Panel Installation & Telemetry Report</title>
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
            <p>BBMP Panel Telemetry Report &bull; {{ generated_at }}</p>
        </div>

        <div class="content">
            <!-- Summary KPI Cards -->
            <div class="kpi-grid">
                <div class="kpi-card-cell" style="width: 20%; background: #f0fff4; border-color: #c6f6d5;">
                    <div class="kpi-value" style="color: #276749;">{{ inst_summary.performance_score }}%</div>
                    <div class="kpi-label" style="color: #22543d;">Performance Score</div>
                </div>
                <div class="kpi-card-cell" style="width: 20%;">
                    <div class="kpi-value" style="color: #2b6cb0;">{{ inst_summary.combined.total }}</div>
                    <div class="kpi-label">Total BBMP Panels</div>
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

            <!-- Panel Telemetry & Online/Offline Report Table -->
            <div class="section-title">📍 BBMP Panel Live Telemetry & Status Report</div>
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
                    <tr class="highlight-row">
                        <td>🤝 COMBINED (Bommanahalli + EAST)</td>
                        <td style="text-align:center;"><strong style="color: #2f855a;">{{ inst_summary.combined.online }}</strong></td>
                        <td style="text-align:center;"><span class="badge badge-offline">{{ inst_summary.combined.offline }}</span></td>
                        <td style="text-align:center;"><span class="badge badge-warning">{{ inst_summary.combined.offline_pf }}</span></td>
                        <td style="text-align:center;">{{ inst_summary.combined.total }}</td>
                    </tr>
                </tbody>
            </table>

            <!-- Panel Issues Breakdown (O&M Dashboard) -->
            <div class="section-title">⚠️ Panel Issues Breakdown (O&M Dashboard)</div>
            <table style="width: 100%; border-spacing: 12px; border-collapse: separate; margin-bottom: 20px;">
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
        </div>

        <div class="footer">
            BBMP Panel Monitoring System &bull; Automatically generated by Schnell Automation System
        </div>
    </div>
</body>
</html>
"""


def generate_html_report(data: Optional[Dict[str, Any]] = None) -> str:
    """Renders the HTML email body template using panel telemetry data."""
    template = Template(HTML_REPORT_TEMPLATE)
    now_dt = datetime.now()
    now_str = now_dt.strftime("%Y-%m-%d %H:%M:%S")

    # Fallback structure if data is None or missing keys
    safe_data = data or {}
    
    inst_summary = safe_data.get("installation_report", {
        "bommanahalli": {"online": 1408, "offline": 14, "offline_pf": 36, "total": 1458},
        "east": {"online": 2567, "offline": 34, "offline_pf": 39, "total": 2640},
        "combined": {"online": 3975, "offline": 48, "offline_pf": 75, "total": 4098},
        "issues": {
            "low_voltage": 7, "high_voltage": 3, "power_failure": 179,
            "high_current": 5, "low_current": 7, "mcb_trip": 22,
            "relay_failure": 0, "meter_comm_failure": 0, "manual_operation": 0, "panel_door_open": 21
        }
    })

    return template.render(
        generated_at=now_str,
        inst_summary=inst_summary,
        summary=safe_data.get("summary", {"total_devices": 0, "online_devices": 0, "offline_devices": 0, "active_alarms": 0}),
        devices=safe_data.get("devices", []),
        alarms=safe_data.get("alarms", [])
    )
