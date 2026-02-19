"""
Tests for the analysis engine.
"""
import pytest
from analysis.engagement import EngagementAnalyzer
from analysis.hook_detector import HookDetector
from analysis.emotion_cluster import EmotionCluster
from analysis.format_recognizer import FormatRecognizer
from analysis.trend_detector import TrendDetector


class TestEngagementAnalyzer:
    def test_analyze_returns_sorted_scores(self, sample_trend_posts):
        analyzer = EngagementAnalyzer()
        scores = analyzer.analyze(sample_trend_posts)
        assert len(scores) == len(sample_trend_posts)
        # Should be sorted descending
        for i in range(len(scores) - 1):
            assert scores[i].normalized_score >= scores[i + 1].normalized_score

    def test_tier_assignment(self, sample_trend_posts):
        analyzer = EngagementAnalyzer()
        scores = analyzer.analyze(sample_trend_posts)
        valid_tiers = {"S", "A", "B", "C", "D"}
        for score in scores:
            assert score.tier in valid_tiers

    def test_empty_input(self):
        analyzer = EngagementAnalyzer()
        assert analyzer.analyze([]) == []

    def test_platform_benchmark(self, sample_trend_posts):
        analyzer = EngagementAnalyzer()
        benchmarks = analyzer.platform_benchmark(sample_trend_posts)
        assert "twitter" in benchmarks
        assert "mean" in benchmarks["twitter"]


class TestHookDetector:
    def setup_method(self):
        self.detector = HookDetector()

    def test_extract_hook_gets_first_line(self):
        text = "Stop trading time for money.\nHere are 5 reasons why."
        hook = self.detector.extract_hook(text)
        assert hook == "Stop trading time for money."

    def test_classify_shock_hook(self):
        hook = "Nobody told you this about passive income"
        htype, confidence = self.detector.classify(hook)
        assert htype == "shock"
        assert confidence > 0.5

    def test_classify_question_hook(self):
        hook = "Why do most people stay broke their entire lives?"
        htype, confidence = self.detector.classify(hook)
        assert htype == "question"

    def test_classify_promise_hook(self):
        hook = "How to make $10K/month with zero experience"
        htype, confidence = self.detector.classify(hook)
        assert htype == "promise"

    def test_unknown_hook(self):
        hook = "Good morning everyone"
        htype, _ = self.detector.classify(hook)
        assert htype == "unknown"

    def test_batch_analysis(self, sample_trend_posts):
        analyses = self.detector.analyze_batch(sample_trend_posts)
        assert len(analyses) == len(sample_trend_posts)
        for a in analyses:
            assert a.hook_type in {"question", "shock", "promise", "story", "contrast", "identity", "unknown"}


class TestEmotionCluster:
    def setup_method(self):
        self.cluster = EmotionCluster()

    def test_detects_aspiration(self, sample_trend_posts):
        from data_layer.base_connector import TrendPost
        post = TrendPost(
            platform="twitter", post_id="1", author_id="a", author_username="u",
            author_follower_count=1000, content_text="Build wealth, achieve freedom, grow your passive income",
            content_type="text", published_at=0
        )
        result = self.cluster.analyze(post)
        assert result.primary_emotion in {"aspiration", "fear", "identity", "hope", "anger", "social_proof"}

    def test_batch_returns_all(self, sample_trend_posts):
        results = self.cluster.analyze_batch(sample_trend_posts)
        assert len(results) == len(sample_trend_posts)


class TestFormatRecognizer:
    def setup_method(self):
        self.recognizer = FormatRecognizer()

    def test_detects_list_format(self, sample_trend_posts):
        from data_layer.base_connector import TrendPost
        post = TrendPost(
            platform="twitter", post_id="1", author_id="a", author_username="u",
            author_follower_count=0, content_type="text", published_at=0,
            content_text="1. Build savings\n2. Invest wisely\n3. Cut expenses"
        )
        result = self.recognizer.analyze(post)
        assert result.format_type == "list"
        assert result.has_numbered_list is True

    def test_detects_cta(self, sample_trend_posts):
        from data_layer.base_connector import TrendPost
        post = TrendPost(
            platform="twitter", post_id="1", author_id="a", author_username="u",
            author_follower_count=0, content_type="text", published_at=0,
            content_text="This changed my life. Follow me for more insights."
        )
        result = self.recognizer.analyze(post)
        assert result.has_cta is True


class TestTrendDetector:
    def test_detect_returns_report(self, sample_trend_posts):
        detector = TrendDetector()
        report = detector.detect(sample_trend_posts)
        assert report.raw_post_count == len(sample_trend_posts)
        assert len(report.top_keywords) > 0
        assert "twitter" in report.platforms

    def test_empty_posts(self):
        detector = TrendDetector()
        report = detector.detect([])
        assert report.raw_post_count == 0
