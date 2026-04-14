import requests
import xml.etree.ElementTree as ElementTree
from datetime import datetime
from django.conf import settings

from catalog.models import BoardGame

VALID_STATUS_CODES = [200, 202]
BGG_TOKEN = settings.BGG_API_TOKEN
REQUEST_HEADERS: dict[str, str] = {
    "User-Agent": "QuestLog/0.1",
    "Authorization": f"Bearer {BGG_TOKEN}"
}


def test():
    id = 246900
    get_bgg_board_game(id)


def get_bgg_board_game(bgg_id: int) -> BoardGame:
    fetch_url: str = f"https://boardgamegeek.com/xmlapi2/thing?id={bgg_id}"
    response: requests.Response = requests.get(url=fetch_url, headers=REQUEST_HEADERS)
    print(response.status_code)
    response_root: ElementTree.Element = ElementTree.fromstring(response.content)

    # TODO: parse xml response to find the primary name and year published
    for item in response_root.findall("item"):
        primary_name: ElementTree.Element[str] = item.find('name[@type="primary"]')
        print(primary_name.attrib.get("value"))
    # TODO: create a new BoardGame record or use fallback name if API failes
    # TODO: return the BoardGame instance


def get_existing_board_game(bgg_id: int, fallback_name: str) -> BoardGame:
    existing_board_game: BoardGame = BoardGame.objects.get(bgg_id=bgg_id)

    if existing_board_game:
        return existing_board_game
    else:
        get_bgg_board_game(bgg_id=bgg_id)


def fetch_bgg_plays(user: str, bgg_username: str) -> tuple[bool, str]:
    fetch_url: str = f"https://boardgamegeek.com/xmlapi2/plays?username={bgg_username}"

    response: requests.Response = requests.get(url=fetch_url, headers=REQUEST_HEADERS)

    if response.status_code not in VALID_STATUS_CODES:
        return False, f"Failed to reach BGG API. Status: {response.status_code}"

    response_root: ElementTree.Element = ElementTree.fromstring(response.content)

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

        # TODO: call get_or_fetch_board_game()

        # TODO: open a transaction block `with transaction.atomic():`

        # TODO: create the PlaySession w/ null group

        # TODO: find the <players> tag and loop loop through its <player> tags
        # TODO: create the SessionPlayer linked to the PlaySession and the user

        sessions_created += 1

    return True, f"Successfully imported {sessions_created} plays."
