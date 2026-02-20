"""
Runway Gen-3 API client.
Sends scene prompts to Runway and downloads the generated video clips.

API docs: https://docs.dev.runwayml.com
Authentication: Bearer token + X-Runway-Version header
"""
import asyncio
import logging
import os
import time
from dataclasses import dataclass

import httpx

logger = logging.getLogger(__name__)

_RUNWAY_API_BASE = "https://api.dev.runwayml.com/v1"
_RUNWAY_VERSION = "2024-11-06"

# Polling config
_POLL_INTERVAL_SECONDS = 5
_MAX_POLL_ATTEMPTS = 60   # 5 min max wait per clip


@dataclass
class GeneratedClip:
    scene_index: int
    visual_prompt: str
    clip_duration: int
    local_path: str
    task_id: str


class RunwayClient:
    """
    Async client for Runway Gen-3 Turbo text-to-video generation.

    Usage:
        async with RunwayClient(api_key) as client:
            clips = await client.generate_scenes(scene_bundle, output_dir)
    """

    def __init__(self, api_key: str = ""):
        self._api_key = api_key or os.getenv("RUNWAYML_API_KEY", "")
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> "RunwayClient":
        self._client = httpx.AsyncClient(
            base_url=_RUNWAY_API_BASE,
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "X-Runway-Version": _RUNWAY_VERSION,
                "Content-Type": "application/json",
            },
            timeout=60.0,
        )
        return self

    async def __aexit__(self, *_) -> None:
        if self._client:
            await self._client.aclose()

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    async def generate_scenes(
        self,
        scenes: list,               # list[VideoScene] from scene_prompt_generator
        output_dir: str,
    ) -> list[GeneratedClip]:
        """
        Generate one video clip per scene, in parallel (max 3 at a time
        to respect Runway rate limits), then download all clips.
        Returns list of GeneratedClip with local file paths.
        """
        os.makedirs(output_dir, exist_ok=True)

        # Submit all tasks first (rate-limited to 3 concurrent)
        semaphore = asyncio.Semaphore(3)
        task_ids: list[tuple[int, str]] = []

        async def submit_scene(scene) -> tuple[int, str] | None:
            async with semaphore:
                task_id = await self._submit_task(scene)
                if task_id:
                    logger.info(f"[runway] scene {scene.index} submitted → task {task_id}")
                    return (scene.index, task_id)
                return None

        results = await asyncio.gather(*[submit_scene(s) for s in scenes])
        task_ids = [r for r in results if r is not None]

        # Poll and download each clip
        clips: list[GeneratedClip] = []
        for scene_index, task_id in task_ids:
            scene = next(s for s in scenes if s.index == scene_index)
            video_url = await self._poll_task(task_id)
            if not video_url:
                logger.warning(f"[runway] scene {scene_index} failed or timed out")
                continue

            local_path = os.path.join(output_dir, f"scene_{scene_index:02d}.mp4")
            await self._download_clip(video_url, local_path)
            clips.append(GeneratedClip(
                scene_index=scene_index,
                visual_prompt=scene.visual_prompt,
                clip_duration=scene.clip_duration,
                local_path=local_path,
                task_id=task_id,
            ))
            logger.info(f"[runway] scene {scene_index} downloaded → {local_path}")

        return sorted(clips, key=lambda c: c.scene_index)

    # ------------------------------------------------------------------ #
    # Internals
    # ------------------------------------------------------------------ #

    async def _submit_task(self, scene) -> str | None:
        """Submit a text-to-video task. Returns task_id or None on error."""
        payload = {
            "taskType": "gen3a_turbo",
            "internal": False,
            "options": {
                "promptText": scene.visual_prompt,
                "duration": scene.clip_duration,
                "ratio": "768:1344",    # 9:16 vertical (TikTok/Reels/Shorts)
                "exploreMode": False,
                "watermark": False,
            },
        }
        try:
            resp = await self._client.post("/tasks", json=payload)
            resp.raise_for_status()
            data = resp.json()
            return data.get("id") or data.get("task_id")
        except httpx.HTTPStatusError as e:
            logger.error(f"[runway] task submit failed: {e.response.status_code} {e.response.text}")
            return None
        except Exception as e:
            logger.error(f"[runway] task submit error: {e}")
            return None

    async def _poll_task(self, task_id: str) -> str | None:
        """Poll task until succeeded or failed. Returns video URL or None."""
        for attempt in range(_MAX_POLL_ATTEMPTS):
            await asyncio.sleep(_POLL_INTERVAL_SECONDS)
            try:
                resp = await self._client.get(f"/tasks/{task_id}")
                resp.raise_for_status()
                data = resp.json()
                status = data.get("status", "")

                if status == "SUCCEEDED":
                    output = data.get("output") or []
                    return output[0] if output else None

                if status in ("FAILED", "CANCELLED"):
                    logger.warning(f"[runway] task {task_id} ended with status={status}")
                    return None

                logger.debug(f"[runway] task {task_id} status={status} (attempt {attempt + 1})")

            except Exception as e:
                logger.error(f"[runway] poll error task {task_id}: {e}")

        logger.error(f"[runway] task {task_id} timed out after {_MAX_POLL_ATTEMPTS} polls")
        return None

    async def _download_clip(self, url: str, local_path: str) -> None:
        """Download a video clip from URL to local path."""
        async with httpx.AsyncClient(timeout=120.0) as dl_client:
            async with dl_client.stream("GET", url) as resp:
                resp.raise_for_status()
                with open(local_path, "wb") as f:
                    async for chunk in resp.aiter_bytes(chunk_size=8192):
                        f.write(chunk)
