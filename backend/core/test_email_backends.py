from __future__ import annotations

import io

from django.core.mail import EmailMessage

from core.email_backends import ReadableConsoleEmailBackend

LONG_LINK = "http://localhost:3000/account/verify-email/MQ%3A1xP6sH%3A27yZ3WCG-W9nl3drqK1JgJ5fYNRdYhVH7xZR-nTkiZ0"


def test_prints_long_links_on_one_line():
    stream = io.StringIO()
    message = EmailMessage(
        subject="Please Confirm Your Email Address",
        body=f"To confirm this is correct, go to {LONG_LINK}\n",
        from_email="QuestLog <noreply@localhost>",
        to=["player@example.com"],
    )

    sent = ReadableConsoleEmailBackend(stream=stream).send_messages([message])

    output = stream.getvalue()
    assert sent == 1
    assert any(LONG_LINK in line for line in output.splitlines())
    assert "To: player@example.com" in output
    assert "Subject: Please Confirm Your Email Address" in output
