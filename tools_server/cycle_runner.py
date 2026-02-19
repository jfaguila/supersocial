"""
Background cycle runner.
Ejecuta los ciclos de George en background para no bloquear el Tool Server.
"""
import asyncio
import uuid
from typing import Optional

from fastapi import BackgroundTasks


class BackgroundCycleRunner:
    def __init__(self):
        self.is_running: bool = False
        self.current_phase: Optional[str] = None
        self.current_job_id: Optional[str] = None
        self.last_summary: Optional[dict] = None

    def start_weekly(
        self,
        strategic_prompt: Optional[str],
        dry_run: bool,
        background_tasks: BackgroundTasks,
    ) -> str:
        job_id = str(uuid.uuid4())[:8]
        self.current_job_id = job_id
        background_tasks.add_task(
            self._run_weekly, job_id, strategic_prompt, dry_run
        )
        return job_id

    def start_daily(self, background_tasks: BackgroundTasks) -> str:
        job_id = str(uuid.uuid4())[:8]
        self.current_job_id = job_id
        background_tasks.add_task(self._run_daily, job_id)
        return job_id

    async def _run_weekly(
        self, job_id: str, strategic_prompt: Optional[str], dry_run: bool
    ) -> None:
        self.is_running = True
        self.current_phase = "starting"
        try:
            # Patch cycle mode if dry_run
            if dry_run:
                import os
                os.environ["GEORGE_CYCLE_MODE"] = "semi"

            from george.agent import GeorgeAgent
            agent = GeorgeAgent()

            # Hook into state transitions to expose current phase
            original_run = agent._execute_weekly_cycle

            async def patched_run(repo, logger, prompt):
                # We can't easily hook phase changes without modifying the agent
                # So we just update phase at start/end
                self.current_phase = "running_weekly_cycle"
                result = await original_run(repo, logger, prompt)
                self.current_phase = "completed"
                return result

            agent._execute_weekly_cycle = patched_run
            summary = await agent.run_weekly_cycle(strategic_prompt=strategic_prompt)
            self.last_summary = summary

        except Exception as e:
            self.last_summary = {"error": str(e), "job_id": job_id}
            self.current_phase = "error"
        finally:
            self.is_running = False
            self.current_job_id = None

    async def _run_daily(self, job_id: str) -> None:
        self.is_running = True
        self.current_phase = "running_daily_cycle"
        try:
            from george.agent import GeorgeAgent
            agent = GeorgeAgent()
            summary = await agent.run_daily_cycle()
            self.last_summary = summary
            self.current_phase = "completed"
        except Exception as e:
            self.last_summary = {"error": str(e), "job_id": job_id}
            self.current_phase = "error"
        finally:
            self.is_running = False
            self.current_job_id = None
