"""Tests for the Flashpoint handler: lookup failures, and GameZIP launch files."""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException

from handler.metadata.flashpoint_handler import (
    FlashpointHandler,
    resolve_gamezip_launch,
)


@pytest.mark.asyncio
async def test_search_games_propagates_an_unreachable_flashpoint():
    """A failed search has to stay distinguishable from a term with no hits."""
    handler = FlashpointHandler()

    with (
        patch.object(FlashpointHandler, "is_enabled", return_value=True),
        patch.object(
            FlashpointHandler,
            "_request",
            new_callable=AsyncMock,
            side_effect=HTTPException(status_code=503, detail="down"),
        ),
        pytest.raises(HTTPException),
    ):
        await handler.search_games("Interactive Buddy")


@pytest.mark.asyncio
async def test_get_rom_by_id_propagates_an_unreachable_flashpoint():
    handler = FlashpointHandler()

    with (
        patch("handler.metadata.flashpoint_handler.FLASHPOINT_API_ENABLED", True),
        patch.object(
            FlashpointHandler,
            "_request",
            new_callable=AsyncMock,
            side_effect=HTTPException(status_code=503, detail="down"),
        ),
        pytest.raises(HTTPException),
    ):
        await handler.get_rom_by_id("dc1f7d99-9a3d-4f3f-8f2a-000000000000")


GAME_DATA = {
    "id": "dc1f7d99-9a3d-4f3f-8f2a-000000000000",
    "title": "Interactive Buddy",
    "originalDescription": "",
    "platform": "Flash",
    "library": "arcade",
    "series": "",
    "developer": "",
    "publisher": "",
    "source": "",
    "tags": [],
    "dateAdded": "",
    "dateModified": "",
    "playMode": "",
    "status": "Playable",
    "version": "",
    "releaseDate": "",
    "language": "en",
    "notes": "",
    "launchCommand": "http://uploads.ungrounded.net/123/buddy.swf",
}


@pytest.mark.asyncio
async def test_get_rom_by_id_keeps_the_launch_command():
    """The player needs it to tell which file in a GameZIP starts the game."""
    handler = FlashpointHandler()

    with (
        patch("handler.metadata.flashpoint_handler.FLASHPOINT_API_ENABLED", True),
        patch.object(
            FlashpointHandler,
            "_request",
            new_callable=AsyncMock,
            return_value=[GAME_DATA],
        ),
    ):
        rom = await handler.get_rom_by_id(GAME_DATA["id"])

    assert rom["flashpoint_metadata"]["launch_command"] == GAME_DATA["launchCommand"]


def test_launch_command_maps_to_its_gamezip_member():
    launch = resolve_gamezip_launch(
        "http://www.example.com/my%20game/main.swf?v=2",
        [
            "content.json",
            "content/www.example.com/my game/main.swf",
            "content/www.example.com/my game/intro.swf",
        ],
    )

    assert launch == (
        "content/www.example.com/my game/main.swf",
        "http://www.example.com/my%20game/main.swf?v=2",
    )


def test_an_older_data_pack_falls_back_to_its_only_swf():
    """An older pack can hold the game under a URL the current one moved from."""
    launch = resolve_gamezip_launch(
        "http://localflash/game.swf",
        ["content/uploads.ungrounded.net/1/game_v1.swf", "content/x.example/a.xml"],
    )

    assert launch == (
        "content/uploads.ungrounded.net/1/game_v1.swf",
        "http://uploads.ungrounded.net/1/game_v1.swf",
    )


def test_an_older_data_pack_falls_back_to_a_swf_of_the_same_name():
    launch = resolve_gamezip_launch(
        "http://chat.example.com/gamez/1/live/game.swf",
        [
            "content/assets.example.com/gamez/1/live/game.swf",
            "content/core.mochibot.com/my/core.swf",
        ],
    )

    assert launch == (
        "content/assets.example.com/gamez/1/live/game.swf",
        "http://assets.example.com/gamez/1/live/game.swf",
    )


def test_no_launch_file_when_several_swfs_and_none_matches():
    assert (
        resolve_gamezip_launch(
            "http://localflash/game.swf",
            ["content/a.example/one.swf", "content/b.example/two.swf"],
        )
        is None
    )


def test_a_shockwave_launch_command_finds_no_swf():
    assert (
        resolve_gamezip_launch(
            '"http://www.example.com/game.dcr" --setTheRunMode "Plugin"',
            ["content/www.example.com/game.dcr"],
        )
        is None
    )


def test_a_game_that_is_not_flash_finds_no_swf():
    """An HTML5 or Shockwave pack can carry a stray SWF; it does not start the game."""
    assert (
        resolve_gamezip_launch(
            "http://www.example.com/game/index.html",
            ["content/www.example.com/game/index.html", "content/ads.example/a.swf"],
        )
        is None
    )


def test_without_a_launch_command_the_only_swf_is_taken():
    launch = resolve_gamezip_launch(None, ["content/x.example/game.swf"])

    assert launch == ("content/x.example/game.swf", "http://x.example/game.swf")
