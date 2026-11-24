"""Team: a named group run by exactly one Leader. Its scope on the shared Blackboard is the
topic prefix "<team>.<step>". The team owns only its leader's running task, never any data;
subagents live inside the leader's `spawn` calls."""

import asyncio
import logging
from typing import Optional

from attrs import define, field

from core.models.leader import Leader

log = logging.getLogger(__name__)


@define
class Team:
    name: str
    _task: Optional[asyncio.Task[None]] = field(default=None, init=False)

    def topic(self, step: str) -> str:
        return f"{self.name}.{step}"

    def lead(self, leader: Leader) -> None:
        """Starts the leader now; call from inside a running event loop."""
        if self._task is not None and not self._task.done():
            raise ValueError(f"{self.name} already has a leader")
        self._task = asyncio.create_task(leader.start(), name=f"{self.name}/{leader.name}")
        self._task.add_done_callback(self._log_crash)

    async def stop(self) -> None:
        if self._task is not None:
            self._task.cancel()
            await asyncio.gather(self._task, return_exceptions=True)

    def _log_crash(self, task: asyncio.Task[None]) -> None:
        # A crashed leader stops only its own team; other teams keep running
        if not task.cancelled() and task.exception():
            log.error("%s crashed", task.get_name(), exc_info=task.exception())
