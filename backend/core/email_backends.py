"""
Email backends for local development.
"""

from __future__ import annotations

from django.core.mail.backends import console


class ReadableConsoleEmailBackend(console.EmailBackend):
    """
    Print emails to the console as plain text, so links in them can be copied as they are.

    Django's console backend prints the encoded MIME message, which wraps long lines with ``=`` (quoted-printable).
    Copying a verification link from that output gives a broken link, so this prints the decoded plain-text body.
    """

    def write_message(self, message) -> None:
        """
        Write one message's headers and plain-text body to the stream.

        :param message: The email to print.
        :type message: django.core.mail.EmailMessage
        """
        lines = [
            f"From: {message.from_email}",
            f"To: {', '.join(message.to)}",
            f"Subject: {message.subject}",
            "",
            message.body,
        ]
        self.stream.write("\n".join(lines) + "\n")
        self.stream.write("-" * 79 + "\n")
