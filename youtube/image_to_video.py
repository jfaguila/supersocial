"""
Image-to-video converter — Converts scene images into video clips.

Uses Runway Gen-3 Alpha Turbo in image-to-video mode.
Each static image becomes an animated clip with camera motion.

The motion prompt (e.g., "slow zoom in") is provided by CharacterManager
based on the scene type.
"""
import asyncio
import logging
import os
from dataclasses import dataclass

import httpx

from .image_generator import GeneratedImage

logger = logging.getLogger(__name__)

_RUNWAY_API_BASE = "https://api.dev.runwayml.com/v1"
_RUNWAY_VERSION = "2024-11-06"
_POLL_INTERVAL = 5
_MAX_POLL_ATTEMPTS = 60  # 5 min max per clip


@dataclass
class VideoClip:
    scene_index: int
    scene_type: str
    local_path: str
    duration_seconds: int
    source_image_path: str
    motion_prompt: str


class ImageToVideoConverter:
    """
    Converts static scene images into animated video clips using
    Runway Gen-3 Alpha Turbo (image-to-video mode).
    """

    def __init__(self, runway_api_key: str = ""):
        self._api_key = runway_api_key or os.getenv("RUNWAYML_API_KEY", "")

    async def convert_scenes(
        self,
        images: list[GeneratedImage],
        motion_prompts: dict[int, str],
        clip_durations: dict[int, int],
        output_dir: str,
    ) -> list[VideoClip]:
        """
        Convert scene images to video clips.

        Args:
            images: Generated scene images
            motion_prompts: {scene_index: "camera motion description"}
            clip_durations: {scene_index: 5 or 10} seconds
            output_dir: Directory to save clips
        """
        os.makedirs(output_dir, exist_ok=True)

        # Runway allows max 3 concurrent tasks
        semaphore = asyncio.Semaphore(3)

        async def convert_one(image: GeneratedImage) -> VideoClip | None:
            async with semaphore:
                motion = motion_prompts.get(image.scene_index, "slow subtle camera movement")
                duration = clip_durations.get(image.scene_index, 5)
                return await self._convert_single(
                    image=image,
                    motion_prompt=motion,
                    duration=duration,
                    output_dir=output_dir,
                )

        results = await asyncio.gather(
            *[convert_one(img) for img in images],
            return_exceptions=True,
        )

        clips = []
        for r in results:
            if isinstance(r, Exception):
                logger.error(f"[img2vid] conversion failed: {r}")
            elif r is not None:
                clips.append(r)

        return sorted(clips, key=lambda c: c.scene_index)

    async def _convert_single(
        self,
        image: GeneratedImage,
        motion_prompt: str,
        duration: int,
        output_dir: str,
    ) -> VideoClip | None:
        """Convert a single image to a video clip via Runway."""
        async with httpx.AsyncClient(
            base_url=_RUNWAY_API_BASE,
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "X-Runway-Version": _RUNWAY_VERSION,
                "Content-Type": "application/json",
            },
            timeout=60.0,
        ) as client:
            # Step 1: Read image and encode as data URI
            import base64
            with open(image.local_path, "rb") as f:
                image_bytes = f.read()
            mime = "image/png" if image.local_path.endswith(".png") else "image/jpeg"
            data_uri = f"data:{mime};base64,{base64.b64encode(image_bytes).decode()}"

            # Step 2: Submit image-to-video task
            payload = {
                "taskType": "gen3a_turbo",
                "internal": False,
                "options": {
                    "promptImage": data_uri,
                    "promptText": motion_prompt,
                    "duration": duration,
                    "ratio": "1344:768",  # 16:9 landscape
                    "exploreMode": False,
                    "watermark": False,
                },
            }

            try:
                resp = await client.post("/tasks", json=payload)
                resp.raise_for_status()
                task_id = resp.json().get("id") or resp.json().get("task_id")
                if not task_id:
                    logger.error(f"[img2vid] no task_id returned for scene {image.scene_index}")
                    return None

                logger.info(
                    f"[img2vid] scene {image.scene_index} submitted → task {task_id}"
                )

                # Step 3: Poll for completion
                video_url = await self._poll_task(client, task_id)
                if not video_url:
                    return None

                # Step 4: Download clip
                local_path = os.path.join(
                    output_dir, f"clip_{image.scene_index:02d}.mp4"
                )
                await self._download_clip(video_url, local_path)

                logger.info(f"[img2vid] scene {image.scene_index} → {local_path}")
                return VideoClip(
                    scene_index=image.scene_index,
                    scene_type=image.scene_type,
                    local_path=local_path,
                    duration_seconds=duration,
                    source_image_path=image.local_path,
                    motion_prompt=motion_prompt,
                )

            except httpx.HTTPStatusError as e:
                logger.error(
                    f"[img2vid] scene {image.scene_index} failed: "
                    f"{e.response.status_code} {e.response.text[:200]}"
                )
                return None
            except Exception as e:
                logger.error(f"[img2vid] scene {image.scene_index} error: {e}")
                return None

    async def _poll_task(
        self, client: httpx.AsyncClient, task_id: str,
    ) -> str | None:
        """Poll Runway task until completed or failed."""
        for attempt in range(_MAX_POLL_ATTEMPTS):
            await asyncio.sleep(_POLL_INTERVAL)
            try:
                resp = await client.get(f"/tasks/{task_id}")
                resp.raise_for_status()
                data = resp.json()
                status = data.get("status", "")

                if status == "SUCCEEDED":
                    output = data.get("output") or []
                    return output[0] if output else None

                if status in ("FAILED", "CANCELLED"):
                    logger.warning(f"[img2vid] task {task_id} ended: {status}")
                    return None

            except Exception as e:
                logger.error(f"[img2vid] poll error {task_id}: {e}")

        logger.error(f"[img2vid] task {task_id} timed out")
        return None

    async def _download_clip(self, url: str, local_path: str) -> None:
        """Download video clip from URL."""
        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream("GET", url) as resp:
                resp.raise_for_status()
                with open(local_path, "wb") as f:
                    async for chunk in resp.aiter_bytes(chunk_size=8192):
                        f.write(chunk)
