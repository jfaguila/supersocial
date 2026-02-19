"""
SRT subtitle file generator.
Takes a FormattedScript and produces a valid .srt subtitle file.
"""
from .script_formatter import FormattedScript, ScriptSegment


def _format_srt_time(seconds: float) -> str:
    """Convert float seconds to SRT timestamp format HH:MM:SS,mmm"""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds - int(seconds)) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


class SRTGenerator:
    MAX_CHARS_PER_LINE = 42   # industry standard subtitle width
    MAX_LINES = 2

    def generate(self, script: FormattedScript) -> str:
        """Generate SRT content as a string."""
        entries = []
        for seg in script.segments:
            # Split long lines
            lines = self._wrap_text(seg.text)
            entries.append(
                f"{seg.index + 1}\n"
                f"{_format_srt_time(seg.start_second)} --> {_format_srt_time(seg.end_second)}\n"
                f"{chr(10).join(lines)}\n"
            )
        return "\n".join(entries)

    def _wrap_text(self, text: str) -> list[str]:
        """Wrap text to max line length."""
        words = text.split()
        lines: list[str] = []
        current_line = ""
        for word in words:
            if len(current_line) + len(word) + 1 <= self.MAX_CHARS_PER_LINE:
                current_line = f"{current_line} {word}".strip()
            else:
                if current_line:
                    lines.append(current_line)
                current_line = word
                if len(lines) >= self.MAX_LINES:
                    break
        if current_line and len(lines) < self.MAX_LINES:
            lines.append(current_line)
        return lines if lines else [text[:self.MAX_CHARS_PER_LINE]]

    def save(self, script: FormattedScript, path: str) -> None:
        srt_content = self.generate(script)
        with open(path, "w", encoding="utf-8") as f:
            f.write(srt_content)
