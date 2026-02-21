"""
YouTube SEO optimizer — Generates titles, descriptions, tags, and hashtags.

Uses LLM to generate SEO-optimized metadata based on the video script,
niche, and trending keywords.

YouTube SEO best practices encoded:
    - Title: 60-70 chars, keyword-first, emotion trigger
    - Description: first 2 lines visible without "show more"
    - Tags: 15-30 relevant tags, mix of broad and specific
    - Hashtags: 3-5 above the title (YouTube displays first 3)
    - Category: mapped to YouTube category IDs
"""
import json
import logging
from dataclasses import dataclass

from content.llm_client import LLMClient

logger = logging.getLogger(__name__)

# YouTube category IDs
YOUTUBE_CATEGORIES = {
    "artificial_intelligence": "28",   # Science & Technology
    "entrepreneurship": "22",          # People & Blogs
    "financial_freedom": "22",         # People & Blogs
    "network_marketing": "22",         # People & Blogs
    "anti_system": "25",               # News & Politics
    "marketing": "22",                 # People & Blogs
    "technology": "28",                # Science & Technology
    "business": "22",                  # People & Blogs
    "education": "27",                 # Education
    "gaming": "20",                    # Gaming
    "entertainment": "24",             # Entertainment
}


@dataclass
class YouTubeSEO:
    title: str
    description: str
    tags: list[str]
    hashtags: list[str]
    category_id: str


class SEOOptimizer:
    """
    Generates YouTube SEO metadata from a video script and context.
    """

    def __init__(self, llm_client: LLMClient | None = None):
        self._llm = llm_client or LLMClient()

    async def optimize(
        self,
        topic: str,
        script_summary: str,
        niche: str,
        language: str = "en",
        channel_name: str = "",
        extra_links: list[str] | None = None,
    ) -> YouTubeSEO:
        """
        Generate SEO-optimized YouTube metadata.

        Args:
            topic: Video topic
            script_summary: Full narration or summary of the script
            niche: Content niche for category mapping
            language: Content language
            channel_name: Channel name for branding
            extra_links: URLs to include in description (affiliate links, etc.)
        """
        system_prompt = self._build_system_prompt(language)
        user_prompt = self._build_user_prompt(
            topic, script_summary, niche, channel_name, extra_links,
        )

        data = await self._llm.generate_json(system_prompt, user_prompt)
        seo = self._parse_response(data, niche)

        logger.info(
            f"[seo] optimized: title='{seo.title[:50]}...' "
            f"tags={len(seo.tags)} hashtags={len(seo.hashtags)}"
        )
        return seo

    def _build_system_prompt(self, language: str) -> str:
        lang_note = ""
        if language != "en":
            lang_note = f"\nIMPORTANT: Generate ALL text in language code '{language}'."

        return f"""You are a YouTube SEO expert. Generate metadata that maximizes click-through rate and discoverability.
{lang_note}
Return valid JSON with this structure:
{{
  "title": "SEO title (max 70 chars, keyword-first, emotion trigger)",
  "description": "Full description (max 5000 chars, first 2 lines are critical)",
  "tags": ["tag1", "tag2", ...],
  "hashtags": ["#hashtag1", "#hashtag2", ...]
}}

RULES:
- Title: 60-70 characters, front-load the main keyword, include a power word
- Description: first 2 lines must hook the viewer (visible without clicking "show more")
  - Include timestamps section (00:00 format)
  - Include 3-5 relevant keywords naturally
  - End with subscribe CTA and relevant links
- Tags: 15-30 tags, mix of:
  - Exact match keywords (e.g., "how to start a business")
  - Broad category (e.g., "entrepreneurship")
  - Long-tail variations (e.g., "business ideas 2024 for beginners")
- Hashtags: exactly 3-5, most relevant keywords with #
- Do NOT use clickbait that misrepresents the content
- Do NOT use tags that are irrelevant to the content"""

    def _build_user_prompt(
        self,
        topic: str,
        script_summary: str,
        niche: str,
        channel_name: str,
        extra_links: list[str] | None,
    ) -> str:
        links_section = ""
        if extra_links:
            links_section = "\nLinks to include in description:\n" + "\n".join(
                f"- {link}" for link in extra_links
            )

        # Truncate script to avoid token waste
        summary_truncated = script_summary[:2000]

        return f"""Generate YouTube SEO metadata for this video:

TOPIC: {topic}
NICHE: {niche}
CHANNEL: {channel_name or 'Not specified'}
{links_section}

SCRIPT SUMMARY (first 2000 chars):
{summary_truncated}

Include a timestamps section in the description based on the 5 scenes:
00:00 - Hook / Introduction
[estimate timestamps for: Problem, Deepening, Solution, CTA]

Return ONLY the JSON object."""

    def _parse_response(self, data: dict, niche: str) -> YouTubeSEO:
        """Parse LLM response into YouTubeSEO."""
        title = data.get("title", "")[:100]
        description = data.get("description", "")[:5000]
        tags = data.get("tags", [])[:30]
        hashtags = data.get("hashtags", [])[:5]

        # Ensure hashtags have # prefix
        hashtags = [h if h.startswith("#") else f"#{h}" for h in hashtags]

        # Map niche to YouTube category
        category_id = YOUTUBE_CATEGORIES.get(niche, "22")

        # Append AI disclosure to description
        ai_disclosure = (
            "This video was created with AI-assisted tools including "
            "AI-generated voice, images, and script."
        )
        if description and ai_disclosure not in description:
            description += f"\n\n---\n{ai_disclosure}"

        return YouTubeSEO(
            title=title,
            description=description,
            tags=tags,
            hashtags=hashtags,
            category_id=category_id,
        )
