"""示例 04：自己用五大子系统搭一只"袖珍猫"。

场景：不依赖 ``create_cat`` / ``CatBase`` 子类化，完全手工组合
``OrganHost + EventBus + Nervous + ReflexArc`` 搭一只最小猫。
用于说明这些子系统的独立装配能力。

运行：``python -m meowcat.examples.04_custom_cat``
"""

from __future__ import annotations

import anyio

from meowcat import (
    EventBus,
    Nervous,
    OrganHost,
    Reflex,
    ReflexArc,
    biology,
)


class Ears:
    name = "ears"

    async def hear(self, msg: str) -> str:
        return f"heard:{msg}"


class Thalamus:
    name = "thalamus"

    async def route(self, signal: str) -> str:
        return f"routed:{signal}"


async def main() -> None:
    # 1. 组合五大子系统
    host = OrganHost(cat_id="mini")
    events = EventBus()
    nervous = Nervous(host, events)
    reflex = ReflexArc(events, nervous)

    # 2. 挂器官
    host.mount("sense", "ears", Ears())
    host.mount("brain", "thalamus", Thalamus())

    # 3. 开通路
    biology.apply_default_wiring(nervous.wiring)

    # 4. 注册一条反射：ears → thalamus
    reflex.register(Reflex(
        name="ear_to_brain",
        trigger=lambda x: isinstance(x, str),
        path=(("sense", "ears"), ("brain", "thalamus")),
    ))

    # 5. freeze + 校验
    reflex.validate_paths()
    nervous.freeze()

    # 6. 用 signal 跨器官传递
    result = await nervous.signal(
        ("sense", "ears"), ("brain", "thalamus"),
        "route", "hello-world",
    )
    print(f"signal result: {result}")

    # 7. 用 reflex.match 匹配一条反射
    matched = reflex.match("some input")
    print(f"matched reflex: {matched.name if matched else None}")

    print("custom cat 五大子系统组合 OK")


if __name__ == "__main__":
    anyio.run(main)
