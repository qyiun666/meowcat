"""meowcat 默认器官桩 — 满足 Protocol 的空操作实现。

每个 Noop* 类均满足对应的 Protocol 接口，函数体为 no-op 或返回安全默认值。
用于快速原型——替换为真实实现即可赋予猫完整能力。
"""

from __future__ import annotations

from typing import Any


class NoopAmygdala:
    """默认杏仁核：永不拒绝，零安全风险。"""

    name: str = "noop_amygdala"

    def is_rejection(self, msg: str) -> bool:
        return False

    def classify_rejection(self, msg: str) -> str:
        return "none"

    def parse_correction(self, msg: str) -> tuple[str, str] | None:
        return None

    async def handle_rejection(
        self, msg: str, last_candidates: list[Any], hippocampus: Any
    ) -> str:
        return msg

    async def handle_correction(
        self, msg: str, hippocampus: Any
    ) -> tuple[str, str] | None:
        return None

    async def assess_safety(self, user_input: str) -> dict[str, Any]:
        return {"safe": True, "risk": "none"}

    @staticmethod
    def assess_tool_risk(tool_name: str, params: dict[str, Any]) -> dict[str, Any]:
        return {"risk": "low", "reason": "noop"}

    def tag_emotion(self, episode: dict[str, Any]) -> dict[str, Any]:
        return episode


class NoopFrontal:
    """默认前额叶：不检测焦点转移，不保存焦点。"""

    name: str = "noop_frontal"

    def detect_shift(self, msg: str) -> bool:
        return False

    def is_continue(self, msg: str) -> bool:
        return False

    def archive_focus(self) -> None:
        pass

    def update_focus(self, result: Any) -> None:
        pass

    def save(self, path: Any | None = None) -> None:
        pass

    def load(self, path: Any | None = None) -> None:
        pass


class NoopHypothalamus:
    """默认下丘脑：不执行维护，不唤醒实体。"""

    name: str = "noop_hypothalamus"

    async def run_maintenance(self, country_code: str | None = None) -> Any:
        return {"decayed": 0, "orphans_cleaned": 0, "woke": 0, "suggestions": []}

    def decay_memories(self, now: Any | None = None) -> dict[str, Any]:
        return {"decayed": 0}

    def compress_long_history(self) -> dict[str, Any]:
        return {"compressed": 0}

    def wake_by_name(self, name: str, session_id: str | None = None) -> list[Any]:
        return []

    def wake_by_keywords(
        self, keywords: list[str], session_id: str | None = None
    ) -> list[Any]:
        return []


class NoopCortex:
    """默认皮质：不摄入世界观，不记录弱点。"""

    name: str = "noop_cortex"

    def ingest(self, source: str, layer: str, key: str, value: Any) -> None:
        pass

    def record_weakness(self, kind: str, detail: str) -> None:
        pass

    def weaknesses(self) -> list[dict[str, Any]]:
        return []


class NoopEars:
    """默认耳朵：听不出关键词，语言固定 unknown。"""

    name: str = "noop_ears"

    async def hear(self, raw_input: str | bytes) -> dict[str, Any]:
        return {"text": str(raw_input), "keywords": [], "language": "unknown"}

    def extract_keywords(self, text: str, top_k: int = 5) -> list[str]:
        return []

    def detect_language(self, text: str) -> str:
        return "unknown"


class NoopEyes:
    """默认眼睛：看不见任何图像。"""

    name: str = "noop_eyes"

    async def see(self, image_data: bytes, mime_type: str = "image/png") -> dict[str, Any]:
        return {}

    async def scan_screen(
        self, region: tuple[int, int, int, int] | None = None
    ) -> dict[str, Any]:
        return {}

    def describe(self, image_path: str) -> str:
        return ""


class NoopWhiskers:
    """默认胡须：无输入感觉，无输出漂移检测。"""

    name: str = "noop_whiskers"

    async def feel_input(self, text: str) -> dict[str, Any]:
        return {}

    async def feel_output(
        self, output: str, expected_schema: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        return {}

    def detect_drift(self, recent_outputs: list[str]) -> dict[str, Any]:
        return {"drift": False}

    def check_hallucination(
        self, reply: str, session_id: str | None = None
    ) -> dict[str, Any]:
        return {"hallucination": False}


class NoopMouth:
    """默认嘴巴：不说话。"""

    name: str = "noop_mouth"

    async def speak(self, text: str, **kwargs: Any) -> str:
        return ""


class NoopPurr:
    """默认咕噜：不流式输出。"""

    name: str = "noop_purr"

    async def stream(self, text: str, **kwargs: Any) -> Any:
        pass


class NoopTail:
    """默认尾巴：不渲染任何终端 UI。"""

    name: str = "noop_tail"

    async def render(self, state: dict[str, Any]) -> None:
        pass
