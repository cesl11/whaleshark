import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
from collections import defaultdict
from typing import Any


@dataclass(frozen=True)
class Artifact:
    author: str
    topic: str
    content: dict[str, Any]
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())