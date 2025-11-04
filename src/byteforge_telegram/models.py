"""
Data models for Telegram bot responses and requests.
"""

from dataclasses import dataclass
from typing import Dict, Any, Optional


@dataclass
class TelegramResponse:
    """
    Type-safe response for Telegram Bot API methods.

    Used when handling webhook updates to construct responses
    that will be returned to Telegram.
    """

    method: str  # Usually 'sendMessage'
    chat_id: int
    text: str
    parse_mode: str = 'HTML'
    reply_markup: Optional[Dict[str, Any]] = None  # For inline keyboards, etc.
    disable_web_page_preview: bool = False
    disable_notification: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary for JSON serialization.

        Returns:
            Dict suitable for returning from webhook endpoint
        """
        result = {
            'method': self.method,
            'chat_id': self.chat_id,
            'text': self.text,
            'parse_mode': self.parse_mode
        }

        if self.reply_markup:
            result['reply_markup'] = self.reply_markup

        if self.disable_web_page_preview:
            result['disable_web_page_preview'] = True

        if self.disable_notification:
            result['disable_notification'] = True

        return result
