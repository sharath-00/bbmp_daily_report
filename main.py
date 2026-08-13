import sys
import time
import argparse
import logging
from typing import List, Optional
from datetime import datetime
from pathlib import Path

from config import Config
from tb_client import ThingsBoardClient
from report_generator import generate_html_report
from mail_sender import EmailSender

logger = logging.getLogger("BBMP_Panel_Report.Main")


def get_mock_panel_data():
    """Generates realistic mock data for testing and preview purposes."""
    return {
        "summary": {
            "total_devices": 5,
            "online_devices": 4,
            "offline_devices": 1,
            "active_alarms": 1
        },
        "devices": [
            {
                "id": "dev-001",
                "name": "Panel-BBMP-Ward-101",
                "label": "MG Road Sector 4",
                "type": "Smart Street Light Panel",
                "is_online": True,
                "telemetry": {
                    "active": "true",
                    "voltage": "230.4 V",
                    "current": "12.5 A",
                    "power": "2880 W",
                    "status": "NORMAL"
                }
            },
            {
                "id": "dev-002",
                "name": "Panel-BBMP-Ward-102",
                "label": "Indiranagar 100ft Rd",
                "type": "Smart Street Light Panel",
                "is_online": True,
                "telemetry": {
                    "active": "true",
                    "voltage": "228.1 V",
                    "current": "15.2 A",
                    "power": "3467 W",
                    "status": "NORMAL"
                }
            },
            {
                "id": "dev-003",
                "name": "Panel-BBMP-Ward-103",
                "label": "Koramangala 80ft Rd",
                "type": "Smart Street Light Panel",
                "is_online": False,
                "telemetry": {
                    "active": "false",
                    "voltage": "0 V",
                    "current": "0 A",
                    "power": "0 W",
                    "status": "OFFLINE"
                }
            },
            {
                "id": "dev-004",
                "name": "Panel-BBMP-Ward-104",
                "label": "HSR Layout Sector 1",
                "type": "Smart Street Light Panel",
                "is_online": True,
                "telemetry": {
                    "active": "true",
                    "voltage": "232.0 V",
                    "current": "11.0 A",
                    "power": "2552 W",
                    "status": "NORMAL"
                }
            },
            {
                "id": "dev-005",
                "name": "Panel-BBMP-Ward-105",
                "label": "Whitefield Main Rd",
                "type": "Smart Street Light Panel",
                "is_online": True,
                "telemetry": {
                    "active": "true",
                    "voltage": "210.5 V",
                    "current": "18.0 A",
                    "power": "3789 W",
                    "status": "LOW_VOLTAGE_WARN"
                }
            }
        ],
        "alarms": [
            {
                "type": "LOW_VOLTAGE_ALARM",
                "severity": "CRITICAL",
                "originatorName": "Panel-BBMP-Ward-105",
                "createdTime": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
        ]
    }


import sys
import io

# Force UTF-8 output encoding for Windows terminals
if hasattr(sys.stdout, 'buffer'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')


def print_terminal_summary(data):
    inst = data.get("installation_report", {})
    bom = inst.get("bommanahalli", {"online": 0, "offline": 0, "offline_pf": 0, "total": 0})
    east = inst.get("east", {"online": 0, "offline": 0, "offline_pf": 0, "total": 0})
    comb = inst.get("combined", {"online": 0, "offline": 0, "offline_pf": 0, "total": 0})
    issues = inst.get("issues", {})
    perf_score = inst.get("performance_score", 0.0)
    kpi_score = inst.get("kpi_score", 0.0)
    penalty_pts = inst.get("penalty_points", 0)

    print("\n" + "="*110)
    print(f"⚡ BANGALORE (BBMP) PANEL TELEMETRY REPORT | PANEL PERFORMANCE SCORE: {perf_score}% | KPI SCORE (excl. PF): {kpi_score}%")
    print(" (Performance Formula: (Online + Offline PF Today) / Total Panels)")
    print("="*110)
    print(f"{'Region / Zone':<26} | {'Online':<8} | {'Offline':<8} | {'PF (Today)':<12} | {'PF (Prior)':<12} | {'Total Panels':<10}")
    print("-" * 110)
    print(f"{'Bommanahalli':<26} | {bom.get('online', 0):<8} | {bom.get('offline', 0):<8} | {bom.get('offline_pf_today', 0):<12} | {bom.get('offline_pf_prior', 0):<12} | {bom.get('total', 0):<10}")
    print(f"{'EAST':<26} | {east.get('online', 0):<8} | {east.get('offline', 0):<8} | {east.get('offline_pf_today', 0):<12} | {east.get('offline_pf_prior', 0):<12} | {east.get('total', 0):<10}")
    print("-" * 110)
    print(f"{'COMBINED (Bommanahalli+EAST)':<26} | {comb.get('online', 0):<8} | {comb.get('offline', 0):<8} | {comb.get('offline_pf_today', 0):<12} | {comb.get('offline_pf_prior', 0):<12} | {comb.get('total', 0):<10}")
    print("="*110)

    print("\n" + "="*95)
    print(f"⚠️  PANEL ISSUES BREAKDOWN (O&M DASHBOARD) | TOTAL PENALTY POINTS: {penalty_pts}")
    print("="*95)
    print(f"{'Input Issues':<28} | {'Output Issues':<32} | {'Other Issues':<28}")
    print("-" * 95)
    print(f"{'Low Voltage:':<20} {issues.get('low_voltage', 0):<7} | {'High Current / Power Theft:':<26} {issues.get('high_current', 0):<5} | {'Relay Failure:':<20} {issues.get('relay_failure', 0):<7}")
    print(f"{'High Voltage:':<20} {issues.get('high_voltage', 0):<7} | {'Low Current:':<26} {issues.get('low_current', 0):<5} | {'MeterComm Failure:':<20} {issues.get('meter_comm_failure', 0):<7}")
    print(f"{'':<28} | {'MCB Trip:':<26} {issues.get('mcb_trip', 0):<5} | {'':<28}")
    print("-" * 95)
    print(f"🚨 LONG-TERM OFFLINE BREAKDOWN (> 7 DAYS):")
    print(f"  • Offline Panels (> 7 Days):    {inst.get('offline_gt_7_days', issues.get('offline_gt_7_days', 0))}")
    print(f"  • Offline PF Panels (> 7 Days): {inst.get('offline_pf_gt_7_days', issues.get('offline_pf_gt_7_days', 0))}")
    print("="*95 + "\n")


import csv

import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter


def export_panel_issues_to_csv(data: dict, output_csv: str = "panel_issues_details.csv") -> str:
    """Exports granular breakdown of panels with specific dashboard issues to CSV."""
    inst = data.get("installation_report", {})
    affected_panels = inst.get("affected_panels", [])
    csv_path = Path(__file__).resolve().parent / output_csv
    
    fieldnames = ["Device ID", "Panel Name", "Panel Label", "Region", "Zone Name", "Ward Name", "Status", "Active Issues"]
    
    exported_count = 0
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(fieldnames)
        for p in affected_panels:
            active_issues = p.get("active_issues", [])
            if not active_issues:
                continue
            writer.writerow([
                p.get("id", ""),
                p.get("name", ""),
                p.get("label", ""),
                p.get("region", ""),
                p.get("zone", ""),
                p.get("ward", ""),
                p.get("status", ""),
                ", ".join(active_issues)
            ])
            exported_count += 1
            
    logger.info(f"Exported detailed panel issues ({exported_count} panels) to {csv_path}")
    return str(csv_path)


def export_panel_issues_to_excel(data: dict, output_excel: str = "panel_issues_details.xlsx") -> str:
    """Exports granular breakdown of panels into separate Excel tabs per region (Bommanahalli, East)."""
    inst = data.get("installation_report", {})
    affected_panels = inst.get("affected_panels", [])
    excel_path = Path(__file__).resolve().parent / output_excel

    wb = openpyxl.Workbook()
    # Remove default sheet
    default_sheet = wb.active
    wb.remove(default_sheet)

    # Filter panels by region
    bom_panels = []
    east_panels = []
    other_panels = []

    for p in affected_panels:
        if not p.get("active_issues"):
            continue
        reg_upper = str(p.get("region", "")).upper()
        if "BOMMANAHALLI" in reg_upper or "BOMMANAHALI" in reg_upper or "BMH" in reg_upper:
            bom_panels.append(p)
        elif "EAST" in reg_upper:
            east_panels.append(p)
        else:
            other_panels.append(p)

    # Header Style (Dark Blue Fill with Bold White Text)
    header_fill = PatternFill(start_color="2B6CB0", end_color="2B6CB0", fill_type="solid")
    header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    header_alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

    # Thin Grid Border
    thin_side = Side(style="thin", color="CBD5E0")
    thin_border = Border(left=thin_side, right=thin_side, top=thin_side, bottom=thin_side)

    # Data Style
    data_font = Font(name="Calibri", size=10)
    data_alignment = Alignment(horizontal="left", vertical="center")

    fieldnames = ["Panel Name", "Panel Label", "Region", "Zone Name", "Ward Name", "Status", "Days Offline", "Active Issues"]

    def create_region_sheet(title, panels):
        ws = wb.create_sheet(title=title)
        ws.append(fieldnames)

        # Format Headers
        for col_idx, header_cell in enumerate(ws[1], start=1):
            header_cell.fill = header_fill
            header_cell.font = header_font
            header_cell.alignment = header_alignment
            header_cell.border = thin_border
        ws.row_dimensions[1].height = 25

        row_idx = 2
        for p in panels:
            ws.append([
                p.get("name", ""),
                p.get("label", ""),
                p.get("region", ""),
                p.get("zone", ""),
                p.get("ward", ""),
                p.get("status", ""),
                p.get("days_offline", "-"),
                ", ".join(p.get("active_issues", []))
            ])
            for col_idx, cell in enumerate(ws[row_idx], start=1):
                cell.font = data_font
                cell.border = thin_border
                if col_idx in (3, 6, 7): # Region, Status & Days Offline centered
                    cell.alignment = Alignment(horizontal="center", vertical="center")
                else:
                    cell.alignment = data_alignment
            ws.row_dimensions[row_idx].height = 20
            row_idx += 1

        # Auto-adjust column widths
        for col in ws.columns:
            max_len = max(len(str(cell.value or '')) for cell in col)
            col_letter = get_column_letter(col[0].column)
            ws.column_dimensions[col_letter].width = max(max_len + 4, 12)

    # Create sheets for Bommanahalli and East
    create_region_sheet("Bommanahalli", bom_panels)
    create_region_sheet("East", east_panels)
    if other_panels:
        create_region_sheet("Other Regions", other_panels)

    wb.save(excel_path)
    logger.info(f"Exported detailed panel issues (Bommanahalli: {len(bom_panels)}, East: {len(east_panels)}) to Excel: {excel_path}")
    return str(excel_path)


def run_pipeline(dry_run: bool = False, use_mock: bool = False, print_cli: bool = False, output_file: str = "report_preview.html", override_recipients: Optional[List[str]] = None):
    """
    Main job function: Fetches data, displays terminal summary, generates HTML report, exports issue details Excel, and sends email or saves preview.
    """
    logger.info("=== Starting BBMP Panel Report Job ===")

    recipients_to_use = override_recipients or Config.RECIPIENT_EMAILS

    # 1. Fetch Data
    if use_mock:
        logger.info("Using mock panel data for report generation.")
        data = {
            "installation_report": {
                "performance_score": 98.83,
                "kpi_score": 94.92,
                "penalty_points": 208,
                "offline_gt_7_days": 18,
                "offline_pf_gt_7_days": 24,
                "bommanahalli": {"online": 1408, "offline": 14, "offline_pf": 36, "total": 1458},
                "east": {"online": 2567, "offline": 34, "offline_pf": 39, "total": 2640},
                "combined": {"online": 3975, "offline": 48, "offline_pf": 75, "total": 4098},
                "issues": {
                    "low_voltage": 7, "high_voltage": 3, "power_failure": 179,
                    "high_current": 5, "low_current": 7, "mcb_trip": 22,
                    "relay_failure": 0, "meter_comm_failure": 0, "manual_operation": 0, "panel_door_open": 21,
                    "offline_gt_7_days": 18, "offline_pf_gt_7_days": 24
                },
                "affected_panels": [
                    {"id": "dev-101", "name": "Panel-BBMP-BMH-001", "label": "Silk Board Flyover", "region": "BOMMANAHALLI", "zone": "Bommanahalli", "ward": "HSR Ward 174", "status": "ONLINE", "days_offline": "-", "active_issues": ["Low Voltage"]},
                    {"id": "dev-102", "name": "Panel-BBMP-BMH-002", "label": "Koramangala 100ft", "region": "BOMMANAHALLI", "zone": "Bommanahalli", "ward": "Koramangala Ward 151", "status": "OFFLINE", "days_offline": "3 Days", "active_issues": ["High Voltage"]},
                    {"id": "dev-103", "name": "Panel-BBMP-EST-005", "label": "MG Road Metro", "region": "EAST", "zone": "East", "ward": "Shanthi Nagar Ward 111", "status": "OFFLINE_PF_PRIOR", "days_offline": "5 Days", "active_issues": ["High Current / Power Theft"]},
                    {"id": "dev-104", "name": "Panel-BBMP-EST-012", "label": "Indiranagar 12th Main", "region": "EAST", "zone": "East", "ward": "CV Raman Ward 88", "status": "ONLINE", "days_offline": "-", "active_issues": ["MCB Trip"]}
                ]
            },
            "summary": {"total_devices": 4098, "online_devices": 3975, "offline_devices": 123, "active_alarms": 0}
        }
    else:
        tb_missing = Config.validate(check_smtp=False, check_tb=True)
        if tb_missing:
            logger.warning(f"Missing ThingsBoard credentials ({', '.join(tb_missing)}). Falling back to mock data.")
            data = get_mock_panel_data()
        else:
            tb_client = ThingsBoardClient()
            if tb_client.login():
                logger.info("Fetching Panel Installation Report for Customer Bangalore (BBMP)...")
                inst_report = tb_client.fetch_panel_installation_report()
                alarms = tb_client.get_active_alarms()
                data = {
                    "installation_report": inst_report,
                    "alarms": alarms,
                    "summary": {
                        "total_devices": inst_report.get("total_panels", 4003),
                        "online_devices": 0,
                        "offline_devices": 0,
                        "active_alarms": len(alarms)
                    }
                }
            else:
                logger.error("Failed to authenticate with ThingsBoard. Falling back to mock data.")
                data = get_mock_panel_data()

    # Always print terminal summary table
    print_terminal_summary(data)

    # Export detailed issues to Excel (.xlsx)
    excel_file_path = export_panel_issues_to_excel(data)

    # 2. Generate HTML Report
    logger.info("Generating HTML report...")
    html_report = generate_html_report(data)

    # 3. Always save a local preview file
    preview_path = Path(__file__).resolve().parent / output_file
    with open(preview_path, "w", encoding="utf-8") as f:
        f.write(html_report)
    logger.info(f"Report saved to local file: {preview_path}")

    # 4. Handle Email Sending or Dry Run / CLI mode
    if dry_run or print_cli:
        logger.info("DRY-RUN / PRINT Mode: Email sending skipped. You can open 'report_preview.html' in your browser to view the formatted report.")
        return True

    # Validate SMTP configuration before sending
    smtp_missing = Config.validate(check_smtp=True, check_tb=False)
    if smtp_missing and not override_recipients:
        logger.error(f"Cannot send email. Missing SMTP configuration/secrets: {', '.join(smtp_missing)}")
        logger.error("Please add SMTP_USERNAME, SMTP_PASSWORD, and RECIPIENT_EMAILS into GitHub Repository Secrets or .env file.")
        sys.exit(1)

    if not recipients_to_use:
        logger.error("No recipient email address available. Use --to your_email@domain.com or set RECIPIENT_EMAILS in .env")
        sys.exit(1)

    mailer = EmailSender(
        enable_threading=Config.ENABLE_EMAIL_THREADING,
        thread_id=Config.EMAIL_THREAD_ID
    )
    subject = f"{Config.EMAIL_SUBJECT_PREFIX} Telemetry Status Report"
    
    # Attach Excel sheet to outgoing email
    attachments_to_send = [excel_file_path]

    logger.info(f"Sending email report to: {', '.join(recipients_to_use)}")
    success = mailer.send_email(
        recipients=recipients_to_use,
        subject=subject,
        html_content=html_report,
        attachment_paths=attachments_to_send,
        enable_threading=Config.ENABLE_EMAIL_THREADING,
        thread_id=Config.EMAIL_THREAD_ID
    )

    if success:
        logger.info("BBMP Panel Report job completed successfully!")
    else:
        logger.error("BBMP Panel Report job encountered email sending errors.")
        sys.exit(1)

    return success


def main():
    parser = argparse.ArgumentParser(description="BBMP ThingsBoard Panel Monitoring & Email Report Tool")
    parser.add_argument("--print", "--cli", action="store_true", help="Fetch data and print summary directly in terminal without sending email")
    parser.add_argument("--dry-run", action="store_true", help="Fetch data and generate report preview without sending emails")
    parser.add_argument("--send-now", action="store_true", help="Fetch data and send email immediately")
    parser.add_argument("--mock", action="store_true", help="Use mock telemetry data for testing")
    parser.add_argument("--to", "--recipient", type=str, help="Override recipient email address(es), comma-separated")
    parser.add_argument("--output", type=str, default="report_preview.html", help="Local preview output filename")

    args = parser.parse_args()

    override_recipients = None
    if args.to:
        override_recipients = [r.strip() for r in args.to.split(",") if r.strip()]

    # If --mock is used without --send-now, default dry_run to True so mock data doesn't send email
    dry_run_mode = args.dry_run
    if args.mock and not args.send_now:
        dry_run_mode = True

    if args.send_now or args.dry_run or args.print or args.mock:
        run_pipeline(dry_run=dry_run_mode, use_mock=args.mock, print_cli=args.print, output_file=args.output, override_recipients=override_recipients)
    else:
        # Default behavior if no flags provided: print terminal summary and save preview without sending email
        logger.info("No specific flag provided. Displaying terminal summary and saving local preview.")
        run_pipeline(dry_run=True, use_mock=args.mock, print_cli=True, output_file=args.output, override_recipients=override_recipients)


if __name__ == "__main__":
    main()
