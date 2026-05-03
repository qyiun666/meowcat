"""python -m meowcat new <name> -- cat project scaffolding.

Comparable to Flask ``flask new`` / FastAPI ``fastapi new`` -- minimal.
"""
# (c) 2025-2026 Axonant. MIT License.


from __future__ import annotations

import sys
from pathlib import Path

TEMPLATES: dict[str, str] = {
    "cat.py": '''"""{{name}} -- your custom cat."""
from meowcat import CatBase, assemble_default_cat


class {{name_class}}(CatBase):
    """Your cat. Call assemble_default_cat after mounting custom organs."""
    pass


async def main() -> None:
    cat = {{name_class}}("{{name}}")
    assemble_default_cat(cat)
    await cat.start()
    print(f"{{name}} is ready.")
    result = await cat.run_loop("conversation", message="Hello, introduce yourself")
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

    name_class = "".join(w.capitalize()
                         for w in name.replace("-", "_").split("_"))

    for filename, template in TEMPLATES.items():
        content = template.replace("{{name}}", name).replace(
            "{{name_class}}", name_class)
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
