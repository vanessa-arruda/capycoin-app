from .base import EmailMessage


class ConsoleEmailSender:
    """Development sender: prints emails instead of delivering them."""

    def send(self, message: EmailMessage) -> None:
        print(
            f"--- email to {message.to}\nSubject: {message.subject}\n\n"
            f"{message.body}\n---",
            flush=True,
        )
