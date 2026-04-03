"""Built-in skills — core commands for date/time, markdown templates, and utilities."""

from __future__ import annotations

import calendar
import time as _time
from datetime import date, datetime
from typing import TYPE_CHECKING

from chatmd.i18n import t
from chatmd.skills.base import Skill, SkillContext, SkillResult

if TYPE_CHECKING:
    from chatmd.engine.router import Router
    from chatmd.engine.scheduler import Scheduler


class DateSkill(Skill):
    """Insert today's date."""

    name = "date"
    description = "date"
    category = "builtin"
    aliases = ["d"]

    def execute(self, input_text: str, args: dict, context: SkillContext) -> SkillResult:
        fmt = args.get("_positional", "%Y-%m-%d")
        try:
            result = datetime.now().strftime(fmt)
        except ValueError:
            result = datetime.now().strftime("%Y-%m-%d")
        return SkillResult(success=True, output=result)


class TimeSkill(Skill):
    """Insert current time."""

    name = "time"
    description = "time"
    category = "builtin"
    aliases = []

    def execute(self, input_text: str, args: dict, context: SkillContext) -> SkillResult:
        return SkillResult(success=True, output=datetime.now().strftime("%H:%M:%S"))


class NowSkill(Skill):
    """Insert current date and time, or a full daily summary."""

    name = "now"
    description = "now"
    category = "builtin"
    aliases = []

    def execute(self, input_text: str, args: dict, context: SkillContext) -> SkillResult:
        mode = args.get("_positional", "").strip().lower()
        if mode == "full":
            now = datetime.now()
            today = now.date()
            weekday = t("output.weekday.names").split(",")[today.weekday()].strip()
            week_num = today.isocalendar()[1]
            day_of_year = today.timetuple().tm_yday
            total_days = 366 if calendar.isleap(today.year) else 365
            pct = day_of_year / total_days * 100
            lines = [
                now.strftime("%Y-%m-%d %H:%M:%S"),
                weekday,
                t("output.week.format", week=week_num),
                t("output.daynum.format", day=day_of_year),
                t("output.progress.format", pct=f"{pct:.2f}", year=today.year),
            ]
            return SkillResult(success=True, output=" | ".join(lines))
        return SkillResult(success=True, output=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))


# ── T-045: Date/time extension skills ────────────────────────────────────


class DatetimeSkill(Skill):
    """Insert current date and time (YYYY-MM-DD HH:MM:SS)."""

    name = "datetime"
    description = "datetime"
    category = "builtin"
    aliases = ["dt"]

    def execute(self, input_text: str, args: dict, context: SkillContext) -> SkillResult:
        return SkillResult(success=True, output=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))


class TimestampSkill(Skill):
    """Insert Unix timestamp."""

    name = "timestamp"
    description = "timestamp"
    category = "builtin"
    aliases = ["ts"]

    def execute(self, input_text: str, args: dict, context: SkillContext) -> SkillResult:
        return SkillResult(success=True, output=str(int(_time.time())))


# ── T-046: Week/progress skills ────────────────────────────────────────────


class WeekSkill(Skill):
    """Insert current ISO week number."""

    name = "week"
    description = "week"
    category = "builtin"
    aliases = ["w"]

    def execute(self, input_text: str, args: dict, context: SkillContext) -> SkillResult:
        week_num = date.today().isocalendar()[1]
        return SkillResult(success=True, output=t("output.week.format", week=week_num))


class WeekdaySkill(Skill):
    """Insert current weekday name."""

    name = "weekday"
    description = "weekday"
    category = "builtin"
    aliases = ["wd"]

    def execute(self, input_text: str, args: dict, context: SkillContext) -> SkillResult:
        names = t("output.weekday.names").split(",")
        return SkillResult(success=True, output=names[date.today().weekday()].strip())


class ProgressSkill(Skill):
    """Insert year progress percentage."""

    name = "progress"
    description = "progress"
    category = "builtin"
    aliases = ["pg"]

    def execute(self, input_text: str, args: dict, context: SkillContext) -> SkillResult:
        today = date.today()
        day_of_year = today.timetuple().tm_yday
        total_days = 366 if calendar.isleap(today.year) else 365
        pct = day_of_year / total_days * 100
        return SkillResult(
            success=True,
            output=t("output.progress.format", pct=f"{pct:.2f}", year=today.year),
        )


class DaynumSkill(Skill):
    """Insert day-of-year number."""

    name = "daynum"
    description = "daynum"
    category = "builtin"
    aliases = ["dn"]

    def execute(self, input_text: str, args: dict, context: SkillContext) -> SkillResult:
        day_of_year = date.today().timetuple().tm_yday
        return SkillResult(
            success=True,
            output=t("output.daynum.format", day=day_of_year),
        )


class CountdownSkill(Skill):
    """Insert countdown days to a target date."""

    name = "countdown"
    description = "countdown"
    category = "builtin"
    aliases = ["cd"]

    def execute(self, input_text: str, args: dict, context: SkillContext) -> SkillResult:
        target_str = args.get("_positional", "").strip()
        today = date.today()
        if target_str:
            try:
                target = date.fromisoformat(target_str)
            except ValueError:
                return SkillResult(
                    success=False, output="",
                    error=t("error.countdown_invalid_date", date=target_str),
                )
        else:
            # Default: one year from today
            target = today.replace(year=today.year + 1)
        delta = (target - today).days
        return SkillResult(
            success=True,
            output=t("output.countdown.format", days=delta, target=target.isoformat()),
        )


# ── T-047: Markdown template skills ───────────────────────────────────────


class TodoSkill(Skill):
    """Insert a to-do checkbox item."""

    name = "todo"
    description = "todo"
    category = "builtin"
    aliases = ["td"]

    def execute(self, input_text: str, args: dict, context: SkillContext) -> SkillResult:
        text = input_text.strip() if input_text else ""
        return SkillResult(success=True, output=f"- [ ] {text}")


class DoneSkill(Skill):
    """Insert a completed to-do checkbox item."""

    name = "done"
    description = "done"
    category = "builtin"
    aliases = ["dn2"]

    def execute(self, input_text: str, args: dict, context: SkillContext) -> SkillResult:
        text = input_text.strip() if input_text else ""
        return SkillResult(success=True, output=f"- [x] {text}")


class TableSkill(Skill):
    """Insert a Markdown table template."""

    name = "table"
    description = "table"
    category = "builtin"
    aliases = ["tb"]

    def execute(self, input_text: str, args: dict, context: SkillContext) -> SkillResult:
        spec = args.get("_positional", "3x3").strip().lower()
        try:
            parts = spec.split("x")
            cols = max(1, int(parts[0]))
            rows = max(1, int(parts[1])) if len(parts) > 1 else 3
        except (ValueError, IndexError):
            cols, rows = 3, 3

        header = "| " + " | ".join(f"Col{c + 1}" for c in range(cols)) + " |"
        sep = "| " + " | ".join("---" for _ in range(cols)) + " |"
        body_rows = [
            "| " + " | ".join("" for _ in range(cols)) + " |"
            for _ in range(rows)
        ]
        return SkillResult(success=True, output="\n".join([header, sep, *body_rows]))


class CodeSkill(Skill):
    """Insert a fenced code block."""

    name = "code"
    description = "code"
    category = "builtin"
    aliases = ["c"]

    def execute(self, input_text: str, args: dict, context: SkillContext) -> SkillResult:
        lang = args.get("_positional", "python").strip()
        return SkillResult(success=True, output=f"```{lang}\n\n```")


class LinkSkill(Skill):
    """Insert a Markdown link template."""

    name = "link"
    description = "link"
    category = "builtin"
    aliases = ["ln"]

    def execute(self, input_text: str, args: dict, context: SkillContext) -> SkillResult:
        return SkillResult(success=True, output="[text](url)")


class ImgSkill(Skill):
    """Insert a Markdown image template."""

    name = "img"
    description = "img"
    category = "builtin"
    aliases = ["i"]

    def execute(self, input_text: str, args: dict, context: SkillContext) -> SkillResult:
        return SkillResult(success=True, output="![alt](url)")


class HrSkill(Skill):
    """Insert a horizontal rule."""

    name = "hr"
    description = "hr"
    category = "builtin"
    aliases = []

    def execute(self, input_text: str, args: dict, context: SkillContext) -> SkillResult:
        return SkillResult(success=True, output="---")


class HeadingSkill(Skill):
    """Insert a Markdown heading."""

    name = "heading"
    description = "heading"
    category = "builtin"
    aliases = ["hd"]

    def execute(self, input_text: str, args: dict, context: SkillContext) -> SkillResult:
        level_str = args.get("_positional", "2").strip()
        try:
            level = max(1, min(6, int(level_str)))
        except ValueError:
            level = 2
        text = input_text.strip() if input_text else ""
        return SkillResult(success=True, output=f"{'#' * level} {text}")


class QuoteSkill(Skill):
    """Insert a Markdown block quote."""

    name = "quote"
    description = "quote"
    category = "builtin"
    aliases = ["q"]

    def execute(self, input_text: str, args: dict, context: SkillContext) -> SkillResult:
        text = input_text.strip() if input_text else ""
        if text:
            lines = text.splitlines()
            quoted = "\n".join(f"> {line}" for line in lines)
            return SkillResult(success=True, output=quoted)
        return SkillResult(success=True, output="> ")


class HelpSkill(Skill):
    """List all available commands."""

    name = "help"
    description = "help"
    category = "builtin"
    aliases = ["h"]

    def __init__(self, router: Router | None = None) -> None:
        self._router = router

    def set_router(self, router: Router) -> None:
        """Inject the router after registration (to avoid circular deps)."""
        self._router = router

    # Skill name → help group mapping
    _DATETIME_SKILLS = frozenset({
        "date", "time", "now", "datetime", "timestamp",
        "week", "weekday", "progress", "daynum", "countdown",
    })
    _MARKDOWN_SKILLS = frozenset({
        "todo", "done", "table", "code", "link", "img", "hr", "heading", "quote",
    })
    _UTILITY_SKILLS = frozenset({
        "help", "status", "list", "sync", "log", "new", "upload",
    })
    _GROUP_ORDER = ("datetime", "ai", "markdown", "utility", "custom")

    def execute(self, input_text: str, args: dict, context: SkillContext) -> SkillResult:
        if self._router is None:
            return SkillResult(success=False, output="", error="Router not configured")

        skills = self._router.list_skills()
        if not skills:
            return SkillResult(success=True, output=t("output.help.empty"))

        # Classify skills into groups
        groups: dict[str, list[Skill]] = {g: [] for g in self._GROUP_ORDER}
        for s in skills:
            groups[self._classify(s)].append(s)

        lines = [t("output.help.header")]
        for group_key in self._GROUP_ORDER:
            group_skills = groups[group_key]
            if not group_skills:
                continue
            group_title = t(f"output.help.group.{group_key}")
            lines.append(f"### {group_title}\n")
            lines.append(t("output.help.table_header"))
            lines.append("|------|------|------|")
            for s in sorted(group_skills, key=lambda x: x.name):
                aliases_str = ", ".join(f"`/{a}`" for a in getattr(s, "aliases", []))
                i18n_key = f"skill.{s.name}.description"
                desc = t(i18n_key)
                # Fallback to skill's own description if i18n key is missing
                if desc == i18n_key:
                    desc = getattr(s, "description", "") or s.name
                lines.append(f"| `/{s.name}` | {aliases_str} | {desc} |")
            lines.append("")

        return SkillResult(success=True, output="\n".join(lines))

    @classmethod
    def _classify(cls, skill: Skill) -> str:
        """Classify a skill into a help display group."""
        if skill.name in cls._DATETIME_SKILLS:
            return "datetime"
        if getattr(skill, "category", "") == "ai":
            return "ai"
        if skill.name in cls._MARKDOWN_SKILLS:
            return "markdown"
        if skill.name in cls._UTILITY_SKILLS:
            return "utility"
        return "custom"


class StatusSkill(Skill):
    """Show Agent status and active tasks."""

    name = "status"
    description = "status"
    category = "builtin"
    aliases = ["st"]

    def __init__(self, scheduler: Scheduler | None = None) -> None:
        self._scheduler = scheduler

    def set_scheduler(self, scheduler: Scheduler) -> None:
        """Inject the scheduler after construction."""
        self._scheduler = scheduler

    def execute(self, input_text: str, args: dict, context: SkillContext) -> SkillResult:
        lines = [t("output.status.running")]
        lines.append(t("output.status.workspace", workspace=context.workspace))

        if self._scheduler:
            active = self._scheduler.get_active_tasks()
            all_tasks = self._scheduler.get_all_tasks()
            lines.append(t("output.status.active_tasks", count=len(active)))
            lines.append(t("output.status.total_tasks", count=len(all_tasks)))
            if active:
                lines.append(t("output.status.running_tasks_header"))
                for task in active:
                    lines.append(
                        f"- `#{task.id}` {task.skill_name}: {task.status.value}"
                    )
        else:
            lines.append(t("output.status.active_tasks", count=0))

        return SkillResult(success=True, output="\n".join(lines))


class ListSkill(Skill):
    """List chat sessions in the workspace."""

    name = "list"
    description = "list"
    category = "builtin"
    aliases = ["ls"]

    def execute(self, input_text: str, args: dict, context: SkillContext) -> SkillResult:
        workspace = context.workspace
        sessions: list[str] = []

        # Default chat.md
        chat_md = workspace / "chat.md"
        if chat_md.exists():
            sessions.append(t("output.list.default_session"))

        # chat/ directory
        chat_dir = workspace / "chat"
        if chat_dir.is_dir():
            for f in sorted(chat_dir.glob("*.md")):
                if f.name.startswith("_"):
                    continue
                sessions.append(f"- `chat/{f.name}`")

        if not sessions:
            return SkillResult(success=True, output=t("output.list.empty"))

        header = t("output.list.header", count=len(sessions))
        return SkillResult(success=True, output=header + "\n".join(sessions))


def register_builtin_skills(
    router: Router,
    scheduler: Scheduler | None = None,
) -> None:
    """Register all built-in skills with the given router."""
    help_skill = HelpSkill()
    status_skill = StatusSkill(scheduler)
    router.register(DateSkill())
    router.register(TimeSkill())
    router.register(NowSkill())
    router.register(help_skill)
    router.register(status_skill)
    router.register(ListSkill())
    # T-045: date/time extensions
    router.register(DatetimeSkill())
    router.register(TimestampSkill())
    # T-046: week/progress skills
    router.register(WeekSkill())
    router.register(WeekdaySkill())
    router.register(ProgressSkill())
    router.register(DaynumSkill())
    router.register(CountdownSkill())
    # T-047: markdown template skills
    router.register(TodoSkill())
    router.register(DoneSkill())
    router.register(TableSkill())
    router.register(CodeSkill())
    router.register(LinkSkill())
    router.register(ImgSkill())
    router.register(HrSkill())
    router.register(HeadingSkill())
    router.register(QuoteSkill())
    help_skill.set_router(router)
