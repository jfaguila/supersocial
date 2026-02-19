"""
Emotional tone clustering using keyword-based and TextBlob sentiment analysis.
Maps content to the 6 core emotional drivers used by high-performing content.
"""
import re
from dataclasses import dataclass

from data_layer.base_connector import TrendPost


EMOTION_LEXICON: dict[str, list[str]] = {
    "fear": [
        "trap", "slave", "stuck", "broke", "fail", "lose", "debt", "prison",
        "nobody", "alone", "dying", "risk", "danger", "warning", "alert",
        "too late", "running out", "before it's too late",
    ],
    "aspiration": [
        "dream", "freedom", "wealthy", "rich", "retire", "passive income",
        "achieve", "build", "create", "grow", "succeed", "win", "goal",
        "vision", "potential", "manifest", "abundance", "elevate",
    ],
    "anger": [
        "unfair", "system", "rigged", "lie", "corrupt", "scam", "wake up",
        "brainwashed", "exploit", "steal", "corporate", "government",
        "manipulate", "control", "propaganda", "slave wage",
    ],
    "identity": [
        "entrepreneur", "founder", "creator", "hustler", "builder",
        "self-made", "network marketer", "leader", "independent",
        "sovereign", "alpha", "maverick", "outlier", "different",
    ],
    "hope": [
        "possible", "can do this", "you got this", "believe", "change",
        "better life", "opportunity", "new beginning", "transform",
        "it gets better", "one day", "soon", "progress", "journey",
    ],
    "social_proof": [
        "everyone", "thousands", "millions", "we did it", "results",
        "proof", "income report", "screenshot", "testimonial",
        "community", "movement", "join us",
    ],
}


@dataclass
class EmotionAnalysis:
    post_id: str
    primary_emotion: str
    secondary_emotion: str | None
    scores: dict[str, float]      # emotion -> score 0.0-1.0
    polarity: float               # -1.0 to 1.0 (negative to positive)
    subjectivity: float           # 0.0 to 1.0


class EmotionCluster:
    def __init__(self):
        self._compiled: dict[str, list[re.Pattern]] = {
            emotion: [re.compile(r"\b" + re.escape(kw) + r"\b", re.IGNORECASE) for kw in keywords]
            for emotion, keywords in EMOTION_LEXICON.items()
        }

    def _score_text(self, text: str) -> dict[str, float]:
        text_lower = text.lower()
        word_count = max(len(text.split()), 1)
        scores: dict[str, float] = {}
        for emotion, patterns in self._compiled.items():
            hits = sum(1 for p in patterns if p.search(text_lower))
            scores[emotion] = min(hits / word_count * 20, 1.0)
        return scores

    def _simple_polarity(self, text: str) -> float:
        """Simple rule-based polarity without heavy NLP dependency."""
        positive_words = ["success", "win", "grow", "freedom", "achieve", "rich", "love", "great"]
        negative_words = ["fail", "lose", "broke", "trap", "scam", "lie", "slave", "debt"]
        pos = sum(1 for w in positive_words if w in text.lower())
        neg = sum(1 for w in negative_words if w in text.lower())
        total = pos + neg
        if total == 0:
            return 0.0
        return (pos - neg) / total

    def analyze(self, post: TrendPost) -> EmotionAnalysis:
        scores = self._score_text(post.content_text)
        sorted_emotions = sorted(scores.items(), key=lambda x: -x[1])
        primary = sorted_emotions[0][0] if sorted_emotions else "unknown"
        secondary = sorted_emotions[1][0] if len(sorted_emotions) > 1 and sorted_emotions[1][1] > 0 else None
        polarity = self._simple_polarity(post.content_text)
        return EmotionAnalysis(
            post_id=post.post_id,
            primary_emotion=primary,
            secondary_emotion=secondary,
            scores=scores,
            polarity=polarity,
            subjectivity=min(sum(scores.values()), 1.0),
        )

    def analyze_batch(self, posts: list[TrendPost]) -> list[EmotionAnalysis]:
        return [self.analyze(p) for p in posts]

    def dominant_emotions(self, analyses: list[EmotionAnalysis]) -> dict[str, int]:
        counts: dict[str, int] = {}
        for a in analyses:
            counts[a.primary_emotion] = counts.get(a.primary_emotion, 0) + 1
        return dict(sorted(counts.items(), key=lambda x: -x[1]))
