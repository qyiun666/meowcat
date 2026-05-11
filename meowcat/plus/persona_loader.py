# Copyright (c) 2026 Axonant
# SPDX-License-Identifier: MIT

"""PersonaLoader — discover and load Persona definitions from PERSONA.yaml files.

Scans a directory for ``PERSONA.yaml`` files, parses YAML content,
creates :class:`~meowcat.persona.Persona` objects registerable into a Colony.

Usage::

    loader = PersonaLoader(dir=Path("./personas"))
    personas = loader.scan()
    await loader.load_all(colony)
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

from meowcat.persona import Persona

if TYPE_CHECKING:
    from meowcat.colony import Colony

logger = logging.getLogger(__name__)


class PersonaLoader:
    """PERSONA.yaml file loader — scans directories and creates Persona objects.

    Each ``PERSONA.yaml`` file contains a single persona definition.  The
    loader scans all ``PERSONA.yaml`` files in the given directory and
    returns a list of :class:`Persona` instances.

    Usage::

        loader = PersonaLoader(dir=Path("./personas"))
        personas = loader.scan()
        await loader.load_all(colony)  # registers to colony
    """

    def __init__(self, dir: Path) -> None:
        self.dir = Path(dir)
        self._personas: list[Persona] = []

    # -- Directory scanning ------------------------------------------------

    def scan(self) -> list[Persona]:
        """Scan ``dir`` for ``PERSONA.yaml`` files and parse each one.

        Returns:
            List of :class:`Persona` objects created from discovered files.
        """
        self._personas.clear()
        if not self.dir.is_dir():
            logger.warning("Persona directory not found: %s", self.dir)
            return []

        for persona_file in sorted(self.dir.rglob("PERSONA.yaml")):
            try:
                persona = self._load_persona(persona_file)
                if persona is not None:
                    self._personas.append(persona)
                    logger.debug("Loaded persona: %s from %s", persona.name, persona_file)
            except Exception as exc:
                logger.warning("Failed to load %s: %s", persona_file, exc)
        return list(self._personas)

    def _load_persona(self, path: Path) -> Persona | None:
        """Parse a single ``PERSONA.yaml`` file into a Persona.

        Args:
            path: Path to the PERSONA.yaml file.

        Returns:
            Persona instance, or None if parsing fails.
        """
        import yaml

        content = path.read_text(encoding="utf-8")
        try:
            data = yaml.safe_load(content)
        except yaml.YAMLError as exc:
            logger.warning("YAML parse error in %s: %s", path, exc)
            return None

        if not isinstance(data, dict):
            logger.warning("PERSONA.yaml content is not a dict: %s", path)
            return None

        if "name" not in data:
            # Fallback: use filename stem as persona name
            data["name"] = path.stem

        return Persona.from_dict(data)

    # -- Colony registration -----------------------------------------------

    async def load_all(self, colony: Colony) -> int:  # noqa: F821
        """Scan and register all personas into the given colony.

        Args:
            colony: Colony instance to register personas into.

        Returns:
            Number of personas registered.
        """
        count = 0
        for persona in self.scan():
            await colony.register_persona(persona)
            count += 1
        return count
