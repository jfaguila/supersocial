"""
Scene image generator — Creates images for each scene of a YouTube video.

Supports:
    - OpenAI DALL-E 3 (primary) — best prompt adherence
    - Replicate Flux 1.1 Pro (low-cost alternative)

Each image is 1920x1080 (16:9) and incorporates the character's visual
identity for consistency across videos.
"""
import asyncio
import logging
import os
from dataclasses import dataclass
from enum import Enum

import httpx

logger = logging.getLogger(__name__)


class ImageProvider(str, Enum):
    DALLE3 = "dalle3"
    FLUX = "flux"


@dataclass
class GeneratedImage:
    scene_index: int
    scene_type: str
    local_path: str
    prompt_used: str
    provider: str
    width: int = 1792
    height: int = 1024


_DALLE_API_URL = "https://api.openai.com/v1/images/generations"
_REPLICATE_API_URL = "https://api.replicate.com/v1/predictions"
_FLUX_MODEL = "black-forest-labs/flux-1.1-pro"


class SceneImageGenerator:
    """
    Generates one image per scene using DALL-E 3 or Flux 1.1 Pro.
    Character identity is injected into prompts by CharacterManager
    before reaching this class.
    """

    def __init__(
        self,
        openai_api_key: str = "",
        replicate_api_key: str = "",
        provider: ImageProvider = ImageProvider.DALLE3,
    ):
        self._openai_key = openai_api_key or os.getenv("OPENAI_API_KEY", "")
        self._replicate_key = replicate_api_key or os.getenv("REPLICATE_API_TOKEN", "")
        self._provider = provider

    async def generate_scene_images(
        self,
        scene_prompts: list[dict],
        output_dir: str,
        negative_prompt: str = "",
    ) -> list[GeneratedImage]:
        """
        Generate images for all scenes.

        Args:
            scene_prompts: list of {"index": int, "scene_type": str, "prompt": str}
            output_dir: Directory to save images
            negative_prompt: What to avoid in images
        """
        os.makedirs(output_dir, exist_ok=True)

        # Generate images with concurrency limit (2 at a time to respect rate limits)
        semaphore = asyncio.Semaphore(2)
        tasks = []

        for sp in scene_prompts:
            tasks.append(
                self._generate_with_semaphore(
                    semaphore=semaphore,
                    prompt=sp["prompt"],
                    scene_index=sp["index"],
                    scene_type=sp["scene_type"],
                    output_dir=output_dir,
                    negative_prompt=negative_prompt,
                )
            )

        results = await asyncio.gather(*tasks, return_exceptions=True)
        images = []
        for r in results:
            if isinstance(r, Exception):
                logger.error(f"[image_gen] scene failed: {r}")
            elif r is not None:
                images.append(r)

        return sorted(images, key=lambda img: img.scene_index)

    async def _generate_with_semaphore(
        self,
        semaphore: asyncio.Semaphore,
        prompt: str,
        scene_index: int,
        scene_type: str,
        output_dir: str,
        negative_prompt: str,
    ) -> GeneratedImage | None:
        async with semaphore:
            if self._provider == ImageProvider.DALLE3:
                return await self._generate_dalle3(
                    prompt, scene_index, scene_type, output_dir,
                )
            else:
                return await self._generate_flux(
                    prompt, scene_index, scene_type, output_dir, negative_prompt,
                )

    async def _generate_dalle3(
        self,
        prompt: str,
        scene_index: int,
        scene_type: str,
        output_dir: str,
    ) -> GeneratedImage | None:
        """Generate an image using OpenAI DALL-E 3."""
        async with httpx.AsyncClient(timeout=120.0) as client:
            try:
                resp = await client.post(
                    _DALLE_API_URL,
                    headers={
                        "Authorization": f"Bearer {self._openai_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": "dall-e-3",
                        "prompt": prompt,
                        "n": 1,
                        "size": "1792x1024",  # Landscape 16:9 (closest DALL-E supports)
                        "quality": "hd",
                        "response_format": "url",
                    },
                )
                resp.raise_for_status()
                data = resp.json()
                image_url = data["data"][0]["url"]

                # Download the image
                local_path = os.path.join(output_dir, f"scene_{scene_index:02d}.png")
                await self._download_image(client, image_url, local_path)

                logger.info(f"[image_gen] DALL-E 3 scene {scene_index} → {local_path}")
                return GeneratedImage(
                    scene_index=scene_index,
                    scene_type=scene_type,
                    local_path=local_path,
                    prompt_used=prompt,
                    provider="dalle3",
                    width=1792,
                    height=1024,
                )

            except httpx.HTTPStatusError as e:
                logger.error(
                    f"[image_gen] DALL-E 3 failed scene {scene_index}: "
                    f"{e.response.status_code} {e.response.text[:200]}"
                )
                return None
            except Exception as e:
                logger.error(f"[image_gen] DALL-E 3 error scene {scene_index}: {e}")
                return None

    async def _generate_flux(
        self,
        prompt: str,
        scene_index: int,
        scene_type: str,
        output_dir: str,
        negative_prompt: str,
    ) -> GeneratedImage | None:
        """Generate an image using Replicate Flux 1.1 Pro."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            try:
                # Create prediction
                resp = await client.post(
                    _REPLICATE_API_URL,
                    headers={
                        "Authorization": f"Bearer {self._replicate_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "version": _FLUX_MODEL,
                        "input": {
                            "prompt": prompt,
                            "negative_prompt": negative_prompt,
                            "width": 1920,
                            "height": 1080,
                            "num_inference_steps": 28,
                            "guidance_scale": 3.5,
                        },
                    },
                )
                resp.raise_for_status()
                prediction = resp.json()
                prediction_id = prediction["id"]

                # Poll for completion
                image_url = await self._poll_replicate(client, prediction_id)
                if not image_url:
                    return None

                local_path = os.path.join(output_dir, f"scene_{scene_index:02d}.png")
                await self._download_image(client, image_url, local_path)

                logger.info(f"[image_gen] Flux scene {scene_index} → {local_path}")
                return GeneratedImage(
                    scene_index=scene_index,
                    scene_type=scene_type,
                    local_path=local_path,
                    prompt_used=prompt,
                    provider="flux",
                    width=1920,
                    height=1080,
                )

            except Exception as e:
                logger.error(f"[image_gen] Flux error scene {scene_index}: {e}")
                return None

    async def _poll_replicate(
        self, client: httpx.AsyncClient, prediction_id: str, max_attempts: int = 60,
    ) -> str | None:
        """Poll Replicate prediction until completed."""
        headers = {
            "Authorization": f"Bearer {self._replicate_key}",
        }
        for _ in range(max_attempts):
            await asyncio.sleep(3)
            resp = await client.get(
                f"{_REPLICATE_API_URL}/{prediction_id}",
                headers=headers,
            )
            data = resp.json()
            status = data.get("status", "")

            if status == "succeeded":
                output = data.get("output")
                if isinstance(output, list) and output:
                    return output[0]
                if isinstance(output, str):
                    return output
                return None

            if status in ("failed", "canceled"):
                logger.warning(f"[image_gen] Replicate prediction {prediction_id} {status}")
                return None

        logger.error(f"[image_gen] Replicate prediction {prediction_id} timed out")
        return None

    async def _download_image(
        self, client: httpx.AsyncClient, url: str, local_path: str,
    ) -> None:
        """Download an image from URL to local path."""
        async with client.stream("GET", url) as resp:
            resp.raise_for_status()
            with open(local_path, "wb") as f:
                async for chunk in resp.aiter_bytes(chunk_size=8192):
                    f.write(chunk)
