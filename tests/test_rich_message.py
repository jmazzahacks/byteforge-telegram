"""
Tests for Rich Message support (Bot API 10.1).

Covers the InputRichMessage model and TelegramBotController.send_rich_message,
which calls the sendRichMessage endpoint via Bot.do_api_request (python-telegram-bot
22.5 has no native wrapper for it).
"""
import pytest
from unittest.mock import AsyncMock, patch
from telegram.error import TelegramError
from byteforge_telegram.notifier import TelegramBotController
from byteforge_telegram.models import InputRichMessage


class TestInputRichMessage:
    """Validation and serialization of the InputRichMessage model."""

    def test_html_only_to_dict(self):
        msg = InputRichMessage(html="<table><tr><td>a</td></tr></table>")
        assert msg.to_dict() == {"html": "<table><tr><td>a</td></tr></table>"}

    def test_markdown_only_to_dict(self):
        msg = InputRichMessage(markdown="# Heading")
        assert msg.to_dict() == {"markdown": "# Heading"}

    def test_optional_flags_included_only_when_true(self):
        msg = InputRichMessage(html="<b>x</b>", is_rtl=True, skip_entity_detection=True)
        assert msg.to_dict() == {
            "html": "<b>x</b>",
            "is_rtl": True,
            "skip_entity_detection": True,
        }

    def test_false_flags_omitted(self):
        msg = InputRichMessage(html="<b>x</b>")
        assert "is_rtl" not in msg.to_dict()
        assert "skip_entity_detection" not in msg.to_dict()

    def test_requires_exactly_one_of_html_or_markdown_neither(self):
        with pytest.raises(ValueError, match="Exactly one"):
            InputRichMessage()

    def test_requires_exactly_one_of_html_or_markdown_both(self):
        with pytest.raises(ValueError, match="Exactly one"):
            InputRichMessage(html="<b>x</b>", markdown="x")

    def test_empty_html_treated_as_not_provided(self):
        # An empty string must not slip past validation as a valid body.
        with pytest.raises(ValueError, match="Exactly one"):
            InputRichMessage(html="")

    def test_empty_string_does_not_count_as_the_one_provided(self):
        # html="" + a real markdown should be accepted (empty html is "not provided").
        msg = InputRichMessage(html="", markdown="# ok")
        assert msg.to_dict() == {"markdown": "# ok"}


class TestSendRichMessage:
    """End-to-end behavior of send_rich_message / send_rich_message_sync."""

    @pytest.mark.asyncio
    async def test_send_rich_message_calls_endpoint(self):
        controller = TelegramBotController("test_token")

        with patch("byteforge_telegram.notifier.Bot") as mock_bot_class:
            mock_bot = AsyncMock()
            mock_bot_class.return_value = mock_bot
            mock_bot.do_api_request = AsyncMock(return_value={})

            msg = InputRichMessage(html="<ul><li>one</li><li>two</li></ul>")
            result = await controller.send_rich_message("123", msg)

            assert result is True
            mock_bot.do_api_request.assert_awaited_once()
            args, kwargs = mock_bot.do_api_request.call_args
            assert args[0] == "sendRichMessage"
            api_kwargs = kwargs["api_kwargs"]
            assert api_kwargs["chat_id"] == "123"
            assert api_kwargs["rich_message"] == {"html": "<ul><li>one</li><li>two</li></ul>"}
            # Untouched: no escaping/repair applied to deliberate rich markup
            assert "&lt;" not in api_kwargs["rich_message"]["html"]

    @pytest.mark.asyncio
    async def test_send_rich_message_passes_optional_params(self):
        controller = TelegramBotController("test_token")

        with patch("byteforge_telegram.notifier.Bot") as mock_bot_class:
            mock_bot = AsyncMock()
            mock_bot_class.return_value = mock_bot
            mock_bot.do_api_request = AsyncMock(return_value={})

            msg = InputRichMessage(markdown="# Title")
            await controller.send_rich_message(
                "123",
                msg,
                message_thread_id=42,
                disable_notification=True,
                protect_content=True,
            )

            api_kwargs = mock_bot.do_api_request.call_args.kwargs["api_kwargs"]
            assert api_kwargs["message_thread_id"] == 42
            assert api_kwargs["disable_notification"] is True
            assert api_kwargs["protect_content"] is True

    @pytest.mark.asyncio
    async def test_send_rich_message_omits_unset_optionals(self):
        controller = TelegramBotController("test_token")

        with patch("byteforge_telegram.notifier.Bot") as mock_bot_class:
            mock_bot = AsyncMock()
            mock_bot_class.return_value = mock_bot
            mock_bot.do_api_request = AsyncMock(return_value={})

            await controller.send_rich_message("123", InputRichMessage(html="<b>x</b>"))

            api_kwargs = mock_bot.do_api_request.call_args.kwargs["api_kwargs"]
            assert "message_thread_id" not in api_kwargs
            assert "disable_notification" not in api_kwargs
            assert "protect_content" not in api_kwargs

    @pytest.mark.asyncio
    async def test_send_rich_message_returns_false_on_error(self):
        controller = TelegramBotController("test_token")

        with patch("byteforge_telegram.notifier.Bot") as mock_bot_class:
            mock_bot = AsyncMock()
            mock_bot_class.return_value = mock_bot
            mock_bot.do_api_request = AsyncMock(side_effect=TelegramError("Bad Request"))

            result = await controller.send_rich_message("123", InputRichMessage(html="<b>x</b>"))
            assert result is False

    def test_send_rich_message_sync(self):
        controller = TelegramBotController("test_token")

        with patch("byteforge_telegram.notifier.Bot") as mock_bot_class:
            mock_bot = AsyncMock()
            mock_bot_class.return_value = mock_bot
            mock_bot.do_api_request = AsyncMock(return_value={})

            result = controller.send_rich_message_sync(
                "123", InputRichMessage(html="<table><tr><td>x</td></tr></table>")
            )

            assert result is True
            mock_bot.do_api_request.assert_awaited_once()
            assert mock_bot.do_api_request.call_args.args[0] == "sendRichMessage"
