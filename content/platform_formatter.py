"""
Platform-specific content formatter.
Enforces character limits, hashtag placement, and format rules per platform.
"""
import re
from dataclasses import dataclass


@dataclass
class FormattedContent:
    platform: str
    text: str
    char_count: int
    hashtags: list[str]
    is_valid: bool
    warnings: list[str]


HASHTAG_RE = re.compile(r"#\w+")
URL_RE = re.compile(r"https?://\S+")

PLATFORM_LIMITS = {
    "twitter": {"max_chars": 280, "max_hashtags": 2},
    "tiktok": {"max_chars": 2200, "max_hashtags": 5},
    "linkedin": {"max_chars": 3000, "max_hashtags": 3},
    "instagram": {"max_chars": 2200, "max_hashtags": 15},
}


class PlatformFormatter:
    def format(self, platform: str, raw_text: str, extra_hashtags: list[str] = None) -> FormattedContent:
        limits = PLATFORM_LIMITS.get(platform, {"max_chars": 280, "max_hashtags": 3})
        warnings = []

        # Normalize whitespace
        text = raw_text.strip()
        text = re.sub(r"\n{3,}", "\n\n", text)

        # Extract inline hashtags
        inline_tags = HASHTAG_RE.findall(text)

        # Merge with extra hashtags (deduped)
        all_tags = list(dict.fromkeys([t.lower() for t in (inline_tags + (extra_hashtags or []))]))
        max_tags = limits["max_hashtags"]

        # Remove inline hashtags from body for clean placement
        clean_text = HASHTAG_RE.sub("", text).strip()
        clean_text = re.sub(r"\s{2,}", " ", clean_text)
        clean_text = re.sub(r"\n\s+\n", "\n\n", clean_text)

        # Select top hashtags
        selected_tags = all_tags[:max_tags]
        tag_string = " ".join(selected_tags) if selected_tags else ""

        # Twitter: no hashtag block, integrate inline or append max 2
        if platform == "twitter":
            final_text = clean_text
            if selected_tags and len(final_text) + len(tag_string) + 1 <= limits["max_chars"]:
                final_text = f"{final_text} {tag_string}".strip()
        else:
            # All other platforms: hashtag block at end
            if tag_string:
                final_text = f"{clean_text}\n\n{tag_string}"
            else:
                final_text = clean_text

        # Enforce character limit
        max_chars = limits["max_chars"]
        if len(final_text) > max_chars:
            # Trim the tag block first
            final_text = clean_text[:max_chars - 1].rsplit(" ", 1)[0] + "…"
            warnings.append(f"Content truncated to {max_chars} characters")
            selected_tags = []

        # Platform-specific rules
        if platform == "linkedin":
            # LinkedIn: line breaks render, encourage them
            if "\n" not in final_text:
                warnings.append("LinkedIn post has no line breaks — structure may appear as wall of text")

        is_valid = len(final_text) <= max_chars and len(final_text) > 20

        return FormattedContent(
            platform=platform,
            text=final_text,
            char_count=len(final_text),
            hashtags=selected_tags,
            is_valid=is_valid,
            warnings=warnings,
        )

    def validate(self, platform: str, text: str) -> tuple[bool, list[str]]:
        result = self.format(platform, text)
        return result.is_valid, result.warnings
