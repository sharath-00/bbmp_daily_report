import time
import logging
import schedule
from config import Config
from main import run_pipeline

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger("BBMP_Panel_Report.SchedulerService")


def main():
    logger.info("Starting BBMP Panel Automated Scheduler Service...")
    logger.info(f"Report scheduled daily at {Config.SCHEDULE_TIME}")

    # Register daily task
    schedule.every().day.at(Config.SCHEDULE_TIME).do(run_pipeline, dry_run=False, use_mock=False)

    # Run once immediately on start if needed (uncomment next line if desired)
    # run_pipeline(dry_run=False, use_mock=False)

    try:
        while True:
            schedule.run_pending()
            time.sleep(10)
    except KeyboardInterrupt:.
        logger.info("Scheduler service stopped by user.")


if __name__ == "__main__":
    main()
