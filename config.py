import os
import logging
from pathlib import Path
from dotenv import load_dotenv

# Set up logging format
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger("BBMP_Panel_Report.Config")

# Load .env file from current directory
env_path = Path(__file__).resolve().parent / ".env"
if env_path.exists():
    load_dotenv(dotenv_path=env_path, override=True)
    logger.info(f"Loaded configuration from {env_path}")
else:
    logger.warning(f".env file not found at {env_path}, using system environment variables or defaults.")


class Config:
    # ThingsBoard Settings
    TB_HOST = os.getenv("THINGSBOARD_HOST", "https://thingsboard.cloud").rstrip("/")
    TB_USERNAME = os.getenv("THINGSBOARD_USERNAME", "").strip()
    TB_PASSWORD = os.getenv("THINGSBOARD_PASSWORD", "").strip()
    TB_ENTITY_TYPE = os.getenv("THINGSBOARD_ENTITY_TYPE", "DEVICE").strip()
    TB_ENTITY_ID = os.getenv("THINGSBOARD_ENTITY_ID", "").strip()
    
    _keys_str = os.getenv("THINGSBOARD_KEYS", "")
    TB_KEYS = [k.strip() for k in _keys_str.split(",") if k.strip()] if _keys_str else []

    # SMTP Email Settings
    SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com").strip()
    SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USE_TLS = os.getenv("SMTP_USE_TLS", "true").lower() in ("true", "1", "yes")
    SMTP_USERNAME = os.getenv("SMTP_USERNAME", "").strip()
    SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "").strip()
    SENDER_EMAIL = os.getenv("SENDER_EMAIL", "").strip() or SMTP_USERNAME
    
    _recipients_str = os.getenv("RECIPIENT_EMAILS", "")
    RECIPIENT_EMAILS = [r.strip() for r in _recipients_str.split(",") if r.strip()]

    EMAIL_SUBJECT_PREFIX = os.getenv("EMAIL_SUBJECT_PREFIX", "[BBMP Panel Report]").strip()
    SCHEDULE_TIME = os.getenv("SCHEDULE_TIME", "08:00").strip()

    @classmethod
    def validate(cls, check_smtp: bool = True, check_tb: bool = True) -> list[str]:
        """Validate critical configuration settings and return list of missing keys."""
        missing = []
        if check_tb:
            if not cls.TB_HOST:
                missing.append("THINGSBOARD_HOST")
            if not cls.TB_USERNAME or cls.TB_USERNAME == "your_thingsboard_email@example.com":
                missing.append("THINGSBOARD_USERNAME")
            if not cls.TB_PASSWORD or cls.TB_PASSWORD == "your_thingsboard_password":
                missing.append("THINGSBOARD_PASSWORD")
        if check_smtp:
            if not cls.SMTP_SERVER:
                missing.append("SMTP_SERVER")
            if not cls.SMTP_USERNAME or cls.SMTP_USERNAME == "your_email@gmail.com":
                missing.append("SMTP_USERNAME")
            if not cls.SMTP_PASSWORD or cls.SMTP_PASSWORD == "your_app_password":
                missing.append("SMTP_PASSWORD")
            if not cls.RECIPIENT_EMAILS or cls.RECIPIENT_EMAILS == ["recipient@example.com"]:
                missing.append("RECIPIENT_EMAILS")
        return missing
