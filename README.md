# byteforge-telegram

A generic, reusable Python library for Telegram bot notifications and webhook management.

## Features

- **TelegramBotController**: Send notifications via Telegram Bot API
  - Plain text messages
  - Formatted messages with title, fields, and footer
  - Both sync and async support
  - Automatic event loop handling
  - Session cleanup to prevent leaks

- **WebhookManager**: Manage Telegram webhooks
  - Set webhook URL
  - Get webhook information
  - Delete webhook
  - CLI tool included

## Installation

```bash
pip install byteforge-telegram
```

Or install from source:

```bash
git clone https://github.com/byteforge/byteforge-telegram.git
cd byteforge-telegram
pip install -e .
```

## Quick Start

### Sending Notifications

```python
from byteforge_telegram import TelegramBotController, ParseMode

# Initialize with your bot token
bot = TelegramBotController("YOUR_BOT_TOKEN")

# Send a simple message
bot.send_message_sync(
    text="Hello from byteforge-telegram!",
    chat_ids=["CHAT_ID_1", "CHAT_ID_2"]
)

# Send a formatted message
bot.send_formatted_sync(
    title="Deployment Complete",
    fields={
        "Environment": "production",
        "Version": "1.2.3",
        "Status": "Success"
    },
    chat_ids=["YOUR_CHAT_ID"],
    emoji="✅",
    footer="Deployed at 2025-01-03 12:00:00 UTC"
)
```

### Managing Webhooks

#### Programmatic API

```python
from byteforge_telegram import WebhookManager

# Initialize manager
manager = WebhookManager("YOUR_BOT_TOKEN")

# Set webhook
result = manager.set_webhook("https://example.com/telegram/webhook")
if result['success']:
    print(f"Webhook set: {result['description']}")

# Get webhook info
info = manager.get_webhook_info()
if info:
    print(f"Current webhook: {info.get('url')}")
    print(f"Pending updates: {info.get('pending_update_count')}")

# Delete webhook
result = manager.delete_webhook()
if result['success']:
    print("Webhook deleted")
```

#### Command-Line Interface

The package includes a `setup-telegram-webhook` CLI tool:

```bash
# Set webhook
setup-telegram-webhook --token YOUR_BOT_TOKEN --url https://example.com/telegram/webhook

# Or use environment variable
export TELEGRAM_BOT_TOKEN=YOUR_BOT_TOKEN
setup-telegram-webhook --url https://example.com/telegram/webhook

# Get webhook info
setup-telegram-webhook --token YOUR_BOT_TOKEN --info

# Delete webhook
setup-telegram-webhook --token YOUR_BOT_TOKEN --delete
```

## API Reference

### TelegramBotController

#### Methods

**`send_message_sync(text, chat_ids, parse_mode=ParseMode.HTML, ...)`**
- Send a plain text message (synchronous)
- Returns: `Dict[str, bool]` - success status for each chat

**`send_formatted_sync(title, fields, chat_ids, emoji=None, footer=None)`**
- Send a formatted message with title, fields, and footer (synchronous)
- Returns: `Dict[str, bool]` - success status for each chat

**`send_message(...)` / `send_formatted(...)`**
- Async versions of the above methods
- Use with `await` in async contexts

**`test_connection_sync(chat_id)`**
- Send a test message to verify bot is working
- Returns: `bool`

#### Parse Modes

```python
from byteforge_telegram import ParseMode

ParseMode.HTML         # HTML formatting (default)
ParseMode.MARKDOWN     # Markdown formatting
ParseMode.MARKDOWN_V2  # MarkdownV2 formatting
ParseMode.NONE         # Plain text, no formatting
```

### WebhookManager

#### Methods

**`set_webhook(webhook_url, timeout=10)`**
- Set the webhook URL for the bot
- Args:
  - `webhook_url`: HTTPS URL (required)
  - `timeout`: Request timeout in seconds
- Returns: `Dict[str, Any]` with `success` and `description`
- Raises: `ValueError` if URL is not HTTPS

**`get_webhook_info(timeout=10)`**
- Get current webhook configuration
- Returns: `Dict[str, Any]` with webhook details, or `None` on error

**`delete_webhook(timeout=10)`**
- Delete the current webhook
- Returns: `Dict[str, Any]` with `success` and `description`

### TelegramResponse

Type-safe dataclass for constructing webhook responses.

#### Fields

- `method`: API method name (usually "sendMessage")
- `chat_id`: Target chat ID
- `text`: Message text
- `parse_mode`: Format type (default: "HTML")
- `reply_markup`: Optional keyboard markup
- `disable_web_page_preview`: Disable link previews (default: False)
- `disable_notification`: Send silently (default: False)

#### Methods

**`to_dict()`**
- Convert to JSON-serializable dictionary
- Returns: `Dict[str, Any]`

#### Example

```python
from byteforge_telegram import TelegramResponse

response = TelegramResponse(
    method='sendMessage',
    chat_id=12345,
    text='<b>Hello!</b>',
    parse_mode='HTML',
    disable_web_page_preview=True
)

# Use in Flask webhook
return jsonify(response.to_dict()), 200
```

## Examples

### Integration with Flask (Simple)

```python
import os
from flask import Flask, request, jsonify
from byteforge_telegram import TelegramBotController

app = Flask(__name__)
bot = TelegramBotController(os.getenv('TELEGRAM_BOT_TOKEN'))

@app.route('/telegram/webhook', methods=['POST'])
def telegram_webhook():
    update = request.get_json()

    # Process the update
    message = update.get('message', {})
    text = message.get('text', '')
    chat_id = str(message.get('chat', {}).get('id'))

    if text == '/start':
        bot.send_message_sync(
            text="Welcome! I'm your bot.",
            chat_ids=[chat_id]
        )

    return jsonify({'ok': True}), 200
```

### Integration with Flask (Using TelegramResponse)

For more complex webhooks, use `TelegramResponse` for type-safe responses:

```python
from flask import Flask, request, jsonify
from byteforge_telegram import TelegramResponse

app = Flask(__name__)

@app.route('/telegram/webhook', methods=['POST'])
def telegram_webhook():
    update = request.get_json()

    # Extract message details
    message = update.get('message', {})
    text = message.get('text', '')
    chat_id = message.get('chat', {}).get('id')

    # Handle command
    if text == '/start':
        response = TelegramResponse(
            method='sendMessage',
            chat_id=chat_id,
            text='<b>Welcome!</b> Type /help for commands.',
            parse_mode='HTML'
        )
        return jsonify(response.to_dict()), 200

    return jsonify({'ok': True}), 200
```

### Async Usage

```python
import asyncio
from byteforge_telegram import TelegramBotController, ParseMode

async def send_notifications():
    bot = TelegramBotController("YOUR_BOT_TOKEN")

    # Send multiple messages concurrently
    results = await bot.send_message(
        text="Async notification",
        chat_ids=["CHAT_1", "CHAT_2", "CHAT_3"],
        parse_mode=ParseMode.HTML
    )

    for chat_id, success in results.items():
        if success:
            print(f"Sent to {chat_id}")
        else:
            print(f"Failed to send to {chat_id}")

asyncio.run(send_notifications())
```

### Error Handling

```python
from byteforge_telegram import TelegramBotController

bot = TelegramBotController("YOUR_BOT_TOKEN")

results = bot.send_message_sync(
    text="Important notification",
    chat_ids=["CHAT_ID"]
)

for chat_id, success in results.items():
    if not success:
        print(f"Failed to send to {chat_id}")
        # Implement retry logic, logging, etc.
```

## Design Philosophy

### Sync/Async Compatibility

The library handles both synchronous and asynchronous contexts automatically:

- `*_sync()` methods work in regular Python code (like Flask apps)
- `async` methods work in async contexts (like FastAPI, async scripts)
- Automatically detects running event loops
- Creates fresh Bot instances per call to avoid loop conflicts

### Session Management

Each message send creates a new Bot instance and properly cleans up the HTTP session afterward. This prevents connection leaks and event loop conflicts.

### Error Handling

- Network errors are caught and logged
- Results dict shows success/failure per chat ID
- Graceful degradation when services are unavailable

## Requirements

- Python 3.9+
- python-telegram-bot >= 20.0
- requests >= 2.31.0

## Development

### Setup

```bash
# Clone repository
git clone https://github.com/jmazzahacks/byteforge-telegram.git
cd byteforge-telegram

# Install in development mode
pip install -e ".[dev]"

# Run tests
pytest

# Format code
black src/
```

### Running Tests

```bash
pytest
pytest --cov=byteforge_telegram  # With coverage
```

## License

MIT License - see LICENSE file for details

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Author

Jason Byteforge (@jmazzahacks)

## Links

- GitHub: https://github.com/jmazzahacks/byteforge-telegram
- Issues: https://github.com/jmazzahacks/byteforge-telegram/issues
- PyPI: https://pypi.org/project/byteforge-telegram/
