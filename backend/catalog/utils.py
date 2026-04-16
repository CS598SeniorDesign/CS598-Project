from __future__ import annotations

import defusedxml.ElementTree as ElementTree
import requests
from typing import TYPE_CHECKING

from catalog.models import BoardGame
from core.constants import VALID_STATUS_CODES, REQUEST_HEADERS

if TYPE_CHECKING:
    from xml.etree.ElementTree import Element


def test():
    id = 246900
    get_bgg_board_game(id)


def get_bgg_board_game(bgg_id: int, backup_name: str) -> BoardGame:
    fetch_url: str = f"https://boardgamegeek.com/xmlapi2/thing?id={bgg_id}&stats=1"

    try:
        response: requests.Response = requests.get(url=fetch_url, headers=REQUEST_HEADERS, timeout=10)

        if response.status_code in VALID_STATUS_CODES:
            # XML Root should be 'items'
            response_root: Element = ElementTree.fromstring(response.content)
            game_item: Element = response_root.find('item')

            if game_item is not None:
                return BoardGame.create_from_xml(game_item, backup_name)
    except Exception:
        print("API fetch failed.")

    return BoardGame.objects.create(bgg_id=bgg_id, primary_name=backup_name)


def get_existing_board_game(bgg_id: int, backup_name: str) -> BoardGame:
    existing_board_game: BoardGame = BoardGame.objects.filter(bgg_id=bgg_id).first()

    if existing_board_game:
        return existing_board_game
    else:
        return get_bgg_board_game(bgg_id, backup_name)
