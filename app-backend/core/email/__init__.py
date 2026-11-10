from functools import cache

from core.config import settings

from .base import EmailMessage, EmailSender

__all__ = ["EmailMessage", "EmailSender", "get_email_sender"]


@cache
def get_email_sender() -> EmailSender:
    if settings.email_backend == "console":
        from .console import ConsoleEmailSender

        return ConsoleEmailSender()
    raise ValueError(f"Unknown email backend: {settings.email_backend}")
