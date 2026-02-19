"""
Weekly trend detector.
Identifies rising themes, keywords, and engagement patterns.
"""
import re
from collections import Counter
from dataclasses import dataclass, field

from data_layer.base_connector import TrendPost


@dataclass
class TrendReport:
    platforms: list[str]
    top_keywords: list[tuple[str, int]]          # (keyword, count)
    top_hashtags: list[tuple[str, int]]
    rising_topics: list[str]
    dominant_content_types: dict[str, int]       # video|image|text -> count
    avg_engagement_by_type: dict[str, float]
    peak_posting_hours: list[int]                # 0-23 UTC
    high_engagement_hooks: list[str]
    raw_post_count: int
    analysis_window_days: int = 7


STOPWORDS = {
    "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "as", "is", "are", "was", "were", "be",
    "been", "have", "has", "had", "do", "does", "did", "will", "would",
    "can", "could", "should", "this", "that", "these", "those", "i",
    "you", "he", "she", "it", "we", "they", "my", "your", "our", "their",
    "just", "not", "so", "if", "about", "up", "out", "get", "got", "like",
}


class TrendDetector:
    def __init__(self, window_days: int = 7):
        self.window_days = window_days
        self._hashtag_re = re.compile(r"#(\w+)")

    def detect(self, posts: list[TrendPost]) -> TrendReport:
        if not posts:
            return TrendReport(
                platforms=[],
                top_keywords=[],
                top_hashtags=[],
                rising_topics=[],
                dominant_content_types={},
                avg_engagement_by_type={},
                peak_posting_hours=[],
                high_engagement_hooks=[],
                raw_post_count=0,
            )

        keyword_counter: Counter = Counter()
        hashtag_counter: Counter = Counter()
        type_counts: dict[str, int] = {}
        type_engagement: dict[str, list[float]] = {}
        hours: list[int] = []
        platforms = list({p.platform for p in posts})

        for post in posts:
            # Keywords
            words = re.findall(r"\b[a-z]{4,}\b", post.content_text.lower())
            keyword_counter.update(w for w in words if w not in STOPWORDS)

            # Hashtags
            tags = self._hashtag_re.findall(post.content_text.lower())
            hashtag_counter.update(tags)

            # Content type
            ct = post.content_type
            type_counts[ct] = type_counts.get(ct, 0) + 1
            type_engagement.setdefault(ct, []).append(post.engagement_rate)

            # Peak hours
            if post.published_at > 0:
                import time
                hour = int(time.gmtime(post.published_at).tm_hour)
                hours.append(hour)

        # Average engagement by type
        avg_eng = {ct: sum(vals) / len(vals) for ct, vals in type_engagement.items()}

        # Peak hours (top 3)
        hour_counter = Counter(hours)
        peak_hours = [h for h, _ in hour_counter.most_common(5)]

        # High engagement hooks (first line of top 20% posts)
        sorted_posts = sorted(posts, key=lambda p: p.engagement_rate, reverse=True)
        top_n = max(1, len(sorted_posts) // 5)
        hooks = []
        for p in sorted_posts[:top_n]:
            first_line = p.content_text.strip().split("\n")[0]
            if first_line and len(first_line) > 10:
                hooks.append(first_line[:120])

        # Rising topics (keywords appearing in top quartile more than bottom)
        mid = len(posts) // 2
        bottom_posts = sorted_posts[mid:]
        top_posts = sorted_posts[:mid]
        top_kw = Counter()
        for p in top_posts:
            words = re.findall(r"\b[a-z]{4,}\b", p.content_text.lower())
            top_kw.update(w for w in words if w not in STOPWORDS)

        rising = [kw for kw, cnt in top_kw.most_common(20)
                  if cnt > keyword_counter.get(kw, 0) * 0.3]

        return TrendReport(
            platforms=platforms,
            top_keywords=keyword_counter.most_common(30),
            top_hashtags=hashtag_counter.most_common(20),
            rising_topics=rising[:10],
            dominant_content_types=type_counts,
            avg_engagement_by_type=avg_eng,
            peak_posting_hours=peak_hours,
            high_engagement_hooks=hooks[:10],
            raw_post_count=len(posts),
            analysis_window_days=self.window_days,
        )
