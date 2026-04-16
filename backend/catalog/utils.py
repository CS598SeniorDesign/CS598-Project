import requests
import defusedxml.ElementTree as ElementTree
from typing import TYPE_CHECKING

from core.constants import VALID_STATUS_CODES, REQUEST_HEADERS
from catalog.models import BoardGame

if TYPE_CHECKING:
    from xml.etree.ElementTree import Element


def test():
    id = 246900
    get_bgg_board_game(id)


def get_bgg_board_game(bgg_id: int) -> BoardGame:
    fetch_url: str = f"https://boardgamegeek.com/xmlapi2/thing?id={bgg_id}"
    response: requests.Response = requests.get(url=fetch_url, headers=REQUEST_HEADERS, timeout=10)

    if response.status_code not in VALID_STATUS_CODES:
        return False, f"Failed to reach BGG API. Status: {response.status_code}"

    # XML Root should be 'items'
    response_root: Element = ElementTree.fromstring(response.content)

    game_item = response_root.find('item')
    return BoardGame.create_from_xml(game_item)


def get_existing_board_game(bgg_id: int) -> BoardGame:
    existing_board_game: BoardGame = BoardGame.objects.filter(bgg_id=bgg_id).first()

    if existing_board_game:
        return existing_board_game
    else:
        return get_bgg_board_game(bgg_id=bgg_id)
