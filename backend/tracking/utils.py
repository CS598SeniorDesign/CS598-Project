import defusedxml.ElementTree as ElementTree
import requests
from django.contrib.auth.models import User
from django.db import transaction
from typing import TYPE_CHECKING

from core.constants import VALID_STATUS_CODES, REQUEST_HEADERS
from tracking.models import PlaySession

if TYPE_CHECKING:
    from xml.etree.ElementTree import Element


def fetch_bgg_plays(user: User, bgg_username: str) -> tuple[bool, str]:
    fetch_url: str = f"https://boardgamegeek.com/xmlapi2/plays?username={bgg_username}"
    response: requests.Response = requests.get(url=fetch_url, headers=REQUEST_HEADERS, timeout=10)

    if response.status_code not in VALID_STATUS_CODES:
        return False, f"Failed to reach BGG API. Status: {response.status_code}"

    # XML Root should be 'plays'
    response_root: Element = ElementTree.fromstring(response.content)
    sessions_created: int = 0

    with transaction.atomic():
        for play in response_root.findall('play'):
            PlaySession.create_from_xml(play, user, bgg_username)

            sessions_created += 1

    return True, f"Successfully imported {sessions_created} plays."
