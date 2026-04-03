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
    "output.help.group.utility": "工具",
    "output.help.group.custom": "自定义",

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
    "output.sync.git_failed": "Git 操作失败: {error}",
    "output.sync.git_not_installed": "Git 未安装",

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

    # ── /new session ───────────────────────────────────────────────────
    "error.new_no_chat_md": "chat.md 不存在",
    "error.new_empty_content": "无内容可归档",
    "output.new.success": "✅ 已归档至 chat/{archive}，新会话已开始",
    "new.fallback_topic": "通用对话",

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
    "agent.async_placeholder": "⏳ {description}中... `#{task_id}`",
    "agent.async_done": "✅ 完成",
    "agent.async_failed_retry": "❌ {error}\n> 输入 `/retry #{task_id}` 重试",

    # ── Confirmation window ─────────────────────────────────────────────
    "confirm.prompt": (
        "> ⏳ 确认执行 `{command}`？"
        "（{delay}s 后自动执行，删除本行取消）"
        " `#{confirm_id}`"
    ),

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
    "init.mode_prompt": (
        "检测到目录已有文件，请选择模式\n"
        "  full      — 完整工作空间（创建 chat.md + chat/）\n"
        "  assistant — 仅注入助手能力（只创建 .chatmd/）\n"
        "模式"
    ),
    "init.workspace_created": "✅ 工作空间已创建: {workspace} (模式: {mode})",
    "init.run_start": "运行 chatmd start 启动 Agent",
    "init.open_chat": "用任何编辑器打开 chat.md 开始交互",
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
    "cli.mode_label": "   模式: {mode}",
    "cli.custom_skills": "   自定义 Skill: {yaml_count} YAML + {py_count} Python",
    "cli.daemon_already_running": "ℹ️ Agent 已在运行中 (PID {pid})",
    "cli.daemon_started": "🚀 Agent 已在后台启动 (PID {pid})\n   工作空间: {workspace}",
    "cli.daemon_log_hint": "   日志: {log}",
    "cli.daemon_stop_hint": "   运行 `chatmd stop` 停止 Agent",
    "cli.daemon_failed": "❌ Agent 后台启动失败 (退出码 {code})",

    # ── service CLI ─────────────────────────────────────────────────────
    "service.installed": "✅ 服务已安装 ({platform}: {name})",
    "service.file_created": "   配置文件: {path}",
    "service.auto_start": "   开机自启：Agent 将在登录/重启后自动启动",
    "service.starting_now": "🚀 正在启动 Agent...",
    "service.started_now": "✅ Agent 已运行 (PID {pid})",
    "service.start_failed": "⚠️ Agent 未能立即启动，请手动运行 `chatmd start --daemon`",
    "service.win_hints": (
        "   管理命令:\n"
        "     chatmd service status   — 查看服务状态\n"
        "     chatmd stop             — 停止 Agent\n"
        "     chatmd service uninstall — 卸载服务"
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
    "upgrade.full_option": "  chatmd upgrade --full  — 升级为完整工作空间",
    "upgrade.done": "✅ 升级完成: {items}",
    "upgrade.already_full": "ℹ️ 工作空间已经是完整模式",

    # ── Default user config aliases ─────────────────────────────────────
    "alias.translate_en": "translate(英文)",
    "alias.translate_jp": "translate(日文)",
    "alias.translate_cn": "translate(中文)",
}
