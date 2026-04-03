# ChatMarkdown

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![PyPI version](https://img.shields.io/pypi/v/chatmd.svg)](https://pypi.org/project/chatmd/)

> Your local-first AI agent, driven by text.

ChatMarkdown (CLI: `chatmd`) lets you interact with an AI Agent through Markdown files in any text editor. No need to leave your editor — type a command, save, and get AI answers, translations, file operations, and more.

## Features

- **Local-first** — All data stored in local Markdown files, works offline
- **Text-driven** — Trigger via `/command` slash commands or `@ai{}` natural language
- **Editor-agnostic** — VS Code, Vim, Typora… any editor that can edit `.md` files
- **Deterministic routing** — Code-centric, not AI-centric; command execution is predictable
- **Extensible** — YAML declarative Skills + Python custom Skills + hot reload
- **Secure** — KernelGate injection prevention + confirmation window + audit log
- **Git sync** — Auto commit + pull/push, seamless multi-device collaboration

## Quick Start

### Step 0: Install Python (if needed)

ChatMarkdown requires **Python 3.10 or later**. Open a terminal and type `python --version`. If you see a version number (e.g. `Python 3.12.x`), skip to the next step.

#### Windows

1. Go to https://www.python.org/downloads/ and click Download Python 3.x.x
2. Run the installer — make sure to check ✅ "Add python.exe to PATH"
3. Close and reopen PowerShell or CMD
4. Verify: `python --version`

> 💡 You can also install Python from the Microsoft Store.

#### macOS

```bash
# Option 1: Download from https://www.python.org/downloads/

# Option 2: Homebrew (recommended if you have brew)
brew install python
```

Verify: `python3 --version`

> 💡 The built-in `python3` on macOS may be outdated. Install the latest from python.org or Homebrew.

#### Linux (Ubuntu/Debian)

```bash
sudo apt update && sudo apt install python3 python3-pip python3-venv -y
```

Verify: `python3 --version`

### Step 1: Install ChatMarkdown

Pick one of the following:

**Option A: pipx (recommended — auto-isolated, hassle-free)**

```bash
# Install pipx (one-time)
pip install pipx
pipx ensurepath
# ⚠️ Restart your terminal (close and reopen)

# Install chatmd
pipx install chatmd
```

> 💡 `pipx` creates an isolated environment for chatmd so it won't conflict with other Python packages.

**Option B: pip + virtual environment (classic)**

```bash
# Linux/macOS
python3 -m venv ~/.chatmd-env
source ~/.chatmd-env/bin/activate
pip install chatmd

# Windows
python -m venv %USERPROFILE%\.chatmd-env
%USERPROFILE%\.chatmd-env\Scripts\activate
pip install chatmd
```

> 💡 You need to activate the virtual environment each time before using chatmd.

**Option C: Direct run (no PATH setup needed)**

```bash
pip install chatmd
python -m chatmd --version
```

Verify installation:

```bash
chatmd --version
```

### Step 2: Initialize a Workspace

```bash
chatmd init ~/my-workspace          # Linux/macOS
chatmd init %USERPROFILE%\my-workspace   # Windows
```

### Step 3: Configure AI Provider (optional)

To use AI features like `/ask` and `/translate`, configure an API key in `.chatmd/agent.yaml`:

```yaml
ai:
  providers:
    - name: litestartup
      type: litestartup
      api_url: https://api.litestartup.com/client/v2/ai/chat
      api_key: ${LITEAGENT_API_KEY}  # environment variable, or paste directly
```

Then set the environment variable:

```bash
export LITEAGENT_API_KEY="your-api-key"   # Linux/macOS
# set LITEAGENT_API_KEY=your-api-key      # Windows
```

> 💡 Local commands like `/date` and `/help` work without an AI provider.

### Auto-save Editors (Obsidian, etc.)

If your editor auto-saves files, switch to **suffix mode** before starting the Agent:

```bash
chatmd mode suffix
```

In suffix mode, commands are only triggered when you end a line with `;`:

```markdown
/help;

/date;

/ask what is ChatMarkdown?;
```

To switch back: `chatmd mode save`

### Step 4: Start the Agent

```bash
cd ~/my-workspace       # Linux/macOS
# cd %USERPROFILE%\my-workspace  # Windows

chatmd start            # foreground (Ctrl+C to stop)
# chatmd start --daemon # or run in background
```

### Step 5: Start Interacting

Open `chat.md` in any editor, type a command, and save:

```markdown
/help

/date

/ask What is ChatMarkdown?

@ai{Translate to Chinese: Hello World}
```

The Agent detects file changes, executes commands, and writes results back into the file.

## Commands

### Basic

| Command | Alias | Description |
|---------|-------|-------------|
| `/help` | `/h` | List all available commands |
| `/date` | `/d` | Insert today's date |
| `/time` | | Insert current time |
| `/now` | | Insert date and time; `/now(full)` for a full summary |
| `/status` | `/st` | Show Agent status |
| `/list` | `/ls` | List conversation sessions |

### Date & Time

| Command | Alias | Description |
|---------|-------|-------------|
| `/datetime` | `/dt` | Insert date and time (YYYY-MM-DD HH:MM:SS) |
| `/timestamp` | `/ts` | Insert Unix timestamp |
| `/week` | `/w` | Insert current week number |
| `/weekday` | `/wd` | Insert day of week |
| `/progress` | `/pg` | Insert year progress |
| `/daynum` | `/dn` | Insert day of year |
| `/countdown(YYYY-MM-DD)` | `/cd` | Countdown to a date |

### Markdown Templates

| Command | Alias | Description |
|---------|-------|-------------|
| `/todo` | `/td` | Insert todo item `- [ ] ` |
| `/done` | `/dn2` | Insert done item `- [x] ` |
| `/table(3x4)` | `/tb` | Insert Markdown table |
| `/code(python)` | `/c` | Insert code block |
| `/link` | `/ln` | Insert link template |
| `/img` | `/i` | Insert image template |
| `/hr` | | Insert horizontal rule |
| `/heading(2)` | `/hd` | Insert heading |
| `/quote` | `/q` | Insert blockquote |

### AI

| Command | Alias | Description |
|---------|-------|-------------|
| `/ask <question>` | | AI conversation (requires API key) |
| `/translate(lang) <text>` | `/t` | AI translation |
| `/rewrite <text>` | `/rw` | AI rewrite |
| `/expand <text>` | `/exp` | AI expand |
| `/polish <text>` | `/pol` | AI grammar check & polish |
| `/summary <text>` | `/sum` | AI summarize |
| `/tag <text>` | | AI extract keywords |
| `/title <text>` | | AI suggest title |
| `/canvas` | `/cv` | AI mind map Canvas |

### Infrastructure

| Command | Alias | Description |
|---------|-------|-------------|
| `/new [topic]` | `/n` | Archive conversation and start a new session |
| `/sync` | | Git sync |
| `/log [N]` | | View audit log |
| `/upload` | `/up` | Upload local images to cloud |

### Trigger Methods

- **Slash commands**: `/command input`
- **@ai{} inline**: `Please help me @ai{summarize this paragraph}`
- **@ai{} multi-line block**:
  ```
  @ai{
  Translate the following:
  Hello World
  }
  ```
- **Suffix signal**: `Summarize this for me;` (enable in config)

## Multi-Session Conversations

ChatMarkdown supports multiple independent conversation sessions. Each `.md` file maintains its own AI context:

- **Default session** — `chat.md`, for everyday Q&A
- **Topic sessions** — Create `.md` files under `chat/`, each file is an independent conversation

```
workspace/
├── chat.md              ← default conversation
└── chat/
    ├── project-plan.md  ← project planning
    ├── english-study.md ← English study
    └── _index.md        ← auto-maintained index (do not edit)
```

Each session's AI conversation history is saved independently and auto-restored on Agent restart. Use `/list` to see all sessions.

## CLI Commands

```bash
chatmd init <path>           # Initialize workspace
chatmd init <path> --mode assistant  # Inject assistant capabilities only
chatmd start [-w <workspace>]  # Start Agent (foreground)
chatmd start --daemon          # Start Agent (background daemon)
chatmd stop [-w <workspace>]   # Stop Agent
chatmd status [-w <workspace>] # Check Agent status
chatmd mode                    # View current trigger mode
chatmd mode suffix             # Switch to suffix mode (for auto-save editors)
chatmd mode save               # Switch to save mode (default, manual save)
chatmd service install         # Register as system service (auto-start on boot)
chatmd service uninstall       # Unregister system service
chatmd service status          # Check system service status
chatmd upgrade --full          # Upgrade assistant → full mode
chatmd --version               # Show version
```

## Configuration

Workspace configuration files are in the `.chatmd/` directory:

- **`agent.yaml`** — Agent behavior (triggers, AI provider, async tasks, etc.)
- **`user.yaml`** — User preferences (language, aliases, etc.)

### AI Provider Configuration

```yaml
ai:
  providers:
    - name: litestartup
      type: litestartup
      api_url: https://api.litestartup.com/client/v2/ai/chat
      api_key: ${LITEAGENT_API_KEY}  # use environment variable
      model: default
      timeout: 60
```

### Custom Aliases

```yaml
# user.yaml
aliases:
  en: "translate(English)"
  jp: "translate(Japanese)"
  zh: "translate(Chinese)"
```

## Custom Skills

### YAML Declarative

Create a YAML file in `.chatmd/skills/`:

```yaml
# greet.yaml
name: greet
description: "Greet the user"
aliases: [hi, hello]
template: "Hello, {{input}}! Have a great day 🌞"
```

### Python Custom

```python
# .chatmd/skills/my_skill.py
from chatmd.skills.base import Skill, SkillContext, SkillResult

class EchoSkill(Skill):
    name = "echo"
    description = "Echo the input"
    category = "custom"

    def execute(self, input_text, args, context):
        return SkillResult(success=True, output=input_text)
```

## Project Structure

```
src/chatmd/
├── cli.py                  # CLI entry point (Click)
├── commands/               # CLI subcommands
│   ├── init_workspace.py   # chatmd init
│   ├── agent_lifecycle.py  # start/stop/status
│   ├── mode.py             # chatmd mode suffix/save
│   └── upgrade.py          # chatmd upgrade
├── engine/                 # Core engine
│   ├── agent.py            # Agent orchestration
│   ├── parser.py           # Command parser
│   ├── router.py           # Deterministic router
│   ├── scheduler.py        # Task scheduler
│   ├── state.py            # Multi-session state
│   └── confirm.py          # Confirmation window
├── watcher/                # File monitoring
│   ├── file_watcher.py     # watchdog monitor
│   ├── suffix_trigger.py   # suffix signal
│   └── auto_upload.py      # Auto image upload
├── skills/                 # Skill system
│   ├── base.py             # Base class
│   ├── builtin.py          # Built-in Skills (date/time + Markdown templates)
│   ├── ai.py               # AI Skills (conversation + translation + writing)
│   ├── canvas.py           # Canvas mind map Skill
│   ├── upload.py           # Image upload Skill
│   ├── infra.py            # Infrastructure Skills
│   ├── loader.py           # YAML/Python loader
│   └── hot_reload.py       # Hot reload
├── providers/              # AI Provider
│   ├── base.py             # Abstract base class
│   ├── litestartup.py      # LiteStartup unified provider
│   ├── liteagent.py        # LiteAgent AI implementation
│   └── openai_compat.py    # OpenAI-compatible implementation
├── security/               # Security
│   └── kernel_gate.py      # KernelGate injection prevention
└── infra/                  # Infrastructure
    ├── config.py           # Configuration management
    ├── file_writer.py      # Atomic file writing
    ├── offline_queue.py    # Offline queue
    ├── git_sync.py         # Git sync
    └── index_manager.py    # Index maintenance
```

## Development

To contribute or debug ChatMarkdown:

```bash
git clone https://github.com/user/chatmd.git
cd chatmd
pip install -e ".[dev]"    # Install dev dependencies (includes test tools)

# Run tests
python -m pytest tests/ -v

# Lint
ruff check src/ tests/
```

## Powered by LiteStartup

[**LiteStartup**](https://litestartup.com) is an AI-powered micro SaaS platform that helps solo developers and small teams build, launch, and grow digital products. ChatMarkdown uses LiteStartup's unified AI API as its default provider — one API key, multiple AI models, no vendor lock-in.

👉 **Get your free API key**: [litestartup.com](https://litestartup.com)

## Contributing

We welcome contributions of all kinds!

- **Bug reports** — [Open an issue](https://github.com/user/chatmd/issues)
- **Feature requests** — [Start a discussion](https://github.com/user/chatmd/discussions)
- **Pull requests** — Fork the repo, create a branch, add tests, and submit a PR

```bash
git clone https://github.com/user/chatmd.git
cd chatmd
pip install -e ".[dev]"
python -m pytest tests/ -v
```

📧 **Contact**: [chatmd@litestartup.com](mailto:chatmd@litestartup.com)

## Support & Community

If you find ChatMarkdown useful, please consider supporting the project:

- ⭐ **Star this repo** — It helps others discover ChatMarkdown
- 👀 **Watch for updates** — Stay notified of new releases
- 📢 **Share with friends** — Spread the word on Twitter, Reddit, or your favorite community
- 🐛 **Report bugs** — Every issue report makes ChatMarkdown better

## License

MIT
