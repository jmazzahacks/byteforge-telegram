"""
Generic Telegram notification module.

A reusable Telegram bot notification system that can be used across different projects.
"""

import logging
from typing import Optional, List, Dict, Any
from enum import Enum
import asyncio
import concurrent.futures
import html
import re
from telegram import Bot
from telegram.error import TelegramError

logger = logging.getLogger(__name__)


def escape_telegram_html(text: str) -> str:
    """
    Escape HTML entities while preserving allowed Telegram formatting tags.

    This function escapes literal <, >, and & characters that could cause
    "Can't parse entities" errors, while preserving intentional HTML formatting
    tags that Telegram supports.

    Allowed tags (from Telegram Bot API):
    - b, strong: bold
    - i, em: italic
    - u, ins: underline
    - s, strike, del: strikethrough
    - code: inline code
    - pre: preformatted block
    - a: hyperlink
    - blockquote, expandable_blockquote: quote
    - tg-spoiler: spoiler
    - tg-emoji: custom emoji

    Example:
        "<b>Score: <70%</b>" → "<b>Score: &lt;70%</b>"
        (preserves <b> tags but escapes <70)

    Args:
        text: Raw text that may contain both formatting tags and special characters

    Returns:
        Text with special characters escaped but allowed HTML tags preserved
    """
    # Pattern to match allowed Telegram HTML tags (opening and closing)
    # Includes optional attributes for tags like <a href="..."> and <tg-emoji emoji-id="...">
    allowed_tags_pattern = (
        r'</?(?:b|strong|i|em|u|ins|s|strike|del|code|pre|a|blockquote|'
        r'expandable_blockquote|tg-spoiler|tg-emoji)(?:\s+[^>]*)?>'
    )

    # Split text into tag and non-tag segments
    # The pattern in parentheses creates capture groups that are included in the result
    parts = re.split(f'({allowed_tags_pattern})', text, flags=re.IGNORECASE)

    # Escape only non-tag parts (even-indexed elements after split)
    escaped_parts = []
    for i, part in enumerate(parts):
        if i % 2 == 0:
            # Non-tag text - escape special characters
            escaped_parts.append(html.escape(part))
        else:
            # Tag - preserve as-is
            escaped_parts.append(part)

    return ''.join(escaped_parts)


class ParseMode(Enum):
    HTML = "HTML"
    MARKDOWN = "Markdown"
    MARKDOWN_V2 = "MarkdownV2"
    NONE = None


class TelegramBotController:
    """
    Generic Telegram bot controller using per-call Bot instances to avoid cross-loop issues.
    """

    def __init__(self, bot_token: str):
        if not bot_token:
            raise ValueError("bot_token is required")
        self.bot_token = bot_token
        logger.debug("Telegram bot controller initialized")

    async def _send_with_new_bot(
        self,
        text: str,
        chat_ids: List[str],
        parse_mode: Optional[ParseMode],
        disable_web_page_preview: bool,
        disable_notification: bool,
    ) -> Dict[str, bool]:
        if not chat_ids:
            logger.warning("No chat_ids provided")
            return {}

        bot = Bot(token=self.bot_token)
        results: Dict[str, bool] = {}
        try:
            for chat_id in chat_ids:
                try:
                    await bot.send_message(
                        chat_id=chat_id,
                        text=text,
                        parse_mode=parse_mode.value if parse_mode else None,
                        disable_web_page_preview=disable_web_page_preview,
                        disable_notification=disable_notification,
                    )
                    results[chat_id] = True
                    logger.debug(f"Message sent successfully to {chat_id}")
                except TelegramError as e:
                    results[chat_id] = False
                    logger.error(f"Telegram error for chat {chat_id}: {e}")
                except Exception as e:
                    results[chat_id] = False
                    logger.error(f"Unexpected error sending to {chat_id}: {e}")
        finally:
            try:
                session = getattr(bot, "session", None)
                if session is not None:
                    aclose = getattr(session, "aclose", None)
                    close = getattr(session, "close", None)
                    if callable(aclose):
                        await aclose()
                        logger.debug("Bot session closed (async)")
                    elif callable(close):
                        close()
                        logger.debug("Bot session closed (sync)")
            except Exception as e:
                logger.warning(f"Failed to close bot session: {e}")
        return results

    async def send_message(
        self,
        text: str,
        chat_ids: List[str],
        parse_mode: ParseMode = ParseMode.HTML,
        disable_web_page_preview: bool = False,
        disable_notification: bool = False,
    ) -> Dict[str, bool]:
        # Escape HTML entities while preserving allowed formatting tags
        if parse_mode == ParseMode.HTML:
            text = escape_telegram_html(text)

        return await self._send_with_new_bot(
            text=text,
            chat_ids=chat_ids,
            parse_mode=parse_mode,
            disable_web_page_preview=disable_web_page_preview,
            disable_notification=disable_notification,
        )

    def send_message_sync(
        self,
        text: str,
        chat_ids: List[str],
        parse_mode: ParseMode = ParseMode.HTML,
        disable_web_page_preview: bool = False,
        disable_notification: bool = False,
    ) -> Dict[str, bool]:
        """
        Synchronously send a message, blocking until completion.

        Works correctly in both sync and async contexts by running
        in a separate thread to avoid event loop conflicts.
        """
        try:
            # Always use a thread pool to run asyncio.run() to avoid event loop conflicts
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(
                    asyncio.run,
                    self.send_message(
                        text=text,
                        chat_ids=chat_ids,
                        parse_mode=parse_mode,
                        disable_web_page_preview=disable_web_page_preview,
                        disable_notification=disable_notification,
                    )
                )
                return future.result()  # Block until complete
        except Exception as e:
            logger.error(f"Error in send_message_sync (chat_ids={len(chat_ids)}): {e}")
            return {cid: False for cid in chat_ids}

    async def send_formatted(
        self,
        title: str,
        fields: Dict[str, Any],
        chat_ids: List[str],
        emoji: Optional[str] = None,
        footer: Optional[str] = None,
    ) -> Dict[str, bool]:
        # Escape user-provided content to prevent parsing errors
        # Use simple html.escape() since we're constructing the HTML ourselves
        escaped_title = html.escape(title)
        parts: List[str] = []
        if emoji:
            parts.append(f"{emoji} <b>{escaped_title}</b>")
        else:
            parts.append(f"<b>{escaped_title}</b>")
        parts.append("")
        for key, value in fields.items():
            if value is None:
                value = "N/A"
            escaped_key = html.escape(str(key))
            escaped_value = html.escape(str(value))
            parts.append(f"<b>{escaped_key}:</b> {escaped_value}")
        if footer:
            parts.append("")
            escaped_footer = html.escape(footer)
            parts.append(f"<i>{escaped_footer}</i>")
        message = "\n".join(parts)
        # Call _send_with_new_bot directly to avoid double-escaping
        # (user content is already escaped, and we've added our own formatting tags)
        return await self._send_with_new_bot(
            text=message,
            chat_ids=chat_ids,
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=False,
            disable_notification=False,
        )

    def send_formatted_sync(
        self,
        title: str,
        fields: Dict[str, Any],
        chat_ids: List[str],
        emoji: Optional[str] = None,
        footer: Optional[str] = None,
    ) -> Dict[str, bool]:
        """
        Synchronously send a formatted message, blocking until completion.

        Works correctly in both sync and async contexts by running
        in a separate thread to avoid event loop conflicts.
        """
        try:
            # Always use a thread pool to run asyncio.run() to avoid event loop conflicts
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(
                    asyncio.run,
                    self.send_formatted(
                        title=title,
                        fields=fields,
                        chat_ids=chat_ids,
                        emoji=emoji,
                        footer=footer,
                    )
                )
                return future.result()  # Block until complete
        except Exception as e:
            logger.error(f"Error in send_formatted_sync (chat_ids={len(chat_ids)}): {e}")
            return {cid: False for cid in chat_ids}

    async def test_connection(self, chat_id: str) -> bool:
        result = await self.send_message("🔔 Telegram notification test successful!", [chat_id])
        return result.get(chat_id, False)

    def test_connection_sync(self, chat_id: str) -> bool:
        """
        Synchronously test connection, blocking until completion.

        Works correctly in both sync and async contexts by running
        in a separate thread to avoid event loop conflicts.
        """
        try:
            # Always use a thread pool to run asyncio.run() to avoid event loop conflicts
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(
                    asyncio.run,
                    self.test_connection(chat_id)
                )
                return future.result()  # Block until complete
        except Exception as e:
            logger.error(f"Error in test_connection_sync (chat_id={chat_id}): {e}")
            return False
