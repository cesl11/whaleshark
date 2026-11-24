"""Blackboard service for multi-agent collaboration: acts as source of truth and information
about general progress."""

from asyncio import Queue
from attrs import define, field as attrs_field
from collections import defaultdict
from typing import Optional

from core.models.artifact import Artifact


# no lock — publish/query have no await, so each runs atomically on the event loop;
# reintroduce asyncio. Lock if either gains one (e.g. persistent store).
# publish/query stay `async` on purpose (Sonar S7503): callers already await them, and a
# persistent store can be added later without changing their signatures.
@define
class Blackboard:
    _corpus: list[Artifact] = attrs_field(factory=list)
    _subscribers: dict[str, list[Queue[Artifact]]] = attrs_field(
        factory=lambda: defaultdict(list)
    )

    def subscribe(self, topic: str) -> Queue[Artifact]:
        """Creates a dedicated tail to allow an agent read a topic"""
        queue: Queue[Artifact] = Queue()
        self._subscribers[topic].append(queue)
        return queue

    def unsubscribe(self, topic: str, queue: Queue[Artifact]) -> None:
        """Detaches a tail so a removed agent stops receiving artifacts"""
        self._subscribers[topic].remove(queue)

    async def publish(self, artifact: Artifact) -> None:
        """Records result and notifies subscribers in corpus order"""
        self._corpus.append(artifact)
        for q in self._subscribers.get(artifact.topic, []):
            q.put_nowait(artifact)

    async def query(self, topic: Optional[str] = None, limit: int = 10) -> list[Artifact]:
        """Allows every agent read a corpus filtered view"""
        items = self._corpus if topic is None else [
            a for a in self._corpus if a.topic == topic
        ]
        return items[-limit:]
