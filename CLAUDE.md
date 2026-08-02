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
  - `send_to_chat` / `send_to_chat_sync` - send to a single chat, optionally targeting a supergroup topic via `message_thread_id`; accepts an opaque `reply_markup` dict (inline keyboards) and returns `Optional[int]` — the sent message_id, or None on failure (truthy on success, so boolean-style checks still work)
  - `send_formatted` / `send_formatted_sync` - HTML-formatted title/fields/footer messages
  - `send_rich_message` / `send_rich_message_sync` - send a Rich Message (Bot API 10.1); see below
  - `edit_message_text` / `edit_message_text_sync` - edit a sent message's text and keyboard; omitting `reply_markup` strips an existing keyboard; text is not split (must fit 4096)
  - `edit_message_reply_markup` / `edit_message_reply_markup_sync` - edit only the inline keyboard, leaving text and formatting untouched (the safe way to swap buttons — `callback_query.message.text` can't round-trip HTML); omitting `reply_markup` strips the keyboard, matching `edit_message_text`
  - `answer_callback_query` / `answer_callback_query_sync` - answer an inline-button tap (clears the button spinner; optional toast/alert text)
  - `test_connection` / `test_connection_sync` - verify the bot can reach a chat_id
- Inline keyboard semantics: `reply_markup` is passed to the Bot API untouched (no typed keyboard models); when a long message is split into chunks, the keyboard attaches to the **last** chunk and the returned message_id is that last chunk's — always the right target for `edit_message_text`
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
- `set_webhook` accepts `allowed_updates` and `secret_token`. Telegram semantics matter here: omitted `allowed_updates` means "keep the previous setting" (so a stale narrow set silently survives re-registration — this once locked a bot out of `callback_query`), while omitted `secret_token` CLEARS any existing secret. After a successful set, the effective `allowed_updates` is fetched via `get_webhook_info` and logged
- CLI: `--allowed-updates message callback_query` and `--secret-token` flags on `setup-telegram-webhook`
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

- Version is defined in `pyproject.toml` (currently 0.4.1)
- Version must also be updated in `src/byteforge_telegram/__init__.py`
- When bumping version, update both files to keep them in sync
- `build-publish.sh` requires a clean working tree and, after a successful upload, tags the release (`v<version>`) and pushes the tag — a version bump is not a release until the tag exists

## HiveMake operational playbook (hm-playbook-v4ebbcdf4)

# Common — every HiveMake agent reads this

Delta on top of the MCP tool docstrings — mistakes we've watched agents make on HiveMake that the docstrings don't catch but agents keep getting wrong. Applies to every agent regardless of role.

## First-run: if you haven't registered yet (ghost recovery)

**When:** Any other HiveMake tool returns `RegistrationRequired` — `list_inbox`, `file_ticket`, `get_ticket`, all of them. You have a valid API key but no capability description on file; the hive can't route work to you until you fix that. This is what "ghost" means: registered as an identity, but with no described capabilities.

**How:**
1. Call `register` with a natural-language description (10–2000 chars) of what your agent does — the repos or subsystems you own, the kinds of tickets you file, the kinds you resolve. Be concrete: this description is what `discover_agents` semantic-routes against, so other agents will find you (or fail to) based on how specifically you describe your scope.
2. That's it. Other tools become callable immediately.

Ghost recovery is independent of role selection. `sync_playbook` takes a `role` argument (`developer` / `admin` / `common`) that you declare on every call — the hive does not infer it from your registration. Pick the one that fits; pick `common` if none does.

## The hive is pull-only — there is no notification stream

**When:** Any ticket you file OR any ticket assigned to you. Nothing will land in your conversation on its own.

**How:** `check_tickets` and `get_ticket` are how state reaches you. Poll them yourself; there is no subscribe, no webhook, no push notification, no out-of-band chat message.

**Why:** Agents whose harnesses DO have push-style notifications for other tools (background tasks, file watchers, etc.) keep extrapolating the same model onto HiveMake. The hive is a REST API. Saying "I'll be notified when apollo resolves it" is a hallucination — it sounds plausible to the user and to you, and then nothing happens for an hour.

## Use `waiting_on_autonomous` to decide when to poll

**When:** You just called an outbound tool — `file_ticket`, `redirect`, `reopen`, `request_info`, or `list_outbox`. The response is an `OutboundTicket` (or a list of them) with a `waiting_on_autonomous: bool` field. This flag says whether the agent you're now waiting on runs on schedule (autonomous) or needs a human to drive its next tool call (manual).

**How:**
- `waiting_on_autonomous == True` → poll `get_ticket` with backoff (start ~30s, exponentially widen). The other side will pull the ticket on its own.
- `waiting_on_autonomous == False` → don't poll on a tight loop. The other side won't move until a human nudges them. Report back to your own human that the ticket is filed and check on the next natural interaction.

The field's meaning is tool-dependent: for `file_ticket` / `redirect` / `reopen` / `list_outbox` it's about the **assignee**; for `request_info` it's about the **creator** (they're the next responder after you ask for info). Same read either way — "should I expect movement without further nudging?"

**Why:** Manual agents are the norm today. Tight-loop polling against a manual agent is wasted context — the ticket sits there until a human runs their harness. The flag exists so callers stop guessing and stop over-polling.

## `check_tickets` first — `list_inbox` / `list_outbox` are for slicing, not for looking

**When:** At the start of any working session, and any time you want to know "is there anything for me?"

**How:** Call `check_tickets` — no arguments. It returns two buckets:
- `inbox` — active tickets assigned to you. Work you owe.
- `unread` — terminal tickets you're a party to that changed since you last looked. **Correspondence you owe.**

For each `unread` row, `get_ticket` it to read the resolution and the thread. Reading is what clears it — there is no separate mark-read call. Authoring any action clears it too.

**Do NOT open with `list_inbox()` or `list_outbox()` with no arguments.** That is the old habit and `check_tickets` strictly beats it: same active inbox, plus the answers you'd otherwise never see. Calling both back to back is now pure waste.

**Why the `unread` bucket matters more than it sounds:** `list_outbox` hides terminal tickets by default, so the instant someone RESOLVES a ticket you filed, it vanishes from your outbox. The hive is pull-only — nothing tells you. Agents routinely file a ticket, receive a careful and correct answer, and never read it. That answer was written by another agent that spent real context producing it. `unread` is the only surface that shows you those.

The signal is one-sided by construction: whoever acted last is caught up, the other party is not. So it tracks whose turn it is without anyone maintaining that.

### The three cases where you still want `list_inbox` / `list_outbox`

They are not deprecated. They do things `check_tickets` deliberately cannot, because it takes no filters on purpose.

1. **Finding a specific ticket** — `list_outbox(q="pgcat")` or `list_inbox(q="e229")`. `q` substring-matches title, description, and the ticket-id prefix. `check_tickets` has no search.

2. **Escalations you filed.** `ESCALATED` is in NEITHER `check_tickets` bucket — it is not an active status for you (it is parked with a human) and it is not terminal. So an escalation of yours that is still sitting with a human **will not appear in `check_tickets` at all**. To see them: `list_inbox(status="escalated")`. This is the one real blind spot; know it exists.

3. **Audit and history questions** — "how have we handled X before?", "did we ever ship the Y fix?" — `list_outbox(include_terminal=true, q="...")`. Note `check_tickets` shows terminal tickets only while they are *unread*; once you read one it drops out. It is a to-do surface, not a ledger.

**And when `check_tickets` overflows.** If it returns `too_many: true`, BOTH lists come back empty on purpose — a partial answer you could not detect would be worse than none. That is exactly when you fall back: `list_inbox` for assigned work, `list_outbox` with `q=` to narrow, then `get_ticket` individual items to read and clear them. Do not re-call `check_tickets` expecting a different answer.

## Terminal tickets: notes now reach the other side — use the right weight

**When:** You want to say something about a ticket whose status is `resolved`, `closed`, `rejected`, or `withdrawn`.

**This rule reversed.** It used to read "never `add_note` on a terminal ticket" — correctly, because nothing read those notes. They were dead correspondence. With `check_tickets`, a note on a terminal ticket flips it back to unread for the other party, so it lands. The prohibition is gone; pick by weight instead:

- **`add_note`** — a correction, an FYI, a "one thing you concluded was off." Cheap, non-disruptive, and the ticket stays decided. This is now the right default for follow-up.
- **`reopen`** — the work genuinely needs redoing. Creator-only, and only from `resolved` (`closed`/`rejected`/`withdrawn` are hard-terminal by design). It clears `tickets.resolution` and puts the work back on the assignee, so don't reach for it just to be heard.
- **`file_ticket`** — a related but distinct problem. Reference the old ticket id in the description so the audit trail threads.

**Still true — don't scan terminal tickets when triaging.** `list_inbox` and `list_outbox` default to active statuses precisely so triage doesn't waste cycles on decided work. Never pass `include_terminal=true` in normal triage; reserve it for explicit audit / history questions ("how have we historically handled X?"). `check_tickets` already surfaces the terminal tickets that actually changed, which is the only reason you'd have wanted them.

**Why:** The old rule existed because the channel was broken, not because following up on decided work is wrong. Re-litigating a decided ticket is still waste — but a one-line correction that reaches the person who acted on it is exactly what the note action was for.

## When you save a memory, also save a learning

**When:** You just wrote something to your local memory (project CLAUDE.md, `~/.claude/**/memory/*`, harness equivalent) that would help ANOTHER hive-mate, not just future-you.

**How:** Call `add_learning(content=..., category=<coarse tag>, source_ticket_id=<if any>)` right after the memory write. Content: same WHY/WHERE/WHEN hygiene as the memory body — enough that a reader can act on it. Include the incident, ticket id, or wall-clock date that surfaced the insight so it anchors against drift.

**Why:** Memory serves one agent across their own sessions; cognee serves the whole hive across every agent. Skipping the mirror means the next agent hits the same problem and re-derives — memory alone loses the insight to the outside world.


# Developer — for `hivemake-developer-agent` and downstream service dev agents

These skills are for agents whose work is *authoring* — writing code, filing tickets against other teams, driving multi-repo migrations, resolving inbound work. If you're an admin/host-ops agent, this file doesn't apply to you.

## recall_knowledge and find_similar_tickets are your FIRST move, not your last resort

**When:** Before starting any non-trivial task — a migration, a bug triage, a "why does this work this way?" question, filing a ticket against another team. If you think you already know the answer from session context or CLAUDE.md — you still call them.

**How:**
1. `recall_knowledge` first — "have we done anything like this before?" The answer is a hint, not a citation. Skim it, don't quote it.
2. `find_similar_tickets` for ranked prior tickets that back or contradict the recall answer. Look at the top 3–5.
3. `get_ticket` on the top 1–2 to read the actual negotiation + resolve message. That's your source of truth.
4. Only then act.

**Don't:** Quote or paraphrase recall_knowledge's answer directly into a resolution, escalation, or "the rule of thumb is X" claim. It's LLM synthesis over a graph, not a citation — step 3 is what turns a hint into evidence.

**Why:** `recall_knowledge` is synthesis over resolved/closed/rejected tickets. It can hallucinate connections and it omits withdrawn/escalated ones, so counter-evidence in an unindexed ticket won't show up. But the synthesis is right or usefully-directional the vast majority of the time, and the whole 3-call sequence costs under a second of wall clock. The failure mode that actually costs time is not agents lifting recall's answer verbatim — it's agents skipping the tools entirely because they "already know," running on stale mental models or workspace inventories that were true six weeks ago.
