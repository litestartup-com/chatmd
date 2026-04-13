"""Core Agent — orchestrates FileWatcher, Parser, Router, Scheduler, FileWriter, KernelGate."""

from __future__ import annotations

import logging
import os
import re
import threading
import time
from pathlib import Path
from typing import Any

from chatmd.engine.confirm import ConfirmationWindow
from chatmd.engine.cron_inline import write_inline_status
from chatmd.engine.cron_log import write_cron_log
from chatmd.engine.cron_parser import CronParser
from chatmd.engine.cron_safety import auto_pause_on_failures, is_dangerous_command
from chatmd.engine.cron_scheduler import CronScheduler
from chatmd.engine.cron_state import (
    detect_missed_jobs,
    load_cron_state,
    restore_scheduler_state,
    save_cron_state,
)
from chatmd.engine.parser import CommandType, Parser
from chatmd.engine.reference_resolver import ReferenceResolver
from chatmd.engine.router import Router
from chatmd.engine.scheduler import Scheduler
from chatmd.exceptions import AgentError, RouteError
from chatmd.i18n import t
from chatmd.infra.config import Config
from chatmd.infra.file_writer import FileWriter
from chatmd.infra.git_sync import GitSync
from chatmd.infra.notification import (
    EmailChannel,
    FileChannel,
    NotificationManager,
    SystemChannel,
)
from chatmd.providers.base import AIProvider
from chatmd.providers.litestartup import LiteStartupProvider
from chatmd.security.kernel_gate import KernelGate
from chatmd.skills.base import SkillContext
from chatmd.skills.builtin import register_builtin_skills
from chatmd.skills.confirm import ConfirmSkill
from chatmd.skills.infra import LogSkill, NewSessionSkill, SyncSkill
from chatmd.skills.loader import load_plugin_skills, load_skills_config
from chatmd.watcher.auto_upload import AutoUploadHandler
from chatmd.watcher.file_watcher import FileWatcher
from chatmd.watcher.suffix_trigger import SuffixTrigger

logger = logging.getLogger(__name__)


class Agent:
    """The ChatMD Agent — the central orchestrator.

    Lifecycle: ``init() -> start() -> [running] -> stop()``
    """

    def __init__(self, workspace: Path) -> None:
        self._workspace = workspace.resolve()
        self._chatmd_dir = self._workspace / ".chatmd"

        if not self._chatmd_dir.is_dir():
            raise AgentError(
                f"Not a ChatMD workspace: {self._workspace}\n"
                "Run `chatmd init` first."
            )

        # Core components
        self._config = Config(self._workspace)
        self._file_writer = FileWriter()
        self._parser = Parser(command_prefix=self._config.get("commands.prefix", "/"))
        self._init_suffix_trigger()
        self._router = Router()
        self._scheduler = Scheduler(
            max_concurrent=self._config.get("async.max_concurrent", 3),
            task_timeout=self._config.get("async.timeout", 60),
        )
        self._kernel_gate = KernelGate(
            audit_enabled=self._config.get("logging.audit", True),
        )
        self._watcher: FileWatcher | None = None
        self._ai_provider: AIProvider | None = None
        self._litestartup: LiteStartupProvider | None = None
        self._auto_upload: AutoUploadHandler | None = None
        self._cron_scheduler: CronScheduler | None = None
        self._notification_mgr: NotificationManager | None = None

        # Confirmation window (R-040)
        confirm_cfg = self._config.get("trigger.confirm", {}) or {}
        self._confirmation_window = ConfirmationWindow(
            enabled=confirm_cfg.get("enabled", False),
            commands=confirm_cfg.get("commands", []),
        )

        # State
        self._running = False
        self._stop_event = threading.Event()
        self._pid_file = self._chatmd_dir / "agent.pid"
        self._stop_signal_file = self._chatmd_dir / "stop.signal"

        # Initialize AI provider (before notification — EmailChannel needs it)
        self._init_ai_provider()

        # Initialize notification manager
        self._init_notification_manager()

        # Initialize auto-upload handler
        self._init_auto_upload()

        # Register skills and aliases
        register_builtin_skills(self._router, scheduler=self._scheduler)
        self._register_infra_skills()
        self._register_ai_skills()
        self._init_cron_scheduler()
        self._load_custom_skills()
        self._router.register_aliases(self._config.aliases)

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def workspace(self) -> Path:
        return self._workspace

    @property
    def config(self) -> Config:
        return self._config

    @property
    def router(self) -> Router:
        return self._router

    @property
    def scheduler(self) -> Scheduler:
        return self._scheduler

    @property
    def litestartup(self) -> LiteStartupProvider | None:
        return self._litestartup

    def start(self) -> None:
        """Start the Agent: watcher, services, main loop."""
        if self._running:
            raise AgentError("Agent is already running")

        self._check_no_other_instance()
        self._clean_stop_signal()
        self._write_pid()

        logger.info("Starting ChatMD Agent at %s", self._workspace)

        # Configure watcher — chatmd/ is always included
        watcher_cfg = self._config.get("watcher", {})
        watch_dirs = self._config.resolve_watch_paths()

        # Resolve cron file absolute path for change detection
        if self._config.get("cron.enabled", False):
            cron_file = (self._config.get("cron", {}) or {}).get("cron_file", "cron.md")
            self._cron_file_abs = self._config.interaction_path(cron_file).resolve()

        self._watcher = FileWatcher(
            workspace=self._workspace,
            callback=self._on_file_changed,
            file_writer=self._file_writer,
            debounce_ms=watcher_cfg.get("debounce_ms", 300),
            max_wait_ms=watcher_cfg.get("max_wait_ms", 600),
            watch_dirs=watch_dirs,
            ignore_patterns=watcher_cfg.get("ignore_patterns", ["_index.md"]),
        )

        self._watcher.start()

        # Start cron scheduler if enabled
        if self._cron_scheduler and self._config.get("cron.enabled", False):
            self._scan_and_register_cron_jobs()
            self._restore_cron_state()
            self._cron_scheduler.start()
            logger.info("CronScheduler started")

        self._running = True

        # Notify startup
        cron_count = len(self._cron_scheduler.get_all_states()) if self._cron_scheduler else 0
        self._notify_agent_lifecycle(
            "started", cron_jobs=cron_count,
        )

        logger.info("Agent started. Watching for changes...")

    def run_forever(self) -> None:
        """Block until stop is signalled (for CLI usage)."""
        if not self._running:
            self.start()
        try:
            # Use a timeout loop so KeyboardInterrupt can be delivered on Windows,
            # where Event.wait() without timeout is not interruptible.
            # Also check for stop signal file (cross-platform graceful shutdown).
            while not self._stop_event.is_set():
                self._stop_event.wait(timeout=1.0)
                if self._check_stop_signal():
                    logger.info("Stop signal file detected, shutting down")
                    break
        except KeyboardInterrupt:
            logger.info("Received keyboard interrupt")
        finally:
            self.stop()

    def stop(self) -> None:
        """Gracefully stop the Agent."""
        if not self._running:
            return

        self._notify_agent_lifecycle("stopped")
        logger.info("Stopping ChatMD Agent...")

        if self._cron_scheduler:
            self._save_cron_state()
            self._cron_scheduler.stop()

        if self._watcher:
            self._watcher.stop()

        self._scheduler.shutdown(wait=True, timeout=30.0)

        self._running = False
        self._stop_event.set()
        self._remove_pid()
        self._clean_stop_signal()

        logger.info("Agent stopped.")

    def _on_file_changed(self, filepath: Path) -> None:
        """Callback invoked by FileWatcher when a watched file changes."""
        # Cron file changed → re-scan and register jobs (no command parsing)
        cron_abs = getattr(self, "_cron_file_abs", None)
        if cron_abs and filepath.resolve() == cron_abs:
            logger.info("Cron file changed, re-scanning jobs: %s", filepath)
            self._scan_and_register_cron_jobs()
            return

        try:
            content = filepath.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            logger.error("Failed to read %s: %s", filepath, exc)
            return

        # Auto-upload: detect and upload new local images
        if self._auto_upload:
            modified = self._auto_upload.process(filepath, content)
            if modified:
                # Re-read after auto-upload rewrote the file
                try:
                    content = filepath.read_text(encoding="utf-8")
                except (OSError, UnicodeDecodeError):
                    pass

        lines = content.splitlines()
        commands = self._parser.parse_lines(lines, source_file=filepath)

        if not commands:
            return

        # Resolve @ references in command input_text
        for cmd in commands:
            if cmd.input_text and ReferenceResolver.is_reference(cmd.input_text.strip()):
                resolver = ReferenceResolver(
                    lines=lines,
                    cmd_line=cmd.source_line,
                    source_file=filepath,
                )
                cmd.input_text = resolver.resolve(cmd.input_text.strip())

        # Execute in reverse order (last command first) to avoid line offset
        # issues when earlier replacements change the file length.
        for cmd in reversed(commands):
            self._execute_command(cmd, filepath)

    def _execute_command(self, cmd: Any, filepath: Path) -> None:
        """Route and execute a single parsed command."""
        # Inline commands (/cmd{text}) use direct in-place replacement
        if getattr(cmd, "type", None) == CommandType.INLINE_CMD:
            self._execute_inline_command(cmd, filepath)
            return

        context = SkillContext(
            source_file=filepath,
            source_line=cmd.source_line,
            workspace=self._workspace,
            interaction_root=getattr(self, "_interaction_root", None),
        )
        end_line = getattr(cmd, "end_line", 0)

        try:
            skill, resolved_cmd = self._router.route(cmd)
        except RouteError as exc:
            # Write error suggestion back to file
            error_text = f"> ⚠️ {exc}"
            self._write_back(filepath, cmd.source_line, end_line, cmd.raw_text, error_text)
            return

        # Confirmation gate (R-040): intercept commands that need explicit /confirm
        if self._confirmation_window.needs_confirmation(f"/{skill.name}"):
            self._request_confirmation(
                skill, resolved_cmd, context, filepath, end_line,
            )
            return

        # Async skills: submit to scheduler with placeholder
        if getattr(skill, "is_async", False):
            self._execute_async(skill, resolved_cmd, context, filepath, end_line=end_line)
            return

        # Sync skills: execute immediately
        t0 = time.monotonic()
        try:
            result = skill.execute(resolved_cmd.input_text, resolved_cmd.args, context)
            result = self._kernel_gate.process_output(skill, result)
        except Exception as exc:
            logger.exception("Skill '%s' failed", skill.name)
            error_text = f"> {t('agent.command_failed', error=exc)}"
            self._write_back(filepath, cmd.source_line, end_line, cmd.raw_text, error_text)
            return
        elapsed = time.monotonic() - t0

        self._write_skill_result(
            filepath, cmd.source_line, cmd.raw_text, skill.name, elapsed,
            getattr(skill, "category", ""), result,
            input_text=resolved_cmd.input_text,
            end_line=end_line,
        )

    def _request_confirmation(
        self, skill: Any, resolved_cmd: Any, context: Any,
        filepath: Path, end_line: int,
    ) -> None:
        """Write a confirmation marker instead of executing the command."""
        pending = self._confirmation_window.request_confirmation(
            command_text=f"/{skill.name} {resolved_cmd.input_text}".strip(),
            source_file=filepath,
            source_line=resolved_cmd.source_line,
            callback=lambda: self._execute_confirmed(
                skill, resolved_cmd, context, filepath, end_line,
            ),
        )
        marker = self._confirmation_window.confirmation_marker(
            pending.confirm_id, pending.command_text,
        )
        self._write_back(
            filepath, resolved_cmd.source_line, end_line,
            resolved_cmd.raw_text, marker,
        )
        logger.info(
            "Confirmation requested for /%s (%s)", skill.name, pending.confirm_id,
        )

    def _execute_confirmed(
        self, skill: Any, resolved_cmd: Any, context: Any,
        filepath: Path, end_line: int,
    ) -> None:
        """Execute a command after user confirmed via /confirm."""
        t0 = time.monotonic()
        try:
            result = skill.execute(resolved_cmd.input_text, resolved_cmd.args, context)
            result = self._kernel_gate.process_output(skill, result)
        except Exception as exc:
            logger.exception("Confirmed skill '%s' failed", skill.name)
            error_text = f"> {t('agent.command_failed', error=exc)}"
            self._file_writer.append_line(filepath, error_text)
            return
        elapsed = time.monotonic() - t0

        # Append result to file (the original command line was already replaced
        # by the confirmation marker, so we append rather than replace)
        output = self._format_output(
            result.output if result.success else (result.error or ""),
            skill.name, elapsed, getattr(skill, "category", ""),
            input_text=resolved_cmd.input_text,
        )
        self._file_writer.append_line(filepath, output)

    def _execute_inline_command(self, cmd: Any, filepath: Path) -> None:
        """Execute an inline /cmd{text} and replace only the matched portion.

        Inline commands always produce direct replacement — no rich text
        wrapping, no info header.  For async skills the replacement is
        deferred via the scheduler.
        """
        context = SkillContext(
            source_file=filepath,
            source_line=cmd.source_line,
            workspace=self._workspace,
            interaction_root=getattr(self, "_interaction_root", None),
        )

        try:
            skill, resolved_cmd = self._router.route(cmd)
        except RouteError as exc:
            # Unknown inline command — replace with error hint
            error_hint = f"[⚠️ {exc}]"
            self._file_writer.write_result(
                filepath, cmd.source_line, cmd.raw_text, error_hint,
            )
            return

        # Show ⏳ placeholder so the user sees progress
        placeholder = f"[⏳ {skill.name}...]"
        self._file_writer.write_result(
            filepath, cmd.source_line, cmd.raw_text, placeholder,
        )

        # Inline commands run synchronously even if skill is normally async,
        # because the replacement is within a line and placeholders would
        # break the text flow.
        try:
            result = skill.execute(resolved_cmd.input_text, resolved_cmd.args, context)
            result = self._kernel_gate.process_output(skill, result)
        except Exception:
            logger.exception("Inline skill '%s' failed", skill.name)
            error_hint = f"[❌ {skill.name} error]"
            self._file_writer.write_result(
                filepath, cmd.source_line, placeholder, error_hint,
            )
            return

        if result.success and result.output:
            # Replace placeholder with the raw output (no formatting)
            output = result.output.strip()
            # Collapse multi-line output to single line for inline replacement
            output = output.replace("\n", " ")
            self._file_writer.write_result(
                filepath, cmd.source_line, placeholder, output,
            )
        elif not result.success:
            # Skill returned an error — show it inline
            error_msg = (result.output or "").strip().replace("\n", " ")
            error_hint = f"[❌ {error_msg}]" if error_msg else f"[❌ {skill.name} failed]"
            self._file_writer.write_result(
                filepath, cmd.source_line, placeholder, error_hint,
            )

    def _execute_async(
        self, skill: Any, cmd: Any, context: SkillContext, filepath: Path,
        *, end_line: int = 0,
    ) -> None:
        """Submit an async skill to the scheduler with a placeholder."""
        user_input = cmd.input_text
        task = self._scheduler.submit_async(
            skill_name=skill.name,
            execute_fn=lambda: skill.execute(
                cmd.input_text, cmd.args, context,
            ),
            input_text=cmd.input_text,
            args=cmd.args,
            source_file=filepath,
            source_line=cmd.source_line,
            raw_text=cmd.raw_text,
            on_complete=lambda t: self._on_async_complete(
                t, skill, filepath, user_input=user_input,
            ),
        )

        # Write placeholder — for AI commands, preserve original text above
        desc = t(f"skill.{skill.name}.description")
        placeholder = f"> {t('agent.async_placeholder', description=desc, task_id=task.id)}"
        if getattr(skill, "category", "") == "ai":
            preserved = self._extract_user_text(cmd.input_text)
            if preserved:
                placeholder = f"{preserved}\n\n{placeholder}"
        self._write_back(
            filepath, cmd.source_line, end_line, cmd.raw_text, placeholder,
        )

    def _on_async_complete(
        self, task: Any, skill: Any, filepath: Path,
        *, user_input: str = "",
    ) -> None:
        """Callback when an async task finishes — replace placeholder."""
        from chatmd.engine.scheduler import TaskStatus
        from chatmd.skills.base import SkillResult

        if task.status == TaskStatus.COMPLETED:
            result = task.result
            if isinstance(result, SkillResult):
                result = self._kernel_gate.process_output(skill, result)
                if result.success:
                    category = getattr(skill, "category", "")
                    elapsed = (
                        (task.completed_at - task.created_at).total_seconds()
                        if task.completed_at and task.created_at
                        else 0.0
                    )
                    output = self._format_output(
                        result.output, skill.name, elapsed, category,
                        input_text=user_input,
                    )
                    self._file_writer.replace_by_task_id(
                        filepath, task.id,
                        output if output else f"> {t('agent.async_done')}",
                    )
                else:
                    error_msg = result.error or t("agent.unknown_error")
                    self._file_writer.replace_by_task_id(
                        filepath, task.id,
                        f"> ❌ {error_msg}",
                    )
            elif isinstance(result, str):
                self._file_writer.replace_by_task_id(
                    filepath, task.id,
                    f"> ✅ {result}" if result else f"> {t('agent.async_done')}",
                )
        elif task.status == TaskStatus.FAILED:
            error_msg = task.error or t("agent.unknown_error")
            self._file_writer.replace_by_task_id(
                filepath, task.id,
                f"> {t('agent.async_failed_retry', error=error_msg, task_id=task.id)}",
            )

    def _write_skill_result(
        self,
        filepath: Path, source_line: int, raw_text: str,
        skill_name: str, elapsed: float,
        category: str, result: Any,
        *, input_text: str = "", end_line: int = 0,
    ) -> None:
        """Write a sync skill result back to file."""
        if result.success:
            output = self._format_output(
                result.output, skill_name, elapsed, category,
                input_text=input_text,
            )
            if category == "ai":
                # AI commands: preserve original text, append result below
                preserved = self._extract_user_text(input_text)
                combined = f"{preserved}\n\n{output}" if preserved else output
                self._write_back(filepath, source_line, end_line, raw_text, combined)
            else:
                self._write_back(filepath, source_line, end_line, raw_text, output)
        else:
            error_text = f"> ❌ {result.error or t('agent.unknown_error')}"
            self._write_back(filepath, source_line, end_line, raw_text, error_text)

    @staticmethod
    def _extract_user_text(input_text: str) -> str:
        """Return the user's original text (already parsed into input_text)."""
        return input_text.strip() if input_text else ""

    def _write_back(
        self, filepath: Path, source_line: int, end_line: int,
        raw_text: str, new_text: str,
    ) -> None:
        """Write replacement text, using range replacement for fenced commands."""
        if end_line > source_line:
            self._file_writer.write_result_range(
                filepath, source_line, end_line, new_text,
            )
        else:
            self._file_writer.write_result(
                filepath, source_line, raw_text, new_text,
            )

    _RICH_TEXT_RE = re.compile(r"^(?:#{1,6}\s|[|].*[|]|\*\*|!\[)", re.MULTILINE)

    # Maximum length for user input in AI conversation display before truncation
    _AI_INPUT_TRUNCATE_LEN = 80

    def _format_output(
        self, output: str, skill_name: str = "",
        elapsed: float = 0.0, category: str = "",
        *, input_text: str = "",
    ) -> str:
        """Format command output for writing back to Markdown.

        Two-tier strategy:

        1. Simple commands (non-AI, plain text) -> direct replacement, no wrapping:
            /date  ->  2026-03-30

        2. Rich text commands (all non-simple, including AI) ->
           single-line blockquote info header + body + ---:
            > chatmd /help 0.03s
            \n
            ## Heading
            \n
            ---

           AI commands additionally show conversation (You/AI):
            > chatmd /ask 1.20s
            \n
            **You:** question text
            \n
            **AI:** response text
            \n
            ---
        """
        elapsed_str = f"{elapsed:.2f}s" if elapsed else ""
        is_ai = category == "ai"
        is_rich = is_ai or self._RICH_TEXT_RE.search(output) is not None

        # Build info tag: "chatmd /cmd 0.01s"
        tag_parts = ["chatmd"]
        if skill_name:
            tag_parts.append(f"/{skill_name}")
        if elapsed_str:
            tag_parts.append(elapsed_str)
        tag = " ".join(tag_parts)

        if is_ai:
            # AI content: info header (blockquote) + conversation (no > prefix)
            you_label = t("output.ai.you_label")
            ai_label = t("output.ai.ai_label")
            display_input = self._truncate_input(input_text)
            return f"> {tag}\n\n{you_label} {display_input}\n\n{ai_label} {output}\n\n---"

        if is_rich:
            # Rich text: blockquote info header + raw Markdown + separator
            return f"> {tag}\n\n{output}\n\n---"

        # Simple plain text: direct replacement, zero noise
        return output

    @classmethod
    def _truncate_input(cls, text: str) -> str:
        """Truncate user input for display, collapsing newlines."""
        # Collapse multi-line to single line for display
        single = " ".join(text.split())
        if len(single) > cls._AI_INPUT_TRUNCATE_LEN:
            return single[:cls._AI_INPUT_TRUNCATE_LEN] + "..."
        return single

    def _init_suffix_trigger(self) -> None:
        """Configure suffix trigger from agent.yaml and attach to parser."""
        signals = self._config.get("trigger.signals", [])
        for sig in signals:
            if sig.get("type") == "suffix":
                trigger = SuffixTrigger(
                    marker=sig.get("marker", ";"),
                    enabled=sig.get("enabled", False),
                )
                self._parser.set_suffix_trigger(trigger)
                if trigger.enabled:
                    logger.info(
                        "Suffix trigger enabled (marker: %s)", trigger.marker
                    )
                return

    def _init_notification_manager(self) -> None:
        """Initialize NotificationManager with FileChannel + optional SystemChannel."""
        notif_cfg = self._config.get("notification", {}) or {}
        enabled = notif_cfg.get("enabled", True)

        self._notification_mgr = NotificationManager(enabled=enabled)

        if not enabled:
            logger.info("Notification manager disabled")
            return

        # FileChannel — always present when enabled
        notif_file = notif_cfg.get("notification_file", "notification.md")
        notif_path = self._config.interaction_path(notif_file)
        self._notification_mgr.add_channel(FileChannel(notif_path))
        logger.info("FileChannel registered: %s", notif_path)

        # SystemChannel — desktop toast (opt-in)
        if notif_cfg.get("system_notify", False):
            self._notification_mgr.add_channel(SystemChannel(enabled=True))
            logger.info("SystemChannel registered (desktop toast)")

        # EmailChannel — LiteStartup email notification (opt-in)
        email_cfg = notif_cfg.get("email", {}) or {}
        if email_cfg.get("enabled", False) and self._litestartup:
            self._notification_mgr.add_channel(EmailChannel(
                provider=self._litestartup,
                from_addr=email_cfg.get("from"),
                from_name=email_cfg.get("from_name"),
                to_addr=email_cfg.get("to"),
                to_name=email_cfg.get("to_name"),
            ))
            logger.info(
                "EmailChannel registered: %s -> %s",
                email_cfg.get("from", "(default)"),
                email_cfg.get("to", "(default)"),
            )

    def _init_ai_provider(self) -> None:
        """Initialize the AI provider and LiteStartup unified provider from config."""
        providers = self._config.get("ai.providers", [])
        if not providers:
            logger.info("No AI providers configured")
            return

        # Use the first/default provider
        cfg = providers[0] if isinstance(providers, list) else {}
        provider_type = cfg.get("type", "litestartup")
        api_key = cfg.get("api_key", "")

        if not api_key or api_key.startswith("${"):
            logger.warning("AI provider API key not set, AI skills will be unavailable")
            return

        # Inherit user language into provider config if not explicitly set
        if "language" not in cfg:
            user_lang = self._config.get("language", "en")
            cfg["language"] = self._map_locale_to_language(user_lang)

        if provider_type == "litestartup":
            # Create unified LiteStartup provider (upload, publish, etc.)
            from chatmd.providers.litestartup import create_litestartup_provider
            self._litestartup = create_litestartup_provider(cfg)
            logger.info("LiteStartup provider initialized: %s", self._litestartup.api_base)

            # Create AI chat provider (delegates to same API)
            from chatmd.providers.liteagent import create_provider_from_config
            self._ai_provider = create_provider_from_config(cfg)
            logger.info("AI provider initialized: %s", provider_type)
        elif provider_type == "openai":
            from chatmd.providers.openai_compat import (
                create_provider_from_config as create_openai,
            )
            self._ai_provider = create_openai(cfg)
            logger.info("AI provider initialized: %s", provider_type)
        else:
            logger.warning("Unknown AI provider type: %s", provider_type)

    def _init_auto_upload(self) -> None:
        """Initialize auto-upload handler if upload.auto is enabled."""
        upload_cfg = self._config.get("upload", {}) or {}
        if not upload_cfg.get("auto", False):
            return
        if not self._litestartup:
            logger.warning("Auto-upload enabled but LiteStartup provider not configured")
            return

        self._auto_upload = AutoUploadHandler(
            provider=self._litestartup,
            max_size_mb=upload_cfg.get("max_size_mb", 10),
            extensions=set(upload_cfg.get("extensions", [])) or None,
        )
        logger.info("Auto-upload handler initialized")

    def _init_cron_scheduler(self) -> None:
        """Initialize CronScheduler and register /cron skill."""
        if not self._config.get("cron.enabled", False):
            return

        cron_cfg = self._config.get("cron", {}) or {}
        tick_interval = cron_cfg.get("tick_interval")
        max_history = cron_cfg.get("max_history", 20)

        job_timeout = cron_cfg.get("job_timeout", 300)

        self._cron_scheduler = CronScheduler(
            tick_interval=tick_interval,
            max_history=max_history,
            job_timeout=float(job_timeout),
        )
        self._cron_scheduler.set_executor(self._execute_cron_command)
        self._cron_scheduler.set_on_job_complete(self._on_cron_job_complete)

        # Register /cron skill
        from chatmd.skills.cron import CronSkill
        cron_skill = CronSkill(cron_scheduler=self._cron_scheduler)
        cron_file_name = cron_cfg.get("cron_file", "cron.md")
        cron_skill.set_cron_file(self._config.interaction_path(cron_file_name))
        cron_skill.set_file_writer(self._file_writer)
        self._router.register(cron_skill)
        logger.info("CronScheduler initialized, /cron skill registered")

    def _scan_and_register_cron_jobs(self) -> None:
        """Scan cron.md (or all watched files) and register jobs."""
        if not self._cron_scheduler:
            return

        cron_cfg = self._config.get("cron", {}) or {}
        source = cron_cfg.get("source", "central")
        cron_file = cron_cfg.get("cron_file", "cron.md")

        if source == "central":
            cron_path = self._config.interaction_path(cron_file)
            jobs = CronParser.parse_file(cron_path)
        else:
            # scan mode: not implemented in Sprint 12
            cron_path = self._config.interaction_path(cron_file)
            jobs = CronParser.parse_file(cron_path)

        self._cron_scheduler.sync_jobs(jobs)
        logger.info("Cron jobs scanned: %d jobs from %s", len(jobs), cron_path)

        # Write back inline status comments (job IDs, next run, etc.)
        self._write_cron_inline_status(cron_path)

    def _on_cron_job_complete(self, job_id: str) -> None:
        """Callback invoked after each cron job finishes — refresh inline status."""
        cron_cfg = self._config.get("cron", {}) or {}
        cron_file = cron_cfg.get("cron_file", "cron.md")
        cron_path = self._config.interaction_path(cron_file)
        self._write_cron_inline_status(cron_path)

    def _write_cron_inline_status(self, cron_path: Path) -> None:
        """Build job_states dict from scheduler and write inline comments."""
        if not self._cron_scheduler:
            return

        all_states = self._cron_scheduler.get_all_states()
        if not all_states:
            return

        job_states: dict[str, dict] = {}
        for job_id, state in all_states.items():
            next_run_str = ""
            if state.next_run:
                next_run_str = state.next_run.strftime("%Y-%m-%d %H:%M:%S")
            job_states[job_id] = {
                "status": state.status.value,
                "next_run_str": next_run_str,
                "raw_line": state.job.raw_line,
            }

        # Mark as agent write so watcher ignores the change
        self._file_writer._mark_agent_write(cron_path)
        try:
            modified = write_inline_status(cron_path, job_states)
            if modified:
                logger.info("Cron inline status written to %s", cron_path)
        except Exception:
            logger.exception("Failed to write cron inline status to %s", cron_path)
        finally:
            self._file_writer._unmark_agent_write(cron_path)

    def _execute_cron_command(self, command: str, job_id: str) -> None:
        """Execute a cron command through the normal Router pipeline.

        Results are written to ``.chatmd/logs/cron_log.md``.
        """
        log_path = self._chatmd_dir / "logs" / "cron_log.md"
        context = SkillContext(
            source_file=log_path,
            source_line=0,
            workspace=self._workspace,
            interaction_root=getattr(self, "_interaction_root", None),
        )

        # Blacklist check — block dangerous commands even if hand-written in cron.md
        if is_dangerous_command(command):
            msg = f"Blocked dangerous command in cron: {command}"
            write_cron_log(log_path, job_id, command, msg, success=False)
            self._notify_cron_failure(job_id, command, msg)
            logger.warning(msg)
            return

        # Parse the command string
        parsed = self._parser.parse_changed_line(command)
        if not parsed:
            msg = f"Failed to parse command: {command}"
            write_cron_log(log_path, job_id, command, msg, success=False)
            self._notify_cron_failure(job_id, command, msg)
            return

        try:
            skill, resolved_cmd = self._router.route(parsed)
        except RouteError as exc:
            write_cron_log(
                log_path, job_id, command, str(exc), success=False,
            )
            self._notify_cron_failure(job_id, command, str(exc))
            return

        try:
            result = skill.execute(
                resolved_cmd.input_text, resolved_cmd.args, context,
            )
            result = self._kernel_gate.process_output(skill, result)
            write_cron_log(
                log_path, job_id, command,
                result.output if result.success else (result.error or ""),
                success=result.success,
            )
            if not result.success:
                self._notify_cron_failure(
                    job_id, command, result.error or "Unknown error",
                )
            # Auto-pause on consecutive failures (uses cron_safety threshold)
            self._check_auto_pause(job_id, command)
        except Exception as exc:
            logger.exception("Cron command failed: %s", command)
            write_cron_log(
                log_path, job_id, command, str(exc), success=False,
            )
            self._notify_cron_failure(job_id, command, str(exc))

    def _notify_cron_failure(
        self, job_id: str, command: str, error: str,
    ) -> None:
        """Send a notification when a cron job fails."""
        if not self._notification_mgr:
            return
        self._notification_mgr.notify(
            title=f"Cron task failed: {job_id}",
            body=f"Command `{command}` failed: {error}",
            level="error",
            source="cron",
            actions=[f"/cron run {job_id}", f"/cron pause {job_id}"],
        )

    def _check_auto_pause(self, job_id: str, command: str) -> None:
        """Check if a cron job should be auto-paused after consecutive failures."""
        if not self._cron_scheduler:
            return
        cron_cfg = self._config.get("cron", {}) or {}
        max_failures = cron_cfg.get("max_failures", 5)
        paused = auto_pause_on_failures(self._cron_scheduler, max_failures=max_failures)
        if job_id in paused:
            self._notify_cron_auto_pause(job_id, command, max_failures)

    def _notify_cron_auto_pause(
        self, job_id: str, command: str, max_failures: int = 5,
    ) -> None:
        """Notify when a cron job is auto-paused after consecutive failures."""
        if not self._notification_mgr:
            return
        self._notification_mgr.notify(
            title=f"Cron task auto-paused: {job_id}",
            body=(
                f"Command `{command}` failed {max_failures} times in a row. "
                "Job has been automatically paused."
            ),
            level="warning",
            source="cron",
            actions=[f"/cron resume {job_id}", f"/cron run {job_id}"],
        )

    # ── Cron state persistence (T-063) ─────────────────────────────

    @property
    def _cron_state_path(self) -> Path:
        return self._chatmd_dir / "state" / "cron_state.json"

    def _save_cron_state(self) -> None:
        """Persist cron scheduler state to disk on shutdown."""
        if not self._cron_scheduler:
            return
        try:
            save_cron_state(
                self._cron_state_path,
                self._cron_scheduler.get_all_states(),
            )
            logger.info("Cron state saved to %s", self._cron_state_path)
        except Exception:
            logger.exception("Failed to save cron state")

    def _restore_cron_state(self) -> None:
        """Load persisted state, restore into scheduler, handle missed jobs."""
        if not self._cron_scheduler:
            return

        saved = load_cron_state(self._cron_state_path)
        if not saved:
            return

        # Restore counters, status, last_run into scheduler
        restore_scheduler_state(self._cron_scheduler, saved)
        logger.info("Restored cron state for %d job(s)", len(saved))

        # Detect and handle missed jobs
        cron_cfg = self._config.get("cron", {}) or {}
        missed_policy = cron_cfg.get("missed_policy", "run")
        missed = detect_missed_jobs(saved)
        if not missed:
            return

        logger.info("Detected %d missed cron job(s): %s", len(missed), missed)
        self._notify_missed_jobs(missed)

        if missed_policy == "run":
            for job_id in missed:
                state = self._cron_scheduler.get_state(job_id)
                if state and state.status.value == "active":
                    logger.info("Running missed job: %s", job_id)
                    self._execute_cron_command(state.job.command, job_id)
        elif missed_policy == "skip":
            logger.info("Missed policy is 'skip', not running missed jobs")

    def _notify_missed_jobs(self, missed_ids: list[str]) -> None:
        """Notify about missed cron jobs detected on startup."""
        if not self._notification_mgr:
            return
        cron_cfg = self._config.get("cron", {}) or {}
        policy = cron_cfg.get("missed_policy", "run")
        action = "will be executed now" if policy == "run" else "were skipped"
        self._notification_mgr.notify(
            title=f"{len(missed_ids)} missed cron job(s) detected",
            body=f"Jobs: {', '.join(missed_ids)}. Policy: `{policy}` — {action}.",
            level="warning",
            source="cron",
        )

    def _notify_agent_lifecycle(
        self, event: str, *, cron_jobs: int = 0,
    ) -> None:
        """Send agent startup/shutdown notifications."""
        if not self._notification_mgr:
            return
        if event == "started":
            parts = [f"Workspace: `{self._workspace.name}`"]
            if cron_jobs:
                parts.append(f"{cron_jobs} cron job(s) registered")
            self._notification_mgr.notify(
                title="Agent started",
                body=". ".join(parts),
                level="info",
                source="agent",
            )
        elif event == "stopped":
            self._notification_mgr.notify(
                title="Agent stopped",
                body=f"Workspace: `{self._workspace.name}`",
                level="info",
                source="agent",
            )

    def _register_infra_skills(self) -> None:
        """Register infrastructure skills (/sync, /log, /new) with the router."""
        # Create GitSync from config if sync is configured
        git_sync: GitSync | None = None
        sync_cfg = self._config.get("sync", {})
        if sync_cfg.get("mode") == "git":
            git_sync = GitSync(workspace=self._workspace)
        self._git_sync = git_sync

        sync_skill = SyncSkill(git_sync=git_sync)
        log_skill = LogSkill(kernel_gate=self._kernel_gate)
        self._router.register(sync_skill)
        self._router.register(log_skill)

        # /new — archive chat.md and create fresh session
        from chatmd.infra.index_manager import IndexManager
        self._interaction_root = self._config.interaction_path(".")
        index_manager = IndexManager(
            self._workspace, interaction_root=self._interaction_root,
        )
        new_skill = NewSessionSkill(index_manager=index_manager)
        self._router.register(new_skill)

        # /upload — manual image upload
        from chatmd.skills.upload import UploadSkill
        upload_cfg = self._config.get("upload", {}) or {}
        upload_skill = UploadSkill(
            provider=self._litestartup,
            max_size_mb=upload_cfg.get("max_size_mb", 10),
            extensions=set(upload_cfg.get("extensions", [])) or None,
        )
        self._router.register(upload_skill)

        # /notify — send notification through all channels
        from chatmd.skills.notify import NotifySkill
        notify_skill = NotifySkill(
            notification_mgr=self._notification_mgr,
        )
        self._router.register(notify_skill)

        # /confirm — execute pending confirmation (R-040)
        confirm_skill = ConfirmSkill(
            confirmation_window=self._confirmation_window,
        )
        self._router.register(confirm_skill)
        logger.info("Infra skills registered: sync, log, new, upload, notify, confirm")

    def _load_custom_skills(self) -> None:
        """Load user-defined skills from .chatmd/skills/ using plugin config."""
        skills_dir = self._chatmd_dir / "skills"
        skills_config = load_skills_config(self._chatmd_dir)

        # Build a lightweight context for configure() — no real source file
        context = SkillContext(
            source_file=self._workspace,
            source_line=0,
            workspace=self._workspace,
            interaction_root=self._interaction_root,
        )

        skills = load_plugin_skills(skills_dir, skills_config, context)

        for skill in skills:
            self._router.register(skill)

        if skills:
            logger.info(
                "Loaded %d custom skill(s) (discover=%s)",
                len(skills), skills_config.discover,
            )

    def _register_ai_skills(self) -> None:
        """Register AI skills with the router."""
        from chatmd.skills.ai import register_ai_skills
        from chatmd.skills.canvas import CanvasSkill
        chat_skill, translate_skill = register_ai_skills(
            self._router, provider=self._ai_provider,
        )
        canvas_skill = CanvasSkill(provider=self._ai_provider)
        self._router.register(canvas_skill)

    _LOCALE_TO_LANGUAGE: dict[str, str] = {
        "en": "en",
        "zh-CN": "zh",
        "zh_CN": "zh",
        "zh": "zh",
        "ja": "ja",
        "ko": "ko",
    }

    @classmethod
    def _map_locale_to_language(cls, locale: str) -> str:
        """Map a locale string (e.g. 'en', 'zh-CN') to a language code for the AI API."""
        return cls._LOCALE_TO_LANGUAGE.get(locale, locale)

    def _check_stop_signal(self) -> bool:
        """Check whether the stop signal file exists (cross-platform graceful shutdown)."""
        return self._stop_signal_file.exists()

    def _clean_stop_signal(self) -> None:
        """Remove the stop signal file if it exists."""
        try:
            self._stop_signal_file.unlink(missing_ok=True)
        except OSError:
            pass

    def _write_pid(self) -> None:
        """Write current PID to .chatmd/agent.pid."""
        self._pid_file.write_text(str(os.getpid()), encoding="utf-8")

    def _remove_pid(self) -> None:
        """Remove the PID file."""
        try:
            self._pid_file.unlink(missing_ok=True)
        except OSError:
            pass

    def _check_no_other_instance(self) -> None:
        """Check if another Agent is already running for this workspace."""
        if not self._pid_file.exists():
            return

        try:
            pid = int(self._pid_file.read_text(encoding="utf-8").strip())
        except (ValueError, OSError):
            self._remove_pid()
            return

        if self._is_process_alive(pid):
            raise AgentError(
                f"Another Agent (PID {pid}) is already running.\n"
                "Use `chatmd stop` first."
            )
        # Stale PID file — remove it
        self._remove_pid()

    @staticmethod
    def _is_process_alive(pid: int) -> bool:
        """Check whether a process with *pid* is currently running (cross-platform)."""
        import sys

        if sys.platform == "win32":
            import ctypes
            kernel32 = ctypes.windll.kernel32  # type: ignore[attr-defined]
            query_limited = 0x1000
            handle = kernel32.OpenProcess(query_limited, False, pid)
            if handle:
                kernel32.CloseHandle(handle)
                return True
            return False

        # Unix: signal 0 checks existence without sending a real signal
        try:
            os.kill(pid, 0)
            return True
        except ProcessLookupError:
            return False
        except PermissionError:
            return True  # Process exists but we lack permission
