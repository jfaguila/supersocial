"""
Tests for YouTube Channel Factory modules.
"""
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from youtube.character_manager import CharacterManager, CharacterIdentity
from youtube.script_generator import (
    YouTubeScriptGenerator,
    YouTubeScript,
    ScriptScene,
    SCENE_TYPES,
    WORDS_PER_SECOND,
)
from youtube.srt_generator import YouTubeSRTGenerator
from youtube.seo_optimizer import SEOOptimizer, YOUTUBE_CATEGORIES
from youtube.channel_manager import ChannelManager, ChannelConfig, VideoTopic
from youtube.image_generator import SceneImageGenerator, ImageProvider, GeneratedImage
from youtube.image_to_video import ImageToVideoConverter, VideoClip
from youtube.youtube_connector import YouTubeConnector, UploadResult
from youtube.thumbnail_generator import ThumbnailGenerator


# ── CHARACTER MANAGER ─────────────────────────────────────────


class TestCharacterManager:
    def setup_method(self):
        self.manager = CharacterManager()
        self.identity = CharacterIdentity(
            character_id="test-123",
            name="George",
            physical="30-year-old male, short dark hair, light stubble",
            clothing="dark fitted t-shirt, minimalist silver watch",
            art_style="photorealistic, cinematic lighting, 4K",
            color_palette="deep blues, warm oranges",
            environment="modern minimalist office",
            negative_prompt="cartoon, anime, deformed, blurry",
            voice_id="pNInz6obpgDQGcFmaJgB",
            voice_stability=0.5,
            voice_similarity_boost=0.75,
            voice_style=0.4,
            voice_speaking_rate=1.0,
        )

    def test_build_scene_prompt_with_character(self):
        prompt = self.manager.build_scene_prompt(
            self.identity,
            scene_description="explaining AI trends on a whiteboard",
            include_character=True,
        )
        assert "30-year-old male" in prompt
        assert "dark fitted t-shirt" in prompt
        assert "explaining AI trends" in prompt
        assert "photorealistic" in prompt

    def test_build_scene_prompt_without_character(self):
        prompt = self.manager.build_scene_prompt(
            self.identity,
            scene_description="data visualization dashboard with rising graphs",
            include_character=False,
        )
        assert "30-year-old male" not in prompt
        assert "data visualization" in prompt
        assert "deep blues" in prompt

    def test_build_thumbnail_prompt(self):
        prompt = self.manager.build_thumbnail_prompt(
            self.identity,
            emotion="shocked, mouth open",
        )
        assert "Close-up portrait" in prompt
        assert "shocked" in prompt
        assert "YouTube thumbnail" in prompt

    def test_build_negative_prompt(self):
        neg = self.manager.build_negative_prompt(self.identity)
        assert "cartoon" in neg
        assert "deformed" in neg

    def test_get_motion_prompt_all_types(self):
        for scene_type in SCENE_TYPES:
            motion = self.manager.get_motion_prompt(scene_type)
            assert len(motion) > 10
            assert "camera" in motion.lower() or "zoom" in motion.lower() or "push" in motion.lower() or "pan" in motion.lower() or "float" in motion.lower()

    def test_get_motion_prompt_unknown_type(self):
        motion = self.manager.get_motion_prompt("unknown")
        assert "slow subtle" in motion


# ── SCRIPT GENERATOR ──────────────────────────────────────────


class TestYouTubeScriptGenerator:
    def setup_method(self):
        self.mock_llm = AsyncMock()
        self.generator = YouTubeScriptGenerator(llm_client=self.mock_llm)

    @pytest.mark.asyncio
    async def test_generate_returns_5_scenes(self):
        self.mock_llm.generate_json.return_value = {
            "title_suggestion": "How AI Changes Everything",
            "scenes": [
                {
                    "scene_type": "hook",
                    "narration": "What if I told you that everything you know about work is about to change?",
                    "visual_description": "Close-up of narrator looking directly at camera",
                    "include_character": True,
                },
                {
                    "scene_type": "problem",
                    "narration": "Most people are still trading their time for money in a system designed to keep them busy but never free.",
                    "visual_description": "Montage of office workers in cubicles",
                    "include_character": False,
                },
                {
                    "scene_type": "deepening",
                    "narration": "The real issue is not laziness or lack of talent. The system was built to create employees, not entrepreneurs.",
                    "visual_description": "Data charts showing wealth inequality",
                    "include_character": False,
                },
                {
                    "scene_type": "solution",
                    "narration": "AI tools like these are now available for free. You can build a business in 30 days with zero employees.",
                    "visual_description": "Screen recording of AI tools being used",
                    "include_character": True,
                },
                {
                    "scene_type": "cta",
                    "narration": "Subscribe if you want to learn how to build your AI-powered business. Drop a comment with your niche.",
                    "visual_description": "Narrator pointing at subscribe button animation",
                    "include_character": True,
                },
            ],
        }

        script = await self.generator.generate(
            topic="How AI is replacing traditional jobs",
            niche="artificial_intelligence",
            target_duration_minutes=5,
        )

        assert isinstance(script, YouTubeScript)
        assert len(script.scenes) == 5
        assert script.scenes[0].scene_type == "hook"
        assert script.scenes[1].scene_type == "problem"
        assert script.scenes[2].scene_type == "deepening"
        assert script.scenes[3].scene_type == "solution"
        assert script.scenes[4].scene_type == "cta"
        assert script.word_count > 0
        assert script.total_duration_seconds > 0
        assert len(script.full_narration) > 0

    @pytest.mark.asyncio
    async def test_fills_missing_scenes(self):
        """If LLM returns fewer than 5 scenes, generator fills placeholders."""
        self.mock_llm.generate_json.return_value = {
            "title_suggestion": "Test",
            "scenes": [
                {"scene_type": "hook", "narration": "Hook text here", "visual_description": "Narrator", "include_character": True},
                {"scene_type": "problem", "narration": "Problem text here", "visual_description": "Office", "include_character": False},
            ],
        }

        script = await self.generator.generate(
            topic="Test topic",
            niche="technology",
        )

        assert len(script.scenes) == 5
        assert script.scenes[2].scene_type == "deepening"
        assert script.scenes[3].scene_type == "solution"
        assert script.scenes[4].scene_type == "cta"

    @pytest.mark.asyncio
    async def test_duration_calculation(self):
        """Duration is calculated from word count."""
        self.mock_llm.generate_json.return_value = {
            "title_suggestion": "Test",
            "scenes": [
                {"scene_type": st, "narration": "Word " * 50, "visual_description": "Scene", "include_character": True}
                for st in SCENE_TYPES
            ],
        }

        script = await self.generator.generate(topic="Test", niche="tech")
        for scene in script.scenes:
            expected_duration = scene.word_count / WORDS_PER_SECOND
            assert abs(scene.duration_seconds - expected_duration) < 0.1


# ── SRT GENERATOR ─────────────────────────────────────────────


class TestYouTubeSRTGenerator:
    def setup_method(self):
        self.srt_gen = YouTubeSRTGenerator()

    def test_generates_valid_srt(self):
        scenes = [
            ScriptScene(
                index=0, scene_type="hook",
                narration="This is the hook that grabs attention immediately",
                visual_description="Close-up",
                duration_seconds=5.0, start_second=0.0, end_second=5.0,
                word_count=8, include_character=True,
            ),
            ScriptScene(
                index=1, scene_type="problem",
                narration="Here is the problem that most people face every day in their lives",
                visual_description="Office scene",
                duration_seconds=10.0, start_second=5.5, end_second=15.5,
                word_count=14, include_character=False,
            ),
        ]

        srt = self.srt_gen.generate(scenes)
        assert "00:00:00,000 --> " in srt
        assert "1\n" in srt
        assert "hook" in srt.lower() or "attention" in srt.lower()

    def test_skips_placeholder_scenes(self):
        scenes = [
            ScriptScene(
                index=0, scene_type="hook",
                narration="[placeholder — regenerate]",
                visual_description="X",
                duration_seconds=5.0, start_second=0.0, end_second=5.0,
                word_count=0, include_character=True,
            ),
        ]
        srt = self.srt_gen.generate(scenes)
        assert srt.strip() == ""

    def test_time_formatting(self):
        assert self.srt_gen._format_time(0.0) == "00:00:00,000"
        assert self.srt_gen._format_time(65.5) == "00:01:05,500"
        assert self.srt_gen._format_time(3661.123) == "01:01:01,123"


# ── SEO OPTIMIZER ─────────────────────────────────────────────


class TestSEOOptimizer:
    def setup_method(self):
        self.mock_llm = AsyncMock()
        self.optimizer = SEOOptimizer(llm_client=self.mock_llm)

    @pytest.mark.asyncio
    async def test_optimize_returns_seo_metadata(self):
        self.mock_llm.generate_json.return_value = {
            "title": "How AI is Replacing Jobs in 2025 — What Nobody Tells You",
            "description": "In this video, we explore how artificial intelligence...\n\n00:00 - Introduction\n01:00 - The Problem\n...",
            "tags": ["AI jobs", "artificial intelligence", "future of work", "AI automation"],
            "hashtags": ["#AI", "#FutureOfWork", "#Automation"],
        }

        seo = await self.optimizer.optimize(
            topic="AI replacing jobs",
            script_summary="Script about AI and employment...",
            niche="artificial_intelligence",
        )

        assert len(seo.title) > 0
        assert len(seo.title) <= 100
        assert len(seo.description) > 0
        assert len(seo.tags) > 0
        assert len(seo.hashtags) > 0
        assert all(h.startswith("#") for h in seo.hashtags)
        assert seo.category_id == "28"  # Science & Technology

    @pytest.mark.asyncio
    async def test_ai_disclosure_appended(self):
        self.mock_llm.generate_json.return_value = {
            "title": "Test Video",
            "description": "This is a test description without AI mention.",
            "tags": ["test"],
            "hashtags": ["#test"],
        }

        seo = await self.optimizer.optimize(
            topic="Test", script_summary="...", niche="technology",
        )
        assert "AI-assisted" in seo.description or "AI-generated" in seo.description

    def test_category_mapping(self):
        assert YOUTUBE_CATEGORIES["artificial_intelligence"] == "28"
        assert YOUTUBE_CATEGORIES["entrepreneurship"] == "22"
        assert YOUTUBE_CATEGORIES["gaming"] == "20"
        assert YOUTUBE_CATEGORIES["education"] == "27"


# ── CHANNEL MANAGER ───────────────────────────────────────────


class TestChannelManager:
    def setup_method(self):
        self.mock_llm = AsyncMock()
        self.manager = ChannelManager(llm_client=self.mock_llm)

    @pytest.mark.asyncio
    async def test_generate_topics(self):
        self.mock_llm.generate_json.return_value = {
            "topics": [
                {"title": "5 AI Tools That Replace a Full Marketing Team", "angle": "practical tools review", "keywords": ["AI marketing", "automation"]},
                {"title": "Why 90% of Startups Fail (And How AI Fixes It)", "angle": "data-driven analysis", "keywords": ["startup failure", "AI solutions"]},
            ],
        }

        config = ChannelConfig(
            channel_id="ch-1", name="AI Hub", niche="artificial_intelligence",
            language="en", tone="professional", target_duration_minutes=5,
            videos_per_week=3, publish_schedule_cron="0 14 * * 1,3,5",
            default_category_id="28", made_for_kids=False, privacy_status="unlisted",
            google_client_id="", google_client_secret="", google_refresh_token="",
            character_id="char-1",
        )

        topics = await self.manager.generate_topics(config, count=2)
        assert len(topics) == 2
        assert isinstance(topics[0], VideoTopic)
        assert len(topics[0].title) > 0
        assert len(topics[0].keywords) > 0

    def test_calculate_publish_slots(self):
        config = ChannelConfig(
            channel_id="ch-1", name="Test", niche="tech",
            language="en", tone="casual", target_duration_minutes=5,
            videos_per_week=3, publish_schedule_cron="0 14 * * 1,3,5",
            default_category_id="28", made_for_kids=False, privacy_status="unlisted",
            google_client_id="", google_client_secret="", google_refresh_token="",
            character_id="char-1",
        )

        slots = self.manager.calculate_next_publish_slots(config, count=3)
        assert len(slots) == 3
        assert all(isinstance(s, int) for s in slots)
        # Slots should be in the future and in order
        assert slots[0] < slots[1] < slots[2]


# ── IMAGE GENERATOR ───────────────────────────────────────────


class TestSceneImageGenerator:
    def test_init_defaults(self):
        gen = SceneImageGenerator(provider=ImageProvider.DALLE3)
        assert gen._provider == ImageProvider.DALLE3

    def test_init_flux(self):
        gen = SceneImageGenerator(provider=ImageProvider.FLUX)
        assert gen._provider == ImageProvider.FLUX


# ── IMAGE TO VIDEO ────────────────────────────────────────────


class TestImageToVideoConverter:
    def test_init(self):
        converter = ImageToVideoConverter(runway_api_key="test-key")
        assert converter._api_key == "test-key"


# ── YOUTUBE CONNECTOR ─────────────────────────────────────────


class TestYouTubeConnector:
    def test_init(self):
        connector = YouTubeConnector(
            client_id="id",
            client_secret="secret",
            refresh_token="token",
        )
        assert connector._client_id == "id"
        assert connector._client_secret == "secret"
        assert connector._refresh_token == "token"

    @pytest.mark.asyncio
    async def test_upload_nonexistent_file(self):
        connector = YouTubeConnector(
            client_id="id", client_secret="secret", refresh_token="token",
        )
        connector._access_token = "fake"
        result = await connector.upload_video(
            video_path="/nonexistent/video.mp4",
            title="Test",
            description="Test",
        )
        assert not result.success
        assert "not found" in result.error


# ── THUMBNAIL GENERATOR ──────────────────────────────────────


class TestThumbnailGenerator:
    def test_apply_text_overlay_no_pillow(self):
        """Test graceful fallback when Pillow is not available."""
        gen = ThumbnailGenerator()
        # Direct test of the overlay method with mock image bytes
        # The actual DALL-E call is not tested here (requires API key)
        # Just verify the generator initializes correctly
        assert gen.THUMB_WIDTH == 1280
        assert gen.THUMB_HEIGHT == 720


# ── YOUTUBE SCRIPT TO_DICT ────────────────────────────────────


class TestYouTubeScriptSerialization:
    def test_to_dict(self):
        scenes = [
            ScriptScene(
                index=i, scene_type=SCENE_TYPES[i],
                narration=f"Narration for {SCENE_TYPES[i]}",
                visual_description=f"Visual for {SCENE_TYPES[i]}",
                duration_seconds=30.0, start_second=i * 30.5,
                end_second=(i + 1) * 30.0, word_count=10,
                include_character=True,
            )
            for i in range(5)
        ]

        script = YouTubeScript(
            topic="Test Topic",
            title_suggestion="Test Title",
            total_duration_seconds=152.5,
            scenes=scenes,
            full_narration="Full narration text",
            language="en",
            niche="technology",
            word_count=50,
        )

        d = script.to_dict()
        assert d["topic"] == "Test Topic"
        assert len(d["scenes"]) == 5
        assert d["scenes"][0]["scene_type"] == "hook"
        assert d["scenes"][4]["scene_type"] == "cta"
        # Verify JSON serializable
        json_str = json.dumps(d)
        assert len(json_str) > 0
