"""
YouTube video assembler — 16:9 montage with audio sync.

Assembles the final YouTube video from:
    - Scene video clips (from image-to-video conversion)
    - Voice-over audio (from ElevenLabs)
    - Subtitles (generated SRT)

Output: 1920x1080 H.264 MP4, optimized for YouTube upload.

Key differences from the existing TikTok assembler:
    - 16:9 landscape (1920x1080) instead of 9:16 vertical
    - Cross-dissolve transitions between scenes
    - Larger subtitle font (28pt vs 22pt)
    - Higher bitrate for YouTube quality
    - Intro/outro padding support
"""
import asyncio
import logging
import os
import shutil

from .image_to_video import VideoClip

logger = logging.getLogger(__name__)


class YouTubeAssembler:
    """
    Assembles a final 16:9 YouTube video from clips, voice-over, and subtitles.
    """

    OUTPUT_WIDTH = 1920
    OUTPUT_HEIGHT = 1080

    # Subtitle style (larger for YouTube desktop viewing)
    SUBTITLE_FONT_SIZE = 28
    SUBTITLE_MARGIN_V = 60
    SUBTITLE_BORDER_WIDTH = 3

    # Cross-dissolve transition duration between scenes
    TRANSITION_DURATION = 0.5

    def __init__(self):
        self._ffmpeg = shutil.which("ffmpeg") or "ffmpeg"

    async def assemble(
        self,
        clips: list[VideoClip],
        voiceover_path: str,
        srt_path: str,
        output_dir: str,
        title: str = "video",
        intro_path: str | None = None,
        outro_path: str | None = None,
    ) -> str:
        """
        Full assembly pipeline:
            1. Scale/pad each clip to 1920x1080
            2. Add cross-dissolve transitions between clips
            3. Concatenate all clips
            4. Mix voice-over audio
            5. Burn subtitles
            6. Export final MP4 optimized for YouTube

        Returns path to the final video file.
        """
        os.makedirs(output_dir, exist_ok=True)
        safe_title = "".join(
            c for c in title if c.isalnum() or c in (" ", "_")
        ).strip()[:50]

        # Step 1: Scale and pad clips to output resolution
        scaled_clips = await self._scale_clips(clips, output_dir)
        if not scaled_clips:
            raise RuntimeError("No clips to assemble")

        # Step 1.5: Prepend intro / append outro if provided
        all_clips = []
        if intro_path and os.path.exists(intro_path):
            all_clips.append(intro_path)
        all_clips.extend(scaled_clips)
        if outro_path and os.path.exists(outro_path):
            all_clips.append(outro_path)

        # Step 2: Concatenate with cross-dissolve transitions
        concat_path = os.path.join(output_dir, "concat_raw.mp4")
        if len(all_clips) > 1:
            await self._concatenate_with_transitions(all_clips, concat_path)
        else:
            await self._concatenate_simple(all_clips, concat_path)

        # Step 3: Burn subtitles + mix voice-over
        final_path = os.path.join(output_dir, f"final_{safe_title}.mp4")
        await self._burn_subtitles_and_audio(
            video_path=concat_path,
            audio_path=voiceover_path,
            srt_path=srt_path,
            output_path=final_path,
        )

        # Cleanup intermediate files
        self._cleanup([concat_path] + scaled_clips)

        logger.info(f"[yt_assembler] final video → {final_path}")
        return final_path

    # ------------------------------------------------------------------ #
    # Internal pipeline steps
    # ------------------------------------------------------------------ #

    async def _scale_clips(
        self, clips: list[VideoClip], output_dir: str,
    ) -> list[str]:
        """Scale and pad each clip to 1920x1080."""
        tasks = []
        scaled_paths: list[tuple[int, str]] = []

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
                "-crf", "20",       # Higher quality than TikTok (CRF 23)
                "-an",              # Strip audio from clips
                "-r", "30",
                out_path,
            ]
            tasks.append(self._run_ffmpeg(cmd, f"scale scene {clip.scene_index}"))

        results = await asyncio.gather(*tasks, return_exceptions=True)
        good = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.warning(f"[yt_assembler] scale failed: {result}")
            else:
                good.append(scaled_paths[i][1])
        return good

    async def _concatenate_with_transitions(
        self, clip_paths: list[str], output_path: str,
    ) -> None:
        """
        Concatenate clips with xfade (cross-dissolve) transitions.
        Uses FFmpeg filter_complex for smooth scene transitions.
        """
        if len(clip_paths) < 2:
            await self._concatenate_simple(clip_paths, output_path)
            return

        # Build FFmpeg xfade filter chain
        # For N clips, we need N-1 xfade filters chained together
        inputs = []
        for path in clip_paths:
            inputs.extend(["-i", path])

        # Build the filter chain progressively
        # First xfade: [0:v][1:v]xfade=transition=fade:duration=0.5[v01]
        # Second: [v01][2:v]xfade=...=offset=X[v012]
        # etc.
        filter_parts = []
        td = self.TRANSITION_DURATION

        # We need to know clip durations for offset calculation
        # Approximate: use a fixed approach, trim to voice-over later
        # Each transition starts at (cumulative_duration - transition_duration)
        offset = 0.0
        prev_label = "[0:v]"

        for i in range(1, len(clip_paths)):
            next_input = f"[{i}:v]"
            out_label = f"[v{i}]" if i < len(clip_paths) - 1 else "[vout]"

            # Offset for xfade = when the transition starts
            # First clip default 5s, so first offset = 5 - 0.5 = 4.5
            if i == 1:
                offset = 4.5  # Default first clip assumed 5s
            else:
                offset += 4.5  # Each subsequent clip

            filter_parts.append(
                f"{prev_label}{next_input}xfade=transition=fade:"
                f"duration={td}:offset={offset}{out_label}"
            )
            prev_label = out_label

        filter_complex = ";".join(filter_parts)

        cmd = [
            self._ffmpeg, "-y",
            *inputs,
            "-filter_complex", filter_complex,
            "-map", "[vout]",
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "20",
            "-r", "30",
            output_path,
        ]

        try:
            await self._run_ffmpeg(cmd, "concatenate with transitions")
        except RuntimeError:
            # Fallback to simple concat if xfade fails (duration mismatch, etc.)
            logger.warning("[yt_assembler] xfade failed, falling back to simple concat")
            await self._concatenate_simple(clip_paths, output_path)

    async def _concatenate_simple(
        self, clip_paths: list[str], output_path: str,
    ) -> None:
        """Simple concat demuxer fallback."""
        concat_list = output_path.replace(".mp4", "_list.txt")
        with open(concat_list, "w") as f:
            for path in clip_paths:
                f.write(f"file '{path}'\n")

        cmd = [
            self._ffmpeg, "-y",
            "-f", "concat", "-safe", "0",
            "-i", concat_list,
            "-c", "copy",
            output_path,
        ]
        await self._run_ffmpeg(cmd, "simple concatenate")
        os.remove(concat_list)

    async def _burn_subtitles_and_audio(
        self,
        video_path: str,
        audio_path: str,
        srt_path: str,
        output_path: str,
    ) -> None:
        """
        Merge video + voice-over + burned subtitles.
        Voice-over drives the total duration (-shortest).
        """
        escaped_srt = srt_path.replace("\\", "/").replace(":", "\\:")

        subtitle_filter = (
            f"subtitles='{escaped_srt}':force_style='"
            f"FontSize={self.SUBTITLE_FONT_SIZE},"
            f"PrimaryColour=&H00FFFFFF,"
            f"OutlineColour=&H00000000,"
            f"Outline={self.SUBTITLE_BORDER_WIDTH},"
            f"MarginV={self.SUBTITLE_MARGIN_V},"
            f"Alignment=2,"
            f"BorderStyle=3,"
            f"BackColour=&H80000000'"
        )

        cmd = [
            self._ffmpeg, "-y",
            "-i", video_path,
            "-i", audio_path,
            "-filter_complex", f"[0:v]{subtitle_filter}[vout]",
            "-map", "[vout]",
            "-map", "1:a",
            "-c:v", "libx264",
            "-preset", "medium",    # Better compression for YouTube
            "-crf", "20",           # YouTube-grade quality
            "-c:a", "aac",
            "-b:a", "192k",
            "-ar", "44100",
            "-shortest",
            "-movflags", "+faststart",
            output_path,
        ]
        await self._run_ffmpeg(cmd, "burn subtitles + merge audio")

    async def _run_ffmpeg(self, cmd: list[str], step_name: str) -> None:
        """Run FFmpeg command asynchronously."""
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
        logger.debug(f"[yt_assembler] ffmpeg '{step_name}' OK")

    def _cleanup(self, paths: list[str]) -> None:
        for path in paths:
            try:
                if os.path.exists(path):
                    os.remove(path)
            except OSError:
                pass
