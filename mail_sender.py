import os
import smtplib
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from typing import List, Optional
from config import Config

logger = logging.getLogger("BBMP_Panel_Report.MailSender")


class EmailSender:
    """SMTP Email Sender supporting HTML bodies, attachments, and TLS/SSL encryption."""

    def __init__(self,
                 smtp_server: Optional[str] = None,
                 smtp_port: Optional[int] = None,
                 use_tls: Optional[bool] = None,
                 username: Optional[str] = None,
                 password: Optional[str] = None,
                 sender_email: Optional[str] = None):
        self.smtp_server = smtp_server or Config.SMTP_SERVER
        self.smtp_port = smtp_port or Config.SMTP_PORT
        self.use_tls = use_tls if use_tls is not None else Config.SMTP_USE_TLS
        self.username = username or Config.SMTP_USERNAME
        self.password = password or Config.SMTP_PASSWORD
        self.sender_email = sender_email or Config.SENDER_EMAIL or self.username

    def send_email(self,
                   recipients: List[str],
                   subject: str,
                   html_content: str,
                   text_content: Optional[str] = None,
                   attachment_paths: Optional[List[str]] = None) -> bool:
        """
        Sends an HTML email to the specified recipient list with optional attachments.
        """
        if not recipients:
            logger.error("No recipient email addresses provided.")
            return False

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = self.sender_email
        msg["To"] = ", ".join(recipients)

        # Plain text fallback
        plain_text = text_content or "Please enable HTML view to see the BBMP Panel Telemetry Report."
        msg.attach(MIMEText(plain_text, "plain", "utf-8"))

        # HTML Part
        msg.attach(MIMEText(html_content, "html", "utf-8"))

        # Attachments
        if attachment_paths:
            for path in attachment_paths:
                if os.path.isfile(path):
                    try:
                        with open(path, "rb") as f:
                            part = MIMEBase("application", "octet-stream")
                            part.set_payload(f.read())
                        encoders.encode_base64(part)
                        part.add_header(
                            "Content-Disposition",
                            f"attachment; filename={os.path.basename(path)}",
                        )
                        msg.attach(part)
                        logger.info(f"Attached file: {path}")
                    except Exception as e:
                        logger.error(f"Failed to attach file {path}: {e}")
                else:
                    logger.warning(f"Attachment file not found: {path}")

        logger.info(f"Connecting to SMTP server {self.smtp_server}:{self.smtp_port}...")
        try:
            if self.smtp_port == 465:
                # SSL Connection
                server = smtplib.SMTP_SSL(self.smtp_server, self.smtp_port, timeout=20)
            else:
                # Standard Connection with STARTTLS
                server = smtplib.SMTP(self.smtp_server, self.smtp_port, timeout=20)
                if self.use_tls:
                    server.starttls()

            if self.username and self.password:
                server.login(self.username, self.password)

            server.sendmail(self.sender_email, recipients, msg.as_string())
            server.quit()
            logger.info(f"Successfully sent email subject '{subject}' to {len(recipients)} recipients: {', '.join(recipients)}")
            return True

        except smtplib.SMTPAuthenticationError as e:
            logger.error(f"SMTP Authentication Failed: Check username/app-password. Error: {e}")
            return False
        except Exception as e:
            logger.error(f"Failed to send email via SMTP: {e}")
            return False
