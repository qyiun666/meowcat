"""示例 07：自定义器官 + Path + Chain + Loop 完整示例。

场景：给猫加一个"鼻子"器官，声明 Path、拼装 Chain、注册 Loop，
演示从 Organ → Path → Chain → Loop 的四层扩展流程。

运行：``python -m meowcat.examples.07_custom_organ``
"""
# (c) 2025-2026 Axonant. MIT License.


from __future__ import annotations

import anyio

from meowcat import CatBase, Path, Chain, Loop, biology


class MyNose:
    """自定义鼻子：实现嗅觉输入。"""

    name = "nose"

    def diagnose(self) -> dict:
        return {"name": self.name, "type": "custom-nose"}

    async def sniff(self, input_data: str) -> dict:
        """分析输入中的气味信息。"""
        smells = ["fish", "catnip", "milk", "rain", "nothing"]
        found = [s for s in smells if s in input_data.lower()]
        return {"smell": found[0] if found else "nothing", "source": "nose"}


class EchoMouth:
    """简化的嘴巴：把输出打印出来。"""

    name = "mouth"

    def diagnose(self) -> dict:
        return {"name": self.name}

    async def say(self, text: str = "", **kw) -> dict:
        # Chain 数据流转：前一步返回值可能以 **kw 形式传入
        if not text and kw:
            text = str(kw)
        print(f"🐱 猫说: {text}")
        return {"spoken": text}


async def main() -> None:
    # 1. 创建猫
    cat = CatBase("custom-organ-cat")

    # 2. 挂载自定义器官
    cat.mount("sense", "ears", type("NoopEars", (), {
              "name": "ears", "diagnose": lambda: {}})(), protocol=None)
    cat.mount("sense", "nose", MyNose())
    cat.mount("voice", "echo_mouth", EchoMouth())

    # 3. 装配默认 wiring + 添加自定义通路
    biology.apply_default_wiring(cat._nervous.wiring)
    cat._nervous.wiring.connect(("sense", "ears"), ("sense", "nose"))
    cat._nervous.wiring.connect(("sense", "nose"), ("voice", "echo_mouth"))
    cat._nervous.freeze()

    # 4. 注册自定义 Path
    sniff_path = Path(
        "sniff",
        ("sense", "ears"),
        ("sense", "nose"),
        "sniff",
        "read",
        "嗅觉输入 — 鼻子分析气味",
    )
    cat.path_registry.register(sniff_path)

    speak_path = Path(
        "say_local",
        ("sense", "nose"),
        ("voice", "echo_mouth"),
        "say",
        "write",
        "输出 — 嘴巴说话",
    )
    cat.path_registry.register(speak_path)

    # 5. 注册自定义 Chain
    smell_chain = Chain(
        "smell_then_speak",
        ("sniff", "say_local"),
        "闻一闻然后说出来",
    )
    cat.chain_registry.register(smell_chain)

    # 6. 注册自定义 Loop
    sniff_loop = Loop(
        "nose_patrol",
        "鼻子巡逻闭环 — 闻→说",
        chain=smell_chain,
        trigger=None,  # 手动触发
    )
    cat.loop_registry.register(sniff_loop)

    # 7. 演示
    print("=== Path 层面：直接 run sniff ===")
    result = await cat.path_registry.run(cat, "sniff", input_data="I smell fish")
    print(f"Path result: {result}")

    print("\n=== Chain 层面：smell_then_speak ===")
    result = await cat.chain_registry.run(cat, "smell_then_speak", input_data="I smell catnip")
    print(f"Chain result: {result}")

    print("\n=== Loop 层面：nose_patrol ===")
    result = await cat.loop_registry.run(cat, "nose_patrol", input_data="I smell rain")
    print(f"Loop result: {result}")

    # 8. 查询注册表
    print("\n=== 已注册的 Path ===")
    for p in cat.path_registry.list_all():
        print(f"  {p.name}: {p.from_organ} → {p.to_organ}.{p.method}")

    print("\n=== 已注册的 Chain ===")
    for c in cat.chain_registry.list_all():
        print(f"  {c.name}: {' → '.join(c.path_names)}")

    print("\n=== 已注册的 Loop ===")
    for lp in cat.loop_registry.list_all():
        print(f"  {lp.name}: trigger={lp.trigger}, chain={lp.chain.name}")

    print("\ncustom organ OK")


if __name__ == "__main__":
    anyio.run(main)
