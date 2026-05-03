"""meowcat testing utilities — helpers for test code.

v1.1.3: CatBase now requires a Container (Colony). These helpers
create minimal test containers so test code doesn't need to change.
"""

from meowcat.colony import Colony
from meowcat.defaults import InMemorySharedStore


def make_test_colony(cat_id: str = "test") -> Colony:
    """Create a minimal Colony for test use."""
    return Colony(cat_id, storage=InMemorySharedStore())


def make_cat(cat_id: str = "test", **kwargs):
    """Create a CatBase with a test container.

    Migration: ``CatBase("x")`` → ``make_cat("x")``
    """
    from meowcat.assembly import CatBase
    colony = make_test_colony(cat_id)
    return CatBase(cat_id, container=colony, **kwargs)
