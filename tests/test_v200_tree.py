# Copyright (c) 2026 Axonant
# SPDX-License-Identifier: MIT

"""meowcat standalone tests: v2.0 KnowledgeTree (TreeNode + Hippocampus tree methods).

Validates:
- TreeNode dataclass creation and defaults
- NoopHippocampus build_tree / get_tree / delete_tree
- NoopHippocampus search_tree keyword matching
- NoopHippocampus query_subtree depth-limited traversal
- NoopHippocampus check_stale detection
- Path execution via cat.path_registry for tree paths
- BUILTIN_PATHS includes 4 tree paths
"""
from __future__ import annotations

import pytest

from meowcat.defaults.organs.hippocampus import NoopHippocampus
from meowcat.path import BUILTIN_PATHS
from meowcat.testing import make_cat
from meowcat.tree import TreeNode


class TestTreeNode:
    """TreeNode dataclass construction and field defaults."""

    def test_create_root_node(self):
        root = TreeNode(id="r", entity_id="e1", parent_id=None,
                        path="/", node_type="project", name="p")
        assert root.id == "r"
        assert root.entity_id == "e1"
        assert root.parent_id is None
        assert root.path == "/"
        assert root.node_type == "project"
        assert root.name == "p"

    def test_create_leaf_node(self):
        leaf = TreeNode(id="n1", entity_id="e1", parent_id="r",
                        path="/src/main.py", node_type="file",
                        name="main.py", summary="Entry point")
        assert leaf.id == "n1"
        assert leaf.entity_id == "e1"
        assert leaf.parent_id == "r"
        assert leaf.path == "/src/main.py"
        assert leaf.node_type == "file"
        assert leaf.name == "main.py"
        assert leaf.summary == "Entry point"

    def test_defaults(self):
        n = TreeNode(id="x", entity_id="e")
        assert n.parent_id is None
        assert n.path == "/"
        assert n.node_type == "file"
        assert n.name == ""
        assert n.summary is None
        assert n.metadata == {}

    def test_metadata(self):
        n = TreeNode(id="y", entity_id="e", metadata={
                     "lang": "py", "size": 1024})
        assert n.metadata["lang"] == "py"
        assert n.metadata["size"] == 1024


class TestNoopHippocampusTree:
    """NoopHippocampus tree CRUD + search + stale detection."""

    @pytest.fixture
    def hippo(self):
        return NoopHippocampus()

    @pytest.fixture
    def sample_tree(self):
        """Build a small 3-node tree and return (hippo, entity_id)."""
        hippo = NoopHippocampus()
        root = TreeNode(id="r", entity_id="e1", parent_id=None,
                        path="/", node_type="project", name="sample")
        n1 = TreeNode(id="f1", entity_id="e1", parent_id="r",
                      path="/src", node_type="directory", name="src")
        n2 = TreeNode(id="f2", entity_id="e1", parent_id="f1",
                      path="/src/main.py", node_type="file",
                      name="main.py", summary="Application entry point")
        # Build tree by passing root; deeper nodes stored in nodes dict
        hippo.build_tree("e1", root)
        # Manually register children for traversal tests
        hippo._trees["e1"]["nodes"]["f1"] = n1
        hippo._trees["e1"]["nodes"]["f2"] = n2
        return hippo, "e1"

    def test_build_and_get(self, hippo):
        root = TreeNode(id="r", entity_id="e1", parent_id=None,
                        path="/", node_type="project", name="my-project")
        count = hippo.build_tree("e1", root)
        assert count == 1

        retrieved = hippo.get_tree("e1")
        assert retrieved is not None
        assert retrieved.id == "r"
        assert retrieved.name == "my-project"

    def test_get_nonexistent(self, hippo):
        assert hippo.get_tree("no-such") is None

    def test_delete_tree(self, hippo):
        root = TreeNode(id="r", entity_id="e1")
        hippo.build_tree("e1", root)
        assert hippo.get_tree("e1") is not None
        hippo.delete_tree("e1")
        assert hippo.get_tree("e1") is None

    def test_delete_nonexistent_noop(self, hippo):
        hippo.delete_tree("no-such")  # should not raise

    def test_search_tree(self, sample_tree):
        hippo, eid = sample_tree
        # Search by name
        results = hippo.search_tree(eid, "main")
        assert len(results) >= 1
        assert results[0].name == "main.py"

        # Search by path
        results = hippo.search_tree(eid, "/src")
        assert len(results) >= 1
        paths = {r.path for r in results}
        assert "/src" in paths

        # Search by summary
        results = hippo.search_tree(eid, "entry")
        assert len(results) >= 1
        assert results[0].summary and "entry" in results[0].summary

    def test_search_tree_empty(self, hippo):
        assert hippo.search_tree("no-such", "x") == []

    def test_search_tree_limit(self, sample_tree):
        hippo, eid = sample_tree
        results = hippo.search_tree(eid, "s", limit=1)
        assert len(results) == 1

    def test_query_subtree(self, sample_tree):
        hippo, eid = sample_tree
        # Query from root with depth 2
        results = hippo.query_subtree(eid, "r", max_depth=2)
        ids = {r.id for r in results}
        assert "r" in ids
        assert "f1" in ids
        assert "f2" in ids

    def test_query_subtree_shallow(self, sample_tree):
        hippo, eid = sample_tree
        results = hippo.query_subtree(eid, "r", max_depth=1)
        ids = {r.id for r in results}
        assert "r" in ids
        assert "f1" in ids
        assert "f2" not in ids  # depth 2

    def test_query_subtree_missing(self, hippo):
        assert hippo.query_subtree("no-such", "x") == []

    def test_query_subtree_missing_node(self, sample_tree):
        hippo, eid = sample_tree
        assert hippo.query_subtree(eid, "no-such") == []

    def test_check_stale_all_fresh(self, sample_tree):
        hippo, eid = sample_tree
        # Add entity to entities dict so it's "fresh"
        hippo._entities = {"e1": {"id": "e1"}}
        assert hippo.check_stale(eid) == []

    def test_check_stale_detects_missing(self, hippo):
        root = TreeNode(id="r", entity_id="e_missing")
        hippo.build_tree("e_missing", root)
        # e_missing is not in entities → stale
        stale = hippo.check_stale("e_missing")
        assert "r" in stale

    def test_check_stale_missing_tree(self, hippo):
        assert hippo.check_stale("no-such") == []


class TestTreePaths:
    """4 tree paths are registered in BUILTIN_PATHS."""

    def test_tree_paths_exist(self):
        names = {p.name for p in BUILTIN_PATHS}
        assert "get_tree" in names
        assert "search_tree" in names
        assert "query_subtree" in names
        assert "build_tree" in names

    def test_get_tree_path_properties(self):
        p = next(p for p in BUILTIN_PATHS if p.name == "get_tree")
        assert p.mode == "read"

    def test_build_tree_path_properties(self):
        p = next(p for p in BUILTIN_PATHS if p.name == "build_tree")
        assert p.mode == "write"


class TestTreePathExecution:
    """Execute tree methods on a cat's mounted hippocampus."""

    @pytest.fixture
    def cat(self):
        c = make_cat("tree_cat")
        c.mount("brain", "hippocampus", NoopHippocampus())
        return c

    def test_build_tree_on_mounted_hippo(self, cat):
        hippo = cat.organ("brain", "hippocampus")
        root = TreeNode(id="r2", entity_id="e2")
        count = hippo.build_tree("e2", root)
        assert count == 1
        assert hippo.get_tree("e2") is not None

    def test_get_tree_on_mounted_hippo(self, cat):
        hippo = cat.organ("brain", "hippocampus")
        root = TreeNode(id="r3", entity_id="e3")
        hippo.build_tree("e3", root)
        retrieved = hippo.get_tree("e3")
        assert retrieved is not None
        assert retrieved.id == "r3"


class TestTreeNodeImport:
    """TreeNode is importable from meowcat top-level."""

    def test_from_meowcat(self):
        import meowcat
        n = meowcat.TreeNode(id="t", entity_id="e")
        assert n.id == "t"

    def test_from_tree_module(self):
        from meowcat.tree import TreeNode
        n = TreeNode(id="t2", entity_id="e2")
        assert n.id == "t2"
