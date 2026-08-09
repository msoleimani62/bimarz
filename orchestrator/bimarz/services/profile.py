"""
Server-profile management service.

سرویس مدیریت پروفایل‌های سرور.
"""

from __future__ import annotations

from bimarz.models import ServerProfile
from bimarz.parsers.vless import parse_vless_link
from bimarz.profiles import ProfileStore


class ProfileService:
    def __init__(
        self,
        store: ProfileStore | None = None,
    ) -> None:
        self.store = store or ProfileStore()

    def add_from_link(
        self,
        link: str,
    ) -> ServerProfile:
        """Parse and persist a VLESS profile.

        لینک VLESS را parse و ذخیره می‌کند.
        """
        profile = parse_vless_link(link)
        self.store.add_profile(profile)
        return profile

    def list_profiles(self) -> list[ServerProfile]:
        return self.store.list_profiles()

    def remove(
        self,
        profile_id: str,
    ) -> None:
        self.store.remove_profile(profile_id)

    def get(
        self,
        profile_id: str,
    ) -> ServerProfile:
        return self.store.get_profile(profile_id)
