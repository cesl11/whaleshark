"""Leader: the only team agent that talks to the Blackboard. It reads new relevant artifacts,
spawns subagents only when a task needs them, and publishes the team's findings."""

import logging
from abc import ABC, abstractmethod
from asyncio import Queue
from collections.abc import Callable, Mapping
from typing import Any, Optional

from attrs import define, field

from core.models.artifact import Artifact
from core.models.subagent import SubAgent
from core.services.blackboard import Blackboard

log = logging.getLogger(__name__)


@define
class Leader(ABC):
    name: str
    bb: Blackboard
    subscribed_topic: str
    out: str  # topic this leader publishes to; wired by the caller so leaders stay team-agnostic
    crew: Mapping[str, Callable[[], SubAgent]] = field(factory=dict)  # role -> factory, never pre-built
    queue: Queue[Artifact] = field(init=False)

    @queue.default
    def _subscribe(self) -> Queue[Artifact]:
        return self.bb.subscribe(self.subscribed_topic)

    async def start(self) -> None:
        """Independent leader loop; stop it by cancelling its task."""
        try:
            while True:
                trigger = await self.queue.get()
                # Shared context from the whole corpus; tune `limit` to the model's context window
                context = await self.bb.query(limit=5)
                result = await self.process(trigger, context)
                if result is not None:
                    await self.bb.publish(result)
        finally:
            self.bb.unsubscribe(self.subscribed_topic, self.queue)

    async def spawn(
        self, role: str, brief: dict[str, Any], context: list[Artifact]
    ) -> Optional[dict[str, Any]]:
        """Creates a fresh `role` subagent for this one task. If it crashes, the crash is
        logged and the call returns None, so the leader and its other subagents keep running."""
        make = self.crew[role]  # an unknown role is a leader bug, so it raises
        try:
            return await make().run(brief, context)
        except Exception:
            log.exception("%s: subagent %r crashed", self.name, role)
            return None

    @abstractmethod
    async def process(self, trigger: Artifact, context: list[Artifact]) -> Optional[Artifact]:
        """Leader logic: handle the trigger alone or `spawn` subagents, then return the report"""
