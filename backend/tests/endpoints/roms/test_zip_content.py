"""Tests for `GET /api/roms/{id}/zip-launch` and `GET /api/roms/{id}/zip/{member}`."""

from zipfile import ZipFile

import pytest
from fastapi import status

from handler.database import db_rom_handler
from utils.zip_cache import ensure_zipfile_writable

SWF = b"FWS\x0a fake movie"


@pytest.fixture
def gamezip(rom, rom_file, tmp_path, monkeypatch):
    """Write the `rom_file` fixture's zip to disk as a Flashpoint GameZIP."""
    monkeypatch.setattr("endpoints.roms.LIBRARY_BASE_PATH", str(tmp_path))
    path = tmp_path / rom_file.full_path
    path.parent.mkdir(parents=True)

    def write(members: dict[str, bytes]):
        ensure_zipfile_writable()
        with ZipFile(path, "w") as zip_file:
            for name, data in members.items():
                zip_file.writestr(name, data)
        return rom

    return write


def auth(token):
    return {"Authorization": f"Bearer {token}"}


def test_zip_member_is_served(client, access_token, gamezip):
    rom = gamezip({"content/example.com/game/main.swf": SWF})

    response = client.get(
        f"/api/roms/{rom.id}/zip/content/example.com/game/main.swf",
        headers=auth(access_token),
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.content == SWF
    assert response.headers["content-type"] == "application/x-shockwave-flash"


def test_zip_member_matches_case_insensitively(client, access_token, gamezip):
    """Flash games were often served from hosts that ignored case."""
    rom = gamezip({"content/example.com/Game/Level1.XML": b"<level/>"})

    response = client.get(
        f"/api/roms/{rom.id}/zip/content/example.com/game/level1.xml",
        headers=auth(access_token),
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.content == b"<level/>"


def test_zip_member_not_in_zip_is_404(client, access_token, gamezip):
    rom = gamezip({"content/example.com/main.swf": SWF})

    response = client.get(
        f"/api/roms/{rom.id}/zip/content/example.com/ads.swf",
        headers=auth(access_token),
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_zip_member_requires_auth(client, gamezip):
    rom = gamezip({"content/example.com/main.swf": SWF})

    response = client.get(f"/api/roms/{rom.id}/zip/content/example.com/main.swf")

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_zip_routes_404_for_a_rom_that_is_not_one_zip(
    client, access_token, multi_file_rom
):
    for path in ("zip-launch", "zip/content/example.com/main.swf"):
        response = client.get(
            f"/api/roms/{multi_file_rom.id}/{path}", headers=auth(access_token)
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND


def test_zip_launch_follows_the_launch_command(client, access_token, gamezip):
    rom = gamezip(
        {
            "content/example.com/game/main.swf": SWF,
            "content/ads.example.net/preloader.swf": SWF,
        }
    )
    db_rom_handler.update_rom(
        rom.id,
        {
            "flashpoint_metadata": {
                "launch_command": "http://example.com/game/main.swf?lang=en"
            }
        },
    )

    response = client.get(f"/api/roms/{rom.id}/zip-launch", headers=auth(access_token))

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {
        "path": "content/example.com/game/main.swf",
        "url": "http://example.com/game/main.swf?lang=en",
    }


def test_zip_launch_without_a_launch_command_takes_the_only_swf(
    client, access_token, gamezip
):
    rom = gamezip(
        {
            "content.json": b"{}",
            "content/uploads.example.com/123/game.swf": SWF,
            "content/uploads.example.com/123/config.xml": b"<c/>",
        }
    )

    response = client.get(f"/api/roms/{rom.id}/zip-launch", headers=auth(access_token))

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {
        "path": "content/uploads.example.com/123/game.swf",
        "url": "http://uploads.example.com/123/game.swf",
    }


def test_zip_launch_is_404_when_no_file_is_known_to_start_it(
    client, access_token, gamezip
):
    rom = gamezip({"content/a.example/one.swf": SWF, "content/b.example/two.swf": SWF})

    response = client.get(f"/api/roms/{rom.id}/zip-launch", headers=auth(access_token))

    assert response.status_code == status.HTTP_404_NOT_FOUND
