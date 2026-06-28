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


@dataclass
class InputRichMessage:
    """
    A rich message to send via Bot API 10.1 sendRichMessage (TelegramBotController.send_rich_message).

    Rich content -- tables, lists, headings, formulas (tg-math), media, collages,
    etc. -- is expressed as a single extended HTML or Markdown string (Telegram's
    "Rich Message Formatting Options"), not as a tree of block objects. Exactly one
    of `html` or `markdown` must be provided.

    For the full list of supported tags, attributes, entities, and limits, see
    docs/rich-messages.md.
    """

    html: Optional[str] = None
    markdown: Optional[str] = None
    is_rtl: bool = False
    skip_entity_detection: bool = False

    def __post_init__(self) -> None:
        # Treat an empty string as "not provided" so the check fails fast with a
        # clear error rather than letting Telegram reject an empty message body.
        if bool(self.html) == bool(self.markdown):
            raise ValueError("Exactly one of html or markdown must be provided")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to the InputRichMessage dict expected by the Bot API."""
        result: Dict[str, Any] = {}

        if self.html:
            result['html'] = self.html

        if self.markdown:
            result['markdown'] = self.markdown

        if self.is_rtl:
            result['is_rtl'] = True

        if self.skip_entity_detection:
            result['skip_entity_detection'] = True

        return result
