import os
import json
import smtplib
import logging
import pathlib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from email.utils import make_msgid
from typing import List, Optional
from config import Config

logger = logging.getLogger("BBMP_Panel_Report.MailSender")

STATE_FILE_PATH = pathlib.Path(__file__).resolve().parent / ".email_thread_state.json"


def _format_msg_id(msg_id: str) -> str:
    """Ensures message ID is enclosed in angle brackets."""
    msg_id = msg_id.strip()
    if not msg_id.startswith("<"):
        msg_id = f"<{msg_id}"
    if not msg_id.endswith(">"):
        msg_id = f"{msg_id}>"
    return msg_id


class EmailSender:
    """SMTP Email Sender supporting HTML bodies, attachments, TLS/SSL encryption, and Threaded Emails."""

    def __init__(self,
                 smtp_server: Optional[str] = None,
                 smtp_port: Optional[int] = None,
                 use_tls: Optional[bool] = None,
                 username: Optional[str] = None,
                 password: Optional[str] = None,
                 sender_email: Optional[str] = None,
                 enable_threading: Optional[bool] = None,
                 thread_id: Optional[str] = None):
        self.smtp_server = smtp_server or Config.SMTP_SERVER
        self.smtp_port = smtp_port or Config.SMTP_PORT
        self.use_tls = use_tls if use_tls is not None else Config.SMTP_USE_TLS
        self.username = username or Config.SMTP_USERNAME
        raw_pwd = password or Config.SMTP_PASSWORD
        self.password = raw_pwd.replace(" ", "").strip() if raw_pwd else ""
        self.sender_email = sender_email or Config.SENDER_EMAIL or self.username
        self.enable_threading = enable_threading if enable_threading is not None else Config.ENABLE_EMAIL_THREADING
        self.thread_id = thread_id or Config.EMAIL_THREAD_ID

    def send_email(self,
                   recipients: List[str],
                   subject: str,
                   html_content: str,
                   text_content: Optional[str] = None,
                   attachment_paths: Optional[List[str]] = None,
                   bcc_recipients: Optional[List[str]] = None,
                   enable_threading: Optional[bool] = None,
                   thread_id: Optional[str] = None) -> bool:
        """
        Sends an HTML email to the specified recipient list with optional attachments, BCC recipients, and threading headers.
        """
        if not recipients:
            logger.error("No recipient email addresses provided.")
            return False

        use_threading = enable_threading if enable_threading is not None else self.enable_threading
        active_thread_id = thread_id or self.thread_id

        # Determine domain for Message-ID generation
        domain = None
        if self.sender_email and "@" in self.sender_email:
            domain = self.sender_email.split("@")[-1].strip()

        current_msg_id = make_msgid(domain=domain)

        # Build MIME Message Structure
        default_plain_text = f"Please enable HTML view to see the {subject}."
        if attachment_paths:
            msg = MIMEMultipart("mixed")
            body_part = MIMEMultipart("alternative")
            plain_text = text_content or default_plain_text
            body_part.attach(MIMEText(plain_text, "plain", "utf-8"))
            body_part.attach(MIMEText(html_content, "html", "utf-8"))
            msg.attach(body_part)
        else:
            msg = MIMEMultipart("alternative")
            plain_text = text_content or default_plain_text
            msg.attach(MIMEText(plain_text, "plain", "utf-8"))
            msg.attach(MIMEText(html_content, "html", "utf-8"))

        msg["Subject"] = subject
        msg["From"] = self.sender_email
        msg["To"] = ", ".join(recipients)
        msg["Message-ID"] = current_msg_id

        # Combine TO and BCC recipients for envelope (do NOT add BCC addresses to MIME headers)
        envelope_recipients = list(dict.fromkeys(recipients + (bcc_recipients or [])))

        # Apply Email Threading Headers (RFC 5322 / Outlook / Gmail threading)
        root_msg_id = None
        if use_threading:
            root_msg_id, parent_msg_id = self._get_thread_headers(active_thread_id)
            msg["In-Reply-To"] = parent_msg_id
            if root_msg_id != parent_msg_id:
                msg["References"] = f"{root_msg_id} {parent_msg_id}"
            else:
                msg["References"] = root_msg_id
            
            # Outlook / Exchange Thread-Topic header
            clean_topic = subject
            for prefix in ["[BBMP Panel Report]", "[5B Innovation Panel Report]", "[5B Innovations Panel Report]", "Re:", "RE:", "FWD:", "Fwd:"]:
                clean_topic = clean_topic.replace(prefix, "").strip()
            msg["Thread-Topic"] = clean_topic or subject
            
            logger.info(f"Email Threading Active | In-Reply-To: {parent_msg_id} | References: {msg['References']}")

        # Attachments
        if attachment_paths:
            import mimetypes
            for path in attachment_paths:
                if os.path.isfile(path):
                    try:
                        filename = os.path.basename(path)
                        ctype, encoding = mimetypes.guess_type(path)
                        if ctype is None or encoding is not None:
                            ctype = "application/octet-stream"
                        maintype, subtype = ctype.split("/", 1)

                        with open(path, "rb") as f:
                            part = MIMEBase(maintype, subtype)
                            part.set_payload(f.read())
                        encoders.encode_base64(part)
                        part.add_header(
                            "Content-Disposition",
                            f'attachment; filename="{filename}"',
                        )
                        msg.attach(part)
                        logger.info(f"Attached file: {path} ({ctype})")
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

            server.sendmail(self.sender_email, envelope_recipients, msg.as_string())
            server.quit()
            logger.info(f"Successfully sent email subject '{subject}' to {len(recipients)} TO recipients ({', '.join(recipients)}) and {len(bcc_recipients or [])} BCC recipients.")

            if use_threading and root_msg_id:
                self._save_thread_state(active_thread_id, root_msg_id, current_msg_id)

            return True

        except smtplib.SMTPAuthenticationError as e:
            logger.error(f"SMTP Authentication Failed: Check username/app-password. Error: {e}")
            return False
        except Exception as e:
            logger.error(f"Failed to send email via SMTP: {e}")
            return False

    def _get_thread_headers(self, thread_id: str) -> tuple:
        """
        Retrieves root_msg_id and parent_msg_id for email threading keyed by thread_id.
        """
        formatted_thread_id = _format_msg_id(thread_id)
        if STATE_FILE_PATH.exists():
            try:
                with open(STATE_FILE_PATH, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    t_data = data.get(thread_id, {})
                    if not t_data and "root_msg_id" in data:
                        t_data = data
                    root_id = t_data.get("root_msg_id") or formatted_thread_id
                    last_id = t_data.get("last_msg_id") or formatted_thread_id
                    return _format_msg_id(root_id), _format_msg_id(last_id)
            except Exception as e:
                logger.warning(f"Could not read email thread state file: {e}")
        return formatted_thread_id, formatted_thread_id

    def _save_thread_state(self, thread_id: str, root_msg_id: str, sent_msg_id: str):
        """Saves current thread state per thread_id to local JSON file for continuity across runs."""
        try:
            data = {}
            if STATE_FILE_PATH.exists():
                try:
                    with open(STATE_FILE_PATH, "r", encoding="utf-8") as f:
                        loaded = json.load(f)
                        if isinstance(loaded, dict):
                            data = loaded
                except Exception:
                    data = {}
            
            data[thread_id] = {
                "root_msg_id": root_msg_id,
                "last_msg_id": sent_msg_id
            }
            with open(STATE_FILE_PATH, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            logger.info(f"Updated thread state file for '{thread_id}' with last_msg_id={sent_msg_id}")
        except Exception as e:
            logger.warning(f"Could not write email thread state file: {e}")
