"""
George's structured logger.
All actions are logged to stdout (structured JSON) AND to the DB agent_logs table.
"""
import json
import time
from typing import Optional

import structlog

from memory.repository import Repository

structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.stdlib.add_log_level,
        structlog.processors.JSONRenderer(),
    ]
)

_log = structlog.get_logger("george")


class GeorgeLogger:
    def __init__(self, repo: Repository, cycle_id: Optional[str] = None):
        self._repo = repo
        self._cycle_id = cycle_id

    def set_cycle_id(self, cycle_id: str) -> None:
        self._cycle_id = cycle_id

    async def info(self, component: str, action: str, payload: Optional[dict] = None, duration_ms: Optional[int] = None) -> None:
        _log.info(action, component=component, cycle_id=self._cycle_id, **(payload or {}))
        if self._cycle_id:
            await self._repo.log(self._cycle_id, "INFO", component, action, payload, duration_ms)

    async def warn(self, component: str, action: str, payload: Optional[dict] = None) -> None:
        _log.warning(action, component=component, cycle_id=self._cycle_id, **(payload or {}))
        if self._cycle_id:
            await self._repo.log(self._cycle_id, "WARN", component, action, payload)

    async def error(self, component: str, action: str, payload: Optional[dict] = None) -> None:
        _log.error(action, component=component, cycle_id=self._cycle_id, **(payload or {}))
        if self._cycle_id:
            await self._repo.log(self._cycle_id, "ERROR", component, action, payload)

    async def debug(self, component: str, action: str, payload: Optional[dict] = None) -> None:
        _log.debug(action, component=component, cycle_id=self._cycle_id, **(payload or {}))
