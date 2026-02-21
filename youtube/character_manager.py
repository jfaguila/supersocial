"""
Character manager — Persistent AI character identity.

Ensures visual and vocal consistency across all videos for a given character.
Uses a "prompt anchoring" strategy: every image generation prompt is prefixed
with the character's frozen visual identity block.

Future: LoRA fine-tuning on best generated images for pixel-perfect consistency.
"""
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class CharacterIdentity:
    """Frozen identity used across all generation calls."""
    character_id: str
    name: str
    physical: str
    clothing: str
    art_style: str
    color_palette: str
    environment: str
    negative_prompt: str
    voice_id: str
    voice_stability: float
    voice_similarity_boost: float
    voice_style: float
    voice_speaking_rate: float


class CharacterManager:
    """
    Builds deterministic prompt blocks from a character's stored identity.
    Every image/thumbnail prompt passes through this manager to ensure
    the same person appears across all videos.
    """

    def load_identity(self, character_row) -> CharacterIdentity:
        """Load a CharacterIdentity from a YouTubeCharacter ORM row."""
        return CharacterIdentity(
            character_id=character_row.id,
            name=character_row.name,
            physical=character_row.physical_description,
            clothing=character_row.clothing_description,
            art_style=character_row.art_style,
            color_palette=character_row.color_palette,
            environment=character_row.default_environment,
            negative_prompt=character_row.negative_prompt,
            voice_id=character_row.elevenlabs_voice_id,
            voice_stability=character_row.voice_stability,
            voice_similarity_boost=character_row.voice_similarity_boost,
            voice_style=character_row.voice_style,
            voice_speaking_rate=character_row.voice_speaking_rate,
        )

    def build_scene_prompt(
        self,
        identity: CharacterIdentity,
        scene_description: str,
        include_character: bool = True,
    ) -> str:
        """
        Build a complete image generation prompt with character identity anchored.

        Args:
            identity: The frozen character identity
            scene_description: What should happen in this scene
            include_character: Whether the character appears in frame
        """
        if include_character:
            prompt = (
                f"Portrait of {identity.physical}, "
                f"wearing {identity.clothing}, "
                f"in {identity.environment}. "
                f"Scene: {scene_description}. "
                f"Color palette: {identity.color_palette}. "
                f"Style: {identity.art_style}."
            )
        else:
            # B-roll scenes without the character (data visualizations, landscapes, etc.)
            prompt = (
                f"{scene_description}. "
                f"Color palette: {identity.color_palette}. "
                f"Style: {identity.art_style}."
            )
        return prompt

    def build_thumbnail_prompt(
        self,
        identity: CharacterIdentity,
        emotion: str = "confident, looking at camera",
        background_context: str = "",
    ) -> str:
        """
        Build a thumbnail-optimized prompt.
        Thumbnails need: large face, strong emotion, clean background.
        """
        bg = background_context or identity.environment
        return (
            f"Close-up portrait of {identity.physical}, "
            f"wearing {identity.clothing}, "
            f"expression: {emotion}, "
            f"background: {bg}, "
            f"Color palette: {identity.color_palette}. "
            f"Style: {identity.art_style}, "
            f"YouTube thumbnail composition, high contrast, ultra sharp, "
            f"eye-catching, professional photography."
        )

    def build_negative_prompt(self, identity: CharacterIdentity) -> str:
        """Return the character's negative prompt for image generation."""
        return identity.negative_prompt

    def get_motion_prompt(self, scene_type: str) -> str:
        """
        Return an appropriate Runway motion prompt based on scene type.
        Controls camera movement for image-to-video conversion.
        """
        motion_map = {
            "hook": "slow dramatic zoom in on face, cinematic",
            "problem": "slow pan left to right, revealing scene, tense atmosphere",
            "deepening": "gentle floating camera, subtle parallax, contemplative mood",
            "solution": "smooth zoom out revealing full scene, uplifting energy",
            "cta": "slow push in on subject, direct eye contact, confident energy",
        }
        return motion_map.get(scene_type, "slow subtle camera movement, cinematic")
