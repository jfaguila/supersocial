"""
Daily micro-cycle runner.
Triggered by cron every day at 06:00 UTC.
"""
import asyncio

from george.agent import GeorgeAgent


class DailyCycleRunner:
    def __init__(self):
        self._agent = GeorgeAgent()

    async def run(self) -> dict:
        return await self._agent.run_daily_cycle()


def main():
    runner = DailyCycleRunner()
    result = asyncio.run(runner.run())
    print(f"Daily cycle complete: {result}")


if __name__ == "__main__":
    main()
