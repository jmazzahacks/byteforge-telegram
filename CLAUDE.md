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
- Constructor takes `bot_token` and optional `rate_limit_seconds` (defaults to `DEFAULT_RATE_LIMIT_SECONDS = 1.1`)
- Sync/async method pairs:
  - `send_message` / `send_message_sync` - fan-out to one or more chat_ids
  - `send_to_chat` / `send_to_chat_sync` - send to a single chat, optionally targeting a supergroup topic via `message_thread_id`
  - `send_formatted` / `send_formatted_sync` - HTML-formatted title/fields/footer messages
  - `send_rich_message` / `send_rich_message_sync` - send a Rich Message (Bot API 10.1); see below
  - `test_connection` / `test_connection_sync` - verify the bot can reach a chat_id
- Creates fresh Bot instances per call to avoid event loop conflicts
- Handles automatic session cleanup to prevent connection leaks
- Per-chat rate limiting: throttles sends per chat_id to respect Telegram limits
- Auto-splits messages longer than `TELEGRAM_MAX_MESSAGE_LENGTH` (4096) into chunks
- Key design: Uses `_send_with_new_bot()` pattern to create disposable Bot instances; send parameters are bundled in the `_SendOptions` dataclass

**Module-level helpers** (`src/byteforge_telegram/notifier.py`, exported from the package)
- `split_message(text, max_length=4096)` - splits long text into Telegram-sized chunks
- `repair_html_tags(text)` - balances/repairs HTML tags so unbalanced markup doesn't silently fail delivery (only `TELEGRAM_ALLOWED_TAGS` are treated as markup)
- `escape_telegram_html(text)` - escapes HTML entities while preserving intentional formatting tags

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

**InputRichMessage** (`src/byteforge_telegram/models.py`)
- Dataclass for the Bot API 10.1 `sendRichMessage` payload
- Fields: `html` / `markdown` (exactly one required), `is_rtl`, `skip_entity_detection`
- `__post_init__` enforces the "exactly one of html/markdown" rule
- `to_dict()` omits unset/false fields

### Rich Messages (Bot API 10.1)

- Rich content (tables, lists, headings, formulas, media, collages, etc.) is **not** built as a tree of block objects. You send it as a single **extended HTML or Markdown string** inside an `InputRichMessage`, via `send_rich_message()` / `send_rich_message_sync()`.
- The extended HTML dialect adds tags on top of the classic set: `table/tr/td/th`, `ul/ol/li`, `h1`-`h6`, `details/summary`, `figure/figcaption/img/video/audio`, `tg-math`/`tg-math-block`, `tg-collage`, `tg-slideshow`, `tg-map`, `tg-thinking`, `tg-reference`, `tg-time`, `mark`, `sub`, `sup`, `aside`, `cite`, etc.
- Rich text is passed through **untouched** - no HTML escaping, tag repair, or message splitting (the caller supplies deliberate rich markup).
- `python-telegram-bot` 22.5 has no `sendRichMessage` wrapper, so the controller calls the endpoint directly via `Bot.do_api_request("sendRichMessage", api_kwargs=...)`, reusing the same per-call Bot + session-cleanup pattern.
- The `RichBlock` / `RichText` class hierarchy in the Bot API docs is the **received/parsed** representation of incoming rich messages and is intentionally **not** modeled here (this is a send-focused library).

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
- Outgoing text is preprocessed (`_preprocess_text`): HTML entities are escaped while preserving allowed formatting tags, and unbalanced tags are repaired so malformed markup doesn't cause Telegram to silently drop the message

### Rate Limiting & Message Splitting

- The controller throttles sends on a per-chat_id basis (`rate_limit_seconds`, default 1.1s) to stay within Telegram limits
- Messages exceeding `TELEGRAM_MAX_MESSAGE_LENGTH` (4096) are automatically split into multiple chunks via `split_message()` and sent in sequence

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
├── notifier.py          # TelegramBotController, ParseMode, and HTML/splitting helpers
├── webhook.py           # WebhookManager
├── models.py            # TelegramResponse and InputRichMessage dataclasses
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

- Test suite lives in `tests/`: `test_notifier.py`, `test_webhook.py`, `test_models.py`, `test_cli.py`, `test_html_escaping.py`, `test_rich_message.py`, `test_async_context_fix.py`
- When adding tests, use `pytest-asyncio` for async test support
- Test both sync and async methods
- Mock Telegram API calls to avoid real API usage
- **CRITICAL**: After making changes, always run `source bin/activate && python -m pytest` BEFORE committing code
- Remember: NEVER use `python3` - always use the venv with `source bin/activate && python`

## Version Management

- Version is defined in `pyproject.toml` (currently 0.3.1)
- Version must also be updated in `src/byteforge_telegram/__init__.py`
- When bumping version, update both files to keep them in sync
