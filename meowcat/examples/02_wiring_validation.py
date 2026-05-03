"""示例 02：只用 Wiring —— 纯数据结构，离线校验通路合法性。

场景：用户在业务代码里自定义了一组神经信号路径，想先离线校验路径合法
（起点终点在同一张 wiring 图上、无重复、双向边自动对称），再上线。

运行：``python -m meowcat.examples.02_wiring_validation``
"""
# (c) 2025-2026 Axonant. MIT License.


from __future__ import annotations

from meowcat import Wiring, biology


def main() -> None:
    wiring = Wiring()
    biology.apply_default_wiring(wiring)

    print(f"默认 wiring 边数: {len(wiring.edges())}")

    # 合法路径（默认听觉 → 丘脑）
    wiring.assert_allowed(("sense", "ears"), ("brain", "thalamus"))
    print("(sense,ears) → (brain,thalamus) ✓")

    # 非法路径（默认表里大脑不直连四肢）
    try:
        wiring.assert_allowed(("brain", "cerebrum"), ("sense", "paws"))
    except Exception as e:
        print(f"(brain,cerebrum) → (sense,paws) 被拦截: {type(e).__name__}")

    # 冻结后不能再改
    wiring.freeze()
    try:
        wiring.add_edge(("brain", "cerebrum"), ("sense", "paws"))
    except Exception as e:
        print(f"冻结后 add_edge 被拦截: {type(e).__name__}")

    print("Wiring 单飞 OK")


if __name__ == "__main__":
    main()
