"""
Helpers for replaying recorded BGG XML API2 responses in tests.

The files in ``test_data`` are trimmed copies of real responses, so tests exercise real structure without sending
requests to BGG.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import Mock

TEST_DATA_DIRECTORY = Path(__file__).parent / "test_data"


def read_bgg_response(file_name: str) -> bytes:
    """
    Read a recorded BGG response from ``test_data``.

    :param file_name: The file name, such as ``"thing_catan.xml"``.
    :type file_name: str
    :returns: The raw response body.
    :rtype: bytes
    """
    return (TEST_DATA_DIRECTORY / file_name).read_bytes()


def bgg_response(content: bytes = b"<items />", status_code: int = 200, headers: dict | None = None) -> Mock:
    """
    Build a stand-in for a ``requests.Response`` from BGG.

    :param content: The response body.
    :type content: bytes
    :param status_code: The HTTP status code.
    :type status_code: int
    :param headers: The response headers.
    :type headers: dict | None
    :returns: A mock with the attributes the BGG client reads.
    :rtype: unittest.mock.Mock
    """
    return Mock(status_code=status_code, content=content, headers=headers or {})
