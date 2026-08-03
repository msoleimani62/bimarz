"""
Parallel health-check service for stored profiles.
سرویس بررسی سلامت موازی برای پروفایل‌های ذخیره‌شده.
"""

from __future__ import annotations

import asyncio
from typing import Any

from bimarz.failover import check_profile_health
from bimarz.models import ServerProfile
from bimarz.profiles import ProfileStore


class HealthService:
    def __init__(self, store: ProfileStore | None = None) -> None:
        self.store = store or ProfileStore()

    async def check_all(self) -> list[tuple[ServerProfile, Any]]:
        """Check health of every stored profile concurrently.
        سلامت تمام پروفایل‌های ذخیره‌شده را به صورت همزمان بررسی می‌کند.
        """
        profiles = self.store.list_profiles()
        if not profiles:
            return []
        tasks = [check_profile_health(p) for p in profiles]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        return list(zip(profiles, results))
