"""English message catalog (default locale)."""

MESSAGES: dict[str, str] = {
    # ── Skill descriptions ──────────────────────────────────────────────
    "skill.date.description": "Insert today's date",
    "skill.time.description": "Insert current time",
    "skill.now.description": "Insert current date and time",
    "skill.help.description": "Show all available commands",
    "skill.status.description": "Show Agent status",
    "skill.list.description": "List chat sessions",
    "skill.ask.description": "AI chat",
    "skill.translate.description": "Translate text",
    "skill.sync.description": "Git sync",
    "skill.log.description": "View audit log",
    "skill.new.description": "Archive chat and start new session",
    "skill.rewrite.description": "AI rewrite text",
    "skill.expand.description": "AI expand text",
    "skill.polish.description": "AI grammar check & polish",
    "skill.summary.description": "AI summarize text",
    "skill.tag.description": "AI extract keywords/tags",
    "skill.title.description": "AI recommend title",
    "skill.canvas.description": "AI generate mind-map canvas",
    "skill.upload.description": "Upload local images to cloud",
    "skill.datetime.description": "Insert date and time",
    "skill.timestamp.description": "Insert Unix timestamp",
    "skill.week.description": "Insert current week number",
    "skill.weekday.description": "Insert current weekday",
    "skill.progress.description": "Insert year progress",
    "skill.daynum.description": "Insert day-of-year number",
    "skill.countdown.description": "Countdown days to target date",
    "skill.todo.description": "Insert to-do item",
    "skill.done.description": "Insert completed to-do item",
    "skill.table.description": "Insert Markdown table",
    "skill.code.description": "Insert code block",
    "skill.link.description": "Insert Markdown link",
    "skill.img.description": "Insert Markdown image",
    "skill.hr.description": "Insert horizontal rule",
    "skill.heading.description": "Insert Markdown heading",
    "skill.quote.description": "Insert block quote",

    # ── /help output ────────────────────────────────────────────────────
    "output.help.empty": "No registered commands",
    "output.help.header": "## Available Commands\n",
    "output.help.table_header": "| Command | Aliases | Description |",
    "output.help.group.datetime": "Date & Time",
    "output.help.group.ai": "AI",
    "output.help.group.markdown": "Markdown Templates",
    "output.help.group.cron": "Cron Tasks",
    "output.help.group.utility": "Utilities",
    "output.help.group.custom": "Custom",
    "output.help.overview_hint": (
        "Use `/help <alias>` for group details (e.g. `/help dt`),"
        " `/help <cmd>` for a single command."
    ),
    "output.help.group_empty": "No commands in this group.",
    "output.help.cmd_not_found": "Command not found: `/{cmd}`",

    # ── /status output ──────────────────────────────────────────────────
    "output.status.running": "🟢 Agent running\n",
    "output.status.workspace": "Workspace: {workspace}",
    "output.status.active_tasks": "Active tasks: {count}",
    "output.status.total_tasks": "Total tasks: {count}",
    "output.status.running_tasks_header": "\n### Running Tasks\n",

    # ── /list output ────────────────────────────────────────────────────
    "output.list.empty": "No chat sessions",
    "output.list.header": "## Chat Sessions ({count})\n",
    "output.list.default_session": "- `chat.md` (default)",

    # ── /log output ─────────────────────────────────────────────────────
    "output.log.empty": "No audit records",
    "output.log.header": "## Recent {count} Audit Records\n",
    "output.log.table_header": "| # | Skill | Category | Status | Error |",

    # ── /sync output ────────────────────────────────────────────────────
    "output.sync.not_git_repo": "Current directory is not a Git repository",
    "output.sync.no_changes": "No changes to sync",
    "output.sync.conflict": "⚠️ Git merge conflict, please resolve manually",
    "output.sync.success": "✅ Git sync completed",
    "output.sync.git_failed": "Git operation failed: {error}",
    "output.sync.git_not_installed": "Git is not installed",

    # ── AI system prompt ───────────────────────────────────────────────
    "ai.language_name": "English",
    "ai.system_prompt": (
        "You are a helpful assistant. "
        "Please respond in {language} unless the user explicitly "
        "requests a different language in their message."
    ),

    # ── /ask errors ─────────────────────────────────────────────────────
    "error.provider_not_configured": "AI Provider not configured",
    "error.ask_empty_input": "Please enter a question, e.g.: /ask What is ChatMD?",

    # ── /translate ──────────────────────────────────────────────────────
    "error.translate_empty_input": (
        "Please enter text to translate, e.g.: /translate(Japanese) Hello World"
    ),
    "translate.default_target": "English",
    "translate.prompt": (
        "Please translate the following text to {target_lang}, "
        "return only the translation result, "
        "no explanations or extra content.\n\n{input_text}"
    ),

    # ── AI writing skills ─────────────────────────────────────────────────
    "error.rewrite_empty_input": "Please enter text to rewrite, e.g.: /rewrite Hello World",
    "error.expand_empty_input": "Please enter text to expand, e.g.: /expand AI is powerful",
    "error.polish_empty_input": "Please enter text to polish, e.g.: /polish He go to school",
    "error.summary_empty_input": "Please enter text to summarize",
    "error.tag_empty_input": "Please enter text to extract tags from",
    "error.title_empty_input": "Please enter text to generate a title for",
    "rewrite.prompt": (
        "Please rewrite the following text to improve clarity and readability. "
        "Keep the original meaning. Return only the rewritten text, "
        "no explanations.\n\n{input_text}"
    ),
    "expand.prompt": (
        "Please expand and elaborate on the following text, "
        "adding more detail and depth while keeping the original meaning. "
        "Return only the expanded text, no explanations.\n\n{input_text}"
    ),
    "polish.prompt": (
        "Please check and fix any grammar, spelling, or punctuation errors "
        "in the following text. Keep the original meaning and style. "
        "Return only the corrected text, no explanations.\n\n{input_text}"
    ),
    "summary.prompt": (
        "Please summarize the following text concisely, "
        "capturing the key points. "
        "Return only the summary, no explanations.\n\n{input_text}"
    ),
    "tag.prompt": (
        "Please extract the main keywords and tags from the following text. "
        "Return them as a comma-separated list, nothing else.\n\n{input_text}"
    ),
    "title.prompt": (
        "Please suggest a concise and descriptive title for the following text. "
        "Return only the title, nothing else.\n\n{input_text}"
    ),

    # ── /canvas ───────────────────────────────────────────────────────
    "error.canvas_empty_input": "Please enter text to generate a mind-map from",
    "error.canvas_empty_response": "AI returned empty response",
    "error.canvas_invalid_json": "AI returned invalid JSON: {detail}",
    "error.canvas_missing_fields": "AI response missing 'title' or 'nodes' field",
    "error.canvas_layout_failed": "Canvas layout failed: {detail}",
    "error.canvas_write_failed": "Canvas file write failed: {detail}",
    "output.canvas.success": (
        "✅ Canvas generated: `{filename}`\n"
        "📊 {nodes} nodes, {edges} edges\n"
        "💡 Open in Obsidian to view the mind-map"
    ),
    "canvas.system_prompt": (
        "You are a mind-map / concept-map generation expert. "
        "The user gives you text content. Analyze it, extract core concepts "
        "and logical relationships, and generate a structured tree.\n\n"
        "Return ONLY valid JSON in this exact format, no other text:\n\n"
        '{\n'
        '  "title": "Central topic (one sentence summary)",\n'
        '  "nodes": [\n'
        '    {\n'
        '      "text": "Level 1 topic",\n'
        '      "children": [\n'
        '        {"text": "Level 2 detail", "children": []}\n'
        '      ]\n'
        '    }\n'
        '  ]\n'
        '}\n\n'
        "Rules:\n"
        "1. title: one sentence summary as the center node\n"
        "2. nodes: level-1 branches, each may have children\n"
        "3. Max 3 levels deep (center \u2192 L1 \u2192 L2 \u2192 L3)\n"
        "4. Each node text: concise, max 30 chars\n"
        "5. 3-7 level-1 nodes, max 5 children per node\n"
        "6. Output ONLY JSON, no markdown fences or extra text"
    ),
    "canvas.user_prompt": (
        "Analyze the following content and generate a mind-map structure:\n\n{input_text}"
    ),

    # ── T-046: week/progress output ─────────────────────────────────
    "output.week.format": "Week {week}",
    "output.weekday.names": "Monday, Tuesday, Wednesday, Thursday, Friday, Saturday, Sunday",
    "output.progress.format": "{pct}% of {year}",
    "output.daynum.format": "Day {day}",
    "output.countdown.format": "{days} days until {target}",
    "error.countdown_invalid_date": "Invalid date format: {date} (expected YYYY-MM-DD)",

    # ── /upload ───────────────────────────────────────────────────────
    "error.upload_not_configured": "Upload provider not configured",
    "error.upload_file_not_found": "File not found: {path}",
    "error.upload_failed": "Upload failed for {path}: {detail}",
    "error.upload_source_not_found": "Source file not found",
    "error.upload_read_failed": "Failed to read file: {detail}",
    "error.upload_write_failed": "Failed to write file: {detail}",
    "error.upload_unsupported_ext": "Unsupported extension {ext} (allowed: {allowed})",
    "error.upload_too_large": "{path} exceeds size limit ({max_mb}MB)",
    "output.upload.single_success": "✅ Uploaded `{filename}` \u2192 {url}",
    "output.upload.no_images": "No local images found in file",
    "output.upload.scan_summary": (
        "Found {found} image(s): {uploaded} uploaded, {failed} failed, {skipped} skipped"
    ),
    "output.upload.detail_ok": "✅ {path} \u2192 {url}",
    "output.upload.detail_failed": "❌ {path}: {detail}",
    "output.upload.detail_not_found": "⚠️ {path}: file not found, skipped",
    "output.upload.detail_skipped": "⚠️ {path}: {reason}",
    "skill.upload.help_text": (
        "### Usage\n\n"
        "| Command | Description |\n"
        "|---------|-------------|\n"
        "| `/upload` | Scan current file, upload all local images, replace with URLs |\n"
        "| `/upload <path>` | Upload a single image file and return its remote URL |\n\n"
        "### Auto Upload\n\n"
        "When `upload.auto` is enabled in `agent.yaml`, new local images added to any "
        "watched `.md` file are **automatically** uploaded and replaced with remote URLs "
        "on save — no manual `/upload` needed.\n\n"
        "### Configuration (`agent.yaml` → `upload:`)\n\n"
        "```yaml\n"
        "upload:\n"
        "  auto: true          # Enable auto-upload on file change\n"
        "  max_size_mb: 10     # Max file size (default 10MB)\n"
        "  extensions:         # Allowed extensions (default below)\n"
        "    - jpg\n"
        "    - jpeg\n"
        "    - png\n"
        "    - gif\n"
        "    - webp\n"
        "    - svg\n"
        "    - ico\n"
        "```\n\n"
        "### Prerequisites\n\n"
        "- A `litestartup` provider must be configured in `ai.providers`\n"
        "- The provider's API key must have upload permission\n\n"
        "### Supported Image Syntax\n\n"
        "| Syntax | Example |\n"
        "|--------|---------|\n"
        "| Markdown | `![alt](./img/photo.png)` |\n"
        "| HTML | `<img src=\"./img/photo.png\" />` |\n\n"
        "Remote URLs (`http://`, `https://`) are automatically skipped."
    ),

    # ── /notify skill ─────────────────────────────────────────────────────
    "skill.notify.description": "Send a notification",
    "error.notify_empty": "Please provide a notification message",
    "error.notify_not_configured": "Notification manager not configured",
    "error.notify_disabled": "Notification is disabled in configuration",
    "output.notify.title": "ChatMD Reminder",
    "output.notify.success": "✅ Notification sent ({channels}): {message}",
    "skill.notify.help_text": (
        "### Usage\n\n"
        "| Command | Description |\n"
        "|---------|-------------|\n"
        "| `/notify <message>` | Send a notification through all channels |\n\n"
        "### With Cron (Scheduled Reminders)\n\n"
        "```cron\n"
        "0 18 * * * /notify Time for dinner!\n"
        "0 9 * * 1 /notify Weekly standup in 15 minutes\n"
        "```\n\n"
        "### Notification Channels\n\n"
        "| Channel | Description |\n"
        "|---------|-------------|\n"
        "| **FileChannel** | Appends to `notification.md` (always active) |\n"
        "| **SystemChannel** | Desktop toast (Windows/macOS/Linux) |\n"
        "| **EmailChannel** | Email via LiteStartup API |\n\n"
        "### Configuration (`agent.yaml` → `notification:`)\n\n"
        "```yaml\n"
        "notification:\n"
        "  enabled: true\n"
        "  system_notify: true     # Desktop toast\n"
        "  email:\n"
        "    enabled: true\n"
        "    from: support@chatmarkdown.org\n"
        "    from_name: ChatMarkdown\n"
        "    to: user@example.com\n"
        "```\n\n"
        "### Prerequisites\n\n"
        "- `notification.enabled: true` in `agent.yaml`\n"
        "- For email: a `litestartup` provider with `notification` scope\n"
        "- For desktop: OS-level notification support"
    ),

    # ── /confirm skill ─────────────────────────────────────────────────────
    "skill.confirm.description": "Execute a pending confirmation",
    "skill.confirm.help_text": (
        "### Usage\n\n"
        "| Command | Description |\n"
        "|---------|-------------|\n"
        "| `/confirm` | Execute the most recent pending command |\n"
        "| `/confirm #confirm-3` | Execute a specific pending command by ID |\n"
        "| `/confirm list` | List all pending confirmations |\n\n"
        "### How It Works\n\n"
        "Commands listed in `trigger.confirm.commands` require explicit confirmation.\n"
        "When you type such a command, a confirmation prompt appears instead of executing.\n"
        "Type `/confirm` to proceed, or delete the prompt line to cancel.\n\n"
        "### Configuration (`agent.yaml` → `trigger.confirm:`)\n\n"
        "```yaml\n"
        "trigger:\n"
        "  confirm:\n"
        "    enabled: true\n"
        "    commands:\n"
        "      - /sync\n"
        "      - /upload\n"
        "      - /new\n"
        "```"
    ),

    # ── /new session ───────────────────────────────────────────────────────
    "error.new_no_chat_md": "chat.md not found",
    "error.new_empty_content": "No content to archive",
    "output.new.success": "✅ Archived to chat/{archive}, new session started",
    "new.fallback_topic": "general-chat",
    "new.datetime_format": "%b %d, %Y %H:%M:%S",
    "new.session_timestamp": (
        "{datetime} {weekday} | Week {week}, Day {day} ({pct}% of {year})"
    ),

    # ── /cron skill ──────────────────────────────────────────────────────
    "skill.cron.description": "Manage cron scheduled tasks",
    "error.cron_not_configured": "Cron scheduler not configured",
    "error.cron_unknown_subcommand": "Unknown subcommand: {subcmd}",
    "output.cron.list_empty": "No cron jobs registered (0 jobs)",
    "output.cron.list_header": "**Cron Jobs** ({count} registered)\n",
    "output.cron.status_summary": (
        "**Cron Status** — {total} jobs"
        " ({active} active, {paused} paused)"
        " | {runs} runs, {fails} failures"
    ),
    "output.cron.next_header": "**Upcoming Executions** (next {count})\n",
    "output.cron.paused": "Job `{job_id}` paused",
    "output.cron.resumed": "Job `{job_id}` resumed",
    "output.cron.run_triggered": "Job `{job_id}` manually triggered",
    "output.cron.test_complete": "[TEST] Job `{job_id}` executed",
    "output.cron.validate_header": "**Cron Validation** ({count} jobs checked)\n",
    "output.cron.history_empty": "No execution history",
    "output.cron.history_header": "**Execution History** ({count} records)\n",
    "error.cron_missing_id": "Job ID required",
    "error.cron_job_not_found": "Job not found: {job_id}",
    "error.cron_add_usage": "Usage: /cron add <expr> <command>",
    "error.cron_dangerous_command": "Dangerous command not allowed in cron: {command}",
    "error.cron_no_file": "Cron file not configured",
    "output.cron.added": "Added cron task: `{expr}` → `{command}`",
    "output.cron.removed": "Job `{job_id}` removed",
    "skill.cron.help_text": (
        "### Subcommands\n\n"
        "| Command | Description |\n"
        "|---------|-------------|\n"
        "| `/cron` | List all registered jobs with next run time |\n"
        "| `/cron status` | Overview with run/fail statistics |\n"
        "| `/cron next [N]` | Preview next N executions (default 5) |\n"
        "| `/cron pause <ID>` | Pause a job |\n"
        "| `/cron resume <ID>` | Resume a paused job |\n"
        "| `/cron run <ID>` | Manually trigger a job |\n"
        "| `/cron test <ID>` | Test-run a job (marked `[TEST]`) |\n"
        "| `/cron validate` | Syntax-check all cron blocks |\n"
        "| `/cron history [ID]` | Last 20 execution records |\n"
        "| `/cron add <expr> <cmd>` | Add a job to cron.md |\n"
        "| `/cron remove <ID>` | Comment out a job in cron.md |\n\n"
        "### Configuration (`agent.yaml` → `cron:`)\n\n"
        "| Key | Default | Description |\n"
        "|-----|---------|-------------|\n"
        "| `enabled` | `false` | Enable cron engine |\n"
        "| `cron_file` | `cron.md` | Cron definition file |\n"
        "| `job_timeout` | `300` | Max seconds per job |\n"
        "| `max_failures` | `5` | Auto-pause after N consecutive failures |\n"
        "| `missed_policy` | `run` | `run` or `skip` missed jobs on startup |\n"
        "| `tick_interval` | auto | Scheduler tick interval (auto-tuned) |\n"
        "| `max_history` | `20` | Execution records kept per job |\n\n"
        "### Safety\n\n"
        "Dangerous commands (`upload`, `new`, `upgrade`) are blocked from cron.\n"
        "Jobs failing ≥ `max_failures` times are auto-paused with notification."
    ),

    # ── /sync skill errors ────────────────────────────────────────────────
    "error.sync_not_configured": "Git sync not configured",

    # ── /log skill errors ───────────────────────────────────────────────
    "error.audit_not_configured": "Audit module not configured",

    # ── AI provider errors (RuntimeError — always English per D3) ──────
    "error.api_timeout": "AI API request timeout ({timeout}s)",
    "error.api_key_invalid": "API Key invalid, please check configuration",
    "error.api_rate_limit": "Request rate too high, please retry later",
    "error.api_http_error": "AI API error (HTTP {status})",
    "error.api_network": "Network error: {detail}",

    # ── AI conversation labels ────────────────────────────────────────
    "output.ai.you_label": "**You:**",
    "output.ai.ai_label": "**AI:**",

    # ── Agent runtime output (written to chat.md) ──────────────────────
    "agent.command_failed": "❌ Command execution failed: {error}",
    "agent.unknown_error": "Unknown error",
    "agent.async_placeholder": "⏳ {description} in progress... `#{task_id}`",
    "agent.async_done": "✅ Done",
    "agent.async_failed_retry": "❌ {error}\n> Type `/retry #{task_id}` to retry",

    # ── Confirmation window ─────────────────────────────────────────────
    "confirm.prompt": (
        "> ⚠️ `{command}` requires confirmation — "
        "type `/confirm` to execute, delete this line to cancel"
        " `#{confirm_id}`"
    ),
    "confirm.confirmed": "✅ Confirmed and executed: `{command}`",
    "confirm.cancelled": "❌ Cancelled: `{command}`",
    "confirm.nothing_pending": "No pending commands to confirm.",
    "confirm.list_header": "Pending confirmations:",
    "confirm.list_item": "  {confirm_id}: `{command}`",

    # ── Index manager ───────────────────────────────────────────────────
    "index.header_note": "> This file is auto-maintained by ChatMD Agent. Do not edit manually.",
    "index.table_header": "| File | Created | Size |",

    # ── init workspace ──────────────────────────────────────────────────
    "init.welcome_title": "# ChatMD",
    "init.welcome_subtitle": "Welcome to ChatMD — your local AI Agent 🚀",
    "init.welcome_quickstart_header": "## Quick Start",
    "init.welcome_commands_intro": "Available commands:",
    "init.welcome_help": "/help    — Show all available commands",
    "init.welcome_date": "/date    — Insert today's date",
    "init.welcome_ask": "/ask     — AI chat",
    "init.welcome_status": "/status  — Show Agent status",
    "init.welcome_instruction": (
        "Type a command below the `---` separator and save the file to execute."
    ),
    "init.workspace_created": "✅ Workspace created: {workspace}",
    "init.run_start": "Run chatmd start to start the Agent",
    "init.open_chat": "Open chat.md with any editor to start interacting",
    "init.notification_title": "Notifications",
    "init.notification_subtitle": (
        "ChatMarkdown notification inbox"
        " — Agent appends notifications here,"
        " you can respond directly."
    ),
    "init.git_not_installed": "⚠️ Git not installed, skipping Git initialization",
    "init.git_failed": "⚠️ Git initialization failed: {error}",

    # ── agent lifecycle CLI ─────────────────────────────────────────────
    "cli.not_workspace": "❌ Not a ChatMD workspace: {workspace}",
    "cli.run_init_first": "Run chatmd init first",
    "cli.starting": "🚀 ChatMD Agent starting... ({workspace})",
    "cli.press_ctrl_c": "Press Ctrl+C to stop",
    "cli.agent_stopped": "\n👋 Agent stopped",
    "cli.no_running_agent": "ℹ️ No running Agent",
    "cli.pid_corrupted": "⚠️ PID file corrupted, cleaned up",
    "cli.stop_signal_sent": "✅ Stop signal sent (PID {pid})",
    "cli.process_not_found": "ℹ️ Agent process not found (may have stopped), cleaning PID file",
    "cli.no_permission": "❌ No permission to stop process (PID {pid})",
    "cli.agent_running": "🟢 Agent running (PID {pid})",
    "cli.agent_not_running": "⚪ Agent not running",
    "cli.agent_not_running_stale": "⚪ Agent not running (stale PID file cleaned)",
    "cli.workspace_label": "   Workspace: {workspace}",
    "cli.custom_skills": "   Custom Skills: {yaml_count} YAML + {py_count} Python",
    "cli.daemon_already_running": "ℹ️ Agent is already running (PID {pid})",
    "cli.daemon_started": "🚀 Agent started in background (PID {pid})\n   Workspace: {workspace}",
    "cli.daemon_log_hint": "   Logs: {log}",
    "cli.daemon_stop_hint": "   Run `chatmd stop` to stop the Agent",
    "cli.daemon_failed": "❌ Agent failed to start in background (exit code {code})",
    "cli.restart_stopping": "🔄 Stopping Agent (PID {pid})...",
    "cli.restart_starting": "🔄 Restarting Agent...",
    "cli.restart_not_running": "ℹ️ No running Agent found, starting new daemon...",

    # ── service CLI ─────────────────────────────────────────────────────
    "service.installed": "\u2705 Service installed ({platform}: {name})",
    "service.file_created": "   Config file: {path}",
    "service.auto_start": "   Auto-start: the Agent will start on login/reboot",
    "service.starting_now": "\U0001f680 Starting Agent now...",
    "service.started_now": "\u2705 Agent is running (PID {pid})",
    "service.start_failed": (
        "\u26a0\ufe0f Agent could not be started now. "
        "Run `chatmd start --daemon` manually."
    ),
    "service.win_hints": (
        "   Manage with:\n"
        "     chatmd service status   \u2014 check service\n"
        "     chatmd stop             \u2014 stop Agent\n"
        "     chatmd service uninstall \u2014 remove service"
    ),
    "service.launchd_hints": (
        "   Manage with:\n"
        "     chatmd service status   \u2014 check service\n"
        "     chatmd stop             \u2014 stop Agent\n"
        "     chatmd service uninstall \u2014 remove service"
    ),
    "service.systemd_hints": (
        "   Manage with:\n"
        "     systemctl --user status {name}\n"
        "     systemctl --user stop {name}\n"
        "     systemctl --user restart {name}"
    ),
    "service.uninstalled": "\u2705 Service uninstalled ({platform}: {path})",
    "service.status_info": "Service ({platform}): {name} \u2014 {status}",
    "service.unsupported_platform": "\u274c Unsupported platform: {platform}",

    # ── mode CLI ───────────────────────────────────────────────────────
    "mode.current_suffix": "Trigger mode: suffix (marker: {marker})",
    "mode.current_save": "Trigger mode: save (execute on file save)",
    "mode.switched_suffix": (
        "Trigger mode switched to: suffix (marker: {marker})\n"
        "Commands will only execute when you end a line with \"{marker}\""
    ),
    "mode.switched_save": (
        "Trigger mode switched to: save\n"
        "Commands will execute when the file is saved"
    ),

    # ── upgrade CLI ─────────────────────────────────────────────────────
    "upgrade.not_workspace": "❌ Not a ChatMD workspace, run `chatmd init` first",
    "upgrade.specify_option": "Please specify an upgrade option:",
    "upgrade.full_option": "  chatmd upgrade --full  — Ensure chatmd/ structure is complete",
    "upgrade.done": "✅ Upgrade completed: {items}",
    "upgrade.already_full": "ℹ️ Workspace structure is already complete",

    # ── Default user config aliases ─────────────────────────────────────
    "alias.translate_en": "translate(English)",
    "alias.translate_jp": "translate(Japanese)",
    "alias.translate_cn": "translate(Chinese)",
}
