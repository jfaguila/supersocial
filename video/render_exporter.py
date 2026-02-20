"""
Video pipeline orchestrator.
Replaces the old HeyGen/Runway stub exporter with a full
AI-generated video pipeline:

  ScenePromptGenerator  →  RunwayClient  →  ElevenLabsClient  →  VideoAssembler
                                                                       ↓
                                                               final_video.mp4

George calls VideoPipeline.run() for every video_script post.
"""
import logging
import os
import time
from dataclasses import dataclass

from .script_formatter import FormattedScript
from .scene_prompt_generator import ScenePromptGenerator
from .runway_client import RunwayClient
from .elevenlabs_client import ElevenLabsClient
from .video_assembler import VideoAssembler
from .srt_generator import SRTGenerator

logger = logging.getLogger(__name__)


@dataclass
class VideoResult:
    success: bool
    final_video_path: str = ""
    srt_path: str = ""
    scenes_count: int = 0
    duration_seconds: float = 0.0
    error: str = ""


class VideoPipeline:
    """
    Full autonomous AI video pipeline.

    Takes a formatted script and produces a ready-to-publish .mp4 video:
    1. Splits script into visual scenes with Runway prompts
    2. Generates each scene clip via Runway Gen-3
    3. Generates voice-over via ElevenLabs
    4. Assembles clips + voice + subtitles via FFmpeg

    Usage:
        pipeline = VideoPipeline(settings)
        result = await pipeline.run(
            script=formatted_script,
            output_dir="/data/video_exports/cycle_1",
            niches=["artificial_intelligence", "entrepreneurship"],
            business_context="AI automation agency",
        )
        if result.success:
            print(result.final_video_path)
    """

    def __init__(self, settings=None):
        from config.settings import get_settings
        self._settings = settings or get_settings()
        self._scene_generator = ScenePromptGenerator()
        self._assembler = VideoAssembler()
        self._srt_gen = SRTGenerator()

    async def run(
        self,
        script: FormattedScript,
        output_dir: str,
        niches: list[str] | None = None,
        business_context: str = "",
    ) -> VideoResult:
        """
        Run the full pipeline. Returns VideoResult with final video path.

        Args:
            script: FormattedScript from ScriptFormatter
            output_dir: Directory to save all output files
            niches: Content niches for visual context (e.g. ['artificial_intelligence'])
            business_context: Business description for visual prompts
        """
        start_time = time.time()
        safe_title = "".join(c for c in script.title if c.isalnum() or c in (" ", "_")).strip()[:40]
        run_dir = os.path.join(output_dir, f"{safe_title}_{int(start_time)}")
        os.makedirs(run_dir, exist_ok=True)

        try:
            # --- Step 1: Generate scene prompts ---
            logger.info(f"[video_pipeline] generating scene prompts for '{script.title}'")
            scene_bundle = self._scene_generator.generate(
                script=script,
                niches=niches or [],
                business_context=business_context,
            )
            logger.info(f"[video_pipeline] {len(scene_bundle.scenes)} scenes ready")

            # --- Step 2: Generate video clips with Runway ---
            logger.info("[video_pipeline] submitting scenes to Runway Gen-3")
            runway_api_key = getattr(self._settings, "runwayml_api_key", "")
            async with RunwayClient(api_key=runway_api_key) as runway:
                clips = await runway.generate_scenes(
                    scenes=scene_bundle.scenes,
                    output_dir=os.path.join(run_dir, "clips"),
                )

            if not clips:
                return VideoResult(
                    success=False,
                    error="Runway returned no clips — check API key and credits",
                )
            logger.info(f"[video_pipeline] {len(clips)} clips downloaded from Runway")

            # --- Step 3: Generate voice-over with ElevenLabs ---
            logger.info("[video_pipeline] generating voice-over with ElevenLabs")
            voiceover_path = os.path.join(run_dir, "voiceover.mp3")
            elevenlabs_api_key = getattr(self._settings, "elevenlabs_api_key", "")
            elevenlabs_voice_id = getattr(self._settings, "elevenlabs_voice_id", "")
            async with ElevenLabsClient(
                api_key=elevenlabs_api_key,
                voice_id=elevenlabs_voice_id,
            ) as eleven:
                await eleven.generate_voiceover(
                    narration_text=scene_bundle.full_narration,
                    output_path=voiceover_path,
                )
            logger.info(f"[video_pipeline] voice-over saved → {voiceover_path}")

            # --- Step 4: Assemble final video ---
            logger.info("[video_pipeline] assembling final video with FFmpeg")
            final_video_path = await self._assembler.assemble(
                clips=clips,
                voiceover_path=voiceover_path,
                script=script,
                output_dir=run_dir,
                title=script.title,
            )

            # Save SRT separately for reference
            srt_path = os.path.join(run_dir, f"{safe_title}.srt")
            self._srt_gen.save(script, srt_path)

            elapsed = round(time.time() - start_time, 1)
            logger.info(
                f"[video_pipeline] DONE in {elapsed}s → {final_video_path}"
            )

            return VideoResult(
                success=True,
                final_video_path=final_video_path,
                srt_path=srt_path,
                scenes_count=len(clips),
                duration_seconds=script.total_duration_seconds,
            )

        except Exception as e:
            logger.error(f"[video_pipeline] pipeline failed: {e}")
            return VideoResult(success=False, error=str(e))
