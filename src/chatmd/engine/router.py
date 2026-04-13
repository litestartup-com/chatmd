"""Command router — deterministic skill matching with alias resolution."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from chatmd.engine.parser import CommandType, ParsedCommand
from chatmd.exceptions import RouteError

if TYPE_CHECKING:
    from chatmd.skills.base import Skill

logger = logging.getLogger(__name__)


# Skill priority: lower number = higher priority
_CATEGORY_PRIORITY: dict[str, int] = {
    "builtin": 0,
    "ai": 10,
    "custom": 20,
    "remote": 30,
}


class Router:
    """Deterministic command router that maps commands to Skills."""

    def __init__(self) -> None:
        self._routes: dict[str, Skill] = {}
        self._aliases: dict[str, str] = {}
        self._conflicts: list[dict] = []

    def register(self, skill: Skill) -> None:
        """Register a Skill and its aliases, respecting category priority."""
        name = skill.name
        if name in self._routes:
            existing = self._routes[name]
            winner = self._resolve_conflict(existing, skill)
            self._conflicts.append({
                "name": name,
                "existing": f"{existing.name} ({existing.category})",
                "incoming": f"{skill.name} ({skill.category})",
                "winner": winner.category,
            })
            if winner is existing:
                logger.warning(
                    "Skill conflict: '%s' (%s) blocked by existing (%s)",
                    name, skill.category, existing.category,
                )
                return
            logger.warning(
                "Skill conflict: '%s' (%s) replaced by (%s)",
                name, existing.category, skill.category,
            )
        self._routes[name] = skill

        for alias in getattr(skill, "aliases", []):
            if alias in self._aliases:
                logger.warning(
                    "Alias conflict: '%s' already maps to '%s'", alias, self._aliases[alias]
                )
            self._aliases[alias] = name
            logger.debug("Registered alias '%s' -> '%s'", alias, name)

        logger.debug("Registered skill '%s' (%s)", name, skill.category)

    def unregister(self, name: str) -> bool:
        """Remove a skill and its aliases from the router.

        Returns True if the skill was found and removed.
        """
        skill = self._routes.pop(name, None)
        if skill is None:
            return False

        # Remove aliases that point to this skill
        dead_aliases = [a for a, t in self._aliases.items() if t == name]
        for alias in dead_aliases:
            del self._aliases[alias]

        logger.debug("Unregistered skill '%s' (removed %d aliases)", name, len(dead_aliases))
        return True

    def register_aliases(self, aliases: dict[str, str]) -> None:
        """Register user-defined aliases from config (highest priority)."""
        for alias, target in aliases.items():
            self._aliases[alias] = target
            logger.debug("Registered user alias '%s' -> '%s'", alias, target)

    def route(self, parsed: ParsedCommand) -> tuple[Skill, ParsedCommand]:
        """Route a parsed command to the matching Skill.

        Returns a ``(skill, resolved_command)`` tuple.  The command may be
        updated if an alias was resolved.

        Raises :class:`RouteError` if no matching Skill is found.
        """
        if parsed.type in (CommandType.SLASH_CMD, CommandType.INLINE_CMD):
            return self._route_slash(parsed)
        if parsed.type in (CommandType.OPEN_CHAT, CommandType.AT_AI):
            return self._route_open_chat(parsed)
        raise RouteError(f"Unsupported command type: {parsed.type}")

    def get_skill(self, name: str) -> Skill | None:
        """Look up a skill by name (no alias resolution)."""
        return self._routes.get(name)

    def list_skills(self) -> list[Skill]:
        """Return all registered skills."""
        return list(self._routes.values())

    def get_conflicts(self) -> list[dict]:
        """Return all detected registration conflicts."""
        return list(self._conflicts)

    @staticmethod
    def _resolve_conflict(existing: Skill, incoming: Skill) -> Skill:
        """Resolve a name conflict — lower category priority wins."""
        ex_pri = _CATEGORY_PRIORITY.get(existing.category, 50)
        in_pri = _CATEGORY_PRIORITY.get(incoming.category, 50)
        if in_pri < ex_pri:
            return incoming
        return existing

    def _route_slash(self, parsed: ParsedCommand) -> tuple[Skill, ParsedCommand]:
        """Route a SLASH_CMD to a registered Skill."""
        cmd_name = parsed.command

        # Resolve alias
        resolved_name = self._resolve(cmd_name)

        # Check if the resolved name contains params (e.g. "translate(English)")
        if "(" in resolved_name:
            base, _, param_rest = resolved_name.partition("(")
            param_val = param_rest.rstrip(")")
            resolved_name = base
            # Inject alias params if command had no explicit params
            if "_positional" not in parsed.args:
                parsed.args["_positional"] = param_val
                parsed.args["_pos_0"] = param_val

        skill = self._routes.get(resolved_name)
        if skill is None:
            suggestions = self._fuzzy_suggest(cmd_name)
            hint = ""
            if suggestions:
                opts = " / ".join(f"`/{s}`" for s in suggestions)
                hint = f", did you mean: {opts}"
            raise RouteError(f"Unknown command `{cmd_name}`{hint}")

        parsed.command = resolved_name
        return skill, parsed

    def _route_open_chat(self, parsed: ParsedCommand) -> tuple[Skill, ParsedCommand]:
        """Route OPEN_CHAT to the chat/ask skill."""
        chat_skill = self._routes.get("ask") or self._routes.get("chat")
        if chat_skill is None:
            raise RouteError("No chat skill registered")
        return chat_skill, parsed

    def _resolve(self, name: str) -> str:
        """Resolve an alias chain (max 5 hops to prevent cycles)."""
        current = name
        for _ in range(5):
            if current in self._routes:
                return current
            if current in self._aliases:
                current = self._aliases[current]
            else:
                return current
        return current

    def _fuzzy_suggest(self, name: str, max_results: int = 3) -> list[str]:
        """Return similar command names using edit-distance + prefix matching."""
        candidates = list(self._routes.keys()) + list(self._aliases.keys())
        scored: list[tuple[float, str]] = []
        name_lower = name.lower()
        for c in candidates:
            c_lower = c.lower()
            # Exact prefix match gets highest score
            if c_lower.startswith(name_lower) or name_lower.startswith(c_lower):
                scored.append((0.5, c))
                continue
            dist = _levenshtein(name_lower, c_lower)
            if dist <= max(2, len(name) // 2):
                scored.append((dist, c))
        scored.sort()
        seen: set[str] = set()
        result: list[str] = []
        for _, c in scored:
            if c not in seen:
                seen.add(c)
                result.append(c)
                if len(result) >= max_results:
                    break
        return result


def _levenshtein(s1: str, s2: str) -> int:
    """Compute Levenshtein edit distance between two strings."""
    if len(s1) < len(s2):
        return _levenshtein(s2, s1)
    if len(s2) == 0:
        return len(s1)
    prev_row = list(range(len(s2) + 1))
    for i, c1 in enumerate(s1):
        curr_row = [i + 1]
        for j, c2 in enumerate(s2):
            cost = 0 if c1 == c2 else 1
            curr_row.append(min(
                curr_row[j] + 1,
                prev_row[j + 1] + 1,
                prev_row[j] + cost,
            ))
        prev_row = curr_row
    return prev_row[-1]
