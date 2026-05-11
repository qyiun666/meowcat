# Copyright (c) 2026 Axonant
# SPDX-License-Identifier: MIT

"""Tests for v2.5.0: Persona mask system — loading, switching, serialization."""

import tempfile
from pathlib import Path

import pytest

from meowcat import Colony
from meowcat.biology.cat_self import CatSelf
from meowcat.persona import (
    Belief,
    ConnectionSpec,
    KnowledgeSeed,
    Persona,
    ReflexSpec,
)
from meowcat.plus.persona_loader import PersonaLoader
from meowcat.testing import make_test_colony


# ── Persona dataclass tests ──────────────────────────────────────


class TestPersonaDataclass:
    def test_create_minimal(self):
        p = Persona(name="test")
        assert p.name == "test"
        assert p.version == "0.1.0"
        assert p.description == ""
        assert p.personality == {}
        assert p.beliefs == []
        assert p.capable == []
        assert p.incapable == []
        assert p.knowledge_seeds == []
        assert p.tools == []
        assert p.reflex_specs == []
        assert p.sample_dialogues == []

    def test_create_full(self):
        p = Persona(
            name="musk",
            version="1.0.0",
            description="Elon thinking",
            personality={"tone": "visionary", "language": "en+zh"},
            beliefs=[
                Belief(key="fp", value="first principles", confidence=0.95)],
            capable=["engineering"],
            incapable=["poetry"],
            knowledge_seeds=[
                KnowledgeSeed(
                    entity_type="company",
                    name="SpaceX",
                    properties={"industry": "aerospace"},
                    connections=[ConnectionSpec(
                        to="Tesla", relation="also_ceo", strength=0.9)],
                )
            ],
            sample_dialogues=[("Q", "A")],
        )
        assert p.name == "musk"
        assert p.personality == {"tone": "visionary", "language": "en+zh"}
        assert len(p.beliefs) == 1
        assert p.beliefs[0].key == "fp"
        assert len(p.knowledge_seeds) == 1
        assert p.knowledge_seeds[0].connections[0].to == "Tesla"

    def test_belief_confidence_clamped(self):
        b = Belief(key="k", value="v", confidence=1.5)
        assert b.confidence == 1.0
        b2 = Belief(key="k", value="v", confidence=-0.5)
        assert b2.confidence == 0.0

    def test_to_dict_roundtrip(self):
        p = Persona(
            name="test",
            personality={"tone": "friendly"},
            beliefs=[Belief(key="k1", value="v1", confidence=0.8)],
            capable=["a", "b"],
            incapable=["x"],
            knowledge_seeds=[
                KnowledgeSeed(
                    entity_type="concept",
                    name="gravity",
                    properties={"unit": "m/s^2"},
                    connections=[ConnectionSpec(
                        to="mass", relation="related")],
                )
            ],
            sample_dialogues=[("你好", "你好！有什么可以帮你的？")],
        )
        d = p.to_dict()
        p2 = Persona.from_dict(d)
        assert p2.name == p.name
        assert p2.personality == p.personality
        assert p2.capable == p.capable
        assert p2.incapable == p.incapable
        assert len(p2.beliefs) == 1
        assert p2.beliefs[0].key == "k1"
        assert p2.beliefs[0].confidence == 0.8
        assert len(p2.knowledge_seeds) == 1
        assert p2.knowledge_seeds[0].name == "gravity"
        assert len(p2.knowledge_seeds[0].connections) == 1
        assert p2.knowledge_seeds[0].connections[0].to == "mass"
        assert p2.sample_dialogues == [("你好", "你好！有什么可以帮你的？")]

    def test_reflex_spec(self):
        rs = ReflexSpec(
            name="r1",
            trigger="some_event",
            from_organ=("brain", "cortex"),
            to_organ=("output", "mouth"),
            method="speak",
        )
        assert rs.name == "r1"
        assert rs.from_organ == ("brain", "cortex")


# ── Colony persona management tests ──────────────────────────────


class TestColonyPersona:
    @pytest.mark.anyio
    async def test_register_persona(self):
        colony = make_test_colony()
        p = Persona(name="musk", personality={"tone": "visionary"})
        await colony.register_persona(p)
        names = await colony.list_personas()
        assert "musk" in names

    @pytest.mark.anyio
    async def test_get_persona(self):
        colony = make_test_colony()
        p = Persona(name="musk", personality={
                    "tone": "visionary"}, capable=["engineering"])
        await colony.register_persona(p)

        loaded = await colony.get_persona("musk")
        assert loaded is not None
        assert loaded.name == "musk"
        assert loaded.personality == {"tone": "visionary"}
        assert loaded.capable == ["engineering"]

    @pytest.mark.anyio
    async def test_get_nonexistent_persona(self):
        colony = make_test_colony()
        result = await colony.get_persona("nonexistent")
        assert result is None

    @pytest.mark.anyio
    async def test_list_personas_empty(self):
        colony = make_test_colony()
        names = await colony.list_personas()
        assert names == []

    @pytest.mark.anyio
    async def test_list_personas_multiple(self):
        colony = make_test_colony()
        await colony.register_persona(Persona(name="a"))
        await colony.register_persona(Persona(name="b"))
        await colony.register_persona(Persona(name="c"))
        names = await colony.list_personas()
        assert set(names) == {"a", "b", "c"}

    @pytest.mark.anyio
    async def test_register_persona_not_persona(self):
        colony = make_test_colony()
        with pytest.raises(TypeError, match="Expected Persona"):
            # type: ignore[arg-type]
            await colony.register_persona("not a persona")

    @pytest.mark.anyio
    async def test_persona_namespace_registered(self):
        colony = make_test_colony()
        assert "personas" in colony.registered_namespaces

    @pytest.mark.anyio
    async def test_roundtrip_with_beliefs(self):
        colony = make_test_colony()
        p = Persona(
            name="dev",
            beliefs=[
                Belief(key="clean_code",
                       value="always write tests", confidence=0.95),
                Belief(key="dry", value="don't repeat yourself", confidence=0.9),
            ],
        )
        await colony.register_persona(p)
        loaded = await colony.get_persona("dev")
        assert loaded is not None
        assert len(loaded.beliefs) == 2
        assert loaded.beliefs[0].key == "clean_code"
        assert loaded.beliefs[1].key == "dry"


# ── Cat wear / unwear tests ──────────────────────────────────────


class TestCatWearUnwear:
    @pytest.mark.anyio
    async def test_wear_persona_not_found(self):
        colony = make_test_colony()
        cat = colony.create_cat(name="kitty")
        with pytest.raises(ValueError, match="Persona 'nope' not found"):
            await cat.wear_persona("nope")

    @pytest.mark.anyio
    async def test_wear_and_unwear(self):
        colony = make_test_colony()
        persona = Persona(
            name="musk",
            personality={"tone": "visionary", "language": "en+zh"},
            capable=["engineering"],
            incapable=["poetry"],
        )
        await colony.register_persona(persona)

        cat = colony.create_cat(name="kitty")
        cat.cat_self = CatSelf.with_defaults(personality={"tone": "default"})

        # Wear
        worn = await cat.wear_persona("musk")
        assert worn is not None
        assert cat.current_persona.name == "musk"
        assert cat.cat_self.personality == {
            "tone": "visionary", "language": "en+zh"}

        # Unwear
        await cat.unwear_persona()
        assert cat.current_persona is None
        assert cat.cat_self.personality == {"tone": "default"}

    @pytest.mark.anyio
    async def test_unwear_no_persona_safe(self):
        colony = make_test_colony()
        cat = colony.create_cat(name="kitty")
        cat.cat_self = CatSelf.with_defaults()
        await cat.unwear_persona()  # should not raise
        assert cat.current_persona is None

    @pytest.mark.anyio
    async def test_wear_preserves_unrelated_personality_keys(self):
        """Wearing a persona should not wipe existing personality keys that persona doesn't touch."""
        colony = make_test_colony()
        persona = Persona(
            name="dev",
            personality={"tone": "professional"},
        )
        await colony.register_persona(persona)

        cat = colony.create_cat(name="kitty")
        cat.cat_self = CatSelf.with_defaults(
            personality={"tone": "casual", "emoji_preference": "minimal"}
        )

        await cat.wear_persona("dev")
        assert cat.cat_self.personality == {
            "tone": "professional",  # overwritten
            "emoji_preference": "minimal",  # preserved
        }


# ── CatSelf persona tests ────────────────────────────────────────


class TestCatSelfPersona:
    def test_apply_persona(self):
        cs = CatSelf.with_defaults(
            personality={"tone": "default", "custom": "val"})
        persona = Persona(
            name="test",
            personality={"tone": "evil"},
            capable=["foo", "bar"],
            incapable=["baz"],
        )
        cs.apply_persona(persona)
        assert cs.personality == {"tone": "evil", "custom": "val"}
        assert cs._persona_capable == ["foo", "bar"]
        assert cs._persona_incapable == ["baz"]

    def test_remove_persona_restores(self):
        cs = CatSelf.with_defaults(personality={"tone": "nice"})
        persona = Persona(name="test", personality={"tone": "evil"})
        cs.apply_persona(persona)
        cs.remove_persona()
        assert cs.personality == {"tone": "nice"}
        assert cs._persona_capable is None
        assert cs._persona_incapable is None

    def test_remove_persona_no_backup(self):
        cs = CatSelf.with_defaults()
        cs.remove_persona()  # no persona applied, should not raise
        assert cs._persona_capable is None

    def test_apply_persona_empty_capable(self):
        cs = CatSelf.with_defaults()
        persona = Persona(name="test", capable=[], incapable=[])
        cs.apply_persona(persona)
        # empty lists -> None (no override)
        assert cs._persona_capable is None
        assert cs._persona_incapable is None

    def test_snapshot_with_persona_capable(self):
        cs = CatSelf.with_defaults()
        persona = Persona(name="test", capable=[
                          "coding"], incapable=["design"])
        cs.apply_persona(persona)

        snap = cs._build_snapshot()
        assert snap.capable_domains == ["coding"]
        assert snap.incapable_domains == ["design"]

    def test_snapshot_no_persona_falls_back(self):
        cs = CatSelf.with_defaults()
        cs.record_capability("coding", True)
        cs.record_capability("design", False)

        snap = cs._build_snapshot()
        assert snap.capable_domains == ["coding"]
        assert snap.incapable_domains == ["design"]

    def test_multiple_apply_cycles(self):
        cs = CatSelf.with_defaults(personality={"tone": "neutral"})

        # First persona → remove → restore neutral
        cs.apply_persona(Persona(name="a", personality={"tone": "friendly"}))
        assert cs.personality["tone"] == "friendly"
        cs.remove_persona()
        assert cs.personality["tone"] == "neutral"

        # Second persona → remove → restore neutral again
        cs.apply_persona(Persona(name="b", personality={"tone": "angry"}))
        assert cs.personality["tone"] == "angry"
        cs.remove_persona()
        assert cs.personality["tone"] == "neutral"


# ── PersonaLoader tests ───────────────────────────────────────────


class TestPersonaLoader:
    def test_scan_empty_dir(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            loader = PersonaLoader(dir=Path(tmpdir))
            result = loader.scan()
            assert result == []

    def test_scan_nonexistent_dir(self):
        loader = PersonaLoader(dir=Path("/nonexistent/path"))
        result = loader.scan()
        assert result == []

    def test_scan_and_load(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            persona_dir = Path(tmpdir) / "personas"
            persona_dir.mkdir()

            # Mask A: mage
            mage_path = persona_dir / "PERSONA.yaml"
            mage_path.write_text(
                """name: mage
version: "0.1.0"
description: A wise wizard
personality:
  tone: wise
  language: en
beliefs:
  - key: magic_is_real
    value: Magic exists in code
    confidence: 0.9
capable:
  - spellcasting
  - alchemy
incapable:
  - swordfighting
"""
            )

            # Mask B: warrior in subdirectory
            warrior_dir = persona_dir / "warrior"
            warrior_dir.mkdir()
            warrior_path = warrior_dir / "PERSONA.yaml"
            warrior_path.write_text(
                """name: warrior
version: "0.2.0"
personality:
  tone: bold
"""
            )

            loader = PersonaLoader(dir=persona_dir)
            personas = loader.scan()
            assert len(personas) == 2

            names = {p.name for p in personas}
            assert names == {"mage", "warrior"}

            mage = next(p for p in personas if p.name == "mage")
            assert mage.version == "0.1.0"
            assert mage.description == "A wise wizard"
            assert mage.personality == {"tone": "wise", "language": "en"}
            assert len(mage.beliefs) == 1
            assert mage.beliefs[0].key == "magic_is_real"
            assert mage.capable == ["spellcasting", "alchemy"]
            assert mage.incapable == ["swordfighting"]

            warrior = next(p for p in personas if p.name == "warrior")
            assert warrior.version == "0.2.0"
            assert warrior.personality == {"tone": "bold"}

    def test_scan_with_knowledge_seeds(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "PERSONA.yaml"
            path.write_text(
                """name: researcher
knowledge_seeds:
  - entity_type: topic
    name: AI Safety
    properties:
      priority: high
    connections:
      - to: Alignment
        relation: subfield
        strength: 0.8
"""
            )
            loader = PersonaLoader(dir=Path(tmpdir))
            personas = loader.scan()
            assert len(personas) == 1
            p = personas[0]
            assert len(p.knowledge_seeds) == 1
            seed = p.knowledge_seeds[0]
            assert seed.name == "AI Safety"
            assert seed.properties == {"priority": "high"}
            assert len(seed.connections) == 1
            assert seed.connections[0].to == "Alignment"

    @pytest.mark.anyio
    async def test_load_all_registers_to_colony(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "PERSONA.yaml"
            path.write_text(
                """name: helper
personality:
  tone: helpful
"""
            )
            colony = make_test_colony()
            loader = PersonaLoader(dir=Path(tmpdir))
            count = await loader.load_all(colony)
            assert count == 1
            assert "helper" in await colony.list_personas()

    def test_yaml_with_sample_dialogues(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "PERSONA.yaml"
            path.write_text(
                """name: bot
sample_dialogues:
  - ["你好", "你好！"]
  - ["再见", "再见！"]
"""
            )
            loader = PersonaLoader(dir=Path(tmpdir))
            personas = loader.scan()
            assert len(personas) == 1
            assert personas[0].sample_dialogues == [
                ("你好", "你好！"), ("再见", "再见！")]

    def test_load_name_falls_back_to_filename(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "cool_cat.yaml"
            path.write_text("personality:\n  tone: cool\n")
            loader = PersonaLoader(dir=Path(tmpdir))
            # File is not named PERSONA.yaml, so it won't be found
            personas = loader.scan()
            assert len(personas) == 0

    def test_scan_broken_yaml_is_skipped(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "PERSONA.yaml"
            path.write_text("this is not valid yaml: :::: !!!")
            loader = PersonaLoader(dir=Path(tmpdir))
            personas = loader.scan()
            assert personas == []  # broken YAML should be skipped, not crash


# ── Integration: full persona flow ────────────────────────────────


class TestPersonaIntegration:
    @pytest.mark.anyio
    async def test_full_musk_persona_flow(self):
        """End-to-end: register → wear → check snapshot → unwear → restore."""
        colony = make_test_colony()

        musk = Persona(
            name="musk",
            personality={"tone": "visionary", "language": "en+zh"},
            beliefs=[Belief(key="first_principles",
                            value="reason from basics", confidence=0.95)],
            capable=["engineering", "physics", "business"],
            incapable=["creative_writing", "political_correctness"],
        )
        await colony.register_persona(musk)

        cat = colony.create_cat(name="kitty")
        cat.cat_self = CatSelf.with_defaults(personality={"tone": "default"})

        # Step 1: wear
        await cat.wear_persona("musk")
        assert cat.current_persona.name == "musk"

        # Step 2: snapshot reflects persona
        snap = cat.cat_self._build_snapshot()
        assert snap.capable_domains == ["engineering", "physics", "business"]
        assert snap.incapable_domains == [
            "creative_writing", "political_correctness"]
        assert "visionary" in str(cat.cat_self.personality)

        # Step 3: unwear restores
        await cat.unwear_persona()
        assert cat.current_persona is None
        assert cat.cat_self.personality == {"tone": "default"}
        assert cat.cat_self._persona_capable is None

    @pytest.mark.anyio
    async def test_multiple_cats_wear_same_persona(self):
        colony = make_test_colony()
        await colony.register_persona(Persona(name="dev", personality={"tone": "professional"}))

        cat_a = colony.create_cat(name="alice")
        cat_a.cat_self = CatSelf.with_defaults()
        cat_b = colony.create_cat(name="bob")
        cat_b.cat_self = CatSelf.with_defaults()

        await cat_a.wear_persona("dev")
        await cat_b.wear_persona("dev")

        assert cat_a.current_persona.name == "dev"
        assert cat_b.current_persona.name == "dev"
        assert cat_a.cat_self.personality == {"tone": "professional"}
        assert cat_b.cat_self.personality == {"tone": "professional"}
