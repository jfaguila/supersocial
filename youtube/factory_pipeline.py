"""
YouTube Factory Pipeline — Main orchestrator.

Chains all YouTube Factory modules into a single production pipeline:

    Topic → Script → Voice → Images → Video Clips → Assembly → Thumbnail → SEO → Upload

This is the primary entry point for producing and publishing YouTube videos.
George's weekly cycle calls FactoryPipeline.produce() for each scheduled video.
"""
import logging
import os
import time
from dataclasses import dataclass

from config.settings import get_settings

from .character_manager import CharacterManager, CharacterIdentity
from .script_generator import YouTubeScriptGenerator, YouTubeScript
from .image_generator import SceneImageGenerator, ImageProvider
from .image_to_video import ImageToVideoConverter
from .youtube_assembler import YouTubeAssembler
from .srt_generator import YouTubeSRTGenerator
from .thumbnail_generator import ThumbnailGenerator
from .seo_optimizer import SEOOptimizer
from .youtube_connector import YouTubeConnector, UploadResult
from .channel_manager import ChannelConfig

from content.llm_client import LLMClient
from video.elevenlabs_client import ElevenLabsClient

logger = logging.getLogger(__name__)


@dataclass
class ProductionResult:
    """Result of a full video production pipeline run."""
    success: bool
    video_id: str = ""
    youtube_url: str = ""
    video_file_path: str = ""
    thumbnail_file_path: str = ""
    voiceover_file_path: str = ""
    srt_file_path: str = ""
    title: str = ""
    description: str = ""
    duration_seconds: float = 0.0
    scenes_count: int = 0
    script: YouTubeScript | None = None
    error: str = ""
    pipeline_duration_seconds: float = 0.0


class FactoryPipeline:
    """
    Full YouTube video production pipeline.

    Usage:
        pipeline = FactoryPipeline()
        result = await pipeline.produce(
            topic="How AI is replacing traditional jobs in 2025",
            channel_config=channel_config,
            character_identity=character_identity,
            output_dir="/data/youtube_exports/channel_1",
        )
        if result.success:
            print(f"Published: {result.youtube_url}")
    """

    def __init__(self, settings=None):
        self._settings = settings or get_settings()
        self._llm = LLMClient()
        self._char_manager = CharacterManager()
        self._script_gen = YouTubeScriptGenerator(self._llm)
        self._image_gen = SceneImageGenerator(
            openai_api_key=self._settings.openai_api_key,
        )
        self._img2vid = ImageToVideoConverter(
            runway_api_key=getattr(self._settings, "runwayml_api_key", ""),
        )
        self._assembler = YouTubeAssembler()
        self._srt_gen = YouTubeSRTGenerator()
        self._thumb_gen = ThumbnailGenerator(
            openai_api_key=self._settings.openai_api_key,
        )
        self._seo = SEOOptimizer(self._llm)

    async def produce(
        self,
        topic: str,
        channel_config: ChannelConfig,
        character_identity: CharacterIdentity,
        output_dir: str,
        upload: bool = True,
    ) -> ProductionResult:
        """
        Run the full production pipeline for a single video.

        Args:
            topic: Video topic/concept
            channel_config: Channel settings
            character_identity: Character visual/voice identity
            output_dir: Base output directory
            upload: Whether to upload to YouTube (False for dry runs)

        Returns:
            ProductionResult with all file paths and YouTube metadata.
        """
        start_time = time.time()
        safe_topic = "".join(
            c for c in topic if c.isalnum() or c in (" ", "_")
        ).strip()[:40]
        run_dir = os.path.join(output_dir, f"{safe_topic}_{int(start_time)}")
        os.makedirs(run_dir, exist_ok=True)

        try:
            # ── PHASE 1: SCRIPT GENERATION ──────────────────────────
            logger.info(f"[factory] Phase 1: Generating script for '{topic}'")
            script = await self._script_gen.generate(
                topic=topic,
                niche=channel_config.niche,
                tone=channel_config.tone,
                target_duration_minutes=channel_config.target_duration_minutes,
                language=channel_config.language,
                character_name=character_identity.name,
            )
            logger.info(
                f"[factory] Script ready: {script.word_count} words, "
                f"{script.total_duration_seconds:.0f}s, {len(script.scenes)} scenes"
            )

            # ── PHASE 2: VOICE GENERATION ───────────────────────────
            logger.info("[factory] Phase 2: Generating voice-over")
            voiceover_path = os.path.join(run_dir, "voiceover.mp3")
            elevenlabs_key = getattr(self._settings, "elevenlabs_api_key", "")
            voice_id = character_identity.voice_id or getattr(
                self._settings, "elevenlabs_voice_id", ""
            )
            async with ElevenLabsClient(
                api_key=elevenlabs_key,
                voice_id=voice_id,
            ) as eleven:
                await eleven.generate_voiceover(
                    narration_text=script.full_narration,
                    output_path=voiceover_path,
                    stability=character_identity.voice_stability,
                    similarity_boost=character_identity.voice_similarity_boost,
                    style=character_identity.voice_style,
                    speaking_rate=character_identity.voice_speaking_rate,
                )
            logger.info(f"[factory] Voice-over saved → {voiceover_path}")

            # ── PHASE 3: SCENE IMAGE GENERATION ─────────────────────
            logger.info("[factory] Phase 3: Generating scene images")
            scene_prompts = []
            for scene in script.scenes:
                prompt = self._char_manager.build_scene_prompt(
                    identity=character_identity,
                    scene_description=scene.visual_description,
                    include_character=scene.include_character,
                )
                scene_prompts.append({
                    "index": scene.index,
                    "scene_type": scene.scene_type,
                    "prompt": prompt,
                })

            images_dir = os.path.join(run_dir, "images")
            images = await self._image_gen.generate_scene_images(
                scene_prompts=scene_prompts,
                output_dir=images_dir,
                negative_prompt=self._char_manager.build_negative_prompt(character_identity),
            )

            if not images:
                return ProductionResult(
                    success=False,
                    error="Image generation failed — no images produced",
                )
            logger.info(f"[factory] {len(images)} scene images generated")

            # ── PHASE 4: IMAGE-TO-VIDEO CONVERSION ──────────────────
            logger.info("[factory] Phase 4: Converting images to video clips")
            motion_prompts = {}
            clip_durations = {}
            for scene in script.scenes:
                motion_prompts[scene.index] = self._char_manager.get_motion_prompt(
                    scene.scene_type,
                )
                # Clip duration based on narration length:
                # Scenes with >60 words get 10s clips, rest get 5s
                clip_durations[scene.index] = 10 if scene.word_count > 60 else 5

            clips_dir = os.path.join(run_dir, "clips")
            clips = await self._img2vid.convert_scenes(
                images=images,
                motion_prompts=motion_prompts,
                clip_durations=clip_durations,
                output_dir=clips_dir,
            )

            if not clips:
                return ProductionResult(
                    success=False,
                    error="Image-to-video conversion failed — no clips produced",
                )
            logger.info(f"[factory] {len(clips)} video clips generated")

            # ── PHASE 5: VIDEO ASSEMBLY ─────────────────────────────
            logger.info("[factory] Phase 5: Assembling final video")
            srt_path = os.path.join(run_dir, f"{safe_topic}.srt")
            self._srt_gen.save(script.scenes, srt_path)

            final_video_path = await self._assembler.assemble(
                clips=clips,
                voiceover_path=voiceover_path,
                srt_path=srt_path,
                output_dir=run_dir,
                title=safe_topic,
            )
            logger.info(f"[factory] Final video → {final_video_path}")

            # ── PHASE 6: THUMBNAIL GENERATION ───────────────────────
            logger.info("[factory] Phase 6: Generating thumbnail")
            thumb_prompt = self._char_manager.build_thumbnail_prompt(
                identity=character_identity,
                emotion="confident, engaged, looking at camera",
                background_context=script.scenes[0].visual_description[:100] if script.scenes else "",
            )
            thumbnail_path = os.path.join(run_dir, "thumbnail.jpg")
            await self._thumb_gen.generate(
                image_prompt=thumb_prompt,
                title_text=topic[:30],
                output_path=thumbnail_path,
            )
            logger.info(f"[factory] Thumbnail → {thumbnail_path}")

            # ── PHASE 7: SEO OPTIMIZATION ───────────────────────────
            logger.info("[factory] Phase 7: Generating SEO metadata")
            seo = await self._seo.optimize(
                topic=topic,
                script_summary=script.full_narration,
                niche=channel_config.niche,
                language=channel_config.language,
                channel_name=channel_config.name,
            )
            logger.info(f"[factory] SEO title: '{seo.title}'")

            # ── PHASE 8: YOUTUBE UPLOAD ─────────────────────────────
            video_id = ""
            youtube_url = ""

            if upload:
                logger.info("[factory] Phase 8: Uploading to YouTube")
                connector = YouTubeConnector(
                    client_id=channel_config.google_client_id,
                    client_secret=channel_config.google_client_secret,
                    refresh_token=channel_config.google_refresh_token,
                )

                # Build description with hashtags at top
                hashtag_line = " ".join(seo.hashtags[:3])
                full_description = f"{hashtag_line}\n\n{seo.description}"

                upload_result = await connector.upload_video(
                    video_path=final_video_path,
                    title=seo.title,
                    description=full_description,
                    tags=seo.tags,
                    category_id=seo.category_id,
                    privacy_status=channel_config.privacy_status,
                    made_for_kids=channel_config.made_for_kids,
                    is_ai_generated=True,
                )

                if upload_result.success:
                    video_id = upload_result.video_id
                    youtube_url = upload_result.youtube_url

                    # Upload thumbnail
                    await connector.upload_thumbnail(video_id, thumbnail_path)
                    logger.info(f"[factory] Published → {youtube_url}")
                else:
                    logger.error(f"[factory] Upload failed: {upload_result.error}")
                    return ProductionResult(
                        success=False,
                        error=f"Upload failed: {upload_result.error}",
                        video_file_path=final_video_path,
                        thumbnail_file_path=thumbnail_path,
                        voiceover_file_path=voiceover_path,
                        srt_file_path=srt_path,
                        title=seo.title,
                        description=full_description,
                        script=script,
                    )
            else:
                logger.info("[factory] Upload skipped (dry run mode)")

            elapsed = round(time.time() - start_time, 1)
            logger.info(f"[factory] COMPLETE in {elapsed}s")

            return ProductionResult(
                success=True,
                video_id=video_id,
                youtube_url=youtube_url,
                video_file_path=final_video_path,
                thumbnail_file_path=thumbnail_path,
                voiceover_file_path=voiceover_path,
                srt_file_path=srt_path,
                title=seo.title,
                description=seo.description,
                duration_seconds=script.total_duration_seconds,
                scenes_count=len(script.scenes),
                script=script,
                pipeline_duration_seconds=elapsed,
            )

        except Exception as e:
            elapsed = round(time.time() - start_time, 1)
            logger.error(f"[factory] Pipeline failed after {elapsed}s: {e}")
            return ProductionResult(
                success=False,
                error=str(e),
                pipeline_duration_seconds=elapsed,
            )
