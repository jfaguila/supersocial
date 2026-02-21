"""
YouTube SRT subtitle generator.

Generates SRT files from YouTubeScript scenes.
Optimized for YouTube viewing:
    - Larger text blocks (max 50 chars/line)
    - 2 lines maximum
    - Scene-type markers in timing
"""
import os
import textwrap
from dataclasses import dataclass


class YouTubeSRTGenerator:
    """Generates SRT subtitle files from YouTube scripts."""

    MAX_LINE_WIDTH = 50   # Characters per line (wider for YouTube 16:9)
    MAX_LINES = 2

    def generate(self, scenes: list) -> str:
        """
        Generate SRT content from a list of ScriptScene objects.
        Returns the SRT string.
        """
        entries = []
        entry_index = 1

        for scene in scenes:
            narration = scene.narration.strip()
            if not narration or narration.startswith("["):
                continue

            # Split narration into subtitle chunks (~8-10 words each)
            words = narration.split()
            chunks = []
            current_chunk: list[str] = []

            for word in words:
                current_chunk.append(word)
                if len(current_chunk) >= 8:
                    chunks.append(" ".join(current_chunk))
                    current_chunk = []

            if current_chunk:
                chunks.append(" ".join(current_chunk))

            if not chunks:
                continue

            # Distribute timing evenly across chunks within the scene
            scene_duration = scene.end_second - scene.start_second
            chunk_duration = scene_duration / len(chunks)

            for i, chunk in enumerate(chunks):
                start = scene.start_second + (i * chunk_duration)
                end = start + chunk_duration

                # Wrap text to max line width
                wrapped = textwrap.fill(
                    chunk, width=self.MAX_LINE_WIDTH, max_lines=self.MAX_LINES,
                )

                entries.append(
                    f"{entry_index}\n"
                    f"{self._format_time(start)} --> {self._format_time(end)}\n"
                    f"{wrapped}\n"
                )
                entry_index += 1

        return "\n".join(entries)

    def save(self, scenes: list, output_path: str) -> str:
        """Generate and save SRT file."""
        srt_content = self.generate(scenes)
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(srt_content)
        return output_path

    def _format_time(self, seconds: float) -> str:
        """Format seconds into SRT time format: HH:MM:SS,mmm"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"
