"""SubAgent: a team worker with no Blackboard access. Its leader spawns it for one task,
hands it the relevant context, and reports whatever it finds."""

from abc import ABC, abstractmethod
from typing import Any, Optional

from core.models.artifact import Artifact


class SubAgent(ABC):
    @abstractmethod
    async def run(self, brief: dict[str, Any], context: list[Artifact]) -> Optional[dict[str, Any]]:
        """Does one task and returns findings for the leader, or None if there are none"""
