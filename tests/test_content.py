"""
Tests for content generation layer.
"""
import pytest
from content.platform_formatter import PlatformFormatter
from content.deduplication import DeduplicationGuard, jaccard_similarity


class TestPlatformFormatter:
    def setup_method(self):
        self.formatter = PlatformFormatter()

    def test_twitter_char_limit(self):
        long_text = "A" * 500
        result = self.formatter.format("twitter", long_text)
        assert result.char_count <= 280

    def test_hashtag_placement_at_end(self):
        text = "Build passive income today. #freedom is possible."
        result = self.formatter.format("linkedin", text, extra_hashtags=["#entrepreneur"])
        assert result.text.index("#") > result.text.index("Build")

    def test_valid_short_twitter_post(self):
        text = "Stop trading time for money. Build passive income instead."
        result = self.formatter.format("twitter", text)
        assert result.is_valid is True

    def test_max_hashtags_enforced(self):
        text = "Great content here"
        tags = [f"#tag{i}" for i in range(20)]
        result = self.formatter.format("instagram", text, extra_hashtags=tags)
        assert len(result.hashtags) <= 15


class TestDeduplication:
    def test_jaccard_identical(self):
        a = "The system is rigged against the average worker"
        assert jaccard_similarity(a, a) == 1.0

    def test_jaccard_different(self):
        a = "Build passive income streams for financial freedom"
        b = "The weather is nice today in the city"
        sim = jaccard_similarity(a, b)
        assert sim < 0.2

    def test_jaccard_partial_overlap(self):
        a = "Build passive income for financial freedom"
        b = "Build passive income today and retire early"
        sim = jaccard_similarity(a, b)
        assert sim > 0.3

    @pytest.mark.asyncio
    async def test_duplicate_detection(self, mock_repo):
        guard = DeduplicationGuard(mock_repo)
        text = "Nobody tells you this about money and freedom"
        guard.register(text)
        is_dup, reason = await guard.is_duplicate(text)
        assert is_dup is True
        assert "exact_hash_session" in reason

    @pytest.mark.asyncio
    async def test_unique_passes(self, mock_repo):
        guard = DeduplicationGuard(mock_repo)
        text1 = "Build wealth through passive income"
        text2 = "The education system failed us all completely"
        guard.register(text1)
        is_dup, reason = await guard.is_duplicate(text2)
        assert is_dup is False
