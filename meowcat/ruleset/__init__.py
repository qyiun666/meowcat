# Copyright (c) 2026 Axonant
# SPDX-License-Identifier: MIT

"""meowcat v2.1.0 RuleSet unified rule engine.

Framework provides the container (Rule + RuleSet dataclass + render engine);
application layer fills in the content (rules, route names, blocks).

Example::

    from meowcat.ruleset import Rule, RuleSet

    rs = RuleSet(
        always_on=[Rule("安全第一", "不要执行危险操作", "critical")],
        per_route={
            "deep_reason": [Rule("SQL规范", "参数化查询", "critical")],
        },
        role_block="<role>安全审计专家</role>",
    )
    block = rs.render("deep_reason")
"""

from __future__ import annotations

from dataclasses import dataclass, field

_PRIORITY_ORDER: dict[str, int] = {
    "critical": 0,
    "high": 1,
    "medium": 2,
    "low": 3,
}


@dataclass
class Rule:
    """A single injectable rule.

    Attributes:
        name: Rule display name, e.g. ``"SQL注入防护"``.
        content: Rule body — plain Markdown, code blocks, or both.
            Framework wraps it as-is inside ``<rule_content>``.
        priority: Injection order — ``"critical"`` / ``"high"`` /
            ``"medium"`` / ``"low"``.  Default ``"medium"``.
        tags: Optional tags for application-layer use.
            Framework never reads or validates them.
    """

    name: str
    content: str
    priority: str = "medium"
    tags: list[str] = field(default_factory=list)


@dataclass
class RuleSet:
    """Per-cat rule container with route-based dispatch.

    One cat = one RuleSet.  All LLM call points (cerebrum, cerebellum,
    amygdala, frontal) read from the same RuleSet, routing via
    ``render(route)`` to get the correct subset of rules.

    Attributes:
        always_on: Rules injected for *every* route.
        per_route: Route-specific rules.  Key ``"*"`` acts as a wildcard
            matching any route.
        role_block: Fixed XML block for role description.
        output_format_block: Fixed XML block for output format constraints.
        context_block: Fixed XML block for context information.
    """

    always_on: list[Rule] = field(default_factory=list)
    per_route: dict[str, list[Rule]] = field(default_factory=dict)
    role_block: str = ""
    output_format_block: str = ""
    context_block: str = ""

    def resolve(self, route: str) -> list[Rule]:
        """Merge always-on + route-specific + wildcard rules, sorted by priority.

        Resolution order: ``always_on`` → ``per_route[route]`` →
        ``per_route["*"]``, then sorted by priority (critical first).
        """
        rules = list(self.always_on)
        rules.extend(self.per_route.get(route, []))
        rules.extend(self.per_route.get("*", []))
        rules.sort(key=lambda r: _PRIORITY_ORDER.get(r.priority, 2))
        return rules

    def render(self, route: str) -> str:
        """Render rules into a system-prompt injection block.

        Outer structure is always XML::

            <role>...</role>

            <context>...</context>

            <rules>
              <rule name="..." priority="...">
                <rule_content>
            ... (application content, preserved as-is)
                </rule_content>
              </rule>
            </rules>

            <output_format>...</output_format>

        Returns an empty string when there are no rules and no blocks.
        """
        rules = self.resolve(route)
        parts: list[str] = []

        if self.role_block:
            parts.append(self.role_block)
        if self.context_block:
            parts.append(self.context_block)

        if rules:
            lines: list[str] = ["<rules>"]
            for r in rules:
                lines.append(
                    f'  <rule name="{r.name}" priority="{r.priority}">\n'
                    f"    <rule_content>\n{r.content}\n"
                    f"    </rule_content>\n"
                    f"  </rule>"
                )
            lines.append("</rules>")
            parts.append("\n".join(lines))

        if self.output_format_block:
            parts.append(self.output_format_block)

        return "\n\n".join(parts) if parts else ""
