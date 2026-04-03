"""Core Agent — orchestrates FileWatcher, Parser, Router, Scheduler, FileWriter, KernelGate."""

from __future__ import annotations

import logging
import os
import re
import threading
import time
from pathlib import Path
from typing import Any

from chatmd.engine.parser import CommandType, Parser
from chatmd.engine.reference_resolver import ReferenceResolver
from chatmd.engine.router import Router
from chatmd.engine.scheduler import Scheduler
from chatmd.exceptions import AgentError, RouteError
from chatmd.i18n import t
from chatmd.infra.config import Config
from chatmd.infra.file_writer import FileWriter
from chatmd.infra.git_sync import GitSync
from chatmd.providers.base import AIProvider
from chatmd.providers.litestartup import LiteStartupProvider
from chatmd.security.kernel_gate import KernelGate
from chatmd.skills.base import SkillContext
from chatmd.skills.builtin import register_builtin_skills
from chatmd.skills.infra import LogSkill, NewSessionSkill, SyncSkill
from chatmd.skills.loader import load_python_skills, load_yaml_skills
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

        # State
        self._running = False
        self._stop_event = threading.Event()
        self._pid_file = self._chatmd_dir / "agent.pid"
        self._stop_signal_file = self._chatmd_dir / "stop.signal"

        # Initialize AI provider
        self._init_ai_provider()

        # Initialize auto-upload handler
        self._init_auto_upload()

        # Register skills and aliases
        register_builtin_skills(self._router, scheduler=self._scheduler)
        self._register_infra_skills()
        self._register_ai_skills()
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

        # Configure watcher
        watcher_cfg = self._config.get("watcher", {})
        self._watcher = FileWatcher(
            workspace=self._workspace,
            callback=self._on_file_changed,
            file_writer=self._file_writer,
            debounce_ms=watcher_cfg.get("debounce_ms", 300),
            watch_files=watcher_cfg.get("watch_files", ["chat.md"]),
            watch_dirs=watcher_cfg.get("watch_dirs", ["chat/"]),
            ignore_patterns=watcher_cfg.get("ignore_patterns", ["_index.md"]),
        )

        self._watcher.start()
        self._running = True

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

        logger.info("Stopping ChatMD Agent...")

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
        )
        end_line = getattr(cmd, "end_line", 0)

        try:
            skill, resolved_cmd = self._router.route(cmd)
        except RouteError as exc:
            # Write error suggestion back to file
            error_text = f"> ⚠️ {exc}"
            self._write_back(filepath, cmd.source_line, end_line, cmd.raw_text, error_text)
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

    def _register_infra_skills(self) -> None:
        """Register infrastructure skills (/sync, /log, /new) with the router."""
        # Create GitSync from config if sync is configured
        git_sync: GitSync | None = None
        sync_cfg = self._config.get("sync", {})
        if sync_cfg.get("mode") == "git":
            git_sync = GitSync(
                workspace=self._workspace,
                auto_commit=sync_cfg.get("auto_commit", True),
                interval=sync_cfg.get("interval", 300),
            )

        sync_skill = SyncSkill(git_sync=git_sync)
        log_skill = LogSkill(kernel_gate=self._kernel_gate)
        self._router.register(sync_skill)
        self._router.register(log_skill)

        # /new — archive chat.md and create fresh session
        from chatmd.infra.index_manager import IndexManager
        index_manager = IndexManager(self._workspace)
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
        logger.info("Infra skills registered: sync, log, new, upload")

    def _load_custom_skills(self) -> None:
        """Load user-defined YAML and Python skills from .chatmd/skills/."""
        skills_dir = self._chatmd_dir / "skills"
        if not skills_dir.is_dir():
            return

        yaml_skills = load_yaml_skills(skills_dir)
        python_skills = load_python_skills(skills_dir)

        for skill in yaml_skills + python_skills:
            self._router.register(skill)

        total = len(yaml_skills) + len(python_skills)
        if total:
            logger.info(
                "Loaded %d custom skill(s) (%d YAML, %d Python)",
                total, len(yaml_skills), len(python_skills),
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
