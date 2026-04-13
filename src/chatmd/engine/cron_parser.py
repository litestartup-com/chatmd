"""CronParser — zero-dependency cron expression parser and Markdown code block extractor.

Supports:
- Standard 5-field cron: ``minute hour day month weekday``
- Linux shortcuts: ``@hourly``, ``@daily``/``@midnight``, ``@weekly``, ``@monthly``, ``@reboot``
- ChatMD extension: ``@every <N><unit>`` (s/m/h/d)
- Markdown ````` ```cron ````` code block extraction
- Deterministic job IDs based on ``source_file + line_content``
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

# Pattern to strip inline status comments written by cron_inline.py
_INLINE_STATUS_RE = re.compile(r"\s+#\s*\[cron-[a-f0-9]+\].*$")
_INLINE_ERROR_RE = re.compile(r"\s+#\s*❌.*$")

# ── Name mappings ─────────────────────────────────────────────────

_MONTH_NAMES = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4,
    "may": 5, "jun": 6, "jul": 7, "aug": 8,
    "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}

_WEEKDAY_NAMES = {
    "sun": 0, "mon": 1, "tue": 2, "wed": 3,
    "thu": 4, "fri": 5, "sat": 6,
}

_SHORTCUTS = {
    "@hourly": "0 * * * *",
    "@daily": "0 0 * * *",
    "@midnight": "0 0 * * *",
    "@weekly": "0 0 * * 0",
    "@monthly": "0 0 1 * *",
    "@yearly": "0 0 1 1 *",
    "@annually": "0 0 1 1 *",
}

# ── Field ranges ──────────────────────────────────────────────────

_FIELD_RANGES: list[tuple[int, int]] = [
    (0, 59),   # minute
    (0, 23),   # hour
    (1, 31),   # day of month
    (1, 12),   # month
    (0, 7),    # weekday (0 and 7 = Sunday)
]

_FIELD_NAMES = ["minute", "hour", "day", "month", "weekday"]

# ── Exceptions ────────────────────────────────────────────────────


class CronSyntaxError(ValueError):
    """Raised when a cron expression cannot be parsed."""


# ── CronExpr ──────────────────────────────────────────────────────


@dataclass(frozen=True)
class CronExpr:
    """Parsed 5-field cron expression with next-fire calculation."""

    minutes: frozenset[int]
    hours: frozenset[int]
    days: frozenset[int]
    months: frozenset[int]
    weekdays: frozenset[int]

    # ------------------------------------------------------------------
    # Parsing
    # ------------------------------------------------------------------

    @classmethod
    def parse(cls, expression: str) -> CronExpr:
        """Parse a 5-field cron expression string."""
        parts = expression.strip().split()
        if len(parts) != 5:
            raise CronSyntaxError(
                f"Expected 5 fields, got {len(parts)}: {expression!r}"
            )

        sets: list[set[int]] = []
        for i, part in enumerate(parts):
            lo, hi = _FIELD_RANGES[i]
            name_map = (
                _MONTH_NAMES if i == 3
                else _WEEKDAY_NAMES if i == 4
                else None
            )
            parsed = _parse_field(part, lo, hi, _FIELD_NAMES[i], name_map)
            sets.append(parsed)

        # Normalize weekday 7 → 0 (Sunday)
        wd = sets[4]
        if 7 in wd:
            wd.discard(7)
            wd.add(0)

        return cls(
            minutes=frozenset(sets[0]),
            hours=frozenset(sets[1]),
            days=frozenset(sets[2]),
            months=frozenset(sets[3]),
            weekdays=frozenset(wd),
        )

    @classmethod
    def from_shortcut(cls, shortcut: str) -> CronExpr:
        """Parse a ``@shortcut`` into a CronExpr."""
        key = shortcut.strip().lower()
        if key not in _SHORTCUTS:
            raise CronSyntaxError(f"Unknown shortcut: {shortcut!r}")
        return cls.parse(_SHORTCUTS[key])

    # ------------------------------------------------------------------
    # Next-fire calculation
    # ------------------------------------------------------------------

    def next_fire(self, after: datetime) -> datetime:
        """Return the next fire time strictly after *after*.

        Searches up to ~2 years ahead; raises if no match found.
        """
        # Start from the next minute
        candidate = after.replace(second=0, microsecond=0) + timedelta(
            minutes=1,
        )
        limit = after + timedelta(days=366 * 2)

        while candidate <= limit:
            if candidate.month not in self.months:
                # Jump to the 1st of the next valid month
                candidate = _next_month(candidate, self.months)
                continue

            if candidate.day not in self.days:
                candidate = candidate.replace(
                    hour=0, minute=0,
                ) + timedelta(days=1)
                continue

            if candidate.weekday() not in self._py_weekdays:
                candidate = candidate.replace(
                    hour=0, minute=0,
                ) + timedelta(days=1)
                continue

            if candidate.hour not in self.hours:
                candidate = candidate.replace(minute=0) + timedelta(hours=1)
                continue

            if candidate.minute not in self.minutes:
                candidate += timedelta(minutes=1)
                continue

            return candidate

        raise CronSyntaxError(  # pragma: no cover
            "Could not find next fire time within 2 years"
        )

    @property
    def _py_weekdays(self) -> frozenset[int]:
        """Convert cron weekdays (0=Sun) to Python weekdays (0=Mon)."""
        mapping = {0: 6, 1: 0, 2: 1, 3: 2, 4: 3, 5: 4, 6: 5}
        return frozenset(mapping[d] for d in self.weekdays)


# ── EveryExpr ─────────────────────────────────────────────────────

_EVERY_RE = re.compile(r"^@every\s+(\d+)([smhd])$", re.IGNORECASE)
_UNIT_MAP = {"s": "seconds", "m": "minutes", "h": "hours", "d": "days"}


@dataclass(frozen=True)
class EveryExpr:
    """Parsed ``@every <N><unit>`` interval expression."""

    interval: timedelta

    @classmethod
    def parse(cls, expression: str) -> EveryExpr:
        """Parse an ``@every 5m`` style expression."""
        m = _EVERY_RE.match(expression.strip())
        if not m:
            raise CronSyntaxError(
                f"Invalid @every expression: {expression!r}"
            )
        value = int(m.group(1))
        unit = m.group(2).lower()
        if value <= 0:
            raise CronSyntaxError(
                f"@every interval must be > 0: {expression!r}"
            )
        return cls(interval=timedelta(**{_UNIT_MAP[unit]: value}))

    def next_fire(
        self,
        now: datetime,
        last_run: datetime | None = None,
    ) -> datetime:
        """Return the next fire time.

        If *last_run* is provided, next = last_run + interval.
        If that time is in the past, fire immediately (returns *now*).
        Without *last_run*, returns ``now + interval``.
        """
        if last_run is not None:
            candidate = last_run + self.interval
            if candidate <= now:
                return now
            return candidate
        return now + self.interval


# ── CronJob ───────────────────────────────────────────────────────

Schedule = CronExpr | EveryExpr


@dataclass
class CronJob:
    """A single parsed cron job."""

    job_id: str
    schedule: Schedule
    command: str
    raw_line: str
    source_file: Path
    source_line_num: int
    is_reboot: bool = False


@dataclass
class CronError:
    """A line that failed to parse."""

    raw_line: str
    source_file: Path
    source_line_num: int
    error: str


# ── CronParser ────────────────────────────────────────────────────


class CronParser:
    """Extract and parse cron jobs from Markdown text or files."""

    @staticmethod
    def parse_text(
        text: str,
        *,
        source_file: Path = Path("unknown"),
    ) -> list[CronJob]:
        """Parse cron jobs from Markdown text, silently skipping errors."""
        jobs, _errors = CronParser.parse_text_with_errors(
            text, source_file=source_file,
        )
        return jobs

    @staticmethod
    def parse_text_with_errors(
        text: str,
        *,
        source_file: Path = Path("unknown"),
    ) -> tuple[list[CronJob], list[CronError]]:
        """Parse cron jobs and collect errors separately."""
        jobs: list[CronJob] = []
        errors: list[CronError] = []

        lines = text.splitlines()
        in_cron_block = False

        for line_num_0, line in enumerate(lines):
            line_num = line_num_0 + 1  # 1-indexed
            stripped = line.strip()

            # Detect code block boundaries
            if stripped.startswith("```"):
                if in_cron_block:
                    in_cron_block = False
                    continue
                lang = stripped[3:].strip().lower()
                if lang == "cron":
                    in_cron_block = True
                continue

            if not in_cron_block:
                continue

            # Skip comments and blank lines inside cron block
            if not stripped or stripped.startswith("#"):
                continue

            # Strip inline status comments (written by cron_inline.py)
            clean = _INLINE_STATUS_RE.sub("", stripped)
            clean = _INLINE_ERROR_RE.sub("", clean).strip()
            if not clean:
                continue

            # Parse the line
            try:
                job = _parse_cron_line(
                    clean, source_file, line_num,
                )
                jobs.append(job)
            except CronSyntaxError as exc:
                errors.append(CronError(
                    raw_line=clean,
                    source_file=source_file,
                    source_line_num=line_num,
                    error=str(exc),
                ))

        return jobs, errors

    @staticmethod
    def parse_file(filepath: Path) -> list[CronJob]:
        """Parse cron jobs from a Markdown file."""
        if not filepath.exists():
            return []
        text = filepath.read_text(encoding="utf-8")
        return CronParser.parse_text(text, source_file=filepath)


# ── Internal helpers ──────────────────────────────────────────────


def _parse_cron_line(
    line: str,
    source_file: Path,
    line_num: int,
) -> CronJob:
    """Parse a single cron line into a CronJob."""
    # @reboot special
    if line.lower().startswith("@reboot"):
        command = line[len("@reboot"):].strip()
        if not command:
            raise CronSyntaxError(f"Missing command: {line!r}")
        return CronJob(
            job_id=_make_job_id(source_file, line),
            schedule=CronExpr.parse("* * * * *"),  # placeholder
            command=command,
            raw_line=line,
            source_file=source_file,
            source_line_num=line_num,
            is_reboot=True,
        )

    # @every expression
    if line.lower().startswith("@every "):
        parts = line.split(None, 2)
        if len(parts) < 3:
            raise CronSyntaxError(f"Missing command: {line!r}")
        expr_str = f"{parts[0]} {parts[1]}"
        command = parts[2]
        schedule = EveryExpr.parse(expr_str)
        return CronJob(
            job_id=_make_job_id(source_file, line),
            schedule=schedule,
            command=command,
            raw_line=line,
            source_file=source_file,
            source_line_num=line_num,
        )

    # @ shortcut
    if line.startswith("@"):
        parts = line.split(None, 1)
        if len(parts) < 2:
            raise CronSyntaxError(f"Missing command: {line!r}")
        schedule = CronExpr.from_shortcut(parts[0])
        return CronJob(
            job_id=_make_job_id(source_file, line),
            schedule=schedule,
            command=parts[1],
            raw_line=line,
            source_file=source_file,
            source_line_num=line_num,
        )

    # Standard 5-field: need at least 6 tokens (5 fields + command)
    tokens = line.split(None, 5)
    if len(tokens) < 6:
        raise CronSyntaxError(
            f"Expected 5 cron fields + command, got: {line!r}"
        )
    expr_str = " ".join(tokens[:5])
    command = tokens[5]
    schedule = CronExpr.parse(expr_str)
    return CronJob(
        job_id=_make_job_id(source_file, line),
        schedule=schedule,
        command=command,
        raw_line=line,
        source_file=source_file,
        source_line_num=line_num,
    )


def _make_job_id(source_file: Path, line: str) -> str:
    """Generate a deterministic short ID from source_file + line content."""
    key = f"{source_file}:{line}"
    digest = hashlib.sha256(key.encode()).hexdigest()[:8]
    return f"cron-{digest}"


def _replace_names(part: str, name_map: dict[str, int]) -> str:
    """Replace name tokens (MON, JAN, etc.) with their numeric values.

    Handles plain names, ranges (MON-FRI), and ranges with steps (MON-FRI/2).
    """
    # Split off step first: "MON-FRI/2" → "MON-FRI", "2"
    step_suffix = ""
    if "/" in part:
        base, step_suffix = part.split("/", 1)
        step_suffix = "/" + step_suffix
    else:
        base = part

    # Replace names in the base
    if "-" in base:
        pieces = base.split("-", 1)
        resolved = []
        for p in pieces:
            low = p.strip().lower()
            if low in name_map:
                resolved.append(str(name_map[low]))
            else:
                resolved.append(p.strip())
        return "-".join(resolved) + step_suffix
    else:
        low = base.strip().lower()
        if low in name_map:
            return str(name_map[low]) + step_suffix
        return part


def _parse_field(
    token: str,
    lo: int,
    hi: int,
    field_name: str,
    name_map: dict[str, int] | None = None,
) -> set[int]:
    """Parse a single cron field (e.g. ``*/5``, ``1-15``, ``MON,WED``)."""
    result: set[int] = set()

    for part in token.split(","):
        part = part.strip()
        if not part:
            continue

        # Replace name aliases (MON, JAN, etc.)
        if name_map:
            part = _replace_names(part, name_map)

        # Parse the part: *, */N, N, N-M, N-M/S
        try:
            if part == "*":
                result.update(range(lo, hi + 1))
            elif part.startswith("*/"):
                step = int(part[2:])
                result.update(range(lo, hi + 1, step))
            elif "/" in part:
                range_part, step_str = part.split("/", 1)
                step = int(step_str)
                if "-" in range_part:
                    start, end = range_part.split("-", 1)
                    result.update(
                        range(int(start), int(end) + 1, step),
                    )
                else:
                    result.update(
                        range(int(range_part), hi + 1, step),
                    )
            elif "-" in part:
                start, end = part.split("-", 1)
                result.update(range(int(start), int(end) + 1))
            else:
                result.add(int(part))
        except ValueError as exc:
            raise CronSyntaxError(
                f"{field_name}: invalid value {part!r}"
            ) from exc

    # Validate ranges
    for v in result:
        # weekday allows 0-7 (7 normalized later)
        effective_hi = hi
        if v < lo or v > effective_hi:
            raise CronSyntaxError(
                f"{field_name}: value {v} out of range [{lo}-{hi}]"
            )

    return result


def _next_month(
    dt: datetime,
    valid_months: frozenset[int],
) -> datetime:
    """Advance *dt* to the 1st day 00:00 of the next valid month."""
    month = dt.month
    year = dt.year
    for _ in range(24):  # max 2 years
        month += 1
        if month > 12:
            month = 1
            year += 1
        if month in valid_months:
            return datetime(year, month, 1, 0, 0)
    return dt + timedelta(days=366 * 2)  # pragma: no cover
