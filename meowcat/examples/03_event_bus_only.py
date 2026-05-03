"""示例 03：只用 EventBus —— 纯异步发布订阅，零猫依赖。

场景：用户只想要一个"订阅事件名 → 触发回调"的异步总线，不关心器官/通路/
反射。

运行：``python -m meowcat.examples.03_event_bus_only``
"""
# (c) 2025-2026 Axonant. MIT License.


from __future__ import annotations

import anyio

from meowcat import EventBus


async def main() -> None:
    bus = EventBus()
    received: list[dict] = []

    async def on_user(payload: dict) -> None:
        received.append(payload)

    bus.on("user.login", on_user)
    await bus.emit("user.login", {"uid": 42, "from": "cli"})
    await bus.emit("user.login", {"uid": 7, "from": "web"})

    print(f"received {len(received)} events")
    for ev in received:
        print(f"  - {ev}")

    # 取消订阅
    bus.off("user.login", on_user)
    await bus.emit("user.login", {"uid": 100})
    assert len(received) == 2
    print("EventBus 单飞 OK")


if __name__ == "__main__":
    anyio.run(main)
