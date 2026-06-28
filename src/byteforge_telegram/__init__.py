"""
byteforge-telegram: Generic Telegram bot notification and webhook management library.

This library provides reusable components for:
- Sending Telegram notifications (plain and formatted)
- Managing Telegram webhooks
- Webhook response models
- Both sync and async support
"""

from byteforge_telegram.notifier import TelegramBotController, ParseMode, split_message, repair_html_tags
from byteforge_telegram.webhook import WebhookManager
from byteforge_telegram.models import TelegramResponse, InputRichMessage

__version__ = "0.3.0"

__all__ = [
    "TelegramBotController",
    "ParseMode",
    "WebhookManager",
    "TelegramResponse",
    "InputRichMessage",
    "split_message",
    "repair_html_tags",
]
