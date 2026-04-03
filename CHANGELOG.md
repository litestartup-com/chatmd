# Changelog

> Format follows [Keep a Changelog](https://keepachangelog.com/). Versioning follows [Semantic Versioning](https://semver.org/).

---

## [0.2.1] — 2026-04-02

Cross-platform startup experience improvements + configuration audit + code quality fixes.

### Added

- `chatmd mode suffix/save` — trigger mode switching command
- `chatmd start --daemon` — background daemon mode (Unix nohup/double-fork + Windows pythonw)
- `chatmd service install/uninstall/status` — system service registration (systemd/launchd/Windows Service)
- Windows graceful shutdown via signal file (replaces SIGTERM)

### Fixed

- Windows `chatmd service install` and `_start_agent_now` now use `pythonw.exe` instead of `python.exe`, eliminating the cmd window popup when the service starts
- Removed unimplemented default config entries (`trigger.confirm`, `async.retry`, `commands.natural_language`, `display_name`, `preferences`) to avoid misleading users
- `KernelGate` now respects `logging.audit` config toggle
- `Scheduler` async task timeout (`async.timeout` config + watchdog timer)
- `file_writer` atomic write auto-retry + fallback on Windows PermissionError
- `logging.level` config now correctly applies to file log handler

### Changed

- Recommend `pipx` as the primary installation method
- README updated with Python installation guide

---

## [0.2.0] — 2026-04-01

Provider unified abstraction + long text + AI writing + Canvas + upload + date/time + Markdown templates. 595 tests passed.

### Added

- LiteStartupProvider unified abstraction (multi-endpoint routing: AI/upload, backward compatible)
- Parser extensions: `:::` fenced long text + `/cmd{text}` inline command + `@` reference markers
- AI writing commands: `/rewrite`, `/expand`, `/polish`, `/summary`, `/tag`, `/title`
- `/canvas` — AI Canvas mind map (structured AI output + tree layout + .canvas export)
- `/upload` — manual image upload + auto-upload mode (Watcher integration)
- `/new` — archive conversation and start new session
- Date/time extensions: `/datetime`, `/timestamp`, `/week`, `/weekday`, `/progress`, `/daynum`, `/countdown`
- Markdown templates: `/todo`, `/done`, `/table`, `/code`, `/link`, `/img`, `/hr`, `/heading`, `/quote`
- `/help` grouped by category (datetime/ai/markdown/utility/custom)

### Fixed

- Alias conflict: `/q` restored to `/quote`

---

## [0.1.0] — 2026-03-30

First official release. 168 tests passed. 6 sprints, 35 development tasks.

### Added

- Project skeleton: pyproject.toml + src/chatmd/ modular structure + CLI entry point
- `chatmd init` — workspace initialization (full/assistant mode + Git + config generation)
- `chatmd start/stop/status` — Agent lifecycle management (PID dedup + graceful stop)
- `chatmd upgrade --full` — assistant → full workspace conversion
- Config loading (agent.yaml + user.yaml + defaults merge + ${ENV} variable resolution)
- FileWatcher (watchdog + 300ms debounce + Agent write-back filter)
- Parser (`/command(args) input` syntax + `@ai{}` inline/multi-line + code block protection)
- Router (deterministic match + alias chain resolution + Levenshtein fuzzy suggestions)
- FileWriter (task ID anchor replacement + atomic write + thread-lock serialization)
- Scheduler (sync/async task dispatch + 6-state machine + ThreadPool)
- AI Skills: `/ask` conversation + `/translate` multi-language translation
- LiteAgent AI Provider (httpx + timeout/401/429 error handling)
- KernelGate security filter (AI output `/command` escaping + audit log)
- Multi-turn AI conversation context (ChatSession + max_turns truncation)
- Multi-session state management (StateManager + JSON persistence)
- Offline queue (OfflineQueue + FIFO + disk persistence)
- Git auto-sync + `/sync` (auto-commit + pull --rebase + push)
- Suffix signal trigger (SuffixTrigger + custom marker + enable/disable)
- Confirmation window (ConfirmationWindow + delay timer + delete-to-cancel)
- `@ai{}` enhanced (inline + multi-line block + code block protection)
- YAML/Python Skill Loader (declarative templates + dynamic import)
- Command conflict detection and priority (builtin > ai > custom > remote)
- Skill hot reload (SkillReloader + YAML/Python dynamic loading)
- `chat/_index.md` auto-maintenance (IndexManager)
- Built-in Skills: `/help`, `/date`, `/time`, `/now`, `/status`, `/list`, `/log`, `/sync`

### Fixed

- Skill base class `field()` compatibility on non-dataclass ABC

---

## [0.0.0] — 2026-03-30

Project initialization.
