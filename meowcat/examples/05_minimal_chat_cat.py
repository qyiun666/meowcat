"""示例 05：最小对话猫 —— 用 Path/Chain/Loop 四层体系。

场景：最简猫，只挂载必需器官，演示 Path/Chain/Loop 的注册和执行。
使用 CatBase 直接装配（不用 create_cat），展示底层灵活性。

运行：``python -m meowcat.examples.05_minimal_chat_cat``
"""
# (c) 2025-2026 Axonant. MIT License.


from __future__ import annotations

import anyio

from meowcat import CatBase, Path, Chain, Loop, biology


class EchoBrain:
    """最简大脑：把输入 echo 回去。"""

    name = "cerebrum"

    async def generate(self, prompt: str = "", **kw) -> str:
        # Chain 数据流转：listen 返回 {"text": ...} 作为 kw 传入
        p = prompt or kw.get("text", str(kw))
        return f"喵！你问了: {p[:60]}"


class SimpleMouth:
    """最简嘴巴：打印回复。"""

    name = "mouth"

    async def speak(self, text: str = "", **kw) -> str:
        # Chain 数据流转：前一步返回值可能以 _result 形式传入
        msg = text or kw.get("_result", str(kw))
        print(f"🐱: {msg}")
        return msg


class SimpleEars:
    """最简耳朵：直接透传文本。"""

    name = "ears"

    async def hear(self, raw_input: str) -> dict:
        return {"text": str(raw_input)}


async def main() -> None:
    # 1. 创建猫 + 挂载最简器官
    cat = CatBase("minimal-cat")
    echo = EchoBrain()
    cat.mount("brain", "cerebrum", echo)
    # 同实例，cerebrum→cerebellum 默认 wiring 已通
    cat.mount("brain", "cerebellum", echo)
    cat.mount("voice",  "mouth",  SimpleMouth())
    cat.mount("sense", "ears",   SimpleEars())

    # 2. 装配自定义 wiring + freeze
    biology.apply_default_wiring(cat._nervous.wiring)
    # 添加自定义通路：ears → cerebrum（默认 wiring 没有这条边）
    cat._nervous.wiring.connect(("sense", "ears"), ("brain", "cerebrum"))
    cat._nervous.freeze()

    # 3. 注册自定义 Path
    cat.path_registry.register(Path(
        "hear_local", ("sense", "ears"), ("sense", "ears"),
        "hear", "read", "耳朵自环 — 接收文本输入",
    ))
    cat.path_registry.register(Path(
        "think", ("sense", "ears"), ("brain", "cerebrum"),
        "generate", "read", "耳朵→大脑 — 推理",
    ))
    cat.path_registry.register(Path(
        "speak_local", ("brain", "cerebellum"), ("voice", "mouth"),
        "speak", "write", "小脑→嘴巴输出",
    ))

    # 4. 注册 Chain：听→想→说
    cat.chain_registry.register(Chain(
        "quick_chat", ("hear_local", "think", "speak_local"), "快速对话",
    ))

    # 5. 注册 Loop
    cat.loop_registry.register(Loop(
        "quick_chat_loop", "快速对话闭环",
        chain=cat.chain_registry.get("quick_chat"),
    ))

    # 6. 执行
    print("=== Chain: quick_chat ===")
    result = await cat.chain_registry.run(cat, "quick_chat", raw_input="你好世界")
    print(f"Chain result: {result}")

    print("\n=== Loop: quick_chat_loop ===")
    result = await cat.loop_registry.run(cat, "quick_chat_loop", raw_input="你叫什么")
    print(f"Loop result: {result}")

    # 7. 查看注册表
    print("\n=== Paths ===")
    for p in cat.path_registry.list_all():
        print(f"  {p.name}: {p.from_organ} → {p.to_organ}.{p.method}")
    print("\n=== Chains ===")
    for c in cat.chain_registry.list_all():
        names = " → ".join(c.path_names) if c.path_names else "(empty)"
        print(f"  {c.name}: {names}")
    print("\n=== Loops ===")
    for lp in cat.loop_registry.list_all():
        print(f"  {lp.name}: trigger={lp.trigger}, chain={lp.chain.name}")

    print("\nminimal chat cat OK")


if __name__ == "__main__":
    anyio.run(main)
