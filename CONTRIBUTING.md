# Contributing to ChatMarkdown

Thank you for your interest in contributing to ChatMarkdown! This guide will help you get started.

## Quick Start

```bash
# 1. Fork and clone
git clone https://github.com/<your-username>/chatmd.git
cd chatmd

# 2. Create a virtual environment
python -m venv .venv
source .venv/bin/activate    # Linux/macOS
# .venv\Scripts\activate     # Windows

# 3. Install dev dependencies
pip install -e ".[dev]"

# 4. Verify everything works
pytest
ruff check src/
```

## Development Guidelines

### Code Style

- **Python 3.10+** — use modern type hints (`list[str]`, `X | None`)
- **Ruff** for linting — run `ruff check src/ tests/` before committing
- **100-character** line width
- **Google-style** docstrings for all public functions
- **English** for all code, comments, variable names, and commit messages

### Testing

- **pytest + pytest-asyncio** — tests live in `tests/`
- Run the full suite: `pytest`
- Run with coverage: `coverage run -m pytest && coverage report`
- Markers: `@pytest.mark.unit`, `@pytest.mark.integration`, `@pytest.mark.e2e`, `@pytest.mark.slow`
- **All new features must include tests** — aim for ≥ 80% coverage

### Commit Messages

We follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <description>
```

**Types**: `feat`, `fix`, `docs`, `test`, `refactor`, `chore`, `ci`, `perf`

**Examples**:
- `feat(skills): add /weather skill`
- `fix(parser): handle empty lines in fenced blocks`
- `docs: update README with new CLI commands`
- `test(cron): add persistence edge case tests`

### Branch Strategy

| Branch | Purpose |
|--------|---------|
| `main` | Stable releases |
| `dev` | Integration branch |
| `feat/<name>` | New features |
| `fix/<name>` | Bug fixes |

## How to Contribute

### Reporting Bugs

1. Search [existing issues](https://github.com/chatmarkdown/chatmd/issues) first
2. Use the **Bug Report** issue template
3. Include: Python version, OS, steps to reproduce, expected vs actual behavior

### Suggesting Features

1. Open a **Feature Request** issue
2. Describe the use case and expected behavior
3. We'll discuss feasibility before implementation

### Submitting Pull Requests

1. **Fork** the repo and create a branch from `dev`
2. **Write tests** for your changes
3. **Run checks** before pushing:
   ```bash
   pytest
   ruff check src/ tests/
   ```
4. **Open a PR** against `dev` with a clear description
5. Link related issues (e.g., "Closes #42")

### Creating Custom Skills

ChatMarkdown supports a plugin system for custom skills. See [`rules/custom_skills.md`](rules/custom_skills.md) for the full guide.

Quick overview:
1. Create a Python module with a class extending `Skill`
2. Register it in `.chatmd/skills.yaml`
3. Skills support `configure()` / `teardown()` lifecycle hooks

## Project Structure

```
src/chatmd/
├── cli.py                  # CLI entry point (Click)
├── commands/               # CLI subcommands (init, start, stop, upgrade)
├── engine/                 # Core engine (parser, router, agent, scheduler, cron)
├── watcher/                # File watcher + suffix trigger
├── skills/                 # Built-in skills (ai, cron, infra, builtin)
├── providers/              # AI provider backends
├── security/               # KernelGate safety checks
├── infra/                  # Config, file writer, git sync, notifications
└── i18n/                   # Internationalization (en, zh_CN)

tests/                      # All tests (unit, integration, e2e)
rules/                      # Development rules and conventions
docs/                       # Project documentation
```

## i18n

- All user-facing strings use `t("key.name")` from `chatmd.i18n`
- Default locale: `en`, supported: `zh-CN`
- **Never hardcode user-facing text** — always use i18n keys
- Add keys to both `i18n/en.py` and `i18n/zh_CN.py`

## Security

- **No hardcoded API keys** — use environment variables or `.env`
- Commands in `security/kernel_gate.py` blacklist are blocked
- Destructive operations require explicit `/confirm`

## Code of Conduct

Be respectful, constructive, and inclusive. We follow the [Contributor Covenant](https://www.contributor-covenant.org/) Code of Conduct.

## License

By contributing, you agree that your contributions will be licensed under the [MIT License](LICENSE).

## Questions?

- Open a [Discussion](https://github.com/chatmarkdown/chatmd/discussions) for general questions
- Check the [README](README.md) for usage documentation
