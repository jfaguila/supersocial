"""
Hook pattern detector.
Identifies the opening sentence structure of high-performing posts
and classifies it into actionable pattern types.
"""
import re
from dataclasses import dataclass

from data_layer.base_connector import TrendPost


HOOK_PATTERNS = {
    "question": [
        r"^(what|why|how|when|who|which|can|do|does|is|are|have|has|will|would|could|should)\b.+\?",
        r"^.+(secret|truth|reason).+\?$",
    ],
    "shock": [
        r"^(nobody|no one|everyone|most people).+(know|told|says|thinks|realizes)",
        r"^(stop|quit|never|don't|avoid)\b",
        r"^\d+\s*(things|reasons|ways|mistakes|facts|truths)",
        r"^(i was|i used to|i thought|i believed).+(wrong|broke|failed|stupid)",
    ],
    "promise": [
        r"^(how to|the secret to|the key to|the fastest way to)",
        r"^in \d+ (days?|weeks?|months?|years?)[,:]",
        r"^(this|one thing|a simple).+(changed|transformed|made me)",
        r"^(here's|here is) (how|what|why)",
    ],
    "story": [
        r"^(at \d+|when i was|years ago|back in \d+|i remember)",
        r"^(last (week|month|year)|yesterday|today)\b",
        r"^(my|our).+(story|journey|failure|success|mistake)",
    ],
    "contrast": [
        r"^(then vs\.? now|before.+after|rich.+poor|employee.+entrepreneur)",
        r"^(everyone.+but i|they.+but we|school taught.+but)",
        r"^\w+\.?\s+\w+\.\s+(now|but|however)",
    ],
    "identity": [
        r"^(if you're a|for the|this is for).+(entrepreneur|founder|freelancer|builder)",
        r"^(real entrepreneurs?|true freedom|the wealthy)\b",
    ],
}


@dataclass
class HookAnalysis:
    post_id: str
    hook_text: str
    hook_type: str          # question|shock|promise|story|contrast|identity|unknown
    confidence: float       # 0.0–1.0
    word_count: int


class HookDetector:
    def __init__(self):
        self._compiled: dict[str, list[re.Pattern]] = {
            htype: [re.compile(p, re.IGNORECASE | re.MULTILINE) for p in patterns]
            for htype, patterns in HOOK_PATTERNS.items()
        }

    def extract_hook(self, text: str) -> str:
        """Extract the first sentence / first line as the hook."""
        if not text:
            return ""
        # First line
        first_line = text.strip().split("\n")[0].strip()
        # First sentence (up to 30 words max)
        sentences = re.split(r"(?<=[.!?])\s+", first_line)
        hook = sentences[0] if sentences else first_line
        # Cap at 30 words
        words = hook.split()
        return " ".join(words[:30])

    def classify(self, hook_text: str) -> tuple[str, float]:
        """Returns (hook_type, confidence)."""
        if not hook_text:
            return "unknown", 0.0

        matches: list[tuple[str, int]] = []
        for htype, patterns in self._compiled.items():
            for pattern in patterns:
                if pattern.search(hook_text):
                    matches.append(htype)
                    break  # one match per type is enough

        if not matches:
            return "unknown", 0.2
        if len(matches) == 1:
            return matches[0], 0.9
        # Multiple matches — return highest priority
        priority = ["shock", "promise", "question", "story", "contrast", "identity"]
        for p in priority:
            if p in matches:
                return p, 0.7
        return matches[0], 0.6

    def analyze_batch(self, posts: list[TrendPost]) -> list[HookAnalysis]:
        results = []
        for post in posts:
            hook = self.extract_hook(post.content_text)
            htype, confidence = self.classify(hook)
            results.append(
                HookAnalysis(
                    post_id=post.post_id,
                    hook_text=hook,
                    hook_type=htype,
                    confidence=confidence,
                    word_count=len(hook.split()),
                )
            )
        return results

    def summarize_patterns(self, analyses: list[HookAnalysis]) -> dict[str, int]:
        """Count occurrences of each hook type in batch."""
        counts: dict[str, int] = {}
        for a in analyses:
            counts[a.hook_type] = counts.get(a.hook_type, 0) + 1
        return dict(sorted(counts.items(), key=lambda x: -x[1]))
