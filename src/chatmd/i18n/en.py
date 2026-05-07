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
    "output.sync.success_detail": "✅ Git sync completed ({detail})",
    "output.sync.pulled": "↓{count} pulled",
    "output.sync.pushed": "↑{count} pushed",
    "output.sync.git_failed": "Git operation failed: {error}",
    "output.sync.git_not_installed": "Git is not installed",
    "output.sync.accepted_placeholder": "> ✅ /sync accepted",

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
    "error.notify_invalid_channel": (
        "Invalid channel: {channels}. Valid channels: {valid}"
    ),
    "output.notify.title": "ChatMD Reminder",
    "output.notify.success": "✅ Notification sent ({channels}): {message}",
    "skill.notify.help_text": (
        "### Usage\n\n"
        "| Command | Description |\n"
        "|---------|-------------|\n"
        "| `/notify <message>` | Send through all channels |\n"
        "| `/notify(email) <msg>` | Send via email only |\n"
        "| `/notify(bot) <msg>` | Send via bot only |\n"
        "| `/notify(email,bot) <msg>` | Send via email + bot |\n\n"
        "### With Cron (Scheduled Reminders)\n\n"
        "```cron\n"
        "0 18 * * * /notify Time for dinner!\n"
        "0 9 * * 1 /notify(bot) Weekly standup in 15 minutes\n"
        "```\n\n"
        "### Notification Channels\n\n"
        "| Channel | Short Name | Description |\n"
        "|---------|------------|-------------|\n"
        "| **FileChannel** | `file` | Appends to `notification.md` (always active) |\n"
        "| **SystemChannel** | `system` | Desktop toast (Windows/macOS/Linux) |\n"
        "| **EmailChannel** | `email` | Email via LiteStartup API |\n"
        "| **BotNotificationChannel** | `bot` | Push to Telegram/Feishu Bot |\n\n"
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

    # ── /inbox skill ───────────────────────────────────────────────────────
    "skill.inbox.description": "Show today's inbox summary",
    "error.inbox_invalid_date": "Invalid date format: {date} (expected YYYY-MM-DD)",
    "output.inbox.empty": "No inbox messages for {date}",
    "output.inbox.header": "## Inbox {date} ({count} messages)\n",
    "output.inbox.table_header": "| Time | Preview |",
    "output.inbox.summary": "{count} messages, {first} — {last}",
    "skill.inbox.help_text": (
        "### Usage\n\n"
        "| Command | Description |\n"
        "|---------|-------------|\n"
        "| `/inbox` | Show today's inbox summary |\n"
        "| `/inbox YYYY-MM-DD` | Show inbox for a specific date |\n\n"
        "### What It Shows\n\n"
        "- Message count and time range\n"
        "- Preview table with time and first line of each message\n\n"
        "### How It Works\n\n"
        "Reads `chatmd/inbox/YYYY-MM-DD.md` files written by the Telegram Bot.\n"
        "Use `/sync` first to pull the latest messages from the remote repo."
    ),

    # ── /bind skill ────────────────────────────────────────────────────────
    "skill.bind.description": "Bind your Git repo to a Telegram Bot",
    "error.bind_no_provider": (
        "LiteStartup provider not configured."
        " Check ai.providers in agent.yaml"
    ),
    "error.bind_missing_token": "Please provide your Git platform Access Token.",
    "error.bind_no_remote": (
        "No git remote origin found in this workspace."
        " Is this a Git repository?"
    ),
    "error.bind_invalid_repo": "Invalid repository URL format",
    "error.bind_invalid_platform": "Unsupported platform (currently only Telegram is supported)",
    "error.bind_already_active": (
        "You already have an active binding."
        " Unbind first if you want to rebind"
    ),
    "error.bind_unauthorized": "Authentication failed. Check your API key in agent.yaml",
    "error.bind_rate_limited": "Too many requests. Please wait a few minutes and try again",
    "error.bind_unknown": "Bind failed (unknown error) [code={code}] raw={raw}",
    "error.bind_server_error": "Bind API not available: {detail}",
    "output.bind.title": "🔗 Bot Binding",
    "output.bind.detected_repo": "Detected repo: `{repo_url}`",
    "output.bind.platform_detected": "Platform: **{platform}**",
    "output.bind.token_help_link": "📖 How to create a token: {url}",
    "output.bind.usage_hint": "Usage: `/bind <your_access_token>`",
    "output.bind.repo_line": "Repo: `{repo_url}`",
    "output.bind.platform_line": "Platform: **{platform}**",
    "output.bind.code_line": "Bind code: **{code}** ({minutes} min valid)",
    "output.bind.bot_link": "Open Telegram Bot: [{name}]({link})",
    "output.bind.bot_name": "Telegram Bot: {name}",
    "output.bind.waiting": "⏳ Send the bind code to the Bot to complete binding.",
    "output.bind.already_active": "⚠️ You already have an active binding:",
    "output.bind.current_binding": (
        "- Platform: **{platform}**\n"
        "- Repo: `{repo}`\n"
        "- Bound at: {bound_at}"
    ),
    "skill.bind.help_text": (
        "### Usage\n\n"
        "```\n"
        "/bind <git_access_token>\n"
        "```\n\n"
        "Bind your Git note repository to a Telegram Bot so you can send "
        "voice/text/image messages from your phone and have them auto-synced "
        "to your notes.\n\n"
        "### How It Works\n\n"
        "1. chatmd reads your `git remote origin` automatically\n"
        "2. Calls LiteStartup API to get a 6-digit bind code\n"
        "3. You send the code to the Telegram Bot\n"
        "4. Binding complete! Messages → `inbox/` → git sync → your notes\n\n"
        "### Getting a Token\n\n"
        "| Platform | Token Type | URL |\n"
        "|----------|-----------|-----|\n"
        "| GitHub | Fine-grained PAT | https://github.com/settings/tokens?type=beta |\n"
        "| GitLab | Personal Access Token |"
        " https://gitlab.com/-/user_settings/personal_access_tokens |\n"
        "| Gitee | Private Token | https://gitee.com/profile/personal_access_tokens |\n\n"
        "**Required permissions**: Repository read & write only.\n\n"
        "### Example\n\n"
        "```\n"
        "/bind ghp_xxxxxxxxxxxxxxxxxxxx\n"
        "```"
    ),

    # ── /bind status sub-command (T-R083 / T-126) ─────────────────────────
    "output.bind.list_header": "📋 Bound repos ({count})",
    "output.bind.list_row": "{marker} `{alias}` — `{url}`",
    "output.bind.list_empty": (
        "📋 No bot bindings yet.\n\n"
        "Run `/bind <git_access_token>` to create one."
    ),
    "output.bind.list_footer": "Legend: ✅ active · ▶ this workspace · · other",
    "output.bind.list_unnamed_alias": "(no alias)",
    "error.bind_list_failed": "List bindings failed: {detail}",

    # ── /unbind skill (T-R083 / T-126) ────────────────────────────────────
    "skill.unbind.description": "Remove a Telegram Bot repo binding",
    "skill.unbind.help_text": (
        "### Usage\n\n"
        "| Command | Description |\n"
        "|---------|-------------|\n"
        "| `/unbind` | Remove the binding for **this** workspace's repo |\n"
        "| `/unbind <alias>` | Remove the binding addressed by alias |\n"
        "| `/unbind --all` | Wipe every binding for this user |\n\n"
        "### How It Works\n\n"
        "The default no-arg form looks up the alias automatically by "
        "matching `git remote origin` against the server's binding list — "
        "you never have to type or copy an alias for the common case "
        '("disconnect this notebook").\n\n'
        "When the active binding is removed, the server promotes the next "
        "survivor and reports the new active alias so you immediately know "
        "what `/use` defaults to from Telegram.\n\n"
        "Use `/bind status` to see all your bindings before deciding which "
        "to remove."
    ),
    "output.unbind.success": (
        "🗑️ Unbound `{alias}`. {remaining} binding(s) remaining."
    ),
    "output.unbind.new_active": "✅ New active binding: `{alias}`",
    "output.unbind.all_success": (
        "🗑️ Cleared {count} binding(s): {aliases}"
    ),
    "output.unbind.all_empty": (
        "📋 No bindings to clear."
    ),
    "error.unbind_alias_not_found": (
        "Alias `{alias}` not found. Run `/bind status` to see available "
        "bindings."
    ),
    "error.unbind_alias_not_found_generic": (
        "Alias not found. Run `/bind status` to see available bindings."
    ),
    "error.unbind_no_workspace_match": (
        "No binding matches this workspace's repo (`{url}`).\n\n"
        "Run `/bind status` to see your bindings, then "
        "`/unbind <alias>` to remove one."
    ),
    "error.unbind_no_addressable_alias": (
        "Found a matching binding but it has no addressable alias.\n\n"
        "Run `/bind status` and use `/unbind --all` to wipe everything, "
        "or upgrade your LiteStartup server (T-125)."
    ),
    "error.unbind_failed": "Unbind failed: {detail}",

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
    "agent.network_placeholder": "⏳ {description}...",
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
    "confirm.accepted_placeholder": "✅ Confirmed",
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
    "init.interaction.readme": (
        "# ChatMD Interaction Directory\n\n"
        "This directory is the shared workspace for you and the ChatMD Agent. "
        "It contains commands, Agent results, notifications, and conversation files.\n\n"
        "## Access Boundary\n\n"
        "- You may read and edit files here.\n"
        "- The ChatMD Agent may read and update files here while serving your commands.\n"
        "- Third-party tools, bots, plugins, scripts, or services must not enter, scan, "
        "rewrite, organize, or delete files in this directory by default.\n"
        "- If a third-party tool needs access, it must ask you first and proceed only "
        "after your explicit confirmation.\n\n"
        "## Safe Use\n\n"
        "- Write commands in `chat.md`.\n"
        "- Keep automation changes visible and reversible.\n"
        "- Review unexpected modifications before continuing.\n"
    ),
    "init.profile.readme": (
        "# Personal Workspace\n\n"
        "This workspace is designed around five simple actions:\n\n"
        "1. Capture — put raw inputs into `C-Inbox/`.\n"
        "2. Clarify — turn useful items into notes, projects, or actions.\n"
        "3. Connect — link notes to projects, resources, and decisions.\n"
        "4. Review — use daily and weekly reviews to keep the system clean.\n"
        "5. Produce — turn knowledge into reports, plans, writing, or decisions.\n\n"
        "## Start Here\n\n"
        "- Daily entry: `B-Dashboard/Today.md`\n"
        "- Chat with Agent: `A-ChatMD/chat.md`\n"
        "- Capture inbox: `C-Inbox/`\n"
        "- Active projects: `E-Projects/01-Active/`\n"
        "- Reusable templates: `L-Resources/01-Templates/`\n\n"
        "## Weekly Routine\n\n"
        "- Empty inbox.\n"
        "- Update active projects.\n"
        "- Review daily notes.\n"
        "- Archive stale items.\n"
        "- Choose one to three outputs for next week.\n"
    ),
    "init.profile.inbox_readme": (
        "# Inbox\n\n"
        "Use this as a temporary capture zone for raw ideas, links, messages, files, "
        "voice transcripts, and Agent outputs.\n\n"
        "## Rules\n\n"
        "- Capture quickly; organize later.\n"
        "- Review at least once a week.\n"
        "- Move useful items to projects, notes, resources, or daily records.\n"
        "- Delete or archive noise.\n"
        "- Do not let inbox become permanent storage.\n"
    ),
    "init.profile.projects_readme": (
        "# Projects\n\n"
        "Use projects for outcomes that need multiple steps.\n\n"
        "## Structure\n\n"
        "- `01-Active/` — projects you are actively moving forward.\n"
        "- `02-Someday/` — ideas that may become projects later.\n\n"
        "## Project Health Check\n\n"
        "- Is the outcome clear?\n"
        "- Is there a next action?\n"
        "- Are decisions and resources linked?\n"
        "- Should this stay active, pause, or move to archive?\n"
    ),
    "init.profile.notes_readme": (
        "# Notes\n\n"
        "Use notes for reusable knowledge, not temporary tasks.\n\n"
        "## Where to Put Notes\n\n"
        "- `01-Ideas/` — concepts, questions, and early thoughts.\n"
        "- `02-Books/` — reading notes and book summaries.\n"
        "- `03-Meetings/` — meeting records and follow-ups.\n"
        "- `04-Learnings/` — lessons, tutorials, and study notes.\n\n"
        "## Good Note Pattern\n\n"
        "- One sentence summary.\n"
        "- Key points.\n"
        "- Links to projects or sources.\n"
        "- Next possible use.\n"
    ),
    "init.profile.archive_readme": (
        "# Archive\n\n"
        "Use archive for completed, inactive, or reference-only material.\n\n"
        "## Archive When\n\n"
        "- A project is finished.\n"
        "- A note is no longer active but may be useful later.\n"
        "- A resource should be kept but not shown in daily work.\n\n"
        "Archive is not a trash bin. Delete what has no future value.\n"
    ),
    "init.profile.people_readme": (
        "# People\n\n"
        "Use this area for relationship context and follow-up memory.\n\n"
        "## Privacy\n\n"
        "People notes may contain sensitive information. Do not share them with AI tools, "
        "sync services, or third-party systems unless you explicitly choose to do so.\n\n"
        "## Useful Fields\n\n"
        "- Who they are.\n"
        "- What they care about.\n"
        "- Last interaction.\n"
        "- Next touchpoint.\n"
    ),
    "init.profile.goals_readme": (
        "# Goals\n\n"
        "Use goals for long-term outcomes. Use projects for concrete execution.\n\n"
        "## Review Questions\n\n"
        "- Why does this goal matter?\n"
        "- What would measurable progress look like?\n"
        "- Which active projects support it?\n"
        "- Should the goal continue, change, or stop?\n"
    ),
    "init.profile.habits_readme": (
        "# Habits\n\n"
        "Use habits for repeatable behaviors. Keep tracking lightweight.\n\n"
        "## Rules\n\n"
        "- Define the minimum version.\n"
        "- Track only what helps you adjust behavior.\n"
        "- Review friction instead of blaming yourself.\n"
        "- Stop tracking habits that no longer matter.\n"
    ),
    "init.profile.health_readme": (
        "# Health\n\n"
        "Use this area for private health and energy notes.\n\n"
        "## Privacy\n\n"
        "Health notes are sensitive by default. Do not share them with AI tools, sync "
        "services, or third-party systems unless you explicitly choose to do so.\n\n"
        "## Reminder\n\n"
        "This workspace is for self-observation and reflection. It is not medical advice.\n"
    ),
    "init.profile.dashboard_home": (
        "# Home\n\n"
        "Use this page as your lightweight operating dashboard. Keep it short enough "
        "to review in one minute.\n\n"
        "## Start Here\n\n"
        "- Today: `Today.md`\n"
        "- Knowledge map: `Knowledge-Map.md`\n"
        "- Chat with Agent: `../A-ChatMD/chat.md`\n"
        "- Inbox: `../C-Inbox/`\n"
        "- Active projects: `../E-Projects/01-Active/`\n"
        "- Templates: `../L-Resources/01-Templates/`\n\n"
        "## This Week\n\n"
        "| Priority | Why It Matters | Next Step | Link |\n"
        "|----------|----------------|-----------|------|\n"
        "|          |                |           |      |\n"
        "|          |                |           |      |\n"
        "|          |                |           |      |\n\n"
        "## Active Areas\n\n"
        "- Work:\n"
        "- Learning:\n"
        "- Life:\n"
        "- Health / Energy:\n\n"
        "## Weekly Maintenance\n\n"
        "- [ ] Process inbox\n"
        "- [ ] Review active projects\n"
        "- [ ] Update `Knowledge-Map.md`\n"
        "- [ ] Archive done or stale items\n"
        "- [ ] Pick one output to finish\n"
    ),
    "init.profile.dashboard_today": (
        "# Today\n\n"
        "## One Thing\n\n"
        "- If today goes well, what will be true?\n\n"
        "## Top 3\n\n"
        "- [ ] \n"
        "- [ ] \n"
        "- [ ] \n\n"
        "## Schedule / Blocks\n\n"
        "| Time | Plan | Notes |\n"
        "|------|------|-------|\n"
        "|      |      |       |\n"
        "|      |      |       |\n\n"
        "## Inbox Triage\n\n"
        "- [ ] Capture new inputs\n"
        "- [ ] Move useful items to projects or notes\n"
        "- [ ] Delete or archive noise\n\n"
        "## Work Log\n\n"
        "- \n\n"
        "## End-of-Day Review\n\n"
        "- Done:\n"
        "- Blocked:\n"
        "- Tomorrow:\n"
    ),
    "init.profile.knowledge_map": (
        "# Knowledge Map\n\n"
        "This is a manually maintained map of your important knowledge assets. "
        "It is not an automatic index or an AI global search page.\n\n"
        "## Current Focus\n\n"
        "| Focus | Description | Related Project / Note | Status |\n"
        "|-------|-------------|------------------------|--------|\n"
        "|       |             |                        |        |\n"
        "|       |             |                        |        |\n"
        "|       |             |                        |        |\n\n"
        "## Knowledge Areas\n\n"
        "| Area | Why It Matters | Key Notes | Active Projects | Review Cycle |\n"
        "|------|----------------|-----------|-----------------|--------------|\n"
        "| Work / Career | | | | Weekly |\n"
        "| Learning | | | | Weekly |\n"
        "| Personal System | | | | Monthly |\n"
        "| Health / Energy | | | | Weekly |\n\n"
        "## Core Notes\n\n"
        "| Note | Main Idea | Related Area | Last Reviewed |\n"
        "|------|-----------|--------------|---------------|\n"
        "|      |           |              |               |\n"
        "|      |           |              |               |\n\n"
        "## Active Projects Map\n\n"
        "| Project | Outcome | Related Notes | Related Decisions | Next Review |\n"
        "|---------|---------|---------------|-------------------|-------------|\n"
        "|         |         |               |                   |             |\n"
        "|         |         |               |                   |             |\n\n"
        "## Open Questions\n\n"
        "These are manual thinking anchors, not search prompts.\n\n"
        "| Question | Area | Current Best Answer | Related Notes |\n"
        "|----------|------|---------------------|---------------|\n"
        "|          |      |                     |               |\n"
        "|          |      |                     |               |\n\n"
        "## Decision and Output Index\n\n"
        "| Item | Type | Source / Context | Next Step | Link |\n"
        "|------|------|------------------|-----------|------|\n"
        "|      | Decision / Output | | | |\n"
        "|      | Decision / Output | | | |\n\n"
        "## Maintenance Queue\n\n"
        "- [ ] Notes that need summaries:\n"
        "- [ ] Projects that need clearer next actions:\n"
        "- [ ] Decisions that need review:\n"
        "- [ ] Outputs that should be finished:\n"
        "- [ ] Items that should be archived:\n"
    ),
    "init.template.daily": (
        "# Daily Note\n\n"
        "## Plan\n\n"
        "- Main outcome:\n"
        "- Top 3:\n"
        "  - [ ] \n"
        "  - [ ] \n"
        "  - [ ] \n\n"
        "## Captures\n\n"
        "- \n\n"
        "## Decisions / Changes\n\n"
        "- \n\n"
        "## Learnings\n\n"
        "- \n\n"
        "## Review\n\n"
        "- What worked?\n"
        "- What did not work?\n"
        "- What should change tomorrow?\n"
    ),
    "init.template.note": (
        "# Note\n\n"
        "## Summary\n\n"
        "One sentence summary:\n\n"
        "## Key Points\n\n"
        "- \n"
        "- \n"
        "- \n\n"
        "## Why It Matters\n\n"
        "- \n\n"
        "## Links\n\n"
        "- Related project:\n"
        "- Related note:\n"
        "- Source:\n\n"
        "## Next Use\n\n"
        "- [ ] Use in project\n"
        "- [ ] Turn into output\n"
        "- [ ] Review later\n"
    ),
    "init.template.project": (
        "# Project\n\n"
        "## Outcome\n\n"
        "What does done look like?\n\n"
        "## Why\n\n"
        "Why is this project important?\n\n"
        "## Status\n\n"
        "- State: active / paused / done\n"
        "- Owner:\n"
        "- Deadline:\n\n"
        "## Next Actions\n\n"
        "- [ ] \n"
        "- [ ] \n"
        "- [ ] \n\n"
        "## Resources\n\n"
        "- \n\n"
        "## Decisions\n\n"
        "- \n\n"
        "## Review\n\n"
        "- Progress:\n"
        "- Risk:\n"
        "- Next step:\n"
    ),
    "init.template.meeting": (
        "# Meeting\n\n"
        "## Context\n\n"
        "- Topic:\n"
        "- Date:\n"
        "- People:\n\n"
        "## Notes\n\n"
        "- \n\n"
        "## Decisions\n\n"
        "- \n\n"
        "## Action Items\n\n"
        "- [ ] Owner — action — due date\n\n"
        "## Follow-up\n\n"
        "- What needs to be clarified?\n"
        "- What should be sent or documented?\n"
    ),
    "init.template.decision": (
        "# Decision\n\n"
        "## Context\n\n"
        "What problem are we solving?\n\n"
        "## Options\n\n"
        "1. \n"
        "2. \n"
        "3. \n\n"
        "## Criteria\n\n"
        "- \n"
        "- \n"
        "- \n\n"
        "## Decision\n\n"
        "Chosen option:\n\n"
        "## Reason\n\n"
        "Why this option?\n\n"
        "## Consequences\n\n"
        "- Upside:\n"
        "- Risk:\n"
        "- Revisit date:\n"
    ),
    "init.template.weekly_review": (
        "# Weekly Review\n\n"
        "## Highlights\n\n"
        "- \n\n"
        "## Finished\n\n"
        "- \n\n"
        "## Still Open\n\n"
        "- \n\n"
        "## Lessons\n\n"
        "- \n\n"
        "## Inbox Cleanup\n\n"
        "- [ ] Inbox processed\n"
        "- [ ] Projects updated\n"
        "- [ ] Notes linked\n"
        "- [ ] Archive updated\n\n"
        "## Next Week\n\n"
        "- Main outcome:\n"
        "- Top projects:\n"
        "- Outputs to create:\n"
    ),
    "init.template.report": (
        "# Report\n\n"
        "## Purpose\n\n"
        "Who is this for and why?\n\n"
        "## Summary\n\n"
        "- \n\n"
        "## Findings\n\n"
        "- \n"
        "- \n"
        "- \n\n"
        "## Recommendation\n\n"
        "- \n\n"
        "## Evidence / Links\n\n"
        "- \n\n"
        "## Next Actions\n\n"
        "- [ ] \n"
    ),
    "init.template.output": (
        "# Output\n\n"
        "## Audience\n\n"
        "- Who will use this?\n\n"
        "## Goal\n\n"
        "- What should this output help them do?\n\n"
        "## Draft\n\n"
        "- \n\n"
        "## Source Notes\n\n"
        "- \n\n"
        "## Publish / Share Checklist\n\n"
        "- [ ] Clear title\n"
        "- [ ] Key message visible\n"
        "- [ ] Evidence linked\n"
        "- [ ] Next action included\n"
    ),
    "init.template.person": (
        "# Person\n\n"
        "## Profile\n\n"
        "- Name:\n"
        "- Role:\n"
        "- Context:\n"
        "- Contact:\n\n"
        "## Relationship\n\n"
        "- How we know each other:\n"
        "- What they care about:\n"
        "- How I can help:\n\n"
        "## Interaction Log\n\n"
        "| Date | Topic | Follow-up |\n"
        "|------|-------|-----------|\n"
        "|      |       |           |\n\n"
        "## Next Touchpoint\n\n"
        "- [ ] \n\n"
        "## Notes\n\n"
        "- \n\n"
        "## Privacy\n\n"
        "- Sensitivity: normal / sensitive\n"
        "- Share in AI context: yes / no\n"
    ),
    "init.template.goal": (
        "# Goal\n\n"
        "## Outcome\n\n"
        "What result do I want?\n\n"
        "## Why\n\n"
        "Why does this matter?\n\n"
        "## Time Horizon\n\n"
        "- Start:\n"
        "- Target:\n"
        "- Review cycle:\n\n"
        "## Measures\n\n"
        "- Lead measure:\n"
        "- Lag measure:\n\n"
        "## Milestones\n\n"
        "- [ ] \n"
        "- [ ] \n"
        "- [ ] \n\n"
        "## Obstacles\n\n"
        "- \n\n"
        "## Current Projects\n\n"
        "- \n\n"
        "## Review\n\n"
        "- Progress:\n"
        "- What worked:\n"
        "- What to adjust:\n"
    ),
    "init.template.habit": (
        "# Habit\n\n"
        "## Intent\n\n"
        "What behavior do I want to repeat?\n\n"
        "## Trigger\n\n"
        "When or where does it start?\n\n"
        "## Minimum Version\n\n"
        "What is the smallest acceptable version?\n\n"
        "## Tracker\n\n"
        "| Date | Done | Note |\n"
        "|------|------|------|\n"
        "|      |      |      |\n\n"
        "## Reflection\n\n"
        "- What makes it easier?\n"
        "- What makes it harder?\n"
        "- Should I keep, change, or stop this habit?\n"
    ),
    "init.template.health_log": (
        "# Health Log\n\n"
        "## Date\n\n"
        "## Energy\n\n"
        "- Sleep:\n"
        "- Energy:\n"
        "- Mood:\n"
        "- Stress:\n"
        "- Movement:\n\n"
        "## Notes\n\n"
        "- \n\n"
        "## Signals\n\n"
        "- What improved?\n"
        "- What got worse?\n"
        "- What might be causing it?\n\n"
        "## Adjustment\n\n"
        "- [ ] One small change for tomorrow\n\n"
        "## Privacy\n\n"
        "This note may contain sensitive information. Avoid sharing it unless explicitly "
        "needed.\n"
    ),
    "init.template.life_review": (
        "# Life Review\n\n"
        "## Period\n\n"
        "- Week / Month / Quarter:\n\n"
        "## Energy\n\n"
        "- What gave me energy?\n"
        "- What drained energy?\n\n"
        "## Relationships\n\n"
        "- Who should I reconnect with?\n"
        "- Who needs attention?\n\n"
        "## Goals\n\n"
        "- What moved forward?\n"
        "- What became irrelevant?\n\n"
        "## Habits\n\n"
        "- What stayed consistent?\n"
        "- What needs adjustment?\n\n"
        "## Decisions\n\n"
        "- Any decision to revisit?\n\n"
        "## Next Period\n\n"
        "- Main focus:\n"
        "- One thing to stop:\n"
        "- One thing to start:\n"
    ),
    "init.template.identity": (
        "# Identity Note\n\n"
        "## Current Version\n\n"
        "Who am I becoming?\n\n"
        "## Principles\n\n"
        "- \n"
        "- \n"
        "- \n\n"
        "## Strengths\n\n"
        "- \n\n"
        "## Patterns\n\n"
        "- Helpful patterns:\n"
        "- Harmful patterns:\n\n"
        "## Evidence\n\n"
        "- Recent actions that support this identity:\n"
        "- Recent actions that conflict with this identity:\n\n"
        "## Update\n\n"
        "What should change in how I act?\n"
    ),
    "init.template.monthly_review": (
        "# Monthly Review\n\n"
        "## Month\n\n"
        "- \n\n"
        "## Outcomes\n\n"
        "- What did I finish?\n"
        "- What changed?\n"
        "- What should be archived?\n\n"
        "## Knowledge\n\n"
        "- Best notes:\n"
        "- Reusable resources:\n"
        "- Open questions:\n\n"
        "## Next Month\n\n"
        "- Main focus:\n"
        "- Projects to continue:\n"
        "- Outputs to ship:\n"
    ),
    "init.template.quarterly_review": (
        "# Quarterly Review\n\n"
        "## Quarter\n\n"
        "- \n\n"
        "## Direction\n\n"
        "- What still matters?\n"
        "- What no longer matters?\n"
        "- What deserves more attention?\n\n"
        "## Goals\n\n"
        "- Continue:\n"
        "- Change:\n"
        "- Stop:\n\n"
        "## System Maintenance\n\n"
        "- [ ] Archive inactive projects\n"
        "- [ ] Review sensitive notes\n"
        "- [ ] Update dashboards\n"
        "- [ ] Choose next quarter outputs\n"
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
        "     chatmd service status    \u2014 check service\n"
        "     chatmd service uninstall \u2014 remove service\n"
        "   Or use services.msc to manage the service."
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
    "service.pywin32_required": (
        "\u274c pywin32 is required for Windows Service.\n"
        "   Install with: pip install pywin32"
    ),
    "service.pywin32_postinstall_required": (
        "\u26a0\ufe0f  pywin32 post-install has not been run.\n"
        "   The Windows Service will fail without it.\n"
        "   Please run (as Administrator):\n"
        "     {command}\n"
        "   Then retry: chatmd service install"
    ),
    "service.win_install_failed": (
        "\u274c Failed to install Windows Service: {error}\n"
        "   Make sure you are running as Administrator."
    ),
    "service.win_uninstall_failed": (
        "\u26a0\ufe0f Failed to uninstall Windows Service: {error}"
    ),
    "service.started": "\u2705 Service started ({platform}: {name})",
    "service.stopped": "\u2705 Service stopped ({platform}: {name})",
    "service.start_service_failed": (
        "\u274c Failed to start service: {error}\n"
        "   Hint: run `chatmd service install` first, or check permissions."
    ),
    "service.stop_service_failed": (
        "\u26a0\ufe0f Failed to stop service: {error}\n"
        "   Hint: the service may already be stopped."
    ),
    # ── doctor CLI ──────────────────────────────────────────────────────
    "doctor.header": "\U0001f50d ChatMD Doctor — workspace: {workspace}",
    "doctor.summary": (
        "Summary: {ok} ok · {warn} warning(s) · {error} error(s) · {skip} skipped"
    ),
    "doctor.fix_hint_label": "Fix:",
    "doctor.skipped_no_network": "skipped (--no-network)",
    "doctor.check_crashed": "check crashed: {error}",
    "doctor.category.environment": "Python & Dependencies",
    "doctor.category.workspace": "Workspace & Configuration",
    "doctor.category.service": "Service \u21c4 PID Consistency",
    "doctor.category.provider": "AI Provider",
    "doctor.category.git": "Git Repository",

    "service.no_services_found": "No ChatMD services found.",
    "service.all_services_header": "ChatMD services ({count}):",
    "service.status_all_hint_linux": (
        "List all ChatMD services:\n"
        "  systemctl --user list-units 'chatmd-*'"
    ),
    "service.status_all_hint_macos": (
        "List all ChatMD services:\n"
        "  launchctl list | grep com.chatmd"
    ),
    "service.uninstall_all_win_only": (
        "--all is only supported on Windows for now.\n"
        "Use platform-specific commands to manage services."
    ),

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

    # ── /la skill — destructive confirm (T-MVP03-M2) ────────────────────
    "la.confirm.card_header": "Destructive action requires confirmation",
    "la.confirm.card_hint": (
        "Type `/la confirm {token}` to execute · valid 10 min"
    ),
    "la.confirm.bad_token": (
        "Invalid token format, expected `cft_` + 32 hex chars"
    ),
    "la.confirm.not_found": "Token not found or already expired",
    "la.confirm.forbidden": "This token does not belong to your account",
    "la.confirm.consumed": "This action has already been executed",
    "la.confirm.expired": (
        "Token expired (10 min TTL), please re-issue the command"
    ),
    "la.confirm.generic": "Confirm failed: {message}",
    # ── Config command ─────────────────────────────────────────────────
    "config.no_workspace": (
        "No .chatmd/ directory found. Run `chatmd init <path>` first."
    ),
    "config.empty": "No configuration found.",
    "config.key_not_found": "Key not found: {name}",
    "config.set_success": "\u2705 Set {name} in {file}",
    "config.unknown_key": (
        "Unknown config key: {name}. "
        "Use `chatmd config list` to see available keys."
    ),
    "config.invalid_value": "Invalid value for {name}: {val}",
    "config.init.welcome": "Welcome to ChatMarkdown configuration!",
    "config.init.provider_prompt": "Select AI provider",
    "config.init.api_key_prompt": "Enter your API key (leave empty to skip)",
    "config.init.api_url_prompt": "Enter API URL",
    "config.init.language_prompt": "Select language",
    "config.init.success": "\u2705 Configuration saved.",
    "config.init.doctor_hint": "💡 Run `chatmd doctor` to verify your setup.",
}
