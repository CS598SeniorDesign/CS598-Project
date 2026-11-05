"""
The only module that sends requests to the BoardGameGeek XML API2.

Every request goes through ``_request_xml``, which spaces requests out across all processes, retries when BGG asks the
caller to slow down or try again later, and parses the response with ``defusedxml``. Callers receive parsed XML or one
of the two errors below, never a ``requests`` exception.

Behavior of the API confirmed against live responses (the documentation does not cover it):

- ``/thing`` accepts at most 20 IDs per request. A 21st ID returns HTTP 400 with a plain-text body, not XML.
- IDs that do not exist, or that do not match the requested types, are left out of the response without an error.
- ``/search`` returns every match in one response (no pages), with only the ID, one name, and the publication year.
- ``/search`` lists every expansion twice: once as ``boardgame`` and once as ``boardgameexpansion``.
- Unranked games (every expansion, and many new games) report their rank as the text ``"Not Ranked"``.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Iterable
from dataclasses import dataclass, replace
from typing import TYPE_CHECKING

import requests
from defusedxml import DTDForbidden, ElementTree, EntitiesForbidden
from django.conf import settings
from django.core.cache import cache

from core.constants import REQUEST_HEADERS
from core.metrics import observe_external_call
from core.utils import get_attribute, parse_optional_integer

if TYPE_CHECKING:
    from xml.etree.ElementTree import Element

logger = logging.getLogger(__name__)

BGG_API_BASE_URL = "https://boardgamegeek.com/xmlapi2"
MAXIMUM_THINGS_PER_REQUEST = 20
BOARD_GAME_ITEM_TYPE = "boardgame"
EXPANSION_ITEM_TYPE = "boardgameexpansion"
CATALOG_ITEM_TYPES = (BOARD_GAME_ITEM_TYPE, EXPANSION_ITEM_TYPE)
REQUEST_TIMEOUT_SECONDS = 15

# 202 means BGG has queued the request and the caller should ask again; 429 means the caller is going too fast.
RETRYABLE_STATUS_CODES = frozenset({202, 429, 500, 502, 503, 504})
MAXIMUM_ATTEMPTS = 3
MAXIMUM_RETRY_DELAY_SECONDS = 30

REQUEST_SLOT_CACHE_KEY = "bgg:request-slot"
REQUEST_SLOT_POLL_SECONDS = 0.25
MAXIMUM_REQUEST_SLOT_WAIT_SECONDS = 30


class BoardGameGeekUnavailableError(Exception):
    """
    BGG could not be reached, refused the request, or kept asking QuestLog to slow down or retry later.

    ``is_retryable`` tells background tasks whether trying again later could succeed: True for timeouts, connection
    failures, rate limiting, and server errors; False when BGG rejected the request itself (for example, an unknown
    username), which would fail the same way again.
    """

    def __init__(self, message: str, *, is_retryable: bool = True, status_code: int | None = None) -> None:
        """
        :param message: What went wrong, for logs.
        :type message: str
        :param is_retryable: Whether the same request could succeed if tried again later.
        :type is_retryable: bool
        :param status_code: The HTTP status BGG last answered with, or None if no response was received.
        :type status_code: int | None
        """
        super().__init__(message)
        self.is_retryable = is_retryable
        self.status_code = status_code


class BoardGameGeekMalformedResponseError(Exception):
    """BGG answered, but the body was not XML that could be parsed safely."""


@dataclass(frozen=True)
class SearchResult:
    """
    One match from a BGG name search.

    :param bgg_id: The game's BoardGameGeek ID.
    :param item_type: ``"boardgame"`` or ``"boardgameexpansion"``.
    :param name: The name that matched the search, which is an alternate name when ``is_primary_name`` is False.
    :param is_primary_name: Whether ``name`` is the game's primary name rather than a translation or alternate title.
    :param year_published: The year the game was published, or None when BGG does not know it.
    """

    bgg_id: int
    item_type: str
    name: str
    is_primary_name: bool
    year_published: int | None


def fetch_things(bgg_ids: Iterable[int]) -> dict[int, Element]:
    """
    Fetch full details and statistics for board games and expansions, 20 IDs per request.

    :param bgg_ids: The BoardGameGeek IDs to fetch. Duplicates are fetched once.
    :type bgg_ids: collections.abc.Iterable[int]
    :returns: Each found ``<item>`` element keyed by its ID. IDs BGG does not know, or that are not board games or
        expansions, are missing from the result.
    :rtype: dict[int, xml.etree.ElementTree.Element]
    :raises BoardGameGeekUnavailableError: If any request fails.
    :raises BoardGameGeekMalformedResponseError: If any response cannot be parsed.
    """

    unique_ids = sorted(set(bgg_ids))
    items_by_id: dict[int, Element] = {}

    for start in range(0, len(unique_ids), MAXIMUM_THINGS_PER_REQUEST):
        batch = unique_ids[start : start + MAXIMUM_THINGS_PER_REQUEST]
        root = _request_xml(
            "thing",
            {"id": ",".join(str(bgg_id) for bgg_id in batch), "type": ",".join(CATALOG_ITEM_TYPES), "stats": 1},
        )

        for item in root.findall("item"):
            item_id = parse_optional_integer(item.get("id"))
            if item_id is not None:
                items_by_id[item_id] = item

    return items_by_id


def search(query: str) -> list[SearchResult]:
    """
    Search BGG for board games and expansions whose primary or alternate name contains the query.

    BGG lists every expansion twice, once as ``boardgame`` and once as ``boardgameexpansion``. Each game is returned
    once, at its first position, and is marked as an expansion if either entry says so.

    :param query: The text to search for.
    :type query: str
    :returns: Every match in the order BGG returned them, each game at most once.
    :rtype: list[catalog.bgg_client.SearchResult]
    :raises BoardGameGeekUnavailableError: If the request fails.
    :raises BoardGameGeekMalformedResponseError: If the response cannot be parsed.
    """

    root = _request_xml("search", {"query": query, "type": ",".join(CATALOG_ITEM_TYPES)})
    results_by_id: dict[int, SearchResult] = {}

    for item in root.findall("item"):
        bgg_id = parse_optional_integer(item.get("id"))
        name = get_attribute(item, "name", "value")
        item_type = item.get("type") or BOARD_GAME_ITEM_TYPE

        if bgg_id is None or not name:
            continue

        if bgg_id in results_by_id:
            if item_type == EXPANSION_ITEM_TYPE:
                results_by_id[bgg_id] = replace(results_by_id[bgg_id], item_type=EXPANSION_ITEM_TYPE)
            continue

        year_published = parse_optional_integer(get_attribute(item, "yearpublished", "value"))
        results_by_id[bgg_id] = SearchResult(
            bgg_id=bgg_id,
            item_type=item_type,
            name=name,
            is_primary_name=get_attribute(item, "name", "type") == "primary",
            year_published=year_published or None,
        )

    return list(results_by_id.values())


def fetch_plays_page(bgg_username: str, page: int) -> Element:
    """
    Fetch one page (up to 100 plays) of a BGG user's logged plays.

    :param bgg_username: The BoardGameGeek username whose plays are fetched. Sent as a query parameter, so it is
        URL-encoded and cannot add parameters of its own.
    :type bgg_username: str
    :param page: The page number, starting at 1.
    :type page: int
    :returns: The ``<plays>`` root element, whose ``total`` attribute is the user's total number of plays.
    :rtype: xml.etree.ElementTree.Element
    :raises BoardGameGeekUnavailableError: If the request fails.
    :raises BoardGameGeekMalformedResponseError: If the response cannot be parsed.
    """

    return _request_xml("plays", {"username": bgg_username, "page": page})


def fetch_collection(bgg_username: str) -> Element:
    """
    Fetch the board games in a BGG user's collection, with their owned/wishlist status and play counts.

    BGG answers HTTP 202 while it prepares a collection it has not built recently; _request_xml retries that a few
    times, and raises BoardGameGeekUnavailableError with ``status_code=202`` if BGG is still preparing it. Expansions
    are excluded (they would otherwise be listed under the boardgame subtype too).

    An unknown username is answered with HTTP 200 and an ``<errors>`` document, which is returned as is for the caller
    to check.

    :param bgg_username: The BoardGameGeek username. Sent as a query parameter, so it is URL-encoded.
    :type bgg_username: str
    :returns: The ``<items>`` root element (or ``<errors>``).
    :rtype: xml.etree.ElementTree.Element
    :raises BoardGameGeekUnavailableError: If the request fails or BGG is still preparing the collection.
    :raises BoardGameGeekMalformedResponseError: If the response cannot be parsed.
    """

    return _request_xml(
        "collection",
        {"username": bgg_username, "subtype": BOARD_GAME_ITEM_TYPE, "excludesubtype": EXPANSION_ITEM_TYPE},
    )


def _request_xml(endpoint: str, parameters: dict[str, str | int]) -> Element:
    """
    Send one GET request to a BGG XML API2 endpoint and parse the response, retrying when BGG asks for it.

    :param endpoint: The endpoint name, such as ``"thing"``.
    :type endpoint: str
    :param parameters: The query parameters to send.
    :type parameters: dict[str, str | int]
    :returns: The root element of the response.
    :rtype: xml.etree.ElementTree.Element
    :raises BoardGameGeekUnavailableError: If the request fails or BGG is still asking to retry after the last attempt.
    :raises BoardGameGeekMalformedResponseError: If the response cannot be parsed.
    """

    url = f"{BGG_API_BASE_URL}/{endpoint}"

    for attempt in range(1, MAXIMUM_ATTEMPTS + 1):
        _wait_for_request_slot()

        try:
            response = _send_measured_request(endpoint, url, parameters)
        except requests.RequestException as error:
            raise BoardGameGeekUnavailableError(f"Request to BGG /{endpoint} failed: {error}") from error
        except _UnsuccessfulStatusError as unsuccessful_status:
            response = unsuccessful_status.response
        else:
            return _parse_xml(response.content, endpoint)

        if response.status_code not in RETRYABLE_STATUS_CODES:
            raise BoardGameGeekUnavailableError(
                f"BGG /{endpoint} returned HTTP {response.status_code}.",
                is_retryable=False,
                status_code=response.status_code,
            )

        if attempt < MAXIMUM_ATTEMPTS:
            delay = _retry_delay_seconds(response, attempt)
            logger.info("BGG /%s returned HTTP %s; retrying in %s s.", endpoint, response.status_code, delay)
            time.sleep(delay)

    raise BoardGameGeekUnavailableError(
        f"BGG /{endpoint} was still unavailable after {MAXIMUM_ATTEMPTS} attempts.", status_code=response.status_code
    )


class _UnsuccessfulStatusError(Exception):
    """Raised inside the metrics block for any response other than 200, so the attempt is counted as an error."""

    def __init__(self, response: requests.Response) -> None:
        """
        :param response: The response whose status was not 200.
        :type response: requests.Response
        """
        super().__init__(f"BGG returned HTTP {response.status_code}.")
        self.response = response


def _send_measured_request(endpoint: str, url: str, parameters: dict[str, str | int]) -> requests.Response:
    """
    Send one GET request, recording its duration and outcome in the external API metrics.

    :param endpoint: The endpoint name, used as the metrics label.
    :type endpoint: str
    :param url: The full endpoint URL.
    :type url: str
    :param parameters: The query parameters to send.
    :type parameters: dict[str, str | int]
    :returns: The response, which always has status 200.
    :rtype: requests.Response
    :raises requests.RequestException: If the request could not be completed.
    :raises _UnsuccessfulStatusError: If BGG answered with any status other than 200.
    """

    with observe_external_call("bgg", endpoint):
        response = requests.get(url=url, params=parameters, headers=REQUEST_HEADERS, timeout=REQUEST_TIMEOUT_SECONDS)
        if response.status_code != 200:
            raise _UnsuccessfulStatusError(response)

    return response


def _parse_xml(content: bytes, endpoint: str) -> Element:
    """
    Parse an XML response body, refusing entity and DTD tricks that could exhaust memory or read local files.

    :param content: The raw response body.
    :type content: bytes
    :param endpoint: The endpoint the body came from, for the error message.
    :type endpoint: str
    :returns: The root element.
    :rtype: xml.etree.ElementTree.Element
    :raises BoardGameGeekMalformedResponseError: If the body is not safe, well-formed XML.
    """

    try:
        return ElementTree.fromstring(content)
    except (ElementTree.ParseError, EntitiesForbidden, DTDForbidden) as error:
        raise BoardGameGeekMalformedResponseError(f"BGG /{endpoint} returned unreadable XML: {error}") from error


def _retry_delay_seconds(response: requests.Response, attempt: int) -> int:
    """
    Decide how long to wait before retrying: BGG's ``Retry-After`` header when it sends one, otherwise doubling waits.

    :param response: The response that asked for a retry.
    :type response: requests.Response
    :param attempt: How many attempts have been made so far, starting at 1.
    :type attempt: int
    :returns: The number of seconds to wait, never more than ``MAXIMUM_RETRY_DELAY_SECONDS``.
    :rtype: int
    """

    requested_delay = parse_optional_integer(response.headers.get("Retry-After"))
    delay = requested_delay if requested_delay is not None and requested_delay > 0 else 2**attempt
    return min(delay, MAXIMUM_RETRY_DELAY_SECONDS)


def _wait_for_request_slot() -> None:
    """
    Wait until QuestLog may send its next BGG request, so requests stay spaced out across every web and worker process.

    A request slot is a short-lived cache key: whichever process adds it first may send a request, and the key expires
    after ``BGG_MINIMUM_SECONDS_BETWEEN_REQUESTS``. A spacing of zero turns the wait off.

    :returns: None
    :raises BoardGameGeekUnavailableError: If no slot becomes free within ``MAXIMUM_REQUEST_SLOT_WAIT_SECONDS``.
    """

    spacing_seconds = settings.BGG_MINIMUM_SECONDS_BETWEEN_REQUESTS
    if spacing_seconds <= 0:
        return

    deadline = time.monotonic() + MAXIMUM_REQUEST_SLOT_WAIT_SECONDS
    while not cache.add(REQUEST_SLOT_CACHE_KEY, True, timeout=spacing_seconds):
        if time.monotonic() >= deadline:
            raise BoardGameGeekUnavailableError("Too many BGG requests are waiting; try again shortly.")
        time.sleep(REQUEST_SLOT_POLL_SECONDS)
