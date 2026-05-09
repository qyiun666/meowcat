# Copyright (c) 2026 Axonant
# SPDX-License-Identifier: MIT

"""meowcat KnowledgeTree — TreeNode dataclass for tree-structured entity knowledge.

KnowledgeTree is a hierarchical overlay on hippocampus entities.  Each tree
node represents a piece of structured knowledge (file, class, function, doc
section, etc.) linked to a parent entity.  The scanner logic (CodeScanner,
DocScanner) lives in the application layer — the framework layer only defines
the data type and storage protocol on Hippocampus.

Usage::

    from meowcat.tree import TreeNode

    root = TreeNode(id="r", entity_id="e1", parent_id=None,
                    path="/", node_type="project", name="my-project")
    cat.hippocampus.build_tree("e1", root)
    results = cat.hippocampus.search_tree("e1", "keyword")
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class TreeNode:
    """A single node in the KnowledgeTree.

    Each node belongs to one hippocampus entity (via ``entity_id``) and
    forms a parent-child hierarchy via ``parent_id``.  ``path`` stores the
    filesystem-like path for display and search.

    Attributes:
        id: Unique node identifier within the tree.
        entity_id: Hippocampus entity this tree is attached to.
        parent_id: Parent node id, or ``None`` for the root node.
        path: Filesystem-like path (e.g. ``"/src/main.py"``).
        node_type: Semantic type label (``"project"``, ``"file"``,
            ``"directory"``, ``"class"``, ``"function"``, ``"doc"``, etc.).
        name: Human-readable display name.
        summary: Optional short summary of the node's content.
        metadata: Free-form extra fields.
    """

    id: str
    entity_id: str
    parent_id: str | None = None
    path: str = "/"
    node_type: str = "file"
    name: str = ""
    summary: str | None = None
    metadata: dict[str, object] = field(default_factory=dict)


__all__ = ["TreeNode"]
