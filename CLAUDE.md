# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

`byteforge-telegram` is a reusable Python library for Telegram bot notifications and webhook management. It provides both synchronous and asynchronous APIs for sending Telegram messages and managing webhooks.

## Development Commands

**CRITICAL**: This project uses a virtual environment. ALWAYS use `source bin/activate && python` and `source bin/activate && pip`. NEVER use `python3` or `pip3` directly - these are system executables and we always use the virtual environment.

### Environment Setup
```bash
# Virtual environment is already set up in this project

# Option 1: Install from requirements files
source bin/activate && pip install -r requirements.txt
source bin/activate && pip install -r dev-requirements.txt

# Option 2: Install in development mode (includes all dependencies)
source bin/activate && pip install -e ".[dev]"

# Note: requirements.txt includes mazza-base from private GitHub repo
# This requires CR_PAT environment variable to be set
# export CR_PAT=your_github_token
```

### Running Tests
```bash
# Run all tests
source bin/activate && python -m pytest

# Run with coverage
source bin/activate && python -m pytest --cov=byteforge_telegram

# Run a single test file
source bin/activate && python -m pytest tests/test_notifier.py

# Run a specific test
source bin/activate && python -m pytest tests/test_notifier.py::test_send_message
```

### Code Formatting
```bash
# Format code with Black (line length: 100)
source bin/activate && python -m black src/

# Check formatting without making changes
source bin/activate && python -m black --check src/

# Sort imports with isort
source bin/activate && python -m isort src/

# Check import sorting without making changes
source bin/activate && python -m isort --check-only src/
```

### Type Checking
```bash
# Run mypy type checker
source bin/activate && python -m mypy src/
```

### Building and Publishing
```bash
# Build package
source bin/activate && python -m build

# Publish to PyPI (requires credentials)
source bin/activate && python -m twine upload dist/*
```

### Testing CLI Tool Locally
```bash
# After installing in development mode, the CLI is available
source bin/activate && setup-telegram-webhook --help
source bin/activate && setup-telegram-webhook --token YOUR_TOKEN --info
```

## Architecture

### Core Components

**TelegramBotController** (`src/byteforge_telegram/notifier.py`)
- Main class for sending Telegram notifications
- Supports both sync (`send_message_sync`, `send_formatted_sync`) and async (`send_message`, `send_formatted`) methods
- Creates fresh Bot instances per call to avoid event loop conflicts
- Handles automatic session cleanup to prevent connection leaks
- Key design: Uses `_send_with_new_bot()` pattern to create disposable Bot instances

**WebhookManager** (`src/byteforge_telegram/webhook.py`)
- Manages Telegram webhook configuration via REST API
- Methods: `set_webhook()`, `get_webhook_info()`, `delete_webhook()`
- Uses synchronous `requests` library
- Validates HTTPS requirement for webhook URLs

**CLI Tool** (`src/byteforge_telegram/cli.py`)
- Command-line interface: `setup-telegram-webhook`
- Supports setting, viewing, and deleting webhooks
- Can use `--token` flag or `TELEGRAM_BOT_TOKEN` environment variable

**TelegramResponse** (`src/byteforge_telegram/models.py`)
- Dataclass for type-safe webhook response construction
- Used when handling webhook updates to return responses to Telegram
- Primary method: `to_dict()` - converts to dict for JSON serialization
- Supports reply_markup for inline keyboards and other Telegram features
- Default parse_mode is HTML

### Sync/Async Design Pattern

The library handles both sync and async contexts by:
1. Detecting running event loops with `asyncio.get_running_loop()`
2. Creating tasks in existing loops OR running new loops with `asyncio.run()`
3. Creating fresh Bot instances per message to avoid cross-loop contamination
4. Cleaning up HTTP sessions in `finally` blocks

**CRITICAL**: When modifying async code:
- Never reuse Bot instances across async calls - always create new ones
- Always clean up sessions in `finally` blocks using dynamic attribute detection
- The `*_sync()` methods must handle both running and non-running event loop scenarios
- Use `try/except RuntimeError` to detect if an event loop is already running

### Message Formatting

- Default parse mode: `ParseMode.HTML`
- `send_formatted()` builds HTML-formatted messages with title, key-value fields, optional emoji, and footer
- All formatting is HTML-based (bold with `<b>`, italic with `<i>`)

## Important Patterns

### Error Handling
- Methods return `Dict[str, bool]` mapping chat_id to success status
- Failures are logged but don't raise exceptions
- Network errors caught via `TelegramError` and general `Exception`

### Session Management
- Each message send creates a new Bot instance
- Sessions are explicitly closed in `finally` blocks
- Uses dynamic attribute detection (`getattr`) to handle different session types

### Type Hints
- All public methods include type hints for parameters and return types
- Uses `Optional`, `List`, `Dict`, `Any` from typing module
- Return types are explicit (e.g., `Dict[str, bool]`, `Optional[Dict[str, Any]]`)

### Webhook Response Pattern

There are **two patterns** for handling Telegram webhooks:

**Pattern 1: Simple (using TelegramBotController)**
- Process the webhook update
- Use `TelegramBotController.send_message_sync()` to send responses
- Return `{'ok': True}` to acknowledge webhook
- Good for simple bots and async processing

**Pattern 2: Advanced (using TelegramResponse)**
- Process the webhook update
- Create `TelegramResponse` object
- Return `response.to_dict()` directly in webhook response
- Telegram processes the response inline
- More efficient, no separate API call
- Typical pattern:
  ```python
  response = TelegramResponse(
      method='sendMessage',
      chat_id=chat_id,
      text='<b>Response text</b>',
      parse_mode='HTML'
  )
  return jsonify(response.to_dict()), 200
  ```

## Project Structure

```
src/byteforge_telegram/
├── __init__.py          # Package exports
├── notifier.py          # TelegramBotController and ParseMode
├── webhook.py           # WebhookManager
├── models.py            # TelegramResponse dataclass
└── cli.py               # CLI entry point
```

## Dependencies

**Production (requirements.txt):**
- `python-telegram-bot` - Core Telegram API wrapper
- `mazza-base` - Mazza base library from private GitHub repo (requires CR_PAT env var)

**Development (dev-requirements.txt):**
- `mypy` - Type checking
- `black` - Code formatting
- `isort` - Import sorting

**Additional from pyproject.toml:**
- `requests>=2.31.0` - HTTP client for webhook management
- Dev: `pytest`, `pytest-asyncio`

## Testing Notes

- No test files exist yet in the repository
- When adding tests, use `pytest-asyncio` for async test support
- Test both sync and async methods
- Mock Telegram API calls to avoid real API usage
- **CRITICAL**: After making changes, always run `source bin/activate && python -m pytest` BEFORE committing code
- Remember: NEVER use `python3` - always use the venv with `source bin/activate && python`

## Version Management

- Version is defined in `pyproject.toml` (currently 0.1.0)
- Version must also be updated in `src/byteforge_telegram/__init__.py`
- When bumping version, update both files to keep them in sync
