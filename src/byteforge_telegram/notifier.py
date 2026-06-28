"""
Generic Telegram notification module.

A reusable Telegram bot notification system that can be used across different projects.
"""

import logging
import time
from dataclasses import dataclass
from typing import Optional, List, Dict, Any, Coroutine, TypeVar
from enum import Enum
import asyncio
import concurrent.futures
import html
import re
from bs4 import BeautifulSoup
from telegram import Bot
from telegram.error import TelegramError

from byteforge_telegram.models import InputRichMessage

T = TypeVar("T")

logger = logging.getLogger(__name__)

TELEGRAM_MAX_MESSAGE_LENGTH = 4096
DEFAULT_RATE_LIMIT_SECONDS = 1.1


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
    - blockquote (with optional expandable attribute): quote
    - tg-spoiler, span (with class="tg-spoiler"): spoiler
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
        r'span|tg-spoiler|tg-emoji)(?:\s+[^>]*)?>'
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


TELEGRAM_ALLOWED_TAGS = {
    "b", "strong", "i", "em", "u", "ins", "s", "strike", "del",
    "code", "pre", "a", "blockquote", "tg-spoiler", "tg-emoji",
}


def repair_html_tags(text: str) -> str:
    """
    Repair unbalanced HTML tags to prevent Telegram "Can't parse entities" errors.

    Uses BeautifulSoup's html.parser to auto-close unclosed tags and remove
    orphaned closing tags. Only keeps tags that Telegram's HTML mode supports.

    Should be called after escape_telegram_html() and before sending to Telegram.

    Args:
        text: HTML text that may contain unbalanced tags

    Returns:
        Text with balanced HTML tags
    """
    soup = BeautifulSoup(text, "html.parser")

    # Remove any tags that aren't in Telegram's allowed set. <span> is a special
    # case: Telegram only treats it as markup when it carries class="tg-spoiler"
    # (the alternate spelling of <tg-spoiler>); any other span is unwrapped.
    for tag in soup.find_all(True):
        if tag.name == "span":
            if "tg-spoiler" not in (tag.get("class") or []):
                tag.unwrap()
            continue
        if tag.name not in TELEGRAM_ALLOWED_TAGS:
            tag.unwrap()

    repaired = soup.decode_contents()

    if repaired != text:
        logger.debug("Repaired unbalanced HTML tags in message")

    return repaired


def split_message(text: str, max_length: int = TELEGRAM_MAX_MESSAGE_LENGTH) -> List[str]:
    """
    Split a long message into chunks that fit within Telegram's character limit.

    Tries to split at natural boundaries in order of preference:
    paragraph break, newline, space, then hard cut.

    Args:
        text: The message text to split
        max_length: Maximum characters per chunk (default: 4096)

    Returns:
        List of message chunks, each within max_length
    """
    if len(text) <= max_length:
        return [text]

    chunks: List[str] = []
    remaining = text

    while remaining:
        if len(remaining) <= max_length:
            chunks.append(remaining)
            break

        # Try paragraph boundary first, then newline, then space
        split_pos = remaining.rfind("\n\n", 0, max_length)
        if split_pos == -1:
            split_pos = remaining.rfind("\n", 0, max_length)
        if split_pos == -1:
            split_pos = remaining.rfind(" ", 0, max_length)
        if split_pos == -1:
            split_pos = max_length

        chunks.append(remaining[:split_pos])
        remaining = remaining[split_pos:].lstrip()

    return chunks


class ParseMode(Enum):
    HTML = "HTML"
    MARKDOWN = "Markdown"
    MARKDOWN_V2 = "MarkdownV2"
    NONE = None


@dataclass
class _SendOptions:
    """Internal bundle of optional Bot.send_message parameters used by the send pipeline."""
    parse_mode: Optional[ParseMode] = None
    disable_web_page_preview: bool = False
    disable_notification: bool = False
    message_thread_id: Optional[int] = None


class TelegramBotController:
    """
    Generic Telegram bot controller using per-call Bot instances to avoid cross-loop issues.
    """

    def __init__(self, bot_token: str, rate_limit_seconds: float = DEFAULT_RATE_LIMIT_SECONDS):
        if not bot_token:
            raise ValueError("bot_token is required")
        self.bot_token = bot_token
        self.rate_limit_seconds = rate_limit_seconds
        self._last_send_per_chat: Dict[str, float] = {}
        logger.debug("Telegram bot controller initialized")

    async def _wait_for_rate_limit(self, chat_id: str) -> None:
        """Wait if needed to respect per-chat rate limiting."""
        if self.rate_limit_seconds <= 0:
            return
        last_send = self._last_send_per_chat.get(chat_id, 0.0)
        elapsed = time.monotonic() - last_send
        wait_time = self.rate_limit_seconds - elapsed
        if wait_time > 0:
            logger.debug(f"Rate limiting chat {chat_id}: waiting {wait_time:.2f}s")
            await asyncio.sleep(wait_time)

    def _record_send(self, chat_id: str) -> None:
        """Record the timestamp of a successful send for rate limiting."""
        self._last_send_per_chat[chat_id] = time.monotonic()

    def _preprocess_text(self, text: str, parse_mode: Optional[ParseMode]) -> str:
        """Escape HTML entities and repair unbalanced tags when sending in HTML mode."""
        if parse_mode == ParseMode.HTML:
            text = escape_telegram_html(text)
            text = repair_html_tags(text)
        return text

    def _run_async_sync(
        self,
        coro: "Coroutine[Any, Any, T]",
        on_error: T,
        error_label: str,
    ) -> T:
        """Run a coroutine to completion from sync code, surviving caller event loops."""
        # Run in a fresh thread so asyncio.run() can install its own event loop
        # regardless of whether the caller is already inside a running loop.
        try:
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future: "concurrent.futures.Future[T]" = executor.submit(asyncio.run, coro)
                return future.result()
        except Exception as e:
            logger.error(f"Error in {error_label}: {e}")
            return on_error

    async def _send_chunks_plain_text(
        self,
        bot: Bot,
        chunks: List[str],
        chat_id: str,
        options: _SendOptions,
    ) -> bool:
        """Strip HTML tags from chunks and send as plain text. Used as fallback on parse errors."""
        for chunk in chunks:
            stripped = re.sub(r'<[^>]+>', '', chunk)
            await self._wait_for_rate_limit(chat_id)
            await bot.send_message(
                chat_id=chat_id,
                text=stripped,
                parse_mode=None,
                disable_web_page_preview=options.disable_web_page_preview,
                disable_notification=options.disable_notification,
                message_thread_id=options.message_thread_id,
            )
            self._record_send(chat_id)
        return True

    async def _send_with_new_bot(
        self,
        text: str,
        chat_ids: List[str],
        options: _SendOptions,
    ) -> Dict[str, bool]:
        if not chat_ids:
            logger.warning("No chat_ids provided")
            return {}

        chunks = split_message(text)
        bot = Bot(token=self.bot_token)
        results: Dict[str, bool] = {}
        try:
            for chat_id in chat_ids:
                try:
                    for chunk in chunks:
                        await self._wait_for_rate_limit(chat_id)
                        await bot.send_message(
                            chat_id=chat_id,
                            text=chunk,
                            parse_mode=options.parse_mode.value if options.parse_mode else None,
                            disable_web_page_preview=options.disable_web_page_preview,
                            disable_notification=options.disable_notification,
                            message_thread_id=options.message_thread_id,
                        )
                        self._record_send(chat_id)
                    results[chat_id] = True
                    logger.debug(f"Message sent successfully to {chat_id} ({len(chunks)} chunk(s))")
                except TelegramError as e:
                    if "Can't parse entities" in str(e) and options.parse_mode:
                        logger.warning(
                            f"HTML parse error for chat {chat_id}, retrying as plain text: {e}"
                        )
                        try:
                            results[chat_id] = await self._send_chunks_plain_text(
                                bot, chunks, chat_id, options,
                            )
                            logger.debug(f"Plain text fallback succeeded for {chat_id}")
                        except Exception as retry_err:
                            results[chat_id] = False
                            logger.error(f"Plain text fallback failed for {chat_id}: {retry_err}")
                    else:
                        results[chat_id] = False
                        logger.error(f"Telegram error for chat {chat_id}: {e}")
                except Exception as e:
                    results[chat_id] = False
                    logger.error(f"Unexpected error sending to {chat_id}: {e}")
        finally:
            await self._close_bot_session(bot)
        return results

    async def _close_bot_session(self, bot: Bot) -> None:
        """Close a Bot's HTTP session, tolerating both async and sync session types."""
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

    async def send_message(
        self,
        text: str,
        chat_ids: List[str],
        *,
        parse_mode: ParseMode = ParseMode.HTML,
        disable_web_page_preview: bool = False,
        disable_notification: bool = False,
    ) -> Dict[str, bool]:
        return await self._send_with_new_bot(
            text=self._preprocess_text(text, parse_mode),
            chat_ids=chat_ids,
            options=_SendOptions(
                parse_mode=parse_mode,
                disable_web_page_preview=disable_web_page_preview,
                disable_notification=disable_notification,
            ),
        )

    def send_message_sync(
        self,
        text: str,
        chat_ids: List[str],
        *,
        parse_mode: ParseMode = ParseMode.HTML,
        disable_web_page_preview: bool = False,
        disable_notification: bool = False,
    ) -> Dict[str, bool]:
        """Synchronously send a message, blocking until completion."""
        return self._run_async_sync(
            self.send_message(
                text=text,
                chat_ids=chat_ids,
                parse_mode=parse_mode,
                disable_web_page_preview=disable_web_page_preview,
                disable_notification=disable_notification,
            ),
            on_error={cid: False for cid in chat_ids},
            error_label=f"send_message_sync (chat_ids={len(chat_ids)})",
        )

    async def send_to_chat(
        self,
        chat_id: str,
        text: str,
        *,
        message_thread_id: Optional[int] = None,
        parse_mode: ParseMode = ParseMode.HTML,
        disable_web_page_preview: bool = False,
        disable_notification: bool = False,
    ) -> bool:
        """
        Send to a single chat, optionally targeting a supergroup topic.

        A thread id only applies to one supergroup, so this method takes a single
        chat_id rather than a list. Use send_message for fan-out without topics.
        """
        results = await self._send_with_new_bot(
            text=self._preprocess_text(text, parse_mode),
            chat_ids=[chat_id],
            options=_SendOptions(
                parse_mode=parse_mode,
                disable_web_page_preview=disable_web_page_preview,
                disable_notification=disable_notification,
                message_thread_id=message_thread_id,
            ),
        )
        return results.get(chat_id, False)

    def send_to_chat_sync(
        self,
        chat_id: str,
        text: str,
        *,
        message_thread_id: Optional[int] = None,
        parse_mode: ParseMode = ParseMode.HTML,
        disable_web_page_preview: bool = False,
        disable_notification: bool = False,
    ) -> bool:
        """Synchronously send to a single chat (optionally a topic), blocking until completion."""
        return self._run_async_sync(
            self.send_to_chat(
                chat_id=chat_id,
                text=text,
                message_thread_id=message_thread_id,
                parse_mode=parse_mode,
                disable_web_page_preview=disable_web_page_preview,
                disable_notification=disable_notification,
            ),
            on_error=False,
            error_label=f"send_to_chat_sync (chat_id={chat_id})",
        )

    async def send_rich_message(
        self,
        chat_id: str,
        rich_message: InputRichMessage,
        *,
        message_thread_id: Optional[int] = None,
        disable_notification: bool = False,
        protect_content: bool = False,
    ) -> bool:
        """
        Send a rich message (Bot API 10.1) to a single chat.

        Rich content -- tables, lists, headings, formulas, media, etc. -- is carried
        as an extended HTML or Markdown string inside `rich_message`; see
        InputRichMessage. Unlike send_message, the text is passed through untouched
        (no HTML escaping, tag repair, or splitting), since the caller supplies
        deliberate rich markup.

        python-telegram-bot 22.5 has no sendRichMessage wrapper, so this calls the
        endpoint directly via Bot.do_api_request.

        Returns True on success, False on failure (errors are logged, not raised).
        """
        api_kwargs: Dict[str, Any] = {
            "chat_id": chat_id,
            "rich_message": rich_message.to_dict(),
        }
        if message_thread_id is not None:
            api_kwargs["message_thread_id"] = message_thread_id
        if disable_notification:
            api_kwargs["disable_notification"] = True
        if protect_content:
            api_kwargs["protect_content"] = True

        bot = Bot(token=self.bot_token)
        try:
            await self._wait_for_rate_limit(chat_id)
            await bot.do_api_request("sendRichMessage", api_kwargs=api_kwargs)
            self._record_send(chat_id)
            logger.debug(f"Rich message sent successfully to {chat_id}")
            return True
        except TelegramError as e:
            logger.error(f"Telegram error sending rich message to {chat_id}: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error sending rich message to {chat_id}: {e}")
            return False
        finally:
            await self._close_bot_session(bot)

    def send_rich_message_sync(
        self,
        chat_id: str,
        rich_message: InputRichMessage,
        *,
        message_thread_id: Optional[int] = None,
        disable_notification: bool = False,
        protect_content: bool = False,
    ) -> bool:
        """Synchronously send a rich message, blocking until completion."""
        return self._run_async_sync(
            self.send_rich_message(
                chat_id=chat_id,
                rich_message=rich_message,
                message_thread_id=message_thread_id,
                disable_notification=disable_notification,
                protect_content=protect_content,
            ),
            on_error=False,
            error_label=f"send_rich_message_sync (chat_id={chat_id})",
        )

    async def send_formatted(
        self,
        title: str,
        fields: Dict[str, Any],
        chat_ids: List[str],
        *,
        emoji: Optional[str] = None,
        footer: Optional[str] = None,
    ) -> Dict[str, bool]:
        # We're constructing the HTML ourselves with per-field escaping, so bypass
        # _preprocess_text to avoid double-escaping our own formatting tags.
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
        return await self._send_with_new_bot(
            text=message,
            chat_ids=chat_ids,
            options=_SendOptions(parse_mode=ParseMode.HTML),
        )

    def send_formatted_sync(
        self,
        title: str,
        fields: Dict[str, Any],
        chat_ids: List[str],
        *,
        emoji: Optional[str] = None,
        footer: Optional[str] = None,
    ) -> Dict[str, bool]:
        """Synchronously send a formatted message, blocking until completion."""
        return self._run_async_sync(
            self.send_formatted(
                title=title,
                fields=fields,
                chat_ids=chat_ids,
                emoji=emoji,
                footer=footer,
            ),
            on_error={cid: False for cid in chat_ids},
            error_label=f"send_formatted_sync (chat_ids={len(chat_ids)})",
        )

    async def test_connection(self, chat_id: str) -> bool:
        result = await self.send_message("🔔 Telegram notification test successful!", [chat_id])
        return result.get(chat_id, False)

    def test_connection_sync(self, chat_id: str) -> bool:
        """Synchronously test connection, blocking until completion."""
        return self._run_async_sync(
            self.test_connection(chat_id),
            on_error=False,
            error_label=f"test_connection_sync (chat_id={chat_id})",
        )
