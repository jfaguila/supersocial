"""
Video script formatter.
Takes raw LLM script output and formats it for teleprompter display
and AI video rendering tools.
"""
import re
from dataclasses import dataclass, field


@dataclass
class ScriptSegment:
    index: int
    start_second: float
    end_second: float
    text: str
    segment_type: str   # hook|body|cta


@dataclass
class FormattedScript:
    title: str
    platform: str
    total_duration_seconds: float
    segments: list[ScriptSegment]
    teleprompter_text: str
    word_count: int
    estimated_wpm: int = 130   # average speaking pace


class ScriptFormatter:
    WORDS_PER_SECOND = 130 / 60  # ~2.17 words/sec

    def format(self, raw_script: str, platform: str, title: str = "") -> FormattedScript:
        """Parse raw script and produce timed segments."""
        lines = [l.strip() for l in raw_script.strip().split("\n") if l.strip()]

        segments: list[ScriptSegment] = []
        current_time = 0.0
        idx = 0

        for line in lines:
            # Skip empty or label lines like "HOOK:", "BODY:", "CTA:"
            if re.match(r"^(HOOK|BODY|CTA|INTRO|OUTRO)\s*[\:\-]?\s*$", line, re.IGNORECASE):
                continue

            words = line.split()
            if not words:
                continue

            duration = len(words) / self.WORDS_PER_SECOND
            seg_type = self._classify_segment(idx, len(lines), line)

            segments.append(
                ScriptSegment(
                    index=idx,
                    start_second=round(current_time, 2),
                    end_second=round(current_time + duration, 2),
                    text=line,
                    segment_type=seg_type,
                )
            )
            current_time += duration + 0.3  # 300ms pause between lines
            idx += 1

        total_words = sum(len(s.text.split()) for s in segments)
        teleprompter = self._build_teleprompter(segments)

        return FormattedScript(
            title=title or f"{platform.capitalize()} Script",
            platform=platform,
            total_duration_seconds=round(current_time, 1),
            segments=segments,
            teleprompter_text=teleprompter,
            word_count=total_words,
        )

    def _classify_segment(self, idx: int, total: int, text: str) -> str:
        if idx == 0:
            return "hook"
        if idx >= total - 2:
            return "cta"
        return "body"

    def _build_teleprompter(self, segments: list[ScriptSegment]) -> str:
        """Produce a clean teleprompter-ready text with segment markers."""
        lines = []
        for seg in segments:
            marker = f"[{seg.segment_type.upper()}]" if seg.segment_type != "body" else ""
            if marker:
                lines.append(f"\n{marker}")
            lines.append(seg.text)
        return "\n".join(lines).strip()
