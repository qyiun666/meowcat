"""示例 01：只用 OrganHost —— 当作一个带 Protocol 校验的器官容器。

场景：用户只想要一个"按 (category, name) 挂/取对象"的字典，并且希望在
挂载时自动做 ``isinstance(obj, Protocol)`` 校验。不需要神经系统/反射/事件。

运行：``python -m meowcat.examples.01_organ_host_only``
"""
# (c) 2025-2026 Axonant. MIT License.


from __future__ import annotations

from meowcat import OrganHost
from meowcat.protocols import OrganProtocol


class Cerebrum:
    name = "cerebrum"

    async def generate(self, prompt: str) -> str:
        return "meow"


def main() -> None:
    host = OrganHost(cat_id="demo")

    # 挂载 —— 带 Protocol 校验（isinstance 必须通过）
    host.mount("brain", "cerebrum", Cerebrum(), protocol=OrganProtocol)
    host.mount("sense", "ears", type("Ears", (), {"name": "ears"})())

    # 取回
    brain = host.organ("brain", "cerebrum")
    print(f"got {brain.name}")

    # 查询
    assert host.has_organ("sense", "ears")
    print(f"brain organs: {list(host.organs('brain').keys())}")

    # 校验必挂清单
    host.assert_organs_mounted([("brain", "cerebrum"), ("sense", "ears")])

    # 卸载
    host.unmount("sense", "ears")
    assert not host.has_organ("sense", "ears")
    print("OrganHost 单飞 OK")


if __name__ == "__main__":
    main()
