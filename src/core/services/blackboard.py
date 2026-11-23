import asyncio
from asyncio import Queue
from attrs import define, field as attrs_field
from collections import defaultdict
from typing import Optional

from core.models.artifact import Artifact


@define
class Blackboard:
    _corpus: list[Artifact] = attrs_field(factory=list)
    _subscribers: dict[str, list[Queue[Artifact]]] = attrs_field(
        factory=lambda: defaultdict(list)
    )
    _lock: asyncio.Lock = attrs_field(factory=asyncio.Lock, init=False)
    
    def subscribe(self, topic: str) -> Queue[Artifact]:
        """Creates a dedicated tail to allow an agent read a topic"""
        queue: Queue[Artifact] = Queue()
        self._subscribers[topic].append(queue)
        return queue
    
    async def publish(self, artifact: Artifact) -> None:
        """Safely records result and notify subscribers"""
        async with self._lock:
            self._corpus.append(artifact)
            queues = list(self._subscribers.get(artifact.topic, []))
            
            # Out of lock notification, avoid blocking other writers
            for q in queues:
                await q.put(artifact)
                
    async def query(self, topic: Optional[str] = None, limit: int = 10) -> list[Artifact]:
        """Allows every agent read a corpus filtered view"""
        async with self._lock:
            items = self._corpus if topic is None else [
                a for a in self._corpus if a.topic == topic
            ]
            return items[-limit:]