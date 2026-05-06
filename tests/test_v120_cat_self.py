# Copyright (c) 2026 Axonant
# SPDX-License-Identifier: MIT

"""v1.2.0 CatSelf — unified self + three default closed loops."""

from __future__ import annotations

import pytest

from meowcat.biology.cat_self import (
    CatSelf,
    DefaultConversationLoop,
    DefaultLearnLoop,
    DefaultTaskLoop,
    SelfSnapshot,
)
from meowcat.biology.cortex import Cortex
from meowcat.biology.metacognition import Metacognition
from meowcat.biology.pineal_gland import PinealGland
from meowcat.biology.scribble_pad import ScribblePad
from meowcat.tools.skill import SkillRegistry


# -- Fixtures ---------------------------------------------------------


@pytest.fixture
def pad():
    return ScribblePad(capacity=10)


@pytest.fixture
def gland(pad):
    return PinealGland(pad)


@pytest.fixture
def cortex():
    return Cortex()


@pytest.fixture
def metacog():
    return Metacognition()


@pytest.fixture
def skills():
    return SkillRegistry()


@pytest.fixture
def basic_cat_self(pad, cortex):
    """Minimal CatSelf with just personality + pad + cortex."""
    return CatSelf(
        personality={"tone": "friendly", "language": "zh"},
        cortex=cortex,
        scribble_pad=pad,
    )


@pytest.fixture
def full_cat_self(pad, gland, cortex, metacog, skills):
    """Fully wired CatSelf."""
    return CatSelf(
        personality={"tone": "professional", "language": "en"},
        cortex=cortex,
        scribble_pad=pad,
        pineal_gland=gland,
        metacognition=metacog,
        skills=skills,
    )


# -- Mock Cat for loop tests ------------------------------------------


class MockCat:
    """Minimal cat stub for testing default loops."""

    def __init__(self, cat_self):
        self.cat_self = cat_self


# -- 1. SelfSnapshot --------------------------------------------------


class TestSelfSnapshot:
    """SelfSnapshot dataclass."""

    def test_default_fields(self):
        snap = SelfSnapshot()
        assert snap.personality == {}
        assert snap.beliefs == []
        assert snap.skill_names == []
        assert snap.reflex_names == []
        assert snap.capable_domains == []
        assert snap.incapable_domains == []
        assert snap.scribble_count == 0

    def test_custom_fields(self):
        snap = SelfSnapshot(
            personality={"tone": "friendly"},
            beliefs=[("sql", "use params", 0.9, True)],
            skill_names=["read_file", "search"],
            reflex_names=["text_dialogue"],
            capable_domains=["backend"],
            incapable_domains=["frontend"],
            scribble_count=5,
        )
        assert snap.personality == {"tone": "friendly"}
        assert len(snap.beliefs) == 1
        assert snap.skill_names == ["read_file", "search"]
        assert snap.scribble_count == 5


# -- 2. CatSelf — basic properties -----------------------------------


class TestCatSelfProperties:
    """CatSelf property access."""

    def test_minimal_construction(self):
        cs = CatSelf(personality={"lang": "zh"})
        assert cs.personality == {"lang": "zh"}
        assert cs.cortex is None
        assert cs.worldview is None
        assert cs.skills is None
        assert cs.reflexes is None
        assert cs.scribble_pad is None
        assert cs.pineal_gland is None
        assert cs.metacognition is None

    def test_full_construction(self, pad, gland, cortex, metacog, skills):
        cs = CatSelf(
            personality={"tone": "friendly"},
            cortex=cortex,
            scribble_pad=pad,
            pineal_gland=gland,
            metacognition=metacog,
            skills=skills,
        )
        assert cs.personality == {"tone": "friendly"}
        assert cs.cortex is cortex
        assert cs.worldview is cortex  # defaults to cortex
        assert cs.scribble_pad is pad
        assert cs.pineal_gland is gland
        assert cs.metacognition is metacog
        assert cs.skills is skills

    def test_separate_worldview(self, pad, cortex):
        worldview_cortex = Cortex()
        cs = CatSelf(
            cortex=cortex,
            worldview=worldview_cortex,
            scribble_pad=pad,
        )
        assert cs.cortex is cortex
        assert cs.worldview is worldview_cortex
        assert cs.worldview is not cortex

    def test_personality_mutable(self):
        cs = CatSelf(personality={"tone": "friendly"})
        cs.personality["tone"] = "serious"
        assert cs.personality["tone"] == "serious"


# -- 3. CatSelf — before_act / after_act ------------------------------


class TestCatSelfBeforeAfter:
    """before_act and after_act loop nodes."""

    @pytest.mark.asyncio
    async def test_before_act_basic(self, basic_cat_self, cortex):
        """before_act returns SelfSnapshot."""
        cortex.promote_to_belief("test", "always_test", 0.95)
        snap = await basic_cat_self.before_act("conversation")
        assert isinstance(snap, SelfSnapshot)
        assert snap.personality == {"tone": "friendly", "language": "zh"}
        assert ("test", "always_test", 0.95, True) in snap.beliefs

    @pytest.mark.asyncio
    async def test_before_act_empty(self, pad):
        """before_act works with minimal CatSelf."""
        cs = CatSelf(scribble_pad=pad)
        snap = await cs.before_act("task")
        assert isinstance(snap, SelfSnapshot)
        assert snap.personality == {}
        assert snap.beliefs == []
        assert snap.scribble_count == 0

    @pytest.mark.asyncio
    async def test_before_act_snapshot_scribble_count(self, pad):
        """before_act captures scribble count."""
        pad.scribble("a")
        pad.scribble("b")
        cs = CatSelf(scribble_pad=pad)
        snap = await cs.before_act("learn")
        assert snap.scribble_count == 2

    @pytest.mark.asyncio
    async def test_after_act_writes_to_pad(self, pad):
        """after_act scribbles a summary entry."""
        cs = CatSelf(scribble_pad=pad)
        await cs.after_act("did something", {"key": "val"})
        assert pad.count() == 1
        entry = pad.peek(1)[0]
        assert entry["summary"] == "did something"
        assert entry["impact"] == {"key": "val"}

    @pytest.mark.asyncio
    async def test_after_act_without_pad(self):
        """after_act is safe when no scribble_pad."""
        cs = CatSelf()
        await cs.after_act("no pad", {})
        # Should not raise

    @pytest.mark.asyncio
    async def test_after_act_empty_impact(self, pad):
        """after_act defaults impact to {} when None."""
        cs = CatSelf(scribble_pad=pad)
        await cs.after_act("summary only")
        entry = pad.peek(1)[0]
        assert entry["impact"] == {}


# -- 4. CatSelf — plugin hooks ----------------------------------------


class TestCatSelfPlugs:
    """Pluggable hooks on CatSelf."""

    @pytest.mark.asyncio
    async def test_before_act_override(self, pad):
        """before_act plugin can override snapshot."""
        cs = CatSelf(scribble_pad=pad)
        custom = SelfSnapshot(personality={"custom": True})
        cs.plug("before_act", lambda reason: custom)

        snap = await cs.before_act("test")
        assert snap is custom
        assert snap.personality == {"custom": True}

    @pytest.mark.asyncio
    async def test_after_act_plugin_fires(self, pad):
        """after_act plugin receives summary and impact."""
        cs = CatSelf(scribble_pad=pad)
        received = []

        def tracker(summary, impact):
            received.append((summary, impact))

        cs.plug("after_act", tracker)
        await cs.after_act("test summary", {"a": 1})
        assert len(received) == 1
        assert received[0] == ("test summary", {"a": 1})

    @pytest.mark.asyncio
    async def test_unplug(self, pad):
        """unplug removes a plugin."""
        cs = CatSelf(scribble_pad=pad)
        def fn(reason): return SelfSnapshot(personality={"plugged": True})
        cs.plug("before_act", fn)
        snap = await cs.before_act("test")
        assert snap.personality == {"plugged": True}

        cs.unplug("before_act", fn)
        snap2 = await cs.before_act("test")
        assert snap2.personality != {"plugged": True}

    def test_diagnose(self, pad, cortex):
        """diagnose returns wiring status."""
        cs = CatSelf(
            personality={"tone": "friendly"},
            cortex=cortex,
            scribble_pad=pad,
        )
        diag = cs.diagnose()
        assert diag["has_cortex"] is True
        assert diag["has_scribble_pad"] is True
        assert diag["has_pineal_gland"] is False
        assert diag["has_metacognition"] is False
        assert "personality_keys" in diag
        assert "plugs" in diag


# -- 5. CatSelf — loop() dispatcher -----------------------------------


class TestCatSelfLoop:
    """loop() returns correct default loop instances."""

    def test_loop_conversation(self, basic_cat_self):
        loop = basic_cat_self.loop("conversation")
        assert isinstance(loop, DefaultConversationLoop)

    def test_loop_task(self, basic_cat_self):
        loop = basic_cat_self.loop("task")
        assert isinstance(loop, DefaultTaskLoop)

    def test_loop_learn(self, basic_cat_self):
        loop = basic_cat_self.loop("learn")
        assert isinstance(loop, DefaultLearnLoop)

    def test_loop_invalid(self, basic_cat_self):
        with pytest.raises(ValueError, match="Unknown loop"):
            basic_cat_self.loop("nonexistent")


# -- 6. DefaultConversationLoop ---------------------------------------


class TestDefaultConversationLoop:
    """Default conversation closed loop."""

    @pytest.mark.asyncio
    async def test_run_basic(self, pad):
        """Conversation loop fires before_act/after_act. PinealGland drains pad on trigger."""
        cs = CatSelf(scribble_pad=pad, pineal_gland=PinealGland(pad))
        cat = MockCat(cs)
        loop = DefaultConversationLoop()
        response = await loop.run(cat, "hello world")
        assert "hello world" in response
        # Pad is drained by PinealGland trigger_if(on_event) → 0 entries remain
        assert pad.count() == 0

    @pytest.mark.asyncio
    async def test_run_without_pineal(self, pad):
        """Works without pineal gland."""
        cs = CatSelf(scribble_pad=pad)
        cat = MockCat(cs)
        loop = DefaultConversationLoop()
        response = await loop.run(cat, "hi")
        assert isinstance(response, str)

    @pytest.mark.asyncio
    async def test_run_without_pad(self):
        """Works without scribble pad."""
        cs = CatSelf()
        cat = MockCat(cs)
        loop = DefaultConversationLoop()
        response = await loop.run(cat, "hi")
        assert isinstance(response, str)


# -- 7. DefaultTaskLoop -----------------------------------------------


class TestDefaultTaskLoop:
    """Default task closed loop."""

    @pytest.mark.asyncio
    async def test_run_basic(self, pad):
        cs = CatSelf(scribble_pad=pad)
        cat = MockCat(cs)
        loop = DefaultTaskLoop()
        result = await loop.run(cat, "deploy to prod")
        assert result["task"] == "deploy to prod"
        assert result["status"] == "planned"
        assert pad.count() >= 1

    @pytest.mark.asyncio
    async def test_run_without_pad(self):
        cs = CatSelf()
        cat = MockCat(cs)
        loop = DefaultTaskLoop()
        result = await loop.run(cat, "test task")
        assert result["status"] == "planned"


# -- 8. DefaultLearnLoop ----------------------------------------------


class TestDefaultLearnLoop:
    """Default learn closed loop."""

    @pytest.mark.asyncio
    async def test_run_basic(self, pad):
        """Learn loop fires before_act/after_act. PinealGland trigger() drains pad."""
        cs = CatSelf(scribble_pad=pad, pineal_gland=PinealGland(pad))
        cat = MockCat(cs)
        loop = DefaultLearnLoop()
        result = await loop.run(cat, "Kubernetes networking")
        assert result["topic"] == "Kubernetes networking"
        assert result["learned"] is True
        # Pad is drained by PinealGland trigger() → 0 entries remain
        assert pad.count() == 0

    @pytest.mark.asyncio
    async def test_run_without_pineal(self, pad):
        """Works without pineal gland."""
        cs = CatSelf(scribble_pad=pad)
        cat = MockCat(cs)
        loop = DefaultLearnLoop()
        result = await loop.run(cat, "something")
        assert result["learned"] is True


# -- 9. CatSelf with metacognition ------------------------------------


class TestCatSelfWithMetacognition:
    """CatSelf snapshots include metacognition data."""

    @pytest.mark.asyncio
    async def test_snapshot_includes_capable_domains(self, pad, metacog):
        metacog.record_capability("sql", True, "has mysql tool")
        metacog.record_capability("frontend", False, "no js engine")
        cs = CatSelf(scribble_pad=pad, metacognition=metacog)
        snap = await cs.before_act("task")
        assert "sql" in snap.capable_domains
        assert "frontend" in snap.incapable_domains


# -- 10. CatSelf with skills ------------------------------------------


class TestCatSelfWithSkills:
    """CatSelf snapshots include skill names."""

    @pytest.mark.asyncio
    async def test_snapshot_includes_skill_names(self, pad, skills):
        from meowcat.tools.skill import Skill, SkillSpec
        skills.register(
            Skill(SkillSpec(name="read_file", description="Read file")))
        cs = CatSelf(scribble_pad=pad, skills=skills)
        snap = await cs.before_act("task")
        assert "read_file" in snap.skill_names

