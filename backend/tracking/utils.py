import requests
import defusedxml.ElementTree as ElementTree
from datetime import datetime
from django.db import transaction

from core.constants import VALID_STATUS_CODES, REQUEST_HEADERS
from catalog.utils import get_existing_board_game


def fetch_bgg_plays(user: str, bgg_username: str) -> tuple[bool, str]:
    fetch_url: str = f"https://boardgamegeek.com/xmlapi2/plays?username={bgg_username}"
    response: requests.Response = requests.get(url=fetch_url, headers=REQUEST_HEADERS, timeout=10)

    if response.status_code not in VALID_STATUS_CODES:
        return False, f"Failed to reach BGG API. Status: {response.status_code}"

    # XML Root should be 'plays'
    response_root: ElementTree.Element[str] = ElementTree.fromstring(response.content)

    sessions_created: int = 0
    for play in response_root.findall('play'):
        pass
        extracted_date: datetime = datetime.strptime(play.attrib.get("date"), "%Y-%m-%d").date()
        print(extracted_date)

        length_in_minutes: int = int(play.attrib.get("length"))
        print(length_in_minutes)

        game_item: ElementTree.Element[str] = play.find("item")
        game_object_type: str = game_item.attrib.get("objecttype")
        game_object_id: int = int(game_item.attrib.get("objectid"))

        print(game_object_type)
        print(game_object_id)

        get_existing_board_game(game_object_id)

        # TODO: open a transaction block `with transaction.atomic():`

        # TODO: create the PlaySession w/ null group

        # TODO: find the <players> tag and loop loop through its <player> tags
        # TODO: create the SessionPlayer linked to the PlaySession and the user

        sessions_created += 1

    return True, f"Successfully imported {sessions_created} plays."
