# Copyright (c) 2026 Axonant
# SPDX-License-Identifier: MIT

"""v1.1.22 Collective Growth — anomaly/correction shared to growth/ namespace + colony-level role emergence."""

from __future__ import annotations

import asyncio

from meowcat.colony import Colony
from meowcat.defaults.stores import InMemorySharedStore


def _run(coro):
    return asyncio.run(coro)


# -- 1. CollectiveGrowth — anomaly recording --------------------------------

class TestCollectiveGrowthAnomaly:
    """CollectiveGrowth records anomalies to colony growth/ namespace."""

    def test_record_anomaly(self):
        """record_anomaly stores an anomaly in growth/anomaly:{ts}."""
        colony = Colony("test-ag", storage=InMemorySharedStore())

        async def _test():
            key = await colony.growth.record_anomaly(
                "cat1", "DB schema mismatch",
                snippet="table users not found",
                confidence=0.9, phase="execute",
            )
            assert key.startswith("anomaly:")
            anomalies = await colony.growth.list_anomalies()
            assert len(anomalies) >= 1
            assert anomalies[0]["cat_uid"] == "cat1"
            assert anomalies[0]["reason"] == "DB schema mismatch"
            assert anomalies[0]["confidence"] == 0.9
            assert anomalies[0]["phase"] == "execute"
        _run(_test())

    def test_record_multiple_anomalies(self):
        """Multiple anomalies from different cats are tracked separately."""
        colony = Colony("test-ag2", storage=InMemorySharedStore())

        async def _test():
            await colony.growth.record_anomaly("cat1", "SQL syntax error")
            await colony.growth.record_anomaly("cat2", "Timeout on API")
            await colony.growth.record_anomaly("cat1", "Memory leak")

            all_ = await colony.growth.list_anomalies()
            cat1 = await colony.growth.list_anomalies(cat_uid="cat1")
            cat2 = await colony.growth.list_anomalies(cat_uid="cat2")

            assert len(all_) == 3
            assert len(cat1) == 2
            assert len(cat2) == 1
        _run(_test())

    def test_anomalies_sorted_newest_first(self):
        """list_anomalies returns newest first."""
        colony = Colony("test-ag3", storage=InMemorySharedStore())

        async def _test():
            await colony.growth.record_anomaly("cat1", "First", snippet="old")
            await colony.growth.record_anomaly("cat1", "Second", snippet="new")

            results = await colony.growth.list_anomalies()
            assert results[0]["reason"] == "Second"
            assert results[1]["reason"] == "First"
        _run(_test())


# -- 2. CollectiveGrowth — correction recording ------------------------------

class TestCollectiveGrowthCorrection:
    """CollectiveGrowth records corrections to colony growth/ namespace."""

    def test_record_correction(self):
        """record_correction stores a correction in growth/correction:{ts}."""
        colony = Colony("test-cg", storage=InMemorySharedStore())

        async def _test():
            key = await colony.growth.record_correction(
                "cat1",
                wrong="DROP TABLE users",
                correct="DELETE FROM users WHERE id=:id",
                topic="SQL安全",
            )
            assert key.startswith("correction:")
            corrections = await colony.growth.list_corrections()
            assert len(corrections) >= 1
            assert corrections[0]["cat_uid"] == "cat1"
            assert corrections[0]["wrong"] == "DROP TABLE users"
            assert corrections[0]["correct"] == "DELETE FROM users WHERE id=:id"
            assert corrections[0]["topic"] == "SQL安全"
        _run(_test())

    def test_list_corrections_by_cat(self):
        """list_corrections can filter by cat_uid."""
        colony = Colony("test-cg2", storage=InMemorySharedStore())

        async def _test():
            await colony.growth.record_correction("cat1", "wrong1", "correct1")
            await colony.growth.record_correction("cat2", "wrong2", "correct2")

            assert len(await colony.growth.list_corrections()) == 2
            assert len(await colony.growth.list_corrections(cat_uid="cat1")) == 1
            assert len(await colony.growth.list_corrections(
                cat_uid="cat3")) == 0
        _run(_test())


# -- 3. CollectiveGrowth — count + diagnose ---------------------------------

class TestCollectiveGrowthMisc:
    """CollectiveGrowth count and diagnose methods."""

    def test_count(self):
        """count returns anomaly and correction counts."""
        colony = Colony("test-cnt", storage=InMemorySharedStore())

        async def _test():
            await colony.growth.record_anomaly("cat1", "err1")
            await colony.growth.record_anomaly("cat1", "err2")
            await colony.growth.record_correction("cat1", "w", "c")

            cnt = await colony.growth.count()
            assert cnt["anomalies"] == 2
            assert cnt["corrections"] == 1
        _run(_test())

    def test_diagnose(self):
        """diagnose returns snapshot with counts and plug info."""
        colony = Colony("test-diag", storage=InMemorySharedStore())

        async def _test():
            await colony.growth.record_anomaly("cat1", "err1")
            d = await colony.growth.diagnose()
            assert d["anomalies"] == 1
            assert d["corrections"] == 0
            assert "growth_ns" in d
            assert "plugs" in d
        _run(_test())


# -- 4. CollectiveGrowth — pluggable strategy -------------------------------

class TestCollectiveGrowthPlug:
    """CollectiveGrowth strategy plug can veto recording."""

    def test_strategy_veto_anomaly(self):
        """strategy plug returning False stops anomaly recording."""
        colony = Colony("test-veto", storage=InMemorySharedStore())

        def veto_low_confidence(cat_uid, event):
            if event.get("confidence", 0) < 0.9:
                return False
            return None

        colony.growth.plug("strategy", veto_low_confidence)

        async def _test():
            # confidence=0.5 < 0.9 → vetoed
            key = await colony.growth.record_anomaly(
                "cat1", "low confidence", confidence=0.5)
            assert key == ""
            assert (await colony.growth.count())["anomalies"] == 0

            # confidence=0.95 >= 0.9 → allowed
            await colony.growth.record_anomaly(
                "cat1", "high confidence", confidence=0.95)
            assert (await colony.growth.count())["anomalies"] == 1
        _run(_test())

    def test_strategy_veto_correction(self):
        """strategy plug returning False stops correction recording."""
        colony = Colony("test-veto2", storage=InMemorySharedStore())

        def block_drop(cat_uid, event):
            if "DROP" in event.get("wrong", ""):
                return False
            return None

        colony.growth.plug("strategy", block_drop)

        async def _test():
            key = await colony.growth.record_correction(
                "cat1", "DROP TABLE x", "DELETE x")
            assert key == ""
        _run(_test())


# -- 5. CollectiveEmergence — role detection ---------------------------------

class TestCollectiveEmergence:
    """CollectiveEmergence detects roles from anomaly/correction patterns."""

    def test_detect_roles_from_anomalies(self):
        """detect_roles surfaces cats with recurring anomaly patterns."""
        colony = Colony("test-em", storage=InMemorySharedStore())

        async def _test():
            # Cat1 specialises in SQL detection
            await colony.growth.record_anomaly(
                "sql-guard", "SQL注入风险", confidence=0.9)
            await colony.growth.record_anomaly(
                "sql-guard", "SQL schema错误", confidence=0.85)

            # Cat2 has only one event — not enough for role detection
            await colony.growth.record_anomaly(
                "helper", "timeout", confidence=0.7)

            roles = await colony.emergence.detect_roles(min_events=2)

            # Cat1 should have a role
            sql_roles = [r for r in roles if r["cat_uid"] == "sql-guard"]
            assert len(sql_roles) >= 1
            # Default detector should infer SQL-related role
            assert any("SQL" in sql_roles[0]["role"] for _ in [1])

            # Cat2 should not have a role (below min_events)
            helper_roles = [r for r in roles if r["cat_uid"] == "helper"]
            assert len(helper_roles) == 0
        _run(_test())

    def test_detect_roles_empty(self):
        """detect_roles returns empty when no growth events exist."""
        colony = Colony("test-em2", storage=InMemorySharedStore())

        async def _test():
            roles = await colony.emergence.detect_roles()
            assert roles == []
        _run(_test())


# -- 6. CollectiveEmergence — record_pattern + list -------------------------

class TestCollectiveEmergencePatterns:
    """CollectiveEmergence record_pattern and list methods."""

    def test_record_pattern(self):
        """record_pattern stores to growth/role:{ts}."""
        colony = Colony("test-rp", storage=InMemorySharedStore())

        async def _test():
            key = await colony.emergence.record_pattern(
                "cat1", "SQL审查",
                evidence="发现3次SQL异常",
            )
            assert key.startswith("role:")

            patterns = await colony.emergence.list_patterns()
            assert len(patterns) >= 1
            assert patterns[0]["cat_uid"] == "cat1"
            assert patterns[0]["pattern"] == "SQL审查"
        _run(_test())

    def test_list_patterns_filter_cat(self):
        """list_patterns can filter by cat_uid."""
        colony = Colony("test-rp2", storage=InMemorySharedStore())

        async def _test():
            await colony.emergence.record_pattern("cat1", "p1")
            await colony.emergence.record_pattern("cat2", "p2")

            assert len(await colony.emergence.list_patterns()) == 2
            assert len(await colony.emergence.list_patterns(cat_uid="cat1")) == 1
        _run(_test())


# -- 7. CollectiveEmergence — diagnose + custom detector --------------------

class TestCollectiveEmergencePlug:
    """CollectiveEmergence detect plug for custom role detection."""

    def test_custom_detector(self):
        """Custom detector via plug replaces default role detection."""
        colony = Colony("test-cd", storage=InMemorySharedStore())

        def my_detector(events):
            return [{"cat_uid": "always", "role": "custom",
                     "confidence": 1.0, "events_seen": len(events)}]

        colony.emergence.plug("detector", my_detector)

        async def _test():
            await colony.growth.record_anomaly("cat1", "test reason")
            roles = await colony.emergence.detect_roles()
            assert len(roles) == 1
            assert roles[0]["cat_uid"] == "always"
            assert roles[0]["role"] == "custom"
        _run(_test())

    def test_diagnose(self):
        """diagnose returns snapshot with growth counts and patterns."""
        colony = Colony("test-diag2", storage=InMemorySharedStore())

        async def _test():
            await colony.growth.record_anomaly("cat1", "test")
            await colony.emergence.record_pattern("cat1", "test pattern")

            d = await colony.emergence.diagnose()
            assert d["anomalies"] == 1
            assert d["corrections"] == 0
            assert "role_patterns" in d
            assert "recent_patterns" in d
            assert "plugs" in d
        _run(_test())


# -- 8. Full lifecycle integration -----------------------------------------

class TestFullLifecycle:
    """End-to-end: anomaly → emergence → roles."""

    def test_full_cycle(self):
        """A complete growth cycle: record anomalies → detect roles."""
        colony = Colony("test-full22", storage=InMemorySharedStore())

        async def _test():
            # Phase 1: cats work and record anomalies
            await colony.growth.record_anomaly(
                "db-expert", "SQL注入 detected", confidence=0.92)
            await colony.growth.record_anomaly(
                "db-expert", "SQL schema mismatch", confidence=0.88)
            await colony.growth.record_correction(
                "db-expert", "SELECT * without WHERE",
                correct="SELECT * WHERE id=:id", topic="SQL优化")

            await colony.growth.record_anomaly(
                "sec-guard", "XSS detected in input", confidence=0.95)
            await colony.growth.record_anomaly(
                "sec-guard", "CSRF token missing", confidence=0.90)

            # Phase 2: emergence detects roles
            roles = await colony.emergence.detect_roles(min_events=2)

            # db-expert should have a role
            db_roles = [r for r in roles if r["cat_uid"] == "db-expert"]
            assert len(db_roles) >= 1
            assert db_roles[0]["evidence_count"] >= 3
            assert db_roles[0]["confidence"] > 0

            # sec-guard should have a role
            sec_roles = [r for r in roles if r["cat_uid"] == "sec-guard"]
            assert len(sec_roles) >= 1
            assert sec_roles[0]["evidence_count"] >= 2

            # Phase 3: record emergent role pattern
            await colony.emergence.record_pattern(
                "db-expert", "数据库安全检查",
                evidence="连续发现SQL相关异常")

            patterns = await colony.emergence.list_patterns(cat_uid="db-expert")
            assert len(patterns) >= 1
            assert patterns[0]["pattern"] == "数据库安全检查"
        _run(_test())

