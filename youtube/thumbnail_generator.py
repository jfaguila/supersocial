"""
YouTube thumbnail generator.

Creates eye-catching thumbnails by:
    1. Generating a base image via DALL-E 3 (character close-up)
    2. Overlaying bold title text with Pillow
    3. Exporting as 1280x720 JPEG (<2MB, YouTube spec)

Thumbnail best practices encoded:
    - Large face/character (occupies ~40% of frame)
    - High contrast, saturated colors
    - Max 3-5 words of text
    - Bold, outlined font
"""
import logging
import os
from io import BytesIO

import httpx

logger = logging.getLogger(__name__)

_DALLE_API_URL = "https://api.openai.com/v1/images/generations"


class ThumbnailGenerator:
    """
    Generates YouTube thumbnails with DALL-E 3 base + text overlay.
    """

    THUMB_WIDTH = 1280
    THUMB_HEIGHT = 720

    def __init__(self, openai_api_key: str = ""):
        self._openai_key = openai_api_key or os.getenv("OPENAI_API_KEY", "")

    async def generate(
        self,
        image_prompt: str,
        title_text: str,
        output_path: str,
    ) -> str:
        """
        Generate a YouTube thumbnail.

        Args:
            image_prompt: DALL-E prompt (from CharacterManager.build_thumbnail_prompt)
            title_text: Short text to overlay (3-5 words max)
            output_path: Where to save the final .jpg

        Returns:
            Path to the saved thumbnail.
        """
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        # Step 1: Generate base image with DALL-E 3
        base_image_bytes = await self._generate_base_image(image_prompt)
        if not base_image_bytes:
            logger.error("[thumbnail] failed to generate base image")
            raise RuntimeError("Thumbnail base image generation failed")

        # Step 2: Apply text overlay with Pillow
        final_bytes = self._apply_text_overlay(base_image_bytes, title_text)

        # Step 3: Save as JPEG
        with open(output_path, "wb") as f:
            f.write(final_bytes)

        size_kb = len(final_bytes) // 1024
        logger.info(f"[thumbnail] saved → {output_path} ({size_kb}KB)")
        return output_path

    async def _generate_base_image(self, prompt: str) -> bytes | None:
        """Generate the base thumbnail image via DALL-E 3."""
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
                        "size": "1792x1024",
                        "quality": "hd",
                        "response_format": "url",
                    },
                )
                resp.raise_for_status()
                image_url = resp.json()["data"][0]["url"]

                # Download the image
                dl_resp = await client.get(image_url)
                dl_resp.raise_for_status()
                return dl_resp.content

            except Exception as e:
                logger.error(f"[thumbnail] DALL-E generation failed: {e}")
                return None

    def _apply_text_overlay(self, image_bytes: bytes, text: str) -> bytes:
        """
        Apply bold text overlay to the thumbnail image using Pillow.
        Returns JPEG bytes.
        """
        try:
            from PIL import Image, ImageDraw, ImageFont
        except ImportError:
            logger.warning("[thumbnail] Pillow not installed, returning raw image")
            return image_bytes

        img = Image.open(BytesIO(image_bytes))
        img = img.resize((self.THUMB_WIDTH, self.THUMB_HEIGHT), Image.LANCZOS)
        draw = ImageDraw.Draw(img)

        # Try to use a bold font, fall back to default
        font_size = 72
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", font_size)
        except (OSError, IOError):
            try:
                font = ImageFont.truetype("arial.ttf", font_size)
            except (OSError, IOError):
                font = ImageFont.load_default()

        # Truncate text to 5 words max
        words = text.split()[:5]
        display_text = " ".join(words).upper()

        # Calculate text position (bottom-right area)
        bbox = draw.textbbox((0, 0), display_text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]

        x = (self.THUMB_WIDTH - text_width) // 2
        y = self.THUMB_HEIGHT - text_height - 50

        # Draw text outline (black border)
        outline_range = 4
        for dx in range(-outline_range, outline_range + 1):
            for dy in range(-outline_range, outline_range + 1):
                if dx == 0 and dy == 0:
                    continue
                draw.text((x + dx, y + dy), display_text, font=font, fill="black")

        # Draw main text (white)
        draw.text((x, y), display_text, font=font, fill="white")

        # Export as JPEG
        output = BytesIO()
        img.save(output, format="JPEG", quality=90, optimize=True)
        return output.getvalue()
