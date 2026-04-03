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
    "output.help.group.utility": "Utilities",
    "output.help.group.custom": "Custom",

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

    # ── /new session ───────────────────────────────────────────────────────
    "error.new_no_chat_md": "chat.md not found",
    "error.new_empty_content": "No content to archive",
    "output.new.success": "✅ Archived to chat/{archive}, new session started",
    "new.fallback_topic": "general-chat",

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
        "> ⏳ Confirm `{command}`? "
        "(auto-execute in {delay}s, delete this line to cancel)"
        " `#{confirm_id}`"
    ),

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
    "init.mode_prompt": (
        "Existing files detected, choose a mode\n"
        "  full      — Full workspace (create chat.md + chat/)\n"
        "  assistant — Inject assistant only (create .chatmd/ only)\n"
        "Mode"
    ),
    "init.workspace_created": "✅ Workspace created: {workspace} (mode: {mode})",
    "init.run_start": "Run chatmd start to start the Agent",
    "init.open_chat": "Open chat.md with any editor to start interacting",
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
    "cli.mode_label": "   Mode: {mode}",
    "cli.custom_skills": "   Custom Skills: {yaml_count} YAML + {py_count} Python",
    "cli.daemon_already_running": "ℹ️ Agent is already running (PID {pid})",
    "cli.daemon_started": "🚀 Agent started in background (PID {pid})\n   Workspace: {workspace}",
    "cli.daemon_log_hint": "   Logs: {log}",
    "cli.daemon_stop_hint": "   Run `chatmd stop` to stop the Agent",
    "cli.daemon_failed": "❌ Agent failed to start in background (exit code {code})",

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
    "upgrade.full_option": "  chatmd upgrade --full  — Upgrade to full workspace",
    "upgrade.done": "✅ Upgrade completed: {items}",
    "upgrade.already_full": "ℹ️ Workspace is already in full mode",

    # ── Default user config aliases ─────────────────────────────────────
    "alias.translate_en": "translate(English)",
    "alias.translate_jp": "translate(Japanese)",
    "alias.translate_cn": "translate(Chinese)",
}
