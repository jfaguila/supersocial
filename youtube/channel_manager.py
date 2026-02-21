"""
Channel manager — Multi-channel YouTube orchestration.

Manages multiple YouTube channels, each with:
    - Its own character identity
    - Its own niche and tone
    - Its own publishing schedule
    - Its own YouTube API credentials

Handles topic selection, scheduling, and batch production.
"""
import logging
import time
from dataclasses import dataclass

from content.llm_client import LLMClient

logger = logging.getLogger(__name__)


@dataclass
class ChannelConfig:
    """Runtime configuration for a single YouTube channel."""
    channel_id: str
    name: str
    niche: str
    language: str
    tone: str
    target_duration_minutes: int
    videos_per_week: int
    publish_schedule_cron: str
    default_category_id: str
    made_for_kids: bool
    privacy_status: str
    # YouTube API credentials
    google_client_id: str
    google_client_secret: str
    google_refresh_token: str
    # Character reference
    character_id: str


@dataclass
class VideoTopic:
    """A topic to produce a video about."""
    title: str
    angle: str          # Specific angle/approach
    keywords: list[str]
    priority: int = 1   # 1 = highest


class ChannelManager:
    """
    Orchestrates multiple YouTube channels.
    Handles topic generation, scheduling, and production queue.
    """

    def __init__(self, llm_client: LLMClient | None = None):
        self._llm = llm_client or LLMClient()

    def load_channel_config(self, channel_row) -> ChannelConfig:
        """Load a ChannelConfig from a YouTubeChannel ORM row."""
        return ChannelConfig(
            channel_id=channel_row.id,
            name=channel_row.name,
            niche=channel_row.niche,
            language=channel_row.language,
            tone=channel_row.tone,
            target_duration_minutes=channel_row.target_duration_minutes,
            videos_per_week=channel_row.videos_per_week,
            publish_schedule_cron=channel_row.publish_schedule_cron,
            default_category_id=channel_row.default_category_id,
            made_for_kids=channel_row.made_for_kids,
            privacy_status=channel_row.privacy_status,
            google_client_id=channel_row.google_client_id,
            google_client_secret=channel_row.google_client_secret,
            google_refresh_token=channel_row.google_refresh_token,
            character_id=channel_row.character_id,
        )

    async def generate_topics(
        self,
        channel: ChannelConfig,
        count: int = 4,
        existing_topics: list[str] | None = None,
        trending_keywords: list[str] | None = None,
    ) -> list[VideoTopic]:
        """
        Generate video topics for a channel using LLM.

        Args:
            channel: Channel configuration
            count: Number of topics to generate
            existing_topics: Previously covered topics (for deduplication)
            trending_keywords: Current trending keywords to incorporate
        """
        existing = existing_topics or []
        trending = trending_keywords or []

        system_prompt = (
            f"You are a YouTube content strategist for the '{channel.niche}' niche. "
            f"Tone: {channel.tone}. Language: {channel.language}.\n\n"
            f"Generate exactly {count} video topic ideas. Each must be specific, "
            f"searchable, and different from existing topics.\n\n"
            f"Return valid JSON: "
            f'{{"topics": [{{"title": "...", "angle": "...", "keywords": ["..."]}}]}}'
        )

        avoid_section = ""
        if existing:
            avoid_section = f"\n\nAVOID these already-covered topics:\n" + "\n".join(
                f"- {t}" for t in existing[-20:]
            )

        trend_section = ""
        if trending:
            trend_section = f"\n\nTrending keywords to consider: {', '.join(trending[:10])}"

        user_prompt = (
            f"Generate {count} YouTube video topics for the '{channel.niche}' niche."
            f"{avoid_section}{trend_section}\n\n"
            f"Each topic should be a video someone would search for on YouTube. "
            f"Include a specific angle/approach and 3-5 search keywords per topic."
        )

        data = await self._llm.generate_json(system_prompt, user_prompt)
        return self._parse_topics(data)

    def calculate_next_publish_slots(
        self,
        channel: ChannelConfig,
        count: int = 4,
    ) -> list[int]:
        """
        Calculate the next N publish timestamps based on channel's cron schedule.
        Returns Unix timestamps.
        """
        try:
            from croniter import croniter
        except ImportError:
            # Fallback: simple weekly schedule
            logger.warning("[channel_mgr] croniter not available, using fallback schedule")
            now = int(time.time())
            return [now + (i * 86400 * 2) for i in range(1, count + 1)]

        now_ts = time.time()
        cron = croniter(channel.publish_schedule_cron, now_ts)
        slots = []
        for _ in range(count):
            next_time = cron.get_next(float)
            slots.append(int(next_time))
        return slots

    def _parse_topics(self, data: dict) -> list[VideoTopic]:
        """Parse LLM response into VideoTopic list."""
        raw_topics = data.get("topics", [])
        topics = []
        for i, raw in enumerate(raw_topics):
            topics.append(VideoTopic(
                title=raw.get("title", f"Topic {i + 1}"),
                angle=raw.get("angle", ""),
                keywords=raw.get("keywords", []),
                priority=i + 1,
            ))
        return topics
