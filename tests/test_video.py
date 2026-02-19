"""
Tests for video pipeline.
"""
import pytest
from video.script_formatter import ScriptFormatter
from video.srt_generator import SRTGenerator


class TestScriptFormatter:
    def setup_method(self):
        self.formatter = ScriptFormatter()

    def test_formats_script_into_segments(self):
        raw = """Stop. Nobody told you this about money.
Here's what the rich know that you don't.
Build assets, not income. Build systems, not jobs.
Your time is worth more than your salary.
Follow me for more truths they don't teach in school."""
        result = self.formatter.format(raw, platform="tiktok", title="Money Test")
        assert len(result.segments) > 0
        assert result.total_duration_seconds > 0
        assert result.word_count > 0

    def test_first_segment_is_hook(self):
        raw = "Hook line here.\nBody content follows.\nCTA at the end."
        result = self.formatter.format(raw, "tiktok")
        assert result.segments[0].segment_type == "hook"

    def test_last_segment_is_cta(self):
        raw = "Hook.\nBody 1.\nBody 2.\nCTA line."
        result = self.formatter.format(raw, "instagram")
        assert result.segments[-1].segment_type == "cta"

    def test_teleprompter_text_not_empty(self):
        raw = "This is a script.\nWith multiple lines.\nAnd a CTA."
        result = self.formatter.format(raw, "tiktok")
        assert len(result.teleprompter_text) > 0


class TestSRTGenerator:
    def setup_method(self):
        self.formatter = ScriptFormatter()
        self.srt_gen = SRTGenerator()

    def test_generates_valid_srt(self):
        raw = "This is the hook.\nThis is the body content.\nFollow for more."
        script = self.formatter.format(raw, "tiktok")
        srt = self.srt_gen.generate(script)
        assert "00:00:00,000 --> " in srt
        assert "1\n" in srt

    def test_srt_has_correct_entry_count(self):
        raw = "Line one.\nLine two.\nLine three."
        script = self.formatter.format(raw, "tiktok")
        srt = self.srt_gen.generate(script)
        # Count number-only lines (entry indexes)
        entries = [l for l in srt.split("\n") if l.strip().isdigit()]
        assert len(entries) == len(script.segments)
