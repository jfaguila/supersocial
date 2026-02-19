"""
Authority positioning selector.
Determines the credibility frame for content: how George positions the operator.
"""
from dataclasses import dataclass


AUTHORITY_ANGLES = {
    "experience": "Personal experience and proven results",
    "research": "Data-backed, research-driven insights",
    "contrarian_expert": "Expert who challenges mainstream advice",
    "community_leader": "Voice of a movement, not just an individual",
    "practitioner": "Currently doing it, not just teaching theory",
    "mentor": "Guiding others through a proven path",
}

PLATFORM_PREFERRED_AUTHORITY: dict[str, list[str]] = {
    "twitter": ["contrarian_expert", "research", "experience"],
    "tiktok": ["experience", "practitioner", "mentor"],
    "linkedin": ["research", "experience", "community_leader"],
    "instagram": ["experience", "mentor", "community_leader"],
}


@dataclass
class SelectedAuthority:
    angle_key: str
    description: str
    platform: str


class AuthoritySelector:
    def select(self, platform: str, narrative_key: str) -> SelectedAuthority:
        preferred = PLATFORM_PREFERRED_AUTHORITY.get(platform, ["experience"])
        # For certain narratives, override authority angle
        overrides = {
            "system_expose": "contrarian_expert",
            "social_proof": "practitioner",
            "tactical_value": "mentor",
            "contrarian_take": "contrarian_expert",
        }
        angle = overrides.get(narrative_key, preferred[0])
        return SelectedAuthority(
            angle_key=angle,
            description=AUTHORITY_ANGLES.get(angle, ""),
            platform=platform,
        )
