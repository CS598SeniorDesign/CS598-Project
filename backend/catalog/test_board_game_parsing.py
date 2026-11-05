from __future__ import annotations

from decimal import Decimal

import pytest
from defusedxml import ElementTree

from catalog.bgg_test_responses import read_bgg_response
from catalog.models import UNKNOWN_GAME_NAME, BoardGame


def recorded_item(file_name: str):
    return ElementTree.fromstring(read_bgg_response(file_name)).find("item")


def minimal_item(inner_xml: str, item_type: str = "boardgame"):
    return ElementTree.fromstring(f'<item type="{item_type}" id="1">{inner_xml}</item>')


@pytest.mark.django_db
class TestCreateFromRecordedResponses:
    def test_stores_every_field_of_a_ranked_base_game(self):
        BoardGame.create_from_xml(recorded_item("thing_catan.xml"))
        game = BoardGame.objects.get(bgg_id=13)

        assert game.item_type == BoardGame.BOARD_GAME
        assert game.primary_name == "Catan"
        assert game.year_published == 1995
        assert (game.minimum_players, game.maximum_players) == (3, 4)
        assert (game.playing_time, game.minimum_playtime, game.maximum_playtime) == (120, 60, 120)
        assert game.minimum_age == 10
        assert game.bgg_rank == 624
        assert game.average_rating == Decimal("7.090")
        assert game.average_weight == Decimal("2.280")
        assert game.thumbnail_url is not None
        assert game.thumbnail_url.startswith("https://cf.geekdo-images.com/")
        assert game.mechanics.count() == 2
        assert game.categories.count() == 2

    def test_stores_an_unranked_expansion_instead_of_failing(self):
        game = BoardGame.create_from_xml(recorded_item("thing_catan_seafarers_expansion.xml"))

        assert game.item_type == BoardGame.EXPANSION
        assert game.primary_name == "Catan: Seafarers"
        assert game.bgg_rank is None
        assert game.average_rating is not None

    def test_importing_again_updates_the_game_in_place(self):
        BoardGame.objects.create(bgg_id=13, primary_name="Skeleton")

        BoardGame.create_from_xml(recorded_item("thing_catan.xml"))

        assert BoardGame.objects.count() == 1
        assert BoardGame.objects.get(bgg_id=13).primary_name == "Catan"


@pytest.mark.django_db
class TestCreateFromUnusualValues:
    def test_zero_year_and_zero_averages_mean_unknown(self):
        game = BoardGame.create_from_xml(
            minimal_item(
                """<name type="primary" value="Brand New Game" /><yearpublished value="0" />
                <statistics><ratings><average value="0" /><averageweight value="0" /></ratings></statistics>"""
            )
        )

        assert game.year_published is None
        assert game.average_rating is None
        assert game.average_weight is None

    def test_non_numeric_values_are_stored_as_unknown(self):
        game = BoardGame.create_from_xml(
            minimal_item(
                """<name type="primary" value="Odd Game" /><minplayers value="" /><maxplayers value="lots" />
                <statistics><ratings><ranks>
                    <rank name="boardgame" value="Not Ranked" />
                </ranks></ratings></statistics>"""
            )
        )

        assert game.minimum_players is None
        assert game.maximum_players is None
        assert game.bgg_rank is None

    def test_missing_primary_name_uses_the_backup_name(self):
        game = BoardGame.create_from_xml(minimal_item(""), backup_name="From My Play Log")

        assert game.primary_name == "From My Play Log"

    def test_missing_primary_name_without_a_backup_is_unknown(self):
        game = BoardGame.create_from_xml(minimal_item(""))

        assert game.primary_name == UNKNOWN_GAME_NAME

    def test_types_other_than_expansion_are_stored_as_board_games(self):
        game = BoardGame.create_from_xml(minimal_item('<name type="primary" value="Thing" />', item_type="other"))

        assert game.item_type == BoardGame.BOARD_GAME
