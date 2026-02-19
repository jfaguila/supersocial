"""
Content format pattern recognition.
Identifies structural patterns in high-performing posts.
"""
import re
from dataclasses import dataclass

from data_layer.base_connector import TrendPost


@dataclass
class FormatAnalysis:
    post_id: str
    format_type: str           # list|story|thread|single_insight|question_answer|confession
    structure_score: float     # how well-structured (0.0–1.0)
    has_hook: bool
    has_cta: bool
    has_numbered_list: bool
    has_bullet_list: bool
    line_count: int
    word_count: int
    emoji_count: int
    hashtag_count: int


CTA_PATTERNS = [
    r"\b(follow|subscribe|share|comment|tag|save|bookmark|like|dm|reach out|click)\b",
    r"\b(what do you think|let me know|drop a|tell me)\b",
    r"\b(link in bio|check out|sign up|join|register)\b",
]


class FormatRecognizer:
    def __init__(self):
        self._cta_re = [re.compile(p, re.IGNORECASE) for p in CTA_PATTERNS]
        self._numbered_re = re.compile(r"^\s*\d+[\.\)]\s+", re.MULTILINE)
        self._bullet_re = re.compile(r"^\s*[-•*→]\s+", re.MULTILINE)
        self._emoji_re = re.compile(
            "[\U0001F300-\U0001F9FF\U00002702-\U000027B0\U0000231A-\U0000231B]+"
        )
        self._hashtag_re = re.compile(r"#\w+")

    def _detect_format(self, text: str) -> str:
        has_numbered = bool(self._numbered_re.search(text))
        has_bullet = bool(self._bullet_re.search(text))
        lines = text.strip().split("\n")

        if has_numbered or has_bullet:
            return "list"
        if len(lines) > 5 and any(
            kw in text.lower() for kw in ["thread", "1/", "1)", "(cont", "more below"]
        ):
            return "thread"
        if any(kw in text.lower() for kw in ["i used to", "i was", "when i", "years ago", "story"]):
            return "story"
        if "?" in lines[0] and len(text) > 200:
            return "question_answer"
        if any(kw in text.lower() for kw in ["confession", "admit", "truth is", "honest"]):
            return "confession"
        return "single_insight"

    def _has_hook(self, text: str) -> bool:
        first_line = text.strip().split("\n")[0].strip()
        return len(first_line) > 0 and len(first_line) <= 120

    def _has_cta(self, text: str) -> bool:
        return any(p.search(text) for p in self._cta_re)

    def analyze(self, post: TrendPost) -> FormatAnalysis:
        text = post.content_text or ""
        lines = text.strip().split("\n")
        return FormatAnalysis(
            post_id=post.post_id,
            format_type=self._detect_format(text),
            structure_score=self._structure_score(text),
            has_hook=self._has_hook(text),
            has_cta=self._has_cta(text),
            has_numbered_list=bool(self._numbered_re.search(text)),
            has_bullet_list=bool(self._bullet_re.search(text)),
            line_count=len(lines),
            word_count=len(text.split()),
            emoji_count=len(self._emoji_re.findall(text)),
            hashtag_count=len(self._hashtag_re.findall(text)),
        )

    def _structure_score(self, text: str) -> float:
        score = 0.0
        if self._has_hook(text):
            score += 0.3
        if self._has_cta(text):
            score += 0.2
        if self._numbered_re.search(text) or self._bullet_re.search(text):
            score += 0.2
        lines = text.strip().split("\n")
        if 3 <= len(lines) <= 20:
            score += 0.15
        if 50 <= len(text.split()) <= 300:
            score += 0.15
        return min(score, 1.0)

    def analyze_batch(self, posts: list[TrendPost]) -> list[FormatAnalysis]:
        return [self.analyze(p) for p in posts]

    def dominant_formats(self, analyses: list[FormatAnalysis]) -> dict[str, int]:
        counts: dict[str, int] = {}
        for a in analyses:
            counts[a.format_type] = counts.get(a.format_type, 0) + 1
        return dict(sorted(counts.items(), key=lambda x: -x[1]))
