from __future__ import annotations

import logging
import smtplib
from email.message import EmailMessage

from app.core.config import Settings

logger = logging.getLogger(__name__)


class EmailDeliveryError(RuntimeError):
    pass


class EmailService:
    def __init__(self, settings: Settings):
        self.settings = settings

    def send_register_code(self, *, to_email: str, code: str, expires_minutes: int) -> None:
        if self.settings.EMAIL_DEV_MODE:
            logger.warning("Development email verification code for %s: %s", to_email, code)
            return

        required = [
            self.settings.SMTP_HOST,
            self.settings.SMTP_USERNAME,
            self.settings.SMTP_PASSWORD,
            self.settings.SMTP_FROM_EMAIL,
        ]
        if not all(required):
            raise EmailDeliveryError("SMTP is not fully configured")

        message = EmailMessage()
        message["Subject"] = "AI Second Brain 注册验证码"
        message["From"] = self.settings.SMTP_FROM_EMAIL
        message["To"] = to_email
        message.set_content(
            "\n".join(
                [
                    "您好，",
                    "",
                    f"您的 AI Second Brain 注册验证码是：{code}",
                    f"验证码将在 {expires_minutes} 分钟后过期。",
                    "",
                    "如果不是您本人操作，请忽略这封邮件。",
                ]
            )
        )

        try:
            with smtplib.SMTP(self.settings.SMTP_HOST, self.settings.SMTP_PORT, timeout=10) as smtp:
                if self.settings.SMTP_USE_TLS:
                    smtp.starttls()
                smtp.login(self.settings.SMTP_USERNAME, self.settings.SMTP_PASSWORD)
                smtp.send_message(message)
        except Exception as exc:  # noqa: BLE001
            raise EmailDeliveryError(str(exc)) from exc
