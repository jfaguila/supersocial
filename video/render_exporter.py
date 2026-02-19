"""
JSON export for AI video rendering tools.
Produces HeyGen-compatible and Runway-compatible JSON payloads.
"""
import json
import time
from dataclasses import asdict

from .script_formatter import FormattedScript
from .srt_generator import SRTGenerator


class RenderExporter:
    def __init__(self):
        self._srt_gen = SRTGenerator()

    def to_heygen(self, script: FormattedScript, avatar_id: str = "", voice_id: str = "") -> dict:
        """
        HeyGen API v2 compatible payload.
        https://docs.heygen.com/reference/create-video-v2
        """
        return {
            "video_inputs": [
                {
                    "character": {
                        "type": "avatar",
                        "avatar_id": avatar_id or "default",
                        "avatar_style": "normal",
                    },
                    "voice": {
                        "type": "text",
                        "voice_id": voice_id or "en-US-Neural2-D",
                        "input_text": script.teleprompter_text,
                        "speed": 1.0,
                    },
                    "background": {
                        "type": "color",
                        "value": "#000000",
                    },
                }
            ],
            "dimension": {
                "width": 1080,
                "height": 1920,
            },
            "title": script.title,
            "caption": True,
            "test": False,
            "meta": {
                "platform": script.platform,
                "generated_at": int(time.time()),
                "duration_estimate": script.total_duration_seconds,
            },
        }

    def to_runway(self, script: FormattedScript, style_preset: str = "cinematic") -> dict:
        """
        Runway Gen-2/Gen-3 text-to-video compatible structure.
        """
        return {
            "prompt": script.teleprompter_text[:500],
            "seconds": min(int(script.total_duration_seconds) + 2, 60),
            "watermark": False,
            "style": style_preset,
            "resolution": "1080p",
            "aspect_ratio": "9:16",
            "captions": self._srt_gen.generate(script),
            "meta": {
                "title": script.title,
                "platform": script.platform,
                "generated_at": int(time.time()),
            },
        }

    def export_bundle(
        self,
        script: FormattedScript,
        output_dir: str,
        avatar_id: str = "",
        voice_id: str = "",
    ) -> dict[str, str]:
        """
        Export full video production bundle to output_dir.
        Returns dict of file paths.
        """
        import os
        os.makedirs(output_dir, exist_ok=True)
        safe_title = "".join(c for c in script.title if c.isalnum() or c in (" ", "_")).strip()[:40]
        ts = int(time.time())
        base = f"{output_dir}/{safe_title}_{ts}"

        paths = {}

        # Teleprompter .txt
        tp_path = f"{base}_teleprompter.txt"
        with open(tp_path, "w", encoding="utf-8") as f:
            f.write(script.teleprompter_text)
        paths["teleprompter"] = tp_path

        # SRT
        srt_path = f"{base}.srt"
        self._srt_gen.save(script, srt_path)
        paths["srt"] = srt_path

        # HeyGen JSON
        heygen_path = f"{base}_heygen.json"
        with open(heygen_path, "w") as f:
            json.dump(self.to_heygen(script, avatar_id, voice_id), f, indent=2)
        paths["heygen"] = heygen_path

        # Runway JSON
        runway_path = f"{base}_runway.json"
        with open(runway_path, "w") as f:
            json.dump(self.to_runway(script), f, indent=2)
        paths["runway"] = runway_path

        return paths
