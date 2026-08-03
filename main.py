import sys
import time
import argparse
import logging
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
    penalty_pts = inst.get("penalty_points", 0)

    print("\n" + "="*95)
    print(f"⚡ BANGALORE (BBMP) PANEL TELEMETRY REPORT | OVERALL PERFORMANCE SCORE: {perf_score}%")
    print("="*95)
    print(f"{'Region / Zone':<26} | {'Online':<10} | {'Offline':<10} | {'Offline (PF)':<12} | {'Total Panels':<10}")
    print("-" * 95)
    print(f"{'Bommanahalli':<26} | {bom.get('online', 0):<10} | {bom.get('offline', 0):<10} | {bom.get('offline_pf', 0):<12} | {bom.get('total', 0):<10}")
    print(f"{'EAST':<26} | {east.get('online', 0):<10} | {east.get('offline', 0):<10} | {east.get('offline_pf', 0):<12} | {east.get('total', 0):<10}")
    print("-" * 95)
    print(f"{'COMBINED (Bommanahalli+EAST)':<26} | {comb.get('online', 0):<10} | {comb.get('offline', 0):<10} | {comb.get('offline_pf', 0):<12} | {comb.get('total', 0):<10}")
    print("="*95)

    print("\n" + "="*95)
    print(f"⚠️  PANEL ISSUES BREAKDOWN (O&M DASHBOARD) | TOTAL PENALTY POINTS: {penalty_pts}")
    print("="*95)
    print(f"{'Input Issues':<28} | {'Output Issues':<32} | {'Other Issues':<28}")
    print("-" * 95)
    print(f"{'Low Voltage:':<20} {issues.get('low_voltage', 0):<7} | {'High Current / Power Theft:':<26} {issues.get('high_current', 0):<5} | {'Relay Failure:':<20} {issues.get('relay_failure', 0):<7}")
    print(f"{'High Voltage:':<20} {issues.get('high_voltage', 0):<7} | {'Low Current:':<26} {issues.get('low_current', 0):<5} | {'MeterComm Failure:':<20} {issues.get('meter_comm_failure', 0):<7}")
    print(f"{'':<28} | {'MCB Trip:':<26} {issues.get('mcb_trip', 0):<5} | {'':<28}")
    print("="*95 + "\n")


def run_pipeline(dry_run: bool = False, use_mock: bool = False, print_cli: bool = False, output_file: str = "report_preview.html"):
    """
    Main job function: Fetches data, displays terminal summary, generates HTML report, and sends email or saves preview.
    """
    logger.info("=== Starting BBMP Panel Report Job ===")

    # 1. Fetch Data
    if use_mock:
        logger.info("Using mock panel data for report generation.")
        data = {
            "installation_report": {
                "performance_score": 94.81,
                "penalty_points": 213,
                "bommanahalli": {"online": 1408, "offline": 14, "offline_pf": 36, "total": 1458},
                "east": {"online": 2567, "offline": 34, "offline_pf": 39, "total": 2640},
                "combined": {"online": 3975, "offline": 48, "offline_pf": 75, "total": 4098},
                "issues": {
                    "low_voltage": 7, "high_voltage": 3, "power_failure": 179,
                    "high_current": 5, "low_current": 7, "mcb_trip": 22,
                    "relay_failure": 0, "meter_comm_failure": 0, "manual_operation": 0, "panel_door_open": 21
                }
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
    if smtp_missing:
        logger.error(f"Cannot send email. Missing SMTP configuration/secrets: {', '.join(smtp_missing)}")
        logger.error("Please add SMTP_USERNAME, SMTP_PASSWORD, and RECIPIENT_EMAILS into GitHub Repository Secrets or .env file.")
        sys.exit(1)

    mailer = EmailSender()
    subject = f"{Config.EMAIL_SUBJECT_PREFIX} Telemetry Status Report"
    
    success = mailer.send_email(
        recipients=Config.RECIPIENT_EMAILS,
        subject=subject,
        html_content=html_report,
        attachment_paths=None
    )

    if success:
        logger.info("BBMP Panel Report job completed successfully!")
    else:
        logger.error("BBMP Panel Report job encountered email sending errors.")
        sys.exit(1)

    return success


def start_scheduler():
    """Runs a continuous schedule loop based on SCHEDULE_TIME in config."""
    import schedule

    target_time = Config.SCHEDULE_TIME
    logger.info(f"Scheduling daily report job at {target_time}...")
    
    schedule.every().day.at(target_time).do(run_pipeline, dry_run=False, use_mock=False)

    logger.info("Scheduler started. Press Ctrl+C to stop.")
    try:
        while True:
            schedule.run_pending()
            time.sleep(30)
    except KeyboardInterrupt:
        logger.info("Scheduler stopped by user.")


def main():
    parser = argparse.ArgumentParser(description="BBMP ThingsBoard Panel Monitoring & Email Report Tool")
    parser.add_argument("--print", "--cli", action="store_true", help="Fetch data and print summary directly in terminal without sending email")
    parser.add_argument("--dry-run", action="store_true", help="Fetch data and generate report preview without sending emails")
    parser.add_argument("--send-now", action="store_true", help="Fetch data and send email immediately")
    parser.add_argument("--schedule", action="store_true", help="Start background daily scheduler")
    parser.add_argument("--mock", action="store_true", help="Use mock telemetry data for testing")
    parser.add_argument("--output", type=str, default="report_preview.html", help="Local preview output filename")

    args = parser.parse_args()

    if args.schedule:
        start_scheduler()
    elif args.send_now or args.dry_run or args.print or args.mock:
        run_pipeline(dry_run=args.dry_run, use_mock=args.mock, print_cli=args.print, output_file=args.output)
    else:
        # Default behavior if no flags provided: print terminal summary and save preview
        logger.info("No specific flag provided. Displaying terminal summary and saving local preview.")
        run_pipeline(dry_run=True, use_mock=args.mock, print_cli=True, output_file=args.output)


if __name__ == "__main__":
    main()
