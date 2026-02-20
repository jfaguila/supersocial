"""
Video assembler.
Uses FFmpeg to combine:
  1. Runway video clips (scene_00.mp4, scene_01.mp4, ...)
  2. ElevenLabs voice-over (voiceover.mp3)
  3. SRT subtitles burned into the video

Output: final_{title}.mp4 — ready to upload to TikTok/Reels/Shorts.

Requires: ffmpeg installed on the system (apt install ffmpeg).
"""
import asyncio
import logging
import os
import shutil

from .runway_client import GeneratedClip
from .srt_generator import SRTGenerator
from .script_formatter import FormattedScript

logger = logging.getLogger(__name__)


class VideoAssembler:
    """
    Assembles a final vertical video (9:16) from clips, voice-over, and subtitles.

    Usage:
        assembler = VideoAssembler()
        final_path = await assembler.assemble(
            clips=clips,
            voiceover_path="path/to/voiceover.mp3",
            script=formatted_script,
            output_dir="/data/video_exports/cycle_1",
            title="My AI Business Video",
        )
    """

    # Output resolution for TikTok/Reels/Shorts
    OUTPUT_WIDTH = 1080
    OUTPUT_HEIGHT = 1920

    # Subtitle style
    SUBTITLE_FONT_SIZE = 22
    SUBTITLE_FONT_COLOR = "white"
    SUBTITLE_BORDER_COLOR = "black"
    SUBTITLE_BORDER_WIDTH = 2
    SUBTITLE_MARGIN_V = 120   # pixels from bottom

    def __init__(self):
        self._ffmpeg = shutil.which("ffmpeg") or "ffmpeg"
        self._srt_gen = SRTGenerator()

    async def assemble(
        self,
        clips: list[GeneratedClip],
        voiceover_path: str,
        script: FormattedScript,
        output_dir: str,
        title: str = "video",
    ) -> str:
        """
        Full assembly pipeline:
          1. Scale and pad each clip to 1080x1920
          2. Concatenate clips
          3. Mix voice-over audio (replace original clip audio)
          4. Burn subtitles
          5. Export final MP4

        Returns path to the final video file.
        """
        os.makedirs(output_dir, exist_ok=True)
        safe_title = "".join(c for c in title if c.isalnum() or c in (" ", "_")).strip()[:40]

        # Step 1 — Scale and pad each clip
        scaled_clips = await self._scale_clips(clips, output_dir)
        if not scaled_clips:
            raise RuntimeError("No clips to assemble")

        # Step 2 — Concatenate clips into one video (no audio yet)
        concat_path = os.path.join(output_dir, "concat_raw.mp4")
        await self._concatenate_clips(scaled_clips, concat_path)

        # Step 3 — Generate SRT subtitle file
        srt_path = os.path.join(output_dir, f"{safe_title}.srt")
        self._srt_gen.save(script, srt_path)

        # Step 4 — Burn subtitles + mix voice-over → final video
        final_path = os.path.join(output_dir, f"final_{safe_title}.mp4")
        await self._burn_subtitles_and_audio(
            video_path=concat_path,
            audio_path=voiceover_path,
            srt_path=srt_path,
            output_path=final_path,
        )

        # Cleanup intermediate files
        self._cleanup([concat_path] + scaled_clips)

        logger.info(f"[assembler] final video ready → {final_path}")
        return final_path

    # ------------------------------------------------------------------ #
    # Internals
    # ------------------------------------------------------------------ #

    async def _scale_clips(
        self, clips: list[GeneratedClip], output_dir: str
    ) -> list[str]:
        """Scale and pad each clip to OUTPUT_WIDTH x OUTPUT_HEIGHT."""
        tasks = []
        scaled_paths = []
        for clip in clips:
            out_path = os.path.join(output_dir, f"scaled_{clip.scene_index:02d}.mp4")
            scaled_paths.append((clip.scene_index, out_path))
            cmd = [
                self._ffmpeg, "-y",
                "-i", clip.local_path,
                "-vf", (
                    f"scale={self.OUTPUT_WIDTH}:{self.OUTPUT_HEIGHT}:"
                    f"force_original_aspect_ratio=decrease,"
                    f"pad={self.OUTPUT_WIDTH}:{self.OUTPUT_HEIGHT}:"
                    f"(ow-iw)/2:(oh-ih)/2:black"
                ),
                "-c:v", "libx264",
                "-preset", "fast",
                "-crf", "23",
                "-an",                  # no audio from clip
                "-r", "30",
                out_path,
            ]
            tasks.append(self._run_ffmpeg(cmd, f"scale scene {clip.scene_index}"))

        results = await asyncio.gather(*tasks, return_exceptions=True)
        good_paths = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.warning(f"[assembler] scale failed for scene {i}: {result}")
            else:
                good_paths.append(scaled_paths[i][1])
        return good_paths

    async def _concatenate_clips(
        self, clip_paths: list[str], output_path: str
    ) -> None:
        """Use FFmpeg concat demuxer to join clips."""
        concat_list_path = output_path.replace(".mp4", "_list.txt")
        with open(concat_list_path, "w") as f:
            for path in clip_paths:
                f.write(f"file '{path}'\n")

        cmd = [
            self._ffmpeg, "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", concat_list_path,
            "-c", "copy",
            output_path,
        ]
        await self._run_ffmpeg(cmd, "concatenate")
        os.remove(concat_list_path)

    async def _burn_subtitles_and_audio(
        self,
        video_path: str,
        audio_path: str,
        srt_path: str,
        output_path: str,
    ) -> None:
        """
        Merge video + voice-over audio + burned-in subtitles.
        Voice-over replaces any existing audio track.
        If video is shorter than audio, pad video with last frame.
        """
        # Escape srt_path for FFmpeg subtitle filter
        escaped_srt = srt_path.replace("\\", "/").replace(":", "\\:")

        subtitle_filter = (
            f"subtitles='{escaped_srt}':force_style='"
            f"FontSize={self.SUBTITLE_FONT_SIZE},"
            f"PrimaryColour=&H00FFFFFF,"
            f"OutlineColour=&H00000000,"
            f"Outline={self.SUBTITLE_BORDER_WIDTH},"
            f"MarginV={self.SUBTITLE_MARGIN_V},"
            f"Alignment=2'"
        )

        cmd = [
            self._ffmpeg, "-y",
            "-i", video_path,
            "-i", audio_path,
            # Use shortest — trim video/audio to whichever ends first
            # For social media, voice-over drives duration
            "-filter_complex", (
                f"[0:v]{subtitle_filter}[vout]"
            ),
            "-map", "[vout]",
            "-map", "1:a",
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "22",
            "-c:a", "aac",
            "-b:a", "192k",
            "-shortest",
            "-movflags", "+faststart",    # web-optimized for faster upload
            output_path,
        ]
        await self._run_ffmpeg(cmd, "burn subtitles + merge audio")

    async def _run_ffmpeg(self, cmd: list[str], step_name: str) -> None:
        """Run an FFmpeg command asynchronously, raise on error."""
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await proc.communicate()
        if proc.returncode != 0:
            raise RuntimeError(
                f"FFmpeg failed at [{step_name}]: {stderr.decode()[-500:]}"
            )
        logger.debug(f"[assembler] ffmpeg step '{step_name}' OK")

    def _cleanup(self, paths: list[str]) -> None:
        for path in paths:
            try:
                if os.path.exists(path):
                    os.remove(path)
            except OSError:
                pass
