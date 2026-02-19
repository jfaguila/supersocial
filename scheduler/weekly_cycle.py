"""
Weekly cycle runner.
Triggered by cron every Sunday at 00:00 UTC.
Reads optional strategic prompt from /data/weekly_prompt.txt if present.
"""
import asyncio
import os
from pathlib import Path

from george.agent import GeorgeAgent


PROMPT_FILE = Path("/data/weekly_prompt.txt")


class WeeklyCycleRunner:
    def __init__(self):
        self._agent = GeorgeAgent()

    def _load_prompt(self) -> str | None:
        if PROMPT_FILE.exists():
            content = PROMPT_FILE.read_text(encoding="utf-8").strip()
            # Archive the prompt after reading
            archive = PROMPT_FILE.with_suffix(".used.txt")
            PROMPT_FILE.rename(archive)
            return content or None
        return None

    async def run(self) -> dict:
        prompt = self._load_prompt()
        summary = await self._agent.run_weekly_cycle(strategic_prompt=prompt)
        return summary


def main():
    runner = WeeklyCycleRunner()
    result = asyncio.run(runner.run())
    print(f"Weekly cycle complete: {result}")


if __name__ == "__main__":
    main()
