"""Tests for bimarz.profiles.

Uses an explicit password (bypassing the getpass prompt) and a tmp_path
file, so this suite is fully offline and non-interactive — the same
pattern used for xray_manager's fake-binary tests.

تست‌های bimarz.profiles.

از یک پسورد صریح (به‌جای پرسیدن با getpass) و یک فایل در tmp_path استفاده
می‌کند، پس این مجموعه‌ی تست کاملاً آفلاین و غیرتعاملی است — همان الگویی که
برای تست‌های باینری‌جعلی xray_manager استفاده شده.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from bimarz.profiles import ProfileNotFoundError, ProfileStore, WrongPasswordError
from bimarz.models import ServerProfile


def _make_profile(profile_id: str = "p1") -> ServerProfile:
    return ServerProfile(
        profile_id=profile_id,
        tag=profile_id,
        remark="Test Server",
        outbound_config={"address": "example.com", "port": 443},
        added_at_iso="2026-07-28T00:00:00+00:00",
    )


def test_add_and_list_profile(tmp_path: Path) -> None:
    store = ProfileStore(path=tmp_path / "profiles.enc.json", password="correct-password")
    store.add_profile(_make_profile())

    profiles = store.list_profiles()
    assert len(profiles) == 1
    assert profiles[0].profile_id == "p1"
    assert profiles[0].remark == "Test Server"


def test_get_profile_by_id(tmp_path: Path) -> None:
    store = ProfileStore(path=tmp_path / "profiles.enc.json", password="correct-password")
    store.add_profile(_make_profile())

    fetched = store.get_profile("p1")
    assert fetched.profile_id == "p1"


def test_get_profile_raises_when_missing(tmp_path: Path) -> None:
    store = ProfileStore(path=tmp_path / "profiles.enc.json", password="correct-password")
    with pytest.raises(ProfileNotFoundError):
        store.get_profile("does-not-exist")


def test_remove_profile(tmp_path: Path) -> None:
    store = ProfileStore(path=tmp_path / "profiles.enc.json", password="correct-password")
    store.add_profile(_make_profile())
    store.remove_profile("p1")

    assert store.list_profiles() == []


def test_remove_missing_profile_raises(tmp_path: Path) -> None:
    store = ProfileStore(path=tmp_path / "profiles.enc.json", password="correct-password")
    with pytest.raises(ProfileNotFoundError):
        store.remove_profile("does-not-exist")


def test_file_on_disk_never_contains_plaintext_secrets(tmp_path: Path) -> None:
    path = tmp_path / "profiles.enc.json"
    store = ProfileStore(path=path, password="correct-password")
    store.add_profile(_make_profile())

    raw_bytes = path.read_bytes()
    assert b"example.com" not in raw_bytes
    assert b"Test Server" not in raw_bytes


def test_wrong_password_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "profiles.enc.json"
    ProfileStore(path=path, password="correct-password").add_profile(_make_profile())

    wrong_store = ProfileStore(path=path, password="wrong-password")
    with pytest.raises(WrongPasswordError):
        wrong_store.list_profiles()


def test_listing_a_nonexistent_store_returns_empty(tmp_path: Path) -> None:
    store = ProfileStore(path=tmp_path / "does-not-exist.enc.json", password="any-password")
    assert store.list_profiles() == []
