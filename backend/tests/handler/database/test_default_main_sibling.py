"""MAIN_SIBLING_DEFAULT_USER: one user's main-sibling choices stand in for
users who have made none, in the gallery and in every sibling list."""

import pytest

import handler.database.roms_handler as roms_handler_module
from handler.database import db_rom_handler
from handler.database.base_handler import sync_session
from models.platform import Platform
from models.rom import Rom
from models.user import User


def _sibling(platform: Platform, region: str) -> Rom:
    return db_rom_handler.add_rom(
        Rom(
            platform_id=platform.id,
            name="Game",
            slug="game",
            fs_name=f"Game ({region}).zip",
            fs_name_no_tags="Game",
            fs_name_no_ext=f"Game ({region})",
            fs_extension="zip",
            fs_path=f"{platform.slug}/roms",
            igdb_id=4242,
        )
    )


def _make_main(rom: Rom, user: User) -> None:
    rom_user = db_rom_handler.add_rom_user(rom_id=rom.id, user_id=user.id)
    db_rom_handler.update_rom_user(rom_user.id, {"is_main_sibling": True})


def _gallery(platform: Platform, user: User) -> list[int]:
    roms = db_rom_handler.get_roms_scalar(
        platform_ids=[platform.id],
        order_by="name",
        order_dir="asc",
        group_by_meta_id=True,
        user_id=user.id,
    )
    return [r.id for r in roms]


@pytest.fixture
def siblings(platform: Platform) -> tuple[Rom, Rom]:
    # "Game (USA)" sorts before "Game (World)": the alphabetical fallback picks USA.
    return _sibling(platform, "USA"), _sibling(platform, "World")


@pytest.fixture
def default_is_admin(monkeypatch, admin_user: User):
    monkeypatch.setattr(
        roms_handler_module, "MAIN_SIBLING_DEFAULT_USER", admin_user.username
    )


def test_gallery_uses_the_default_users_main(
    platform, siblings, admin_user, viewer_user, default_is_admin
):
    usa, world = siblings
    _make_main(world, admin_user)

    assert _gallery(platform, viewer_user) == [world.id]


def test_gallery_prefers_the_users_own_main(
    platform, siblings, admin_user, viewer_user, default_is_admin
):
    usa, world = siblings
    _make_main(world, admin_user)
    _make_main(usa, viewer_user)

    assert _gallery(platform, viewer_user) == [usa.id]
    assert _gallery(platform, admin_user) == [world.id]


def test_gallery_without_a_default_falls_back_to_the_alphabet(
    platform, siblings, admin_user, viewer_user
):
    usa, world = siblings
    _make_main(world, admin_user)

    assert _gallery(platform, viewer_user) == [usa.id]


def test_sibling_list_marks_the_default_users_main(
    siblings, admin_user, viewer_user, default_is_admin
):
    usa, world = siblings
    _make_main(world, admin_user)

    with sync_session.begin() as session:
        found = db_rom_handler.get_siblings_for_roms(
            [usa.id], user_id=viewer_user.id, session=session
        )
        assert [(s.id, main) for s, main in found[usa.id]] == [(world.id, True)]


def test_resolve_keeps_a_users_own_choice_over_the_default(
    siblings, admin_user, viewer_user, default_is_admin
):
    usa, world = siblings
    _make_main(world, admin_user)
    _make_main(usa, viewer_user)

    group = {usa.id, world.id}
    assert db_rom_handler.resolve_main_siblings(viewer_user.id, {1: group}) == {
        1: {usa.id}
    }


def test_default_users_pick_rotates_another_users_grouped_cache_key(
    default_is_admin, platform: Platform, admin_user: User, editor_user: User
):
    # The gallery's grouped sidecars are cached per user; a pick by the default
    # user changes what every other user sees, so it must move their key too.
    from endpoints.roms import build_unscoped_sidecar_cache_key

    def key() -> str | None:
        return build_unscoped_sidecar_cache_key(
            editor_user.id, "name", "asc", group_by_meta_id=True, is_unscoped=True
        )

    usa = _sibling(platform, "USA")
    _sibling(platform, "World")
    before = key()
    _make_main(usa, admin_user)
    assert key() != before
