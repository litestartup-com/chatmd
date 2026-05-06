"""Chinese (Simplified) message catalog."""

MESSAGES: dict[str, str] = {
    # ── Skill descriptions ──────────────────────────────────────────────
    "skill.date.description": "插入今天的日期",
    "skill.time.description": "插入当前时间",
    "skill.now.description": "插入当前日期+时间",
    "skill.help.description": "显示所有可用命令",
    "skill.status.description": "显示 Agent 状态",
    "skill.list.description": "列出对话 Session",
    "skill.ask.description": "AI 对话",
    "skill.translate.description": "翻译文本",
    "skill.sync.description": "Git 同步",
    "skill.log.description": "查看审计日志",
    "skill.new.description": "归档对话并新建 Session",
    "skill.rewrite.description": "AI 改写文本",
    "skill.expand.description": "AI 扩写文本",
    "skill.polish.description": "AI 语法检查与润色",
    "skill.summary.description": "AI 摘要生成",
    "skill.tag.description": "AI 提取关键词/标签",
    "skill.title.description": "AI 推荐标题",
    "skill.canvas.description": "AI 生成思维导图 Canvas",
    "skill.upload.description": "上传本地图片到云端",
    "skill.datetime.description": "插入日期和时间",
    "skill.timestamp.description": "插入 Unix 时间戳",
    "skill.week.description": "插入当前周数",
    "skill.weekday.description": "插入星期几",
    "skill.progress.description": "插入年度进度",
    "skill.daynum.description": "插入今年第几天",
    "skill.countdown.description": "倒计时天数",
    "skill.todo.description": "插入待办项",
    "skill.done.description": "插入已完成待办项",
    "skill.table.description": "插入 Markdown 表格",
    "skill.code.description": "插入代码块",
    "skill.link.description": "插入 Markdown 链接",
    "skill.img.description": "插入 Markdown 图片",
    "skill.hr.description": "插入水平分割线",
    "skill.heading.description": "插入 Markdown 标题",
    "skill.quote.description": "插入引用块",

    # ── /help output ────────────────────────────────────────────────────
    "output.help.empty": "暂无已注册命令",
    "output.help.header": "## 可用命令\n",
    "output.help.table_header": "| 命令 | 别名 | 说明 |",
    "output.help.group.datetime": "日期时间",
    "output.help.group.ai": "AI 智能",
    "output.help.group.markdown": "Markdown 模板",
    "output.help.group.cron": "定时任务",
    "output.help.group.utility": "工具",
    "output.help.group.custom": "自定义",
    "output.help.overview_hint": (
        "使用 `/help <别名>` 查看分组详情（如 `/help dt`），"
        "`/help <命令>` 查看单个命令。"
    ),
    "output.help.group_empty": "该分组暂无命令。",
    "output.help.cmd_not_found": "未找到命令: `/{cmd}`",

    # ── /status output ──────────────────────────────────────────────────
    "output.status.running": "🟢 Agent 运行中\n",
    "output.status.workspace": "工作空间: {workspace}",
    "output.status.active_tasks": "活跃任务: {count}",
    "output.status.total_tasks": "总任务数: {count}",
    "output.status.running_tasks_header": "\n### 运行中任务\n",

    # ── /list output ────────────────────────────────────────────────────
    "output.list.empty": "暂无对话 Session",
    "output.list.header": "## 对话列表 ({count})\n",
    "output.list.default_session": "- `chat.md` (默认)",

    # ── /log output ─────────────────────────────────────────────────────
    "output.log.empty": "暂无审计记录",
    "output.log.header": "## 最近 {count} 条审计记录\n",
    "output.log.table_header": "| # | Skill | 类别 | 状态 | 错误 |",

    # ── /sync output ────────────────────────────────────────────────────
    "output.sync.not_git_repo": "当前目录不是 Git 仓库",
    "output.sync.no_changes": "没有需要同步的变更",
    "output.sync.conflict": "⚠️ Git 合并冲突，请手动解决",
    "output.sync.success": "✅ Git 同步完成",
    "output.sync.success_detail": "✅ Git 同步完成（{detail}）",
    "output.sync.pulled": "↓{count} 拉取",
    "output.sync.pushed": "↑{count} 推送",
    "output.sync.git_failed": "Git 操作失败: {error}",
    "output.sync.git_not_installed": "Git 未安装",
    "output.sync.accepted_placeholder": "> ✅ /sync accepted",

    # ── AI system prompt ───────────────────────────────────────────────
    "ai.language_name": "中文",
    "ai.system_prompt": (
        "You are a helpful assistant. "
        "Please respond in {language} unless the user explicitly "
        "requests a different language in their message."
    ),

    # ── /ask errors ─────────────────────────────────────────────────────
    "error.provider_not_configured": "AI Provider 未配置",
    "error.ask_empty_input": "请输入问题，例如: /ask 什么是ChatMD？",

    # ── /translate ──────────────────────────────────────────────────────
    "error.translate_empty_input": "请输入要翻译的文本，例如: /translate(日文) Hello World",
    "translate.default_target": "英文",
    "translate.prompt": (
        "请将以下文本翻译为{target_lang}，"
        "只返回翻译结果，"
        "不要添加解释或额外内容。\n\n{input_text}"
    ),

    # ── AI writing skills ─────────────────────────────────────────────────
    "error.rewrite_empty_input": "请输入要改写的文本，例如: /rewrite 你好世界",
    "error.expand_empty_input": "请输入要扩写的文本，例如: /expand AI很强大",
    "error.polish_empty_input": "请输入要润色的文本，例如: /polish 他去了学校",
    "error.summary_empty_input": "请输入要生成摘要的文本",
    "error.tag_empty_input": "请输入要提取标签的文本",
    "error.title_empty_input": "请输入要生成标题的文本",
    "rewrite.prompt": (
        "请改写以下文本，提升表达清晰度和可读性。"
        "保持原意不变。只返回改写后的文本，"
        "不要添加解释。\n\n{input_text}"
    ),
    "expand.prompt": (
        "请对以下文本进行扩写和展开，"
        "增加更多细节和深度，同时保持原意。"
        "只返回扩写后的文本，不要添加解释。\n\n{input_text}"
    ),
    "polish.prompt": (
        "请检查并修正以下文本中的语法、拼写和标点错误。"
        "保持原意和风格不变。"
        "只返回修正后的文本，不要添加解释。\n\n{input_text}"
    ),
    "summary.prompt": (
        "请简洁地总结以下文本，抓住要点。"
        "只返回摘要，不要添加解释。\n\n{input_text}"
    ),
    "tag.prompt": (
        "请从以下文本中提取主要关键词和标签。"
        "以逗号分隔的列表形式返回，不要添加其他内容。\n\n{input_text}"
    ),
    "title.prompt": (
        "请为以下文本推荐一个简洁且有描述性的标题。"
        "只返回标题，不要添加其他内容。\n\n{input_text}"
    ),

    # ── /canvas ───────────────────────────────────────────────────────
    "error.canvas_empty_input": "请输入要生成思维导图的文本",
    "error.canvas_empty_response": "AI 返回了空响应",
    "error.canvas_invalid_json": "AI 返回的 JSON 格式无效: {detail}",
    "error.canvas_missing_fields": "AI 返回的数据缺少 title 或 nodes 字段",
    "error.canvas_layout_failed": "Canvas 布局生成失败: {detail}",
    "error.canvas_write_failed": "Canvas 文件写入失败: {detail}",
    "output.canvas.success": (
        "✅ Canvas 已生成: `{filename}`\n"
        "📊 {nodes} 个节点, {edges} 条连线\n"
        "💡 在 Obsidian 中打开该文件即可查看思维导图"
    ),
    "canvas.system_prompt": (
        "你是一个思维导图/概念图生成专家。用户会给你一段文本内容，"
        "你需要分析文本，提取核心概念和逻辑关系，生成一个结构化的树形数据。\n\n"
        "请严格按以下 JSON 格式返回，不要添加任何其他文字:\n\n"
        '{\n'
        '  "title": "中心主题（一句话概括）",\n'
        '  "nodes": [\n'
        '    {\n'
        '      "text": "一级主题1",\n'
        '      "children": [\n'
        '        {"text": "二级细节A", "children": []}\n'
        '      ]\n'
        '    }\n'
        '  ]\n'
        '}\n\n'
        "规则：\n"
        "1. title 是对整个内容的一句话概括，作为中心节点\n"
        "2. nodes 是一级分支，每个可以有 children 子节点\n"
        "3. 最多3层深度（中心 → 一级 → 二级 → 三级）\n"
        "4. 每个节点的 text 简洁有力，不超过30字\n"
        "5. 一级节点建议3-7个，每个一级节点的子节点不超过5个\n"
        "6. 只输出 JSON，不要有任何前缀后缀文字"
    ),
    "canvas.user_prompt": (
        "请分析以下内容并生成思维导图结构：\n\n{input_text}"
    ),

    # ── T-046: week/progress output ─────────────────────────────────
    "output.week.format": "第{week}周",
    "output.weekday.names": "星期一, 星期二, 星期三, 星期四, 星期五, 星期六, 星期日",
    "output.progress.format": "{pct}% of {year}",
    "output.daynum.format": "第{day}天",
    "output.countdown.format": "距离 {target} 还有 {days} 天",
    "error.countdown_invalid_date": "日期格式无效: {date}（期望 YYYY-MM-DD）",

    # ── /upload ───────────────────────────────────────────────────────
    "error.upload_not_configured": "上传服务未配置",
    "error.upload_file_not_found": "文件未找到: {path}",
    "error.upload_failed": "{path} 上传失败: {detail}",
    "error.upload_source_not_found": "源文件不存在",
    "error.upload_read_failed": "读取文件失败: {detail}",
    "error.upload_write_failed": "写入文件失败: {detail}",
    "error.upload_unsupported_ext": "不支持的扩展名 {ext}（允许: {allowed}）",
    "error.upload_too_large": "{path} 超过大小限制（{max_mb}MB）",
    "output.upload.single_success": "✅ 已上传 `{filename}` → {url}",
    "output.upload.no_images": "文件中未发现本地图片引用",
    "output.upload.scan_summary": (
        "发现 {found} 张图片: {uploaded} 张已上传, {failed} 张失败, {skipped} 张跳过"
    ),
    "output.upload.detail_ok": "✅ {path} → {url}",
    "output.upload.detail_failed": "❌ {path}: {detail}",
    "output.upload.detail_not_found": "⚠️ {path}: 文件不存在，已跳过",
    "output.upload.detail_skipped": "⚠️ {path}: {reason}",
    "skill.upload.help_text": (
        "### 使用方式\n\n"
        "| 命令 | 说明 |\n"
        "|------|------|\n"
        "| `/upload` | 扫描当前文件中的本地图片，全部上传并替换为远程 URL |\n"
        "| `/upload <路径>` | 上传单个图片文件，返回远程 URL |\n\n"
        "### 自动上传\n\n"
        "在 `agent.yaml` 中启用 `upload.auto` 后，监控的 `.md` 文件中新增的本地图片会在保存时"
        "**自动上传**并替换为远程 URL，无需手动执行 `/upload`。\n\n"
        "### 配置（`agent.yaml` → `upload:`）\n\n"
        "```yaml\n"
        "upload:\n"
        "  auto: true          # 启用保存时自动上传\n"
        "  max_size_mb: 10     # 最大文件大小（默认 10MB）\n"
        "  extensions:         # 允许的扩展名（默认如下）\n"
        "    - jpg\n"
        "    - jpeg\n"
        "    - png\n"
        "    - gif\n"
        "    - webp\n"
        "    - svg\n"
        "    - ico\n"
        "```\n\n"
        "### 前置条件\n\n"
        "- `ai.providers` 中需配置 `litestartup` 类型的 provider\n"
        "- Provider 的 API Key 需具有上传权限\n\n"
        "### 支持的图片语法\n\n"
        "| 语法 | 示例 |\n"
        "|------|------|\n"
        "| Markdown | `![描述](./img/photo.png)` |\n"
        "| HTML | `<img src=\"./img/photo.png\" />` |\n\n"
        "远程 URL（`http://`、`https://`）会自动跳过。"
    ),

    # ── /notify skill ─────────────────────────────────────────────────
    "skill.notify.description": "发送通知",
    "error.notify_empty": "请提供通知内容",
    "error.notify_not_configured": "通知管理器未配置",
    "error.notify_disabled": "通知功能已在配置中禁用",
    "error.notify_invalid_channel": (
        "无效通道: {channels}。可用通道: {valid}"
    ),
    "output.notify.title": "ChatMD 提醒",
    "output.notify.success": "✅ 通知已发送（{channels}）：{message}",
    "skill.notify.help_text": (
        "### 用法\n\n"
        "| 命令 | 说明 |\n"
        "|------|------|\n"
        "| `/notify <消息>` | 通过所有通道发送 |\n"
        "| `/notify(email) <消息>` | 仅通过邮件发送 |\n"
        "| `/notify(bot) <消息>` | 仅通过 Bot 发送 |\n"
        "| `/notify(email,bot) <消息>` | 通过邮件 + Bot 发送 |\n\n"
        "### 配合 Cron（定时提醒）\n\n"
        "```cron\n"
        "0 18 * * * /notify 该吃晚饭了！\n"
        "0 9 * * 1 /notify(bot) 周会还有 15 分钟\n"
        "```\n\n"
        "### 通知通道\n\n"
        "| 通道 | 短名称 | 说明 |\n"
        "|------|--------|------|\n"
        "| **FileChannel** | `file` | 追加写入 `notification.md`（始终启用） |\n"
        "| **SystemChannel** | `system` | 桌面弹窗（Windows/macOS/Linux） |\n"
        "| **EmailChannel** | `email` | 通过 LiteStartup API 发送邮件 |\n"
        "| **BotNotificationChannel** | `bot` | 推送到 Telegram/飞书 Bot |\n\n"
        "### 配置（`agent.yaml` → `notification:`）\n\n"
        "```yaml\n"
        "notification:\n"
        "  enabled: true\n"
        "  system_notify: true     # 桌面弹窗\n"
        "  email:\n"
        "    enabled: true\n"
        "    from: support@chatmarkdown.org\n"
        "    from_name: ChatMarkdown\n"
        "    to: user@example.com\n"
        "```\n\n"
        "### 前置条件\n\n"
        "- `notification.enabled: true`\n"
        "- 邮件通知：需要配置 `litestartup` provider 并具有 `notification` 权限\n"
        "- 桌面通知：需要操作系统支持"
    ),

    # ── /inbox skill ───────────────────────────────────────────────────────
    "skill.inbox.description": "查看今日收件箱摘要",
    "error.inbox_invalid_date": "日期格式无效: {date}（期望 YYYY-MM-DD）",
    "output.inbox.empty": "{date} 无收件箱消息",
    "output.inbox.header": "## 收件箱 {date}（{count} 条消息）\n",
    "output.inbox.table_header": "| 时间 | 预览 |",
    "output.inbox.summary": "共 {count} 条消息，{first} — {last}",
    "skill.inbox.help_text": (
        "### 用法\n\n"
        "| 命令 | 说明 |\n"
        "|------|------|\n"
        "| `/inbox` | 查看今日收件箱摘要 |\n"
        "| `/inbox YYYY-MM-DD` | 查看指定日期的收件箱 |\n\n"
        "### 显示内容\n\n"
        "- 消息数量和时间范围\n"
        "- 每条消息的时间和首行预览\n\n"
        "### 工作原理\n\n"
        "读取 `chatmd/inbox/YYYY-MM-DD.md` 文件（由 Telegram Bot 写入）。\n"
        "请先执行 `/sync` 拉取远程仓库的最新消息。"
    ),

    # ── /bind skill ────────────────────────────────────────────────────────
    "skill.bind.description": "绑定 Git 仓库到 Telegram Bot",
    "error.bind_no_provider": "LiteStartup provider 未配置，请检查 agent.yaml 中的 ai.providers",
    "error.bind_missing_token": "请提供 Git 平台的 Access Token。",
    "error.bind_no_remote": "当前工作空间未检测到 git remote origin，请确认这是一个 Git 仓库",
    "error.bind_invalid_repo": "仓库地址格式不合法",
    "error.bind_invalid_platform": "不支持的平台（当前仅支持 Telegram）",
    "error.bind_already_active": "你已有活跃的绑定，如需重新绑定请先解绑",
    "error.bind_unauthorized": "认证失败，请检查 agent.yaml 中的 API Key",
    "error.bind_rate_limited": "请求过于频繁，请等待几分钟后重试",
    "error.bind_unknown": "绑定失败（未知错误）[code={code}] raw={raw}",
    "error.bind_server_error": "绑定 API 不可用: {detail}",
    "output.bind.title": "🔗 Bot 绑定",
    "output.bind.detected_repo": "检测到仓库: `{repo_url}`",
    "output.bind.platform_detected": "平台: **{platform}**",
    "output.bind.token_help_link": "📖 如何创建 Token: {url}",
    "output.bind.usage_hint": "用法: `/bind <你的access_token>`",
    "output.bind.repo_line": "仓库: `{repo_url}`",
    "output.bind.platform_line": "平台: **{platform}**",
    "output.bind.code_line": "绑定码: **{code}**（{minutes} 分钟有效）",
    "output.bind.bot_link": "打开 Telegram Bot: [{name}]({link})",
    "output.bind.bot_name": "Telegram Bot: {name}",
    "output.bind.waiting": "⏳ 请在 Telegram Bot 中发送绑定码完成关联。",
    "output.bind.already_active": "⚠️ 你已有活跃的绑定：",
    "output.bind.current_binding": (
        "- 平台: **{platform}**\n"
        "- 仓库: `{repo}`\n"
        "- 绑定时间: {bound_at}"
    ),
    "skill.bind.help_text": (
        "### 用法\n\n"
        "```\n"
        "/bind <git_access_token>\n"
        "```\n\n"
        "将 Git 笔记仓库绑定到 Telegram Bot，实现手机端发送语音/文本/图片，"
        "自动同步到笔记仓库。\n\n"
        "### 工作原理\n\n"
        "1. chatmd 自动读取 `git remote origin` 获取仓库地址\n"
        "2. 调用 LiteStartup API 获取 6 位绑定码\n"
        "3. 你在 Telegram Bot 中发送绑定码\n"
        "4. 绑定完成！Bot 消息 → `inbox/` → git sync → 笔记\n\n"
        "### 获取 Token\n\n"
        "| 平台 | Token 类型 | 创建地址 |\n"
        "|------|-----------|----------|\n"
        "| GitHub | Fine-grained PAT | https://github.com/settings/tokens?type=beta |\n"
        "| GitLab | Personal Access Token |"
        " https://gitlab.com/-/user_settings/personal_access_tokens |\n"
        "| Gitee | 私人令牌 | https://gitee.com/profile/personal_access_tokens |\n\n"
        "**所需权限**：仅需仓库读写权限，不要授予过多权限。\n\n"
        "### 示例\n\n"
        "```\n"
        "/bind ghp_xxxxxxxxxxxxxxxxxxxx\n"
        "```"
    ),

    # ── /bind status 子命令 (T-R083 / T-126) ──────────────────────────────
    "output.bind.list_header": "📋 已绑定仓库（{count} 个）",
    "output.bind.list_row": "{marker} `{alias}` — `{url}`",
    "output.bind.list_empty": (
        "📋 当前还没有 Bot 绑定。\n\n"
        "运行 `/bind <你的access_token>` 创建一个。"
    ),
    "output.bind.list_footer": "图例：✅ 当前活跃 · ▶ 当前工作空间 · · 其它",
    "output.bind.list_unnamed_alias": "（未命名）",
    "error.bind_list_failed": "获取绑定列表失败：{detail}",

    # ── /unbind 命令 (T-R083 / T-126) ─────────────────────────────────────
    "skill.unbind.description": "移除 Telegram Bot 仓库绑定",
    "skill.unbind.help_text": (
        "### 用法\n\n"
        "| 命令 | 说明 |\n"
        "|------|------|\n"
        "| `/unbind` | 移除**当前**工作空间对应的绑定 |\n"
        "| `/unbind <alias>` | 按 alias 移除指定绑定 |\n"
        "| `/unbind --all` | 清空当前账号的所有绑定 |\n\n"
        "### 工作原理\n\n"
        "无参形式会自动用 `git remote origin` 与服务端绑定列表匹配，"
        "找出当前 workspace 对应的 alias —— 你不用记 alias 也能解绑当前仓库。\n\n"
        "如果解除的是活跃绑定，服务端会自动把下一个绑定提升为新的活跃，"
        "并在结果中告诉你新活跃 alias，方便你在 Telegram 里继续用 `/use`。\n\n"
        "在解绑前可先用 `/bind status` 查看所有绑定。"
    ),
    "output.unbind.success": (
        "🗑️ 已解绑 `{alias}`，剩余 {remaining} 个绑定。"
    ),
    "output.unbind.new_active": "✅ 新的活跃绑定：`{alias}`",
    "output.unbind.all_success": (
        "🗑️ 已清空 {count} 个绑定：{aliases}"
    ),
    "output.unbind.all_empty": (
        "📋 没有需要清理的绑定。"
    ),
    "error.unbind_alias_not_found": (
        "找不到 alias `{alias}`。可运行 `/bind status` 查看可用绑定。"
    ),
    "error.unbind_alias_not_found_generic": (
        "找不到该 alias。可运行 `/bind status` 查看可用绑定。"
    ),
    "error.unbind_no_workspace_match": (
        "未找到匹配当前工作空间仓库的绑定（`{url}`）。\n\n"
        "请先运行 `/bind status` 查看已有绑定，"
        "再用 `/unbind <alias>` 指定移除。"
    ),
    "error.unbind_no_addressable_alias": (
        "找到了匹配的绑定，但它没有可寻址的 alias。\n\n"
        "请运行 `/bind status` 查看，并用 `/unbind --all` 清空全部，"
        "或升级 LiteStartup 服务端（T-125）。"
    ),
    "error.unbind_failed": "解绑失败：{detail}",

    # ── /confirm skill ─────────────────────────────────────────────────────
    "skill.confirm.description": "执行待确认的命令",
    "skill.confirm.help_text": (
        "### 用法\n\n"
        "| 命令 | 说明 |\n"
        "|------|------|\n"
        "| `/confirm` | 执行最近一条待确认命令 |\n"
        "| `/confirm #confirm-3` | 执行指定 ID 的待确认命令 |\n"
        "| `/confirm list` | 列出所有待确认命令 |\n\n"
        "### 工作原理\n\n"
        "在 `trigger.confirm.commands` 中列出的命令需要显式确认才会执行。\n"
        "输入这类命令时，会显示确认提示而不是直接执行。\n"
        "输入 `/confirm` 确认执行，或删除提示行取消。\n\n"
        "### 配置（`agent.yaml` → `trigger.confirm:`）\n\n"
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

    # ── /new session ───────────────────────────────────────────────────
    "error.new_no_chat_md": "chat.md 不存在",
    "error.new_empty_content": "无内容可归档",
    "output.new.success": "✅ 已归档至 chat/{archive}，新会话已开始",
    "new.fallback_topic": "通用对话",
    "new.datetime_format": "%Y年%m月%d日 %H:%M:%S",
    "new.session_timestamp": (
        "{datetime} {weekday} | 第{week}周 第{day}天 ({pct}% of {year})"
    ),

    # ── /cron skill ──────────────────────────────────────────────────────
    "skill.cron.description": "管理 cron 定时任务",
    "error.cron_not_configured": "Cron 调度器未配置",
    "error.cron_unknown_subcommand": "未知子命令: {subcmd}",
    "output.cron.list_empty": "暂无已注册的 cron 任务 (0 个)",
    "output.cron.list_header": "**Cron 任务** (已注册 {count} 个)\n",
    "output.cron.status_summary": (
        "**Cron 状态** — {total} 个任务"
        " ({active} 活跃, {paused} 暂停)"
        " | 共执行 {runs} 次, 失败 {fails} 次"
    ),
    "output.cron.next_header": "**即将执行** (未来 {count} 次)\n",
    "output.cron.paused": "任务 `{job_id}` 已暂停",
    "output.cron.resumed": "任务 `{job_id}` 已恢复",
    "output.cron.run_triggered": "任务 `{job_id}` 已手动触发",
    "output.cron.test_complete": "[测试] 任务 `{job_id}` 已执行",
    "output.cron.validate_header": "**Cron 语法校验** (共 {count} 个任务)\n",
    "output.cron.history_empty": "暂无执行历史",
    "output.cron.history_header": "**执行历史** (共 {count} 条记录)\n",
    "error.cron_missing_id": "需要指定任务 ID",
    "error.cron_job_not_found": "未找到任务: {job_id}",
    "error.cron_add_usage": "用法: /cron add <表达式> <命令>",
    "error.cron_dangerous_command": "危险命令不允许在 cron 中使用: {command}",
    "error.cron_no_file": "Cron 文件未配置",
    "output.cron.added": "已添加 cron 任务: `{expr}` → `{command}`",
    "output.cron.removed": "任务 `{job_id}` 已移除",
    "skill.cron.help_text": (
        "### 子命令\n\n"
        "| 命令 | 说明 |\n"
        "|------|------|\n"
        "| `/cron` | 列出所有已注册任务及下次执行时间 |\n"
        "| `/cron status` | 概览（含执行/失败统计） |\n"
        "| `/cron next [N]` | 预览未来 N 次执行（默认 5） |\n"
        "| `/cron pause <ID>` | 暂停指定任务 |\n"
        "| `/cron resume <ID>` | 恢复暂停的任务 |\n"
        "| `/cron run <ID>` | 手动触发一次 |\n"
        "| `/cron test <ID>` | 测试执行（标记 `[TEST]`） |\n"
        "| `/cron validate` | 语法校验所有 cron 代码块 |\n"
        "| `/cron history [ID]` | 最近 20 条执行记录 |\n"
        "| `/cron add <表达式> <命令>` | 添加任务到 cron.md |\n"
        "| `/cron remove <ID>` | 注释掉 cron.md 中的任务 |\n\n"
        "### 配置（`agent.yaml` → `cron:`）\n\n"
        "| 配置项 | 默认值 | 说明 |\n"
        "|--------|--------|------|\n"
        "| `enabled` | `false` | 启用 cron 引擎 |\n"
        "| `cron_file` | `cron.md` | 定时任务定义文件 |\n"
        "| `job_timeout` | `300` | 单个任务最长执行秒数 |\n"
        "| `max_failures` | `5` | 连续失败 N 次后自动暂停 |\n"
        "| `missed_policy` | `run` | 启动时对错过的任务：`run` 补跑 / `skip` 跳过 |\n"
        "| `tick_interval` | 自动 | 调度器轮询间隔（自动调优） |\n"
        "| `max_history` | `20` | 每个任务保留的执行记录数 |\n\n"
        "### 安全机制\n\n"
        "危险命令（`upload`、`new`、`upgrade`）禁止在 cron 中使用。\n"
        "连续失败 ≥ `max_failures` 次的任务会自动暂停并发送通知。"
    ),

    # ── /sync skill errors ──────────────────────────────────────────────
    "error.sync_not_configured": "Git 同步未配置",

    # ── /log skill errors ───────────────────────────────────────────────
    "error.audit_not_configured": "审计模块未配置",

    # ── AI provider errors (RuntimeError — always English per D3) ──────
    "error.api_timeout": "AI API 请求超时 ({timeout}s)",
    "error.api_key_invalid": "API Key 无效，请检查配置",
    "error.api_rate_limit": "请求频率过高，请稍后重试",
    "error.api_http_error": "AI API 错误 (HTTP {status})",
    "error.api_network": "网络错误: {detail}",

    # ── AI conversation labels ────────────────────────────────────────
    "output.ai.you_label": "**You:**",
    "output.ai.ai_label": "**AI:**",

    # ── Agent runtime output (written to chat.md) ──────────────────────
    "agent.command_failed": "❌ 命令执行失败: {error}",
    "agent.unknown_error": "未知错误",
    "agent.network_placeholder": "⏳ {description}...",
    "agent.async_placeholder": "⏳ {description}中... `#{task_id}`",
    "agent.async_done": "✅ 完成",
    "agent.async_failed_retry": "❌ {error}\n> 输入 `/retry #{task_id}` 重试",

    # ── Confirmation window ─────────────────────────────────────────────
    "confirm.prompt": (
        "> ⚠️ `{command}` 需要确认 — "
        "输入 `/confirm` 执行，删除本行取消"
        " `#{confirm_id}`"
    ),
    "confirm.confirmed": "✅ 已确认并执行：`{command}`",
    "confirm.accepted_placeholder": "✅ 已确认",
    "confirm.cancelled": "❌ 已取消：`{command}`",
    "confirm.nothing_pending": "没有待确认的命令。",
    "confirm.list_header": "待确认命令：",
    "confirm.list_item": "  {confirm_id}: `{command}`",

    # ── Index manager ───────────────────────────────────────────────────
    "index.header_note": "> 此文件由 ChatMD Agent 自动维护，请勿手动编辑。",
    "index.table_header": "| 文件 | 创建时间 | 大小 |",

    # ── init workspace ──────────────────────────────────────────────────
    "init.welcome_title": "# ChatMD",
    "init.welcome_subtitle": "欢迎使用 ChatMD — 你的本地 AI Agent 🚀",
    "init.welcome_quickstart_header": "## 快速上手",
    "init.welcome_commands_intro": "可用命令示例：",
    "init.welcome_help": "/help    — 查看所有可用命令",
    "init.welcome_date": "/date    — 插入今天的日期",
    "init.welcome_ask": "/ask     — AI 对话",
    "init.welcome_status": "/status  — 显示 Agent 状态",
    "init.welcome_instruction": "在下方 `---` 分隔线之后输入命令，保存文件即可执行。",
    "init.workspace_created": "✅ 工作空间已创建: {workspace}",
    "init.run_start": "运行 chatmd start 启动 Agent",
    "init.open_chat": "用任何编辑器打开 chat.md 开始交互",
    "init.notification_title": "通知中心",
    "init.notification_subtitle": (
        "ChatMarkdown 通知收件箱"
        " — Agent 会自动追加通知，你可以在这里直接回应。"
    ),
    "init.interaction.readme": (
        "# ChatMD 交互目录\n\n"
        "本目录是你与 ChatMD Agent 共同使用的协作空间，包含命令、Agent 结果、通知和会话文件。\n\n"
        "## 访问边界\n\n"
        "- 你本人可以阅读和编辑这里的文件。\n"
        "- ChatMD Agent 可以在执行你的命令时读取和更新这里的文件。\n"
        "- 第三方工具、机器人、插件、脚本或服务默认不得进入、扫描、改写、整理或删除本目录文件。\n"
        "- 如第三方工具确需访问或修改，必须先询问你，并在你明确确认后才可以执行。\n\n"
        "## 安全使用\n\n"
        "- 在 `chat.md` 中输入命令。\n"
        "- 让自动化改动保持可见、可回滚。\n"
        "- 发现异常修改时，先检查再继续使用。\n"
    ),
    "init.profile.readme": (
        "# 个人工作区\n\n"
        "这个工作区围绕五个简单动作设计：\n\n"
        "1. 捕获 — 把原始输入先放进 `C-Inbox/`。\n"
        "2. 澄清 — 把有用内容转成笔记、项目或行动。\n"
        "3. 连接 — 把笔记关联到项目、资源和决策。\n"
        "4. 复盘 — 用每日和每周复盘保持系统清洁。\n"
        "5. 输出 — 把知识转成报告、计划、文章或决策。\n\n"
        "## 从这里开始\n\n"
        "- 今日入口：`B-Dashboard/Today.md`\n"
        "- 与 Agent 交互：`A-ChatMD/chat.md`\n"
        "- 捕获收件箱：`C-Inbox/`\n"
        "- 活跃项目：`E-Projects/01-Active/`\n"
        "- 可复用模板：`L-Resources/01-Templates/`\n\n"
        "## 每周例行维护\n\n"
        "- 清空 inbox。\n"
        "- 更新活跃项目。\n"
        "- 回顾每日笔记。\n"
        "- 归档过期内容。\n"
        "- 为下周选择一到三个输出。\n"
    ),
    "init.profile.inbox_readme": (
        "# Inbox\n\n"
        "这里是临时捕获区，用来存放原始想法、链接、消息、文件、语音转写和 Agent 输出。\n\n"
        "## 规则\n\n"
        "- 先快速捕获，之后再整理。\n"
        "- 至少每周回顾一次。\n"
        "- 把有用内容移动到项目、笔记、资源或每日记录。\n"
        "- 删除或归档噪音。\n"
        "- 不要让 inbox 变成永久仓库。\n"
    ),
    "init.profile.projects_readme": (
        "# Projects\n\n"
        "项目用于管理需要多个步骤才能完成的结果。\n\n"
        "## 结构\n\n"
        "- `01-Active/` — 正在推进的项目。\n"
        "- `02-Someday/` — 以后可能会做的项目想法。\n\n"
        "## 项目健康检查\n\n"
        "- 结果是否清晰？\n"
        "- 是否有下一步行动？\n"
        "- 决策和资源是否已关联？\n"
        "- 这个项目应该继续、暂停，还是归档？\n"
    ),
    "init.profile.notes_readme": (
        "# Notes\n\n"
        "笔记用于沉淀可复用知识，而不是临时任务。\n\n"
        "## 笔记放在哪里\n\n"
        "- `01-Ideas/` — 概念、问题和早期想法。\n"
        "- `02-Books/` — 阅读笔记和书籍摘要。\n"
        "- `03-Meetings/` — 会议记录和后续事项。\n"
        "- `04-Learnings/` — 经验、教程和学习笔记。\n\n"
        "## 好笔记模式\n\n"
        "- 一句话摘要。\n"
        "- 关键要点。\n"
        "- 关联项目或来源。\n"
        "- 下一次可能怎么用。\n"
    ),
    "init.profile.archive_readme": (
        "# Archive\n\n"
        "归档区用于存放已完成、不活跃或仅作参考的材料。\n\n"
        "## 什么时候归档\n\n"
        "- 项目已经完成。\n"
        "- 笔记当前不活跃，但以后可能有用。\n"
        "- 资源需要保留，但不应出现在日常工作流中。\n\n"
        "归档不是垃圾桶。没有未来价值的内容应该删除。\n"
    ),
    "init.profile.people_readme": (
        "# People\n\n"
        "这里用于记录关系上下文和后续跟进记忆。\n\n"
        "## 隐私\n\n"
        "人物笔记可能包含敏感信息。除非你明确选择，"
        "否则不要把它们分享给 AI 工具、同步服务或第三方系统。\n\n"
        "## 有用字段\n\n"
        "- 对方是谁。\n"
        "- 对方关心什么。\n"
        "- 上次互动。\n"
        "- 下一次触达。\n"
    ),
    "init.profile.goals_readme": (
        "# Goals\n\n"
        "目标用于管理长期结果；项目用于具体执行。\n\n"
        "## 复盘问题\n\n"
        "- 这个目标为什么重要？\n"
        "- 什么才算可衡量的进展？\n"
        "- 哪些活跃项目正在支持它？\n"
        "- 这个目标应该继续、调整，还是停止？\n"
    ),
    "init.profile.habits_readme": (
        "# Habits\n\n"
        "习惯用于管理可重复行为。追踪要尽量轻量。\n\n"
        "## 规则\n\n"
        "- 定义最小可执行版本。\n"
        "- 只追踪能帮助你调整行为的信息。\n"
        "- 复盘阻力，而不是责备自己。\n"
        "- 不再重要的习惯就停止追踪。\n"
    ),
    "init.profile.health_readme": (
        "# Health\n\n"
        "这里用于记录私人的健康和精力状态。\n\n"
        "## 隐私\n\n"
        "健康笔记默认是敏感信息。除非你明确选择，"
        "否则不要把它们分享给 AI 工具、同步服务或第三方系统。\n\n"
        "## 提醒\n\n"
        "本工作区只用于自我观察和反思，不构成医疗建议。\n"
    ),
    "init.profile.dashboard_home": (
        "# 首页\n\n"
        "把这里当作轻量工作台。内容要足够短，最好一分钟内可以看完。\n\n"
        "## 从这里开始\n\n"
        "- 今天：`Today.md`\n"
        "- 知识地图：`Knowledge-Map.md`\n"
        "- 与 Agent 交互：`../A-ChatMD/chat.md`\n"
        "- Inbox：`../C-Inbox/`\n"
        "- 活跃项目：`../E-Projects/01-Active/`\n"
        "- 模板：`../L-Resources/01-Templates/`\n\n"
        "## 本周重点\n\n"
        "| 优先级 | 为什么重要 | 下一步 | 链接 |\n"
        "|--------|------------|--------|------|\n"
        "|        |            |        |      |\n"
        "|        |            |        |      |\n"
        "|        |            |        |      |\n\n"
        "## 活跃领域\n\n"
        "- 工作：\n"
        "- 学习：\n"
        "- 生活：\n"
        "- 健康 / 精力：\n\n"
        "## 每周维护\n\n"
        "- [ ] 处理 inbox\n"
        "- [ ] 回顾活跃项目\n"
        "- [ ] 更新 `Knowledge-Map.md`\n"
        "- [ ] 归档已完成或过期内容\n"
        "- [ ] 选择一个要完成的输出\n"
    ),
    "init.profile.dashboard_today": (
        "# 今天\n\n"
        "## 一件事\n\n"
        "- 如果今天过得不错，应该完成什么？\n\n"
        "## 今日前三项\n\n"
        "- [ ] \n"
        "- [ ] \n"
        "- [ ] \n\n"
        "## 时间块\n\n"
        "| 时间 | 计划 | 备注 |\n"
        "|------|------|------|\n"
        "|      |      |      |\n"
        "|      |      |      |\n\n"
        "## Inbox 处理\n\n"
        "- [ ] 捕获新输入\n"
        "- [ ] 把有用内容移动到项目或笔记\n"
        "- [ ] 删除或归档噪音\n\n"
        "## 工作记录\n\n"
        "- \n\n"
        "## 日终复盘\n\n"
        "- 已完成：\n"
        "- 被阻碍：\n"
        "- 明天：\n"
    ),
    "init.profile.knowledge_map": (
        "# 知识地图\n\n"
        "这是手动维护的重要知识资产全景图。它不是自动索引，也不是 AI 全局搜索页面。\n\n"
        "## 当前焦点\n\n"
        "| 焦点 | 说明 | 相关项目 / 笔记 | 状态 |\n"
        "|------|------|-----------------|------|\n"
        "|      |      |                 |      |\n"
        "|      |      |                 |      |\n"
        "|      |      |                 |      |\n\n"
        "## 知识领域\n\n"
        "| 领域 | 为什么重要 | 核心笔记 | 活跃项目 | 复盘周期 |\n"
        "|------|------------|----------|----------|----------|\n"
        "| 工作 / 职业 | | | | 每周 |\n"
        "| 学习 | | | | 每周 |\n"
        "| 个人系统 | | | | 每月 |\n"
        "| 健康 / 精力 | | | | 每周 |\n\n"
        "## 核心笔记\n\n"
        "| 笔记 | 核心观点 | 相关领域 | 上次复盘 |\n"
        "|------|----------|----------|----------|\n"
        "|      |          |          |          |\n"
        "|      |          |          |          |\n\n"
        "## 活跃项目地图\n\n"
        "| 项目 | 目标结果 | 相关笔记 | 相关决策 | 下次复盘 |\n"
        "|------|----------|----------|----------|----------|\n"
        "|      |          |          |          |          |\n"
        "|      |          |          |          |          |\n\n"
        "## 开放问题\n\n"
        "这些是手动维护的思考锚点，不是搜索提示词。\n\n"
        "| 问题 | 领域 | 当前最好答案 | 相关笔记 |\n"
        "|------|------|--------------|----------|\n"
        "|      |      |              |          |\n"
        "|      |      |              |          |\n\n"
        "## 决策与输出索引\n\n"
        "| 条目 | 类型 | 来源 / 背景 | 下一步 | 链接 |\n"
        "|------|------|-------------|--------|------|\n"
        "|      | 决策 / 输出 | | | |\n"
        "|      | 决策 / 输出 | | | |\n\n"
        "## 维护队列\n\n"
        "- [ ] 需要补摘要的笔记：\n"
        "- [ ] 需要明确下一步行动的项目：\n"
        "- [ ] 需要复查的决策：\n"
        "- [ ] 应该完成的输出：\n"
        "- [ ] 应该归档的内容：\n"
    ),
    "init.template.daily": (
        "# 每日笔记\n\n"
        "## 计划\n\n"
        "- 主要结果：\n"
        "- 今日前三项：\n"
        "  - [ ] \n"
        "  - [ ] \n"
        "  - [ ] \n\n"
        "## 捕获\n\n"
        "- \n\n"
        "## 决策 / 变化\n\n"
        "- \n\n"
        "## 学到的东西\n\n"
        "- \n\n"
        "## 复盘\n\n"
        "- 什么有效？\n"
        "- 什么无效？\n"
        "- 明天应该调整什么？\n"
    ),
    "init.template.note": (
        "# 笔记\n\n"
        "## 摘要\n\n"
        "一句话摘要：\n\n"
        "## 关键要点\n\n"
        "- \n"
        "- \n"
        "- \n\n"
        "## 为什么重要\n\n"
        "- \n\n"
        "## 链接\n\n"
        "- 相关项目：\n"
        "- 相关笔记：\n"
        "- 来源：\n\n"
        "## 下一次用途\n\n"
        "- [ ] 用到项目中\n"
        "- [ ] 转化为输出\n"
        "- [ ] 之后复习\n"
    ),
    "init.template.project": (
        "# 项目\n\n"
        "## 结果\n\n"
        "什么才算完成？\n\n"
        "## 原因\n\n"
        "这个项目为什么重要？\n\n"
        "## 状态\n\n"
        "- 状态：active / paused / done\n"
        "- 负责人：\n"
        "- 截止时间：\n\n"
        "## 下一步行动\n\n"
        "- [ ] \n"
        "- [ ] \n"
        "- [ ] \n\n"
        "## 资源\n\n"
        "- \n\n"
        "## 决策\n\n"
        "- \n\n"
        "## 复盘\n\n"
        "- 进展：\n"
        "- 风险：\n"
        "- 下一步：\n"
    ),
    "init.template.meeting": (
        "# 会议\n\n"
        "## 背景\n\n"
        "- 主题：\n"
        "- 日期：\n"
        "- 参与者：\n\n"
        "## 记录\n\n"
        "- \n\n"
        "## 决策\n\n"
        "- \n\n"
        "## 行动项\n\n"
        "- [ ] 负责人 — 行动 — 截止时间\n\n"
        "## 后续\n\n"
        "- 什么需要澄清？\n"
        "- 什么需要发送或沉淀？\n"
    ),
    "init.template.decision": (
        "# 决策\n\n"
        "## 背景\n\n"
        "我们要解决什么问题？\n\n"
        "## 选项\n\n"
        "1. \n"
        "2. \n"
        "3. \n\n"
        "## 标准\n\n"
        "- \n"
        "- \n"
        "- \n\n"
        "## 决定\n\n"
        "选择的方案：\n\n"
        "## 原因\n\n"
        "为什么选择它？\n\n"
        "## 影响\n\n"
        "- 好处：\n"
        "- 风险：\n"
        "- 复查日期：\n"
    ),
    "init.template.weekly_review": (
        "# 周复盘\n\n"
        "## 亮点\n\n"
        "- \n\n"
        "## 已完成\n\n"
        "- \n\n"
        "## 仍未完成\n\n"
        "- \n\n"
        "## 经验\n\n"
        "- \n\n"
        "## Inbox 清理\n\n"
        "- [ ] Inbox 已处理\n"
        "- [ ] 项目已更新\n"
        "- [ ] 笔记已关联\n"
        "- [ ] 归档已更新\n\n"
        "## 下周\n\n"
        "- 主要结果：\n"
        "- 重点项目：\n"
        "- 要产出的内容：\n"
    ),
    "init.template.report": (
        "# 报告\n\n"
        "## 目的\n\n"
        "这份报告给谁看？为什么需要？\n\n"
        "## 摘要\n\n"
        "- \n\n"
        "## 发现\n\n"
        "- \n"
        "- \n"
        "- \n\n"
        "## 建议\n\n"
        "- \n\n"
        "## 证据 / 链接\n\n"
        "- \n\n"
        "## 下一步行动\n\n"
        "- [ ] \n"
    ),
    "init.template.output": (
        "# 输出\n\n"
        "## 受众\n\n"
        "- 谁会使用这个输出？\n\n"
        "## 目标\n\n"
        "- 这个输出要帮助对方完成什么？\n\n"
        "## 草稿\n\n"
        "- \n\n"
        "## 来源笔记\n\n"
        "- \n\n"
        "## 发布 / 分享清单\n\n"
        "- [ ] 标题清晰\n"
        "- [ ] 关键信息明显\n"
        "- [ ] 证据已链接\n"
        "- [ ] 下一步行动明确\n"
    ),
    "init.template.person": (
        "# 人物\n\n"
        "## 资料\n\n"
        "- 姓名：\n"
        "- 角色：\n"
        "- 场景：\n"
        "- 联系方式：\n\n"
        "## 关系\n\n"
        "- 我们如何认识：\n"
        "- 对方关心什么：\n"
        "- 我可以如何帮助：\n\n"
        "## 互动记录\n\n"
        "| 日期 | 主题 | 后续 |\n"
        "|------|------|------|\n"
        "|      |      |      |\n\n"
        "## 下一次触达\n\n"
        "- [ ] \n\n"
        "## 记录\n\n"
        "- \n\n"
        "## 隐私\n\n"
        "- 敏感级别：normal / sensitive\n"
        "- 是否可进入 AI 上下文：yes / no\n"
    ),
    "init.template.goal": (
        "# 目标\n\n"
        "## 结果\n\n"
        "我想要什么结果？\n\n"
        "## 原因\n\n"
        "这件事为什么重要？\n\n"
        "## 时间范围\n\n"
        "- 开始：\n"
        "- 目标日期：\n"
        "- 复盘周期：\n\n"
        "## 衡量方式\n\n"
        "- 领先指标：\n"
        "- 滞后指标：\n\n"
        "## 里程碑\n\n"
        "- [ ] \n"
        "- [ ] \n"
        "- [ ] \n\n"
        "## 障碍\n\n"
        "- \n\n"
        "## 当前项目\n\n"
        "- \n\n"
        "## 复盘\n\n"
        "- 进展：\n"
        "- 有效做法：\n"
        "- 需要调整：\n"
    ),
    "init.template.habit": (
        "# 习惯\n\n"
        "## 意图\n\n"
        "我想重复什么行为？\n\n"
        "## 触发器\n\n"
        "它在什么时候、什么场景开始？\n\n"
        "## 最小版本\n\n"
        "最小可接受版本是什么？\n\n"
        "## 追踪\n\n"
        "| 日期 | 完成 | 备注 |\n"
        "|------|------|------|\n"
        "|      |      |      |\n\n"
        "## 反思\n\n"
        "- 什么让它更容易？\n"
        "- 什么让它更困难？\n"
        "- 这个习惯应该保持、调整，还是停止？\n"
    ),
    "init.template.health_log": (
        "# 健康记录\n\n"
        "## 日期\n\n"
        "## 精力\n\n"
        "- 睡眠：\n"
        "- 精力：\n"
        "- 情绪：\n"
        "- 压力：\n"
        "- 运动：\n\n"
        "## 记录\n\n"
        "- \n\n"
        "## 信号\n\n"
        "- 什么变好了？\n"
        "- 什么变差了？\n"
        "- 可能原因是什么？\n\n"
        "## 调整\n\n"
        "- [ ] 明天做一个小调整\n\n"
        "## 隐私\n\n"
        "这条记录可能包含敏感信息。除非明确需要，否则不要分享。\n"
    ),
    "init.template.life_review": (
        "# 人生复盘\n\n"
        "## 周期\n\n"
        "- 周 / 月 / 季度：\n\n"
        "## 精力\n\n"
        "- 什么给了我能量？\n"
        "- 什么消耗了我的能量？\n\n"
        "## 关系\n\n"
        "- 我应该重新联系谁？\n"
        "- 谁需要更多关注？\n\n"
        "## 目标\n\n"
        "- 什么推进了？\n"
        "- 什么已经不重要了？\n\n"
        "## 习惯\n\n"
        "- 什么保持稳定？\n"
        "- 什么需要调整？\n\n"
        "## 决策\n\n"
        "- 有哪些决策需要复查？\n\n"
        "## 下个周期\n\n"
        "- 主要焦点：\n"
        "- 停止一件事：\n"
        "- 开始一件事：\n"
    ),
    "init.template.identity": (
        "# 身份笔记\n\n"
        "## 当前版本\n\n"
        "我正在成为什么样的人？\n\n"
        "## 原则\n\n"
        "- \n"
        "- \n"
        "- \n\n"
        "## 优势\n\n"
        "- \n\n"
        "## 模式\n\n"
        "- 有帮助的模式：\n"
        "- 有伤害的模式：\n\n"
        "## 证据\n\n"
        "- 最近哪些行动支持这个身份？\n"
        "- 最近哪些行动与这个身份冲突？\n\n"
        "## 更新\n\n"
        "我的行动方式应该改变什么？\n"
    ),
    "init.template.monthly_review": (
        "# 月复盘\n\n"
        "## 月份\n\n"
        "- \n\n"
        "## 结果\n\n"
        "- 我完成了什么？\n"
        "- 什么发生了变化？\n"
        "- 什么应该归档？\n\n"
        "## 知识\n\n"
        "- 最好的笔记：\n"
        "- 可复用资源：\n"
        "- 未解决问题：\n\n"
        "## 下个月\n\n"
        "- 主要焦点：\n"
        "- 继续推进的项目：\n"
        "- 要交付的输出：\n"
    ),
    "init.template.quarterly_review": (
        "# 季度复盘\n\n"
        "## 季度\n\n"
        "- \n\n"
        "## 方向\n\n"
        "- 什么仍然重要？\n"
        "- 什么已经不重要？\n"
        "- 什么值得更多关注？\n\n"
        "## 目标\n\n"
        "- 继续：\n"
        "- 调整：\n"
        "- 停止：\n\n"
        "## 系统维护\n\n"
        "- [ ] 归档不活跃项目\n"
        "- [ ] 回顾敏感笔记\n"
        "- [ ] 更新 Dashboard\n"
        "- [ ] 选择下季度输出\n"
    ),
    "init.git_not_installed": "⚠️ Git 未安装，跳过 Git 初始化",
    "init.git_failed": "⚠️ Git 初始化失败: {error}",

    # ── agent lifecycle CLI ─────────────────────────────────────────────
    "cli.not_workspace": "❌ 不是 ChatMD 工作空间: {workspace}",
    "cli.run_init_first": "请先运行 chatmd init",
    "cli.starting": "🚀 ChatMD Agent 启动中... ({workspace})",
    "cli.press_ctrl_c": "按 Ctrl+C 停止",
    "cli.agent_stopped": "\n👋 Agent 已停止",
    "cli.no_running_agent": "ℹ️ 没有正在运行的 Agent",
    "cli.pid_corrupted": "⚠️ PID 文件损坏，已清理",
    "cli.stop_signal_sent": "✅ 已发送停止信号 (PID {pid})",
    "cli.process_not_found": "ℹ️ Agent 进程不存在（可能已停止），清理 PID 文件",
    "cli.no_permission": "❌ 无权限停止进程 (PID {pid})",
    "cli.agent_running": "🟢 Agent 运行中 (PID {pid})",
    "cli.agent_not_running": "⚪ Agent 未运行",
    "cli.agent_not_running_stale": "⚪ Agent 未运行（残留 PID 文件已清理）",
    "cli.workspace_label": "   工作空间: {workspace}",
    "cli.custom_skills": "   自定义 Skill: {yaml_count} YAML + {py_count} Python",
    "cli.daemon_already_running": "ℹ️ Agent 已在运行中 (PID {pid})",
    "cli.daemon_started": "🚀 Agent 已在后台启动 (PID {pid})\n   工作空间: {workspace}",
    "cli.daemon_log_hint": "   日志: {log}",
    "cli.daemon_stop_hint": "   运行 `chatmd stop` 停止 Agent",
    "cli.daemon_failed": "❌ Agent 后台启动失败 (退出码 {code})",
    "cli.restart_stopping": "🔄 正在停止 Agent (PID {pid})...",
    "cli.restart_starting": "🔄 正在重启 Agent...",
    "cli.restart_not_running": "ℹ️ 未发现运行中的 Agent，启动新的后台进程...",

    # ── service CLI ─────────────────────────────────────────────────────
    "service.installed": "✅ 服务已安装 ({platform}: {name})",
    "service.file_created": "   配置文件: {path}",
    "service.auto_start": "   开机自启：Agent 将在登录/重启后自动启动",
    "service.starting_now": "🚀 正在启动 Agent...",
    "service.started_now": "✅ Agent 已运行 (PID {pid})",
    "service.start_failed": "⚠️ Agent 未能立即启动，请手动运行 `chatmd start --daemon`",
    "service.win_hints": (
        "   管理命令:\n"
        "     chatmd service status    — 查看服务状态\n"
        "     chatmd service uninstall — 卸载服务\n"
        "   也可在 services.msc 中管理此服务。"
    ),
    "service.launchd_hints": (
        "   管理命令:\n"
        "     chatmd service status   — 查看服务状态\n"
        "     chatmd stop             — 停止 Agent\n"
        "     chatmd service uninstall — 卸载服务"
    ),
    "service.systemd_hints": (
        "   管理命令:\n"
        "     systemctl --user status {name}\n"
        "     systemctl --user stop {name}\n"
        "     systemctl --user restart {name}"
    ),
    "service.uninstalled": "✅ 服务已卸载 ({platform}: {path})",
    "service.status_info": "服务 ({platform}): {name} — {status}",
    "service.unsupported_platform": "❌ 不支持的平台: {platform}",
    "service.pywin32_required": (
        "❌ Windows 服务需要 pywin32。\n"
        "   请安装: pip install pywin32"
    ),
    "service.pywin32_postinstall_required": (
        "⚠️  pywin32 安装后初始化尚未完成。\n"
        "   Windows 服务需要此步骤才能正常运行。\n"
        "   请以管理员身份运行:\n"
        "     {command}\n"
        "   然后重试: chatmd service install"
    ),
    "service.win_install_failed": (
        "❌ Windows 服务安装失败: {error}\n"
        "   请确保以管理员身份运行。"
    ),
    "service.win_uninstall_failed": (
        "⚠️ Windows 服务卸载失败: {error}"
    ),
    "service.started": "✅ 服务已启动 ({platform}: {name})",
    "service.stopped": "✅ 服务已停止 ({platform}: {name})",
    "service.start_service_failed": (
        "❌ 服务启动失败: {error}\n"
        "   提示：请先执行 `chatmd service install`，或检查权限。"
    ),
    "service.stop_service_failed": (
        "⚠️ 服务停止失败: {error}\n"
        "   提示：服务可能已经是停止状态。"
    ),
    # ── doctor CLI ──────────────────────────────────────────────────────
    "doctor.header": "🔍 ChatMD Doctor — 工作区: {workspace}",
    "doctor.summary": (
        "汇总: ✅ {ok} 项  ⚠️ {warn} 项警告  ❌ {error} 项错误  ⏭️ {skip} 项跳过"
    ),
    "doctor.fix_hint_label": "修复建议:",
    "doctor.skipped_no_network": "已跳过（--no-network）",
    "doctor.check_crashed": "检查异常: {error}",
    "doctor.category.environment": "Python 与依赖",
    "doctor.category.workspace": "工作区与配置",
    "doctor.category.service": "服务 ⇄ PID 一致性",
    "doctor.category.provider": "AI Provider",
    "doctor.category.git": "Git 仓库",

    "service.no_services_found": "未找到已安装的 ChatMD 服务。",
    "service.all_services_header": "ChatMD 服务 ({count} 个):",
    "service.status_all_hint_linux": (
        "列出所有 ChatMD 服务:\n"
        "  systemctl --user list-units 'chatmd-*'"
    ),
    "service.status_all_hint_macos": (
        "列出所有 ChatMD 服务:\n"
        "  launchctl list | grep com.chatmd"
    ),
    "service.uninstall_all_win_only": (
        "--all 目前仅支持 Windows。\n"
        "请使用平台原生命令管理服务。"
    ),

    # ── mode CLI ───────────────────────────────────────────────────────
    "mode.current_suffix": "触发模式: suffix（标记符: {marker}）",
    "mode.current_save": "触发模式: save（文件保存时执行）",
    "mode.switched_suffix": (
        "触发模式已切换为: suffix（标记符: {marker}）\n"
        "命令需要在行尾加 \"{marker}\" 才会执行"
    ),
    "mode.switched_save": (
        "触发模式已切换为: save\n"
        "命令将在文件保存时执行"
    ),

    # ── upgrade CLI ─────────────────────────────────────────────────────
    "upgrade.not_workspace": "❌ 当前目录不是 ChatMD 工作空间，请先运行 `chatmd init`",
    "upgrade.specify_option": "请指定升级选项：",
    "upgrade.full_option": "  chatmd upgrade --full  — 确保 chatmd/ 目录结构完整",
    "upgrade.done": "✅ 升级完成: {items}",
    "upgrade.already_full": "ℹ️ 工作空间结构已完整",

    # ── Default user config aliases ─────────────────────────────────────
    "alias.translate_en": "translate(英文)",
    "alias.translate_jp": "translate(日文)",
    "alias.translate_cn": "translate(中文)",

    # ── /la skill — destructive confirm (T-MVP03-M2) ────────────────────
    "la.confirm.card_header": "需要确认的破坏性操作",
    "la.confirm.card_hint": (
        "输入 `/la confirm {token}` 确认执行 · 10 分钟内有效"
    ),
    "la.confirm.bad_token": (
        "Token 格式不对，预期 `cft_` + 32 位十六进制"
    ),
    "la.confirm.not_found": "Token 不存在或已失效",
    "la.confirm.forbidden": "这个 Token 不属于当前账号",
    "la.confirm.consumed": "这个操作已经执行过，不能重复确认",
    "la.confirm.expired": "Token 已过期（有效期 10 分钟），请重新发起命令",
    "la.confirm.generic": "确认失败：{message}",
}
