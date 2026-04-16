import requests
import xml.etree.ElementTree as ElementTree
from core.constants import VALID_STATUS_CODES, REQUEST_HEADERS
from catalog.models import BoardGame


def get_bgg_board_game(bgg_id: int) -> BoardGame:
    fetch_url: str = f"https://boardgamegeek.com/xmlapi2/thing?id={bgg_id}"
    response: requests.Response = requests.get(url=fetch_url, headers=REQUEST_HEADERS)

    if response.status_code not in VALID_STATUS_CODES:
        return False, f"Failed to reach BGG API. Status: {response.status_code}"

    # XML Root should be 'items'
    response_root: ElementTree.Element = ElementTree.fromstring(response.content)

    game_item = response_root.find('item')
    primary_name: ElementTree.Element[str] = game_item.find('name[@type="primary"]')
    year_published: ElementTree.Element[str] = game_item.find('yearpublished')

    board_game_record: BoardGame = BoardGame.objects.create(primary_name=primary_name, year_published=year_published)
    return board_game_record


def get_existing_board_game(bgg_id: int) -> BoardGame:
    existing_board_game: BoardGame = BoardGame.objects.get(bgg_id=bgg_id)

    if existing_board_game:
        return existing_board_game
    else:
        get_bgg_board_game(bgg_id=bgg_id)
