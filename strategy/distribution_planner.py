"""
Content distribution planner.
Maps content pieces to optimal platform time slots for the week.
"""
import time
from dataclasses import dataclass

from memory.repository import Repository

# Platform-level default best posting windows (UTC hours)
DEFAULT_PEAK_HOURS: dict[str, list[int]] = {
    "twitter": [9, 12, 17, 20],
    "tiktok": [7, 12, 19, 21],
    "linkedin": [8, 12, 17],
    "instagram": [8, 11, 18, 20],
}


@dataclass
class ScheduledSlot:
    platform: str
    unix_timestamp: int
    day_of_week: int    # 0=Mon, 6=Sun
    hour_utc: int
    slot_rank: int      # 1 = best slot of the day


class DistributionPlanner:
    def __init__(self, repo: Repository):
        self._repo = repo

    async def plan_week(
        self,
        platforms: list[str],
        posts_per_platform_per_day: int = 2,
        start_from_now: bool = True,
    ) -> dict[str, list[ScheduledSlot]]:
        """
        Returns a map of platform -> list of ScheduledSlot for 7 days.
        """
        plan: dict[str, list[ScheduledSlot]] = {}

        # Determine week start (next midnight UTC)
        now = int(time.time())
        today_midnight = now - (now % 86400)
        week_start = today_midnight if start_from_now else today_midnight

        for platform in platforms:
            # Try to use learned peak hours from DB; fall back to defaults
            peak_hours = await self._get_peak_hours(platform)
            slots = []

            for day in range(7):
                day_start = week_start + day * 86400
                day_of_week = (int(time.gmtime(day_start).tm_wday))

                # Skip posting on Sunday (optional rest day) — configurable
                if day_of_week == 6:
                    continue

                for rank, hour in enumerate(peak_hours[:posts_per_platform_per_day], start=1):
                    slot_ts = day_start + hour * 3600
                    # Add small jitter (0-15 min) to avoid exact-second detection
                    import random
                    jitter = random.randint(0, 900)
                    slots.append(
                        ScheduledSlot(
                            platform=platform,
                            unix_timestamp=slot_ts + jitter,
                            day_of_week=day_of_week,
                            hour_utc=hour,
                            slot_rank=rank,
                        )
                    )

            plan[platform] = slots

        return plan

    async def _get_peak_hours(self, platform: str) -> list[int]:
        """Load learned peak hours from strategy weights."""
        weights = await self._repo.get_all_weights(platform)
        hour_weights = {
            int(k.split(".")[1]): v
            for k, v in weights.items()
            if k.startswith("peak_hour.")
        }
        if hour_weights:
            return sorted(hour_weights, key=lambda h: -hour_weights[h])[:4]
        return DEFAULT_PEAK_HOURS.get(platform, [9, 17])
