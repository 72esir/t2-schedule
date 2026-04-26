import logging
import smtplib
from dataclasses import dataclass
from datetime import datetime
from email.message import EmailMessage

from backend.core import settings

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class EmailRecipient:
    email: str
    full_name: str | None = None


def send_new_period_notifications(
    *,
    recipients: list[EmailRecipient],
    alliance: str,
    period_start: str,
    period_end: str,
    deadline: datetime,
) -> None:
    if not recipients:
        return

    if not settings.EMAIL_ENABLED:
        logger.info(
            "Email notifications are disabled; skipped new period notification for alliance %s",
            alliance,
        )
        return

    if not settings.EMAIL_FROM or not settings.SMTP_HOST:
        logger.warning(
            "Email notifications are enabled but SMTP is not configured; skipped new period notification for alliance %s",
            alliance,
        )
        return

    deadline_text = _format_deadline(deadline)
    login_url = settings.FRONTEND_APP_URL.rstrip("/")
    subject = "Открыт новый период для заполнения расписания"

    for recipient in recipients:
        greeting_name = recipient.full_name or recipient.email
        body = (
            f"Здравствуйте, {greeting_name}!\n\n"
            f"Для альянса \"{alliance}\" открыт новый период заполнения расписания.\n"
            f"Период: {period_start} - {period_end}\n"
            f"Дедлайн заполнения: {deadline_text}\n\n"
            f"Перейти в систему: {login_url}\n"
        )
        _send_plain_email(
            to_email=recipient.email,
            subject=subject,
            body=body,
        )


def _send_plain_email(*, to_email: str, subject: str, body: str) -> None:
    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = _build_from_header()
    message["To"] = to_email
    message.set_content(body)

    try:
        if settings.SMTP_USE_SSL:
            with smtplib.SMTP_SSL(settings.SMTP_HOST, settings.SMTP_PORT) as smtp:
                _login_if_needed(smtp)
                smtp.send_message(message)
        else:
            with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as smtp:
                smtp.starttls()
                _login_if_needed(smtp)
                smtp.send_message(message)
    except Exception:
        logger.exception("Failed to send email to %s", to_email)


def _login_if_needed(smtp: smtplib.SMTP) -> None:
    if settings.SMTP_USERNAME:
        smtp.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)


def _build_from_header() -> str:
    if settings.EMAIL_FROM_NAME:
        return f"{settings.EMAIL_FROM_NAME} <{settings.EMAIL_FROM}>"
    return settings.EMAIL_FROM


def _format_deadline(deadline: datetime) -> str:
    return deadline.astimezone().strftime("%d.%m.%Y %H:%M")
