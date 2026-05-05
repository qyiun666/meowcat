"""v1.1.28 GlobalColonyRegistry — multi-colony global registry tests."""

from __future__ import annotations

import pytest

from meowcat.colony import Colony, GlobalColonyRegistry
from meowcat.pluggable import Pluggable


# ════════════════════════════════════════════════════════════════════
# Helpers
# ════════════════════════════════════════════════════════════════════

def _make_colony(cid: str) -> Colony:
    """Create a Colony with InMemorySharedStore for testing."""
    return Colony.default(cid)


# ════════════════════════════════════════════════════════════════════
# Registration
# ════════════════════════════════════════════════════════════════════

class TestRegistration:
    """Register / unregister colonies."""

    def test_register_colony(self):
        reg = GlobalColonyRegistry()
        c = _make_colony("feishu")
        reg.register(c)
        assert "feishu" in reg.list_colonies()
        assert reg.colony_count == 1

    def test_register_overwrites(self):
        reg = GlobalColonyRegistry()
        c1 = _make_colony("feishu")
        c2 = _make_colony("feishu")
        reg.register(c1)
        reg.register(c2)
        assert reg.get_colony("feishu") is c2  # overwritten
        assert reg.colony_count == 1

    def test_unregister_existing(self):
        reg = GlobalColonyRegistry()
        c = _make_colony("feishu")
        reg.register(c)
        assert reg.unregister("feishu") is True
        assert reg.colony_count == 0

    def test_unregister_nonexistent(self):
        reg = GlobalColonyRegistry()
        assert reg.unregister("nope") is False

    def test_multiple_colonies(self):
        reg = GlobalColonyRegistry()
        reg.register(_make_colony("feishu"))
        reg.register(_make_colony("wechat"))
        reg.register(_make_colony("cli"))
        assert reg.colony_count == 3
        assert set(reg.list_colonies()) == {"feishu", "wechat", "cli"}


# ════════════════════════════════════════════════════════════════════
# Lookup
# ════════════════════════════════════════════════════════════════════

class TestLookup:
    """get_colony / find_cat."""

    def test_get_colony(self):
        reg = GlobalColonyRegistry()
        c = _make_colony("feishu")
        reg.register(c)
        assert reg.get_colony("feishu") is c

    def test_get_colony_not_found(self):
        reg = GlobalColonyRegistry()
        with pytest.raises(KeyError, match="nope"):
            reg.get_colony("nope")

    def test_find_cat_by_uid(self):
        reg = GlobalColonyRegistry()
        c = _make_colony("feishu")
        cat = c.create_cat(name="planner")
        reg.register(c)
        found = reg.find_cat(f"feishu_{cat.cat_uid}")
        assert found is cat

    def test_find_cat_by_address(self):
        reg = GlobalColonyRegistry()
        c = _make_colony("feishu")
        cat = c.create_cat(name="planner")
        reg.register(c)
        # cat_address format: colony_id_cat_uid
        found = reg.find_cat(cat.cat_address)
        assert found is cat

    def test_find_cat_invalid_address(self):
        reg = GlobalColonyRegistry()
        reg.register(_make_colony("feishu"))
        with pytest.raises(ValueError, match="Invalid address"):
            reg.find_cat("noseparator")
        with pytest.raises(ValueError, match="Invalid address"):
            reg.find_cat("")
        with pytest.raises(ValueError, match="Invalid address"):
            reg.find_cat("/")

    def test_find_cat_colony_not_found(self):
        reg = GlobalColonyRegistry()
        with pytest.raises(KeyError, match="nope"):
            reg.find_cat("nope_nope01")

    def test_find_cat_not_found(self):
        reg = GlobalColonyRegistry()
        c = _make_colony("feishu")
        c.create_cat(name="planner")
        reg.register(c)
        with pytest.raises(KeyError, match="nope01"):
            reg.find_cat(f"feishu_nope01")


# ════════════════════════════════════════════════════════════════════
# Listing
# ════════════════════════════════════════════════════════════════════

class TestListing:
    """list_colonies / list_cats / list_all_cats."""

    def test_list_colonies_empty(self):
        reg = GlobalColonyRegistry()
        assert reg.list_colonies() == []

    def test_list_cats(self):
        reg = GlobalColonyRegistry()
        c = _make_colony("feishu")
        a = c.create_cat(name="a")
        b = c.create_cat(name="b")
        reg.register(c)
        assert set(reg.list_cats("feishu")) == {a.cat_uid, b.cat_uid}

    def test_list_cats_colony_not_found(self):
        reg = GlobalColonyRegistry()
        with pytest.raises(KeyError, match="nope"):
            reg.list_cats("nope")

    def test_list_all_cats(self):
        reg = GlobalColonyRegistry()
        c1 = _make_colony("feishu")
        a = c1.create_cat(name="a")
        b = c1.create_cat(name="b")
        c2 = _make_colony("wechat")
        x = c2.create_cat(name="x")
        reg.register(c1)
        reg.register(c2)
        all_cats = reg.list_all_cats()
        assert all_cats == {"feishu": [
            a.cat_uid, b.cat_uid], "wechat": [x.cat_uid]}

    def test_list_all_cats_empty(self):
        reg = GlobalColonyRegistry()
        assert reg.list_all_cats() == {}


# ════════════════════════════════════════════════════════════════════
# Counts
# ════════════════════════════════════════════════════════════════════

class TestCounts:
    """colony_count / total_cat_count."""

    def test_colony_count_zero(self):
        reg = GlobalColonyRegistry()
        assert reg.colony_count == 0

    def test_total_cat_count(self):
        reg = GlobalColonyRegistry()
        c1 = _make_colony("feishu")
        c1.create_cat(name="a")
        c1.create_cat(name="b")
        c2 = _make_colony("wechat")
        c2.create_cat(name="x")
        c2.create_cat(name="y")
        c2.create_cat(name="z")
        reg.register(c1)
        reg.register(c2)
        assert reg.total_cat_count() == 5

    def test_total_cat_count_zero(self):
        reg = GlobalColonyRegistry()
        assert reg.total_cat_count() == 0

    def test_total_cat_count_empty_colonies(self):
        reg = GlobalColonyRegistry()
        reg.register(_make_colony("empty1"))
        reg.register(_make_colony("empty2"))
        assert reg.total_cat_count() == 0


# ════════════════════════════════════════════════════════════════════
# Pluggable Hooks
# ════════════════════════════════════════════════════════════════════

class TestPluggableHooks:
    """on_register / on_unregister plugin hooks."""

    def test_on_register_hook_fires(self):
        reg = GlobalColonyRegistry()
        calls: list[str] = []

        def hook(colony):
            calls.append(colony.colony_id)

        reg.plug("on_register", hook)
        reg.register(_make_colony("feishu"))
        assert calls == ["feishu"]

    def test_on_register_multiple_hooks(self):
        reg = GlobalColonyRegistry()
        calls: list[str] = []

        reg.plug("on_register", lambda c: calls.append(f"h1:{c.colony_id}"))
        reg.plug("on_register", lambda c: calls.append(f"h2:{c.colony_id}"))
        reg.register(_make_colony("feishu"))
        assert calls == ["h1:feishu", "h2:feishu"]

    def test_on_unregister_hook_fires(self):
        reg = GlobalColonyRegistry()
        calls: list[str] = []

        def hook(colony_id):
            calls.append(colony_id)

        reg.plug("on_unregister", hook)
        reg.register(_make_colony("feishu"))
        reg.unregister("feishu")
        assert calls == ["feishu"]

    def test_on_unregister_hook_not_fired_when_not_found(self):
        reg = GlobalColonyRegistry()
        calls: list[str] = []

        reg.plug("on_unregister", lambda cid: calls.append(cid))
        reg.unregister("nope")
        assert calls == []

    def test_pluggable_inheritance(self):
        reg = GlobalColonyRegistry()
        assert isinstance(reg, Pluggable)
        assert "on_register" in reg.HOOKS
        assert "on_unregister" in reg.HOOKS

    def test_list_plugs(self):
        reg = GlobalColonyRegistry()
        reg.plug("on_register", lambda c: None)
        reg.plug("on_unregister", lambda cid: None)
        plugs = reg.list_plugs()
        assert plugs == {"on_register": 1, "on_unregister": 1}

    def test_unplug(self):
        reg = GlobalColonyRegistry()

        def hook(colony):
            pass

        reg.plug("on_register", hook)
        assert reg.list_plugs() == {"on_register": 1}
        reg.unplug("on_register", hook)
        assert reg.list_plugs() == {}
