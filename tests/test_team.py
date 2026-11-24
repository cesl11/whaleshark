"""Self-check for Team + Leader + SubAgent + Blackboard. Run: PYTHONPATH=src python3 tests/test_team.py"""

import asyncio
import logging
from typing import Any, Optional

from attrs import define

from core.models.artifact import Artifact
from core.models.leader import Leader
from core.models.subagent import SubAgent
from core.models.team import Team
from core.services.blackboard import Blackboard

spawned: list[str] = []


class Echo(SubAgent):
    def __init__(self) -> None:
        spawned.append("echo")

    async def run(self, brief: dict[str, Any], context: list[Artifact]) -> Optional[dict[str, Any]]:
        return {"brief": brief, "seen": len(context)}


class Boom(SubAgent):
    def __init__(self) -> None:
        spawned.append("boom")

    async def run(self, brief: dict[str, Any], context: list[Artifact]) -> Optional[dict[str, Any]]:
        raise RuntimeError("boom")


class Slow(SubAgent):
    async def run(self, brief: dict[str, Any], context: list[Artifact]) -> Optional[dict[str, Any]]:
        brief["started"].set()
        await asyncio.sleep(10)
        return None


@define
class Lead(Leader):
    async def process(self, trigger: Artifact, context: list[Artifact]) -> Optional[Artifact]:
        needs = trigger.content["needs"]
        # Direct awaits, not gather: gather's own cancel would hide a spawn that swallows it
        found = {r: await self.spawn(r, trigger.content, context) for r in needs}
        return Artifact(self.name, self.out, {"solo": not needs, **found})


async def main() -> None:
    logging.disable(logging.CRITICAL)  # Boom's crash log is expected
    bb = Blackboard()
    team = Team("t")
    inbox, outbox = team.topic("in"), team.topic("out")
    done = bb.subscribe(outbox)

    async def report() -> dict[str, Any]:
        return (await asyncio.wait_for(done.get(), 1)).content

    team.lead(Lead("lead", bb, inbox, out=outbox, crew={"echo": Echo, "boom": Boom}))
    try:
        team.lead(Lead("other", bb, team.topic("x"), out=outbox))
        raise AssertionError("second leader accepted")
    except ValueError:
        pass

    # No subagent needed -> none spawned
    await bb.publish(Artifact("user", inbox, {"needs": []}))
    assert (await report())["solo"] is True
    assert spawned == []

    # Spawned on demand, given the leader's context; a crash yields None and the leader survives
    await bb.publish(Artifact("user", inbox, {"needs": ["echo", "boom"]}))
    r = await report()
    assert r["echo"]["seen"] == 3
    assert r["boom"] is None, r
    assert sorted(spawned) == ["boom", "echo"]

    await bb.publish(Artifact("user", inbox, {"needs": ["echo"]}))
    assert (await report())["echo"]["brief"] == {"needs": ["echo"]}  # fresh subagent per task
    assert spawned.count("echo") == 2

    await team.stop()
    assert bb._subscribers[inbox] == []
    # A stopped team can take a new leader; stop cancels a mid-run subagent instead of
    # spawn swallowing the CancelledError and hanging
    team.lead(Lead("lead2", bb, inbox, out=outbox, crew={"slow": Slow}))
    started = asyncio.Event()
    await bb.publish(Artifact("user", inbox, {"needs": ["slow"], "started": started}))
    await asyncio.wait_for(started.wait(), 1)
    await asyncio.wait_for(team.stop(), 1)
    assert bb._subscribers[inbox] == []
    print("ok")


if __name__ == "__main__":
    asyncio.run(main())
