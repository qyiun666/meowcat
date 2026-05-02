"""示例 06：自定义器官 —— 写一个满足 Protocol 的器官并挂载到猫上。

场景：用户想在猫身上加一个自定义器官（如特殊的听觉处理），
只需满足对应 Protocol 即可通过 wiring 和信号系统参与协作。

运行：``python -m meowcat.examples.06_custom_organ``
"""

from __future__ import annotations

import anyio

from meowcat import CatBase, EarsProtocol, biology


class SharpEars:
    """自定义耳朵：自动提取关键词。满足 EarsProtocol。"""

    name = "sharp-ears"

    async def hear(self, raw_input: str) -> dict:
        return {"text": raw_input, "source": "sharp-ears"}

    def extract_keywords(self, text: str, top_k: int = 5) -> list[str]:
        words = [w for w in text.split() if len(w) > 1]
        return words[:top_k]

    def detect_language(self, text: str) -> str:
        return "zh" if any("\u4e00" <= c <= "\u9fff" for c in text) else "en"

    def diagnose(self) -> dict:
        return {"name": self.name, "type": "custom-ears"}


async def main() -> None:
    # 1. 创建猫
    cat = CatBase("custom-organ-cat")

    # 2. 挂载自定义器官 — 带 Protocol 校验
    cat.mount("sense", "sharp-ears", SharpEars(), protocol=EarsProtocol)

    # 3. 装配默认 wiring 表
    biology.apply_default_wiring(cat._nervous.wiring)

    # 4. 添加自定义器官到 wiring（让其可被其他器官访问）
    cat._nervous.wiring.connect(("sense", "sharp-ears"), ("brain", "thalamus"))
    cat._nervous.freeze()

    # 5. 直接访问器官
    ears = cat.organ("sense", "sharp-ears")
    print(f"mounted: {ears.name}")
    print(f"keywords: {ears.extract_keywords('hello world from meowcat')}")
    print(f"diagnose: {ears.diagnose()}")

    print("custom organ OK")


if __name__ == "__main__":
    anyio.run(main)
