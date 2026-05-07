# Copyright (c) 2026 Axonant
# SPDX-License-Identifier: MIT

"""python -m meowcat new <name> -- cat project scaffolding.

Comparable to Flask ``flask new`` / FastAPI ``fastapi new`` -- minimal.
"""


from __future__ import annotations

import sys
from pathlib import Path

TEMPLATES: dict[str, str] = {
    "cat.py": '''"""{{name}} -- your custom cat."""
from meowcat import Colony
from meowcat.defaults import create_cat
from meowcat.defaults.stores import InMemorySharedStore


class EchoCerebrum:
    name = "echo_cerebrum"

    async def generate(self, prompt, system_prompt=None, temperature=0.7, max_tokens=None):
        return f"[Echo] Received: {prompt[:200]}"

    async def stream_generate(self, prompt, system_prompt=None, temperature=0.7, max_tokens=None):
        yield f"[Echo] {prompt[:200]}"

    def reload_config(self):
        pass

    def diagnose(self):
        return {"echo": True}


async def main() -> None:
    colony = Colony("{{name}}-colony", storage=InMemorySharedStore())
    cat = create_cat("{{name}}", container=colony, cerebrum=EchoCerebrum())
    await cat.start()
    result = await cat.run_loop("conversation", message="Hello!")
    print(result)
    await cat.shutdown()
''',
    "main.py": '''"""{{name}} entry point."""
import asyncio
from cat import main

if __name__ == "__main__":
    asyncio.run(main())
''',
}


def new_project(name: str, target_dir: Path | None = None) -> Path:
    """Generate meowcat skeleton project."""
    dir_ = (target_dir or Path.cwd()) / name
    dir_.mkdir(parents=True, exist_ok=True)

    for filename, template in TEMPLATES.items():
        content = template.replace("{{name}}", name)
        (dir_ / filename).write_text(content)

    print(f"Created {dir_}/")
    print(f"  {name}/cat.py")
    print(f"  {name}/main.py")
    print(f"\ncd {name} && python main.py")
    return dir_


def main() -> None:
    """python -m meowcat CLI entry point."""
    if len(sys.argv) < 3 or sys.argv[1] != "new":
        print("Usage: python -m meowcat new <project-name>")
        print("Example: python -m meowcat new my-cat")
        sys.exit(1)

    name = sys.argv[2]
    new_project(name)


if __name__ == "__main__":
    main()

