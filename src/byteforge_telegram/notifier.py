"""
Generic Telegram notification module.

A reusable Telegram bot notification system that can be used across different projects.
"""

import logging
from typing import Optional, List, Dict, Any
from enum import Enum
import asyncio
from telegram import Bot
from telegram.error import TelegramError

logger = logging.getLogger(__name__)


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
        try:
            try:
                asyncio.get_running_loop()
                asyncio.create_task(
                    self.send_message(
                        text=text,
                        chat_ids=chat_ids,
                        parse_mode=parse_mode,
                        disable_web_page_preview=disable_web_page_preview,
                        disable_notification=disable_notification,
                    )
                )
                return {cid: True for cid in chat_ids}
            except RuntimeError:
                return asyncio.run(
                    self.send_message(
                        text=text,
                        chat_ids=chat_ids,
                        parse_mode=parse_mode,
                        disable_web_page_preview=disable_web_page_preview,
                        disable_notification=disable_notification,
                    )
                )
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
        parts: List[str] = []
        if emoji:
            parts.append(f"{emoji} <b>{title}</b>")
        else:
            parts.append(f"<b>{title}</b>")
        parts.append("")
        for key, value in fields.items():
            if value is None:
                value = "N/A"
            parts.append(f"<b>{key}:</b> {value}")
        if footer:
            parts.append("")
            parts.append(f"<i>{footer}</i>")
        message = "\n".join(parts)
        return await self.send_message(message, chat_ids)

    def send_formatted_sync(
        self,
        title: str,
        fields: Dict[str, Any],
        chat_ids: List[str],
        emoji: Optional[str] = None,
        footer: Optional[str] = None,
    ) -> Dict[str, bool]:
        try:
            try:
                asyncio.get_running_loop()
                asyncio.create_task(
                    self.send_formatted(
                        title=title,
                        fields=fields,
                        chat_ids=chat_ids,
                        emoji=emoji,
                        footer=footer,
                    )
                )
                return {cid: True for cid in chat_ids}
            except RuntimeError:
                return asyncio.run(
                    self.send_formatted(
                        title=title,
                        fields=fields,
                        chat_ids=chat_ids,
                        emoji=emoji,
                        footer=footer,
                    )
                )
        except Exception as e:
            logger.error(f"Error in send_formatted_sync (chat_ids={len(chat_ids)}): {e}")
            return {cid: False for cid in chat_ids}

    async def test_connection(self, chat_id: str) -> bool:
        result = await self.send_message("🔔 Telegram notification test successful!", [chat_id])
        return result.get(chat_id, False)

    def test_connection_sync(self, chat_id: str) -> bool:
        try:
            try:
                asyncio.get_running_loop()
                asyncio.create_task(self.test_connection(chat_id))
                return True
            except RuntimeError:
                return asyncio.run(self.test_connection(chat_id))
        except Exception as e:
            logger.error(f"Error in test_connection_sync (chat_id={chat_id}): {e}")
            return False
