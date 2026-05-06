# Copyright (c) 2026 qyiun666
# SPDX-License-Identifier: MIT

"""meowcat testing utilities — helpers for test code.

v1.1.3: CatBase now requires a Container (Colony). These helpers
create minimal test containers so test code doesn't need to change.
"""

from meowcat.colony import Colony
from meowcat.defaults import InMemorySharedStore

# Copyright (c) 2026 qyiun666
# SPDX-License-Identifier: MIT


# Copyright (c) 2026 qyiun666
# SPDX-License-Identifier: MIT

def make_test_colony(colony_id: str = "test") -> Colony:
    """Create a minimal Colony for test use."""
    return Colony(colony_id, storage=InMemorySharedStore())


def make_cat(name: str = "test", **kwargs):
    """Create a CatBase with a test container.

    Migration: ``CatBase("x")`` → ``make_cat(name="x")``
    """
    colony = make_test_colony()
    return colony.create_cat(name=name, **kwargs)

