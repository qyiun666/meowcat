"""v1.0.18 — BUILTIN_REFLEX_PATHS + SecurityPolicyProtocol."""

from __future__ import annotations

from meowcat.anatomy import AMYGDALA, BRAINSTEM, CEREBELLUM, CEREBRUM, EARS, MOUTH, THALAMUS
from meowcat.reflex import BUILTIN_REFLEX_PATHS
from meowcat.protocols import SecurityPolicyProtocol
from meowcat.wiring import Organ


class TestBuiltinReflexPaths:
    """BUILTIN_REFLEX_PATHS provides predefined reflex path structures."""

    def test_text_dialogue_path_length(self) -> None:
        path = BUILTIN_REFLEX_PATHS["text_dialogue"]
        assert len(path) == 6

    def test_text_dialogue_path_order(self) -> None:
        path = BUILTIN_REFLEX_PATHS["text_dialogue"]
        assert path == (EARS, THALAMUS, BRAINSTEM, CEREBRUM, CEREBELLUM, MOUTH)

    def test_danger_path_length(self) -> None:
        path = BUILTIN_REFLEX_PATHS["danger"]
        assert len(path) == 4

    def test_danger_path_order(self) -> None:
        path = BUILTIN_REFLEX_PATHS["danger"]
        assert path == (EARS, THALAMUS, AMYGDALA, MOUTH)

    def test_paths_are_organ_tuples(self) -> None:
        for name, path in BUILTIN_REFLEX_PATHS.items():
            assert isinstance(path, tuple), f"{name}: not a tuple"
            assert len(path) >= 2, f"{name}: need at least 2 hops"
            for hop in path:
                assert isinstance(hop, tuple), f"{name}: hop {hop} not an Organ"
                assert len(hop) == 2, f"{name}: hop {hop} not (category, name)"

    def test_keys_are_strings(self) -> None:
        for key in BUILTIN_REFLEX_PATHS:
            assert isinstance(key, str)


class TestSecurityPolicyProtocol:
    """SecurityPolicyProtocol is a @runtime_checkable Protocol."""

    def test_protocol_importable(self) -> None:
        assert SecurityPolicyProtocol is not None

    def test_protocol_is_runtime_checkable(self) -> None:
        from typing import runtime_checkable
        assert hasattr(SecurityPolicyProtocol, "__protocol_flags__") or \
            hasattr(SecurityPolicyProtocol, "_is_runtime_protocol")

    def test_minimal_impl_satisfies(self) -> None:
        class Minimal:
            def is_danger(self, input: str) -> bool:
                return False

            def assess_tool_risk(self, name: str, params: dict) -> dict[str, str]:
                return {"risk": "low"}

        m = Minimal()
        assert isinstance(m, SecurityPolicyProtocol)

    def test_empty_impl_fails(self) -> None:
        class Empty:
            pass
        assert not isinstance(Empty(), SecurityPolicyProtocol)
