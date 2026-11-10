from core.email import EmailMessage, get_email_sender
from core.email.console import ConsoleEmailSender


def test_console_backend_is_selected_by_default():
    assert isinstance(get_email_sender(), ConsoleEmailSender)


def test_console_sender_prints_the_message(capsys):
    ConsoleEmailSender().send(
        EmailMessage(to="mom@example.com", subject="Your code", body="123456")
    )

    output = capsys.readouterr().out
    assert "mom@example.com" in output
    assert "Your code" in output
    assert "123456" in output
