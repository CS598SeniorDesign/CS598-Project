"""
Helpers for replaying recorded BGG XML API2 responses in tests.

The files in ``test_data`` are trimmed copies of real responses, so tests exercise real structure without sending
requests to BGG.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import Mock
from xml.etree.ElementTree import Element, tostring

from defusedxml import ElementTree

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


def combined_thing_response(*file_names: str) -> bytes:
    """
    Combine recorded ``/thing`` responses into one, as BGG answers a request for several IDs at once.

    :param file_names: The recorded responses whose items to include, such as ``"thing_catan.xml"``.
    :type file_names: str
    :returns: A single ``<items>`` response body holding every item.
    :rtype: bytes
    """
    combined = Element("items")
    for file_name in file_names:
        combined.extend(ElementTree.fromstring(read_bgg_response(file_name)).findall("item"))
    return tostring(combined)


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
