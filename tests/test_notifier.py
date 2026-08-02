"""
Tests for TelegramBotController.
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from telegram.error import TelegramError
from byteforge_telegram.notifier import TelegramBotController, ParseMode


class TestParseMode:
    """Tests for ParseMode enum."""

    def test_parse_mode_values(self):
        """Test ParseMode enum values."""
        assert ParseMode.HTML.value == "HTML"
        assert ParseMode.MARKDOWN.value == "Markdown"
        assert ParseMode.MARKDOWN_V2.value == "MarkdownV2"
        assert ParseMode.NONE.value is None


class TestTelegramBotController:
    """Tests for TelegramBotController class."""

    def test_init_with_valid_token(self):
        """Test TelegramBotController initialization with valid token."""
        controller = TelegramBotController("test_token_123")
        assert controller.bot_token == "test_token_123"

    def test_init_with_empty_token(self):
        """Test TelegramBotController initialization with empty token raises ValueError."""
        with pytest.raises(ValueError, match="bot_token is required"):
            TelegramBotController("")

    def test_init_with_none_token(self):
        """Test TelegramBotController initialization with None token raises ValueError."""
        with pytest.raises(ValueError, match="bot_token is required"):
            TelegramBotController(None)

    @pytest.mark.asyncio
    async def test_send_message_success(self):
        """Test sending message successfully."""
        controller = TelegramBotController("test_token")

        with patch('byteforge_telegram.notifier.Bot') as mock_bot_class:
            mock_bot = AsyncMock()
            mock_bot_class.return_value = mock_bot
            mock_bot.send_message = AsyncMock()

            result = await controller.send_message(
                text="Test message",
                chat_ids=["123", "456"]
            )

            assert result == {"123": True, "456": True}
            assert mock_bot.send_message.call_count == 2

    @pytest.mark.asyncio
    async def test_send_message_with_parse_mode(self):
        """Test that HTML formatting tags are preserved when using HTML parse mode."""
        controller = TelegramBotController("test_token")

        with patch('byteforge_telegram.notifier.Bot') as mock_bot_class:
            mock_bot = AsyncMock()
            mock_bot_class.return_value = mock_bot
            mock_bot.send_message = AsyncMock()

            # When using HTML parse mode, legitimate HTML tags are preserved
            # This allows users to send formatted messages
            await controller.send_message(
                text="<b>Bold</b>",
                chat_ids=["123"],
                parse_mode=ParseMode.HTML
            )

            # Test focus: HTML formatting tags are preserved (not escaped) and parse_mode is set.
            # Avoid asserting other kwargs here so adding new ones doesn't churn this test.
            mock_bot.send_message.assert_called_once()
            kwargs = mock_bot.send_message.call_args.kwargs
            assert kwargs["text"] == "<b>Bold</b>"
            assert kwargs["parse_mode"] == "HTML"

    @pytest.mark.asyncio
    async def test_send_message_with_options(self):
        """Test sending message with disable options."""
        controller = TelegramBotController("test_token")

        with patch('byteforge_telegram.notifier.Bot') as mock_bot_class:
            mock_bot = AsyncMock()
            mock_bot_class.return_value = mock_bot
            mock_bot.send_message = AsyncMock()

            await controller.send_message(
                text="Test",
                chat_ids=["123"],
                disable_web_page_preview=True,
                disable_notification=True
            )

            # Test focus: the disable_* flags propagate.
            mock_bot.send_message.assert_called_once()
            kwargs = mock_bot.send_message.call_args.kwargs
            assert kwargs["disable_web_page_preview"] is True
            assert kwargs["disable_notification"] is True

    @pytest.mark.asyncio
    async def test_send_message_empty_chat_ids(self):
        """Test sending message with empty chat_ids list."""
        controller = TelegramBotController("test_token")

        result = await controller.send_message(
            text="Test message",
            chat_ids=[]
        )

        assert result == {}

    @pytest.mark.asyncio
    async def test_send_message_telegram_error(self):
        """Test sending message when TelegramError occurs."""
        controller = TelegramBotController("test_token")

        with patch('byteforge_telegram.notifier.Bot') as mock_bot_class:
            mock_bot = AsyncMock()
            mock_bot_class.return_value = mock_bot
            mock_bot.send_message = AsyncMock(side_effect=TelegramError("Invalid chat"))

            result = await controller.send_message(
                text="Test",
                chat_ids=["123"]
            )

            assert result == {"123": False}

    @pytest.mark.asyncio
    async def test_send_message_mixed_results(self):
        """Test sending message with mixed success/failure."""
        controller = TelegramBotController("test_token")

        with patch('byteforge_telegram.notifier.Bot') as mock_bot_class:
            mock_bot = AsyncMock()
            mock_bot_class.return_value = mock_bot

            # First call succeeds, second fails
            mock_bot.send_message = AsyncMock(
                side_effect=[Mock(message_id=1), TelegramError("Error")]
            )

            result = await controller.send_message(
                text="Test",
                chat_ids=["123", "456"]
            )

            assert result == {"123": True, "456": False}

    @pytest.mark.asyncio
    async def test_send_formatted_basic(self):
        """Test sending formatted message."""
        controller = TelegramBotController("test_token")

        with patch('byteforge_telegram.notifier.Bot') as mock_bot_class:
            mock_bot = AsyncMock()
            mock_bot_class.return_value = mock_bot
            mock_bot.send_message = AsyncMock()

            result = await controller.send_formatted(
                title="Test Title",
                fields={"Field1": "Value1", "Field2": "Value2"},
                chat_ids=["123"]
            )

            assert result == {"123": True}
            call_args = mock_bot.send_message.call_args
            message_text = call_args[1]['text']

            assert "<b>Test Title</b>" in message_text
            assert "<b>Field1:</b> Value1" in message_text
            assert "<b>Field2:</b> Value2" in message_text

    @pytest.mark.asyncio
    async def test_send_formatted_with_emoji(self):
        """Test sending formatted message with emoji."""
        controller = TelegramBotController("test_token")

        with patch('byteforge_telegram.notifier.Bot') as mock_bot_class:
            mock_bot = AsyncMock()
            mock_bot_class.return_value = mock_bot
            mock_bot.send_message = AsyncMock()

            await controller.send_formatted(
                title="Test",
                fields={"Key": "Value"},
                chat_ids=["123"],
                emoji="✅"
            )

            call_args = mock_bot.send_message.call_args
            message_text = call_args[1]['text']
            assert "✅ <b>Test</b>" in message_text

    @pytest.mark.asyncio
    async def test_send_formatted_with_footer(self):
        """Test sending formatted message with footer."""
        controller = TelegramBotController("test_token")

        with patch('byteforge_telegram.notifier.Bot') as mock_bot_class:
            mock_bot = AsyncMock()
            mock_bot_class.return_value = mock_bot
            mock_bot.send_message = AsyncMock()

            await controller.send_formatted(
                title="Test",
                fields={"Key": "Value"},
                chat_ids=["123"],
                footer="Footer text"
            )

            call_args = mock_bot.send_message.call_args
            message_text = call_args[1]['text']
            assert "<i>Footer text</i>" in message_text

    @pytest.mark.asyncio
    async def test_send_formatted_with_none_value(self):
        """Test sending formatted message with None field value."""
        controller = TelegramBotController("test_token")

        with patch('byteforge_telegram.notifier.Bot') as mock_bot_class:
            mock_bot = AsyncMock()
            mock_bot_class.return_value = mock_bot
            mock_bot.send_message = AsyncMock()

            await controller.send_formatted(
                title="Test",
                fields={"Key1": "Value1", "Key2": None},
                chat_ids=["123"]
            )

            call_args = mock_bot.send_message.call_args
            message_text = call_args[1]['text']
            assert "<b>Key2:</b> N/A" in message_text

    @pytest.mark.asyncio
    async def test_test_connection(self):
        """Test connection test method."""
        controller = TelegramBotController("test_token")

        with patch('byteforge_telegram.notifier.Bot') as mock_bot_class:
            mock_bot = AsyncMock()
            mock_bot_class.return_value = mock_bot
            mock_bot.send_message = AsyncMock()

            result = await controller.test_connection("123")

            assert result is True
            call_args = mock_bot.send_message.call_args
            assert "test successful" in call_args[1]['text'].lower()

    @pytest.mark.asyncio
    async def test_test_connection_failure(self):
        """Test connection test when it fails."""
        controller = TelegramBotController("test_token")

        with patch('byteforge_telegram.notifier.Bot') as mock_bot_class:
            mock_bot = AsyncMock()
            mock_bot_class.return_value = mock_bot
            mock_bot.send_message = AsyncMock(side_effect=TelegramError("Error"))

            result = await controller.test_connection("123")

            assert result is False

    def test_send_message_sync(self):
        """Test synchronous send_message method."""
        controller = TelegramBotController("test_token")

        with patch('byteforge_telegram.notifier.Bot') as mock_bot_class:
            mock_bot = AsyncMock()
            mock_bot_class.return_value = mock_bot
            mock_bot.send_message = AsyncMock()

            result = controller.send_message_sync(
                text="Test",
                chat_ids=["123"]
            )

            # Result should be a dict
            assert isinstance(result, dict)
            assert "123" in result

    def test_send_formatted_sync(self):
        """Test synchronous send_formatted method."""
        controller = TelegramBotController("test_token")

        with patch('byteforge_telegram.notifier.Bot') as mock_bot_class:
            mock_bot = AsyncMock()
            mock_bot_class.return_value = mock_bot
            mock_bot.send_message = AsyncMock()

            result = controller.send_formatted_sync(
                title="Test",
                fields={"Key": "Value"},
                chat_ids=["123"]
            )

            assert isinstance(result, dict)
            assert "123" in result

    @pytest.mark.asyncio
    async def test_send_to_chat_forwards_thread_id(self):
        """send_to_chat passes message_thread_id through and returns the message_id."""
        controller = TelegramBotController("test_token")

        with patch('byteforge_telegram.notifier.Bot') as mock_bot_class:
            mock_bot = AsyncMock()
            mock_bot_class.return_value = mock_bot
            mock_bot.send_message = AsyncMock(return_value=Mock(message_id=555))

            result = await controller.send_to_chat(
                chat_id="-1001234567890",
                text="hello topic",
                message_thread_id=42,
            )

            assert result == 555
            mock_bot.send_message.assert_called_once()
            kwargs = mock_bot.send_message.call_args.kwargs
            assert kwargs["chat_id"] == "-1001234567890"
            assert kwargs["text"] == "hello topic"
            assert kwargs["message_thread_id"] == 42

    @pytest.mark.asyncio
    async def test_send_to_chat_without_thread_id(self):
        """send_to_chat defaults message_thread_id to None (regular chat send)."""
        controller = TelegramBotController("test_token")

        with patch('byteforge_telegram.notifier.Bot') as mock_bot_class:
            mock_bot = AsyncMock()
            mock_bot_class.return_value = mock_bot
            mock_bot.send_message = AsyncMock(return_value=Mock(message_id=1))

            result = await controller.send_to_chat(
                chat_id="123",
                text="plain",
            )

            assert result == 1
            kwargs = mock_bot.send_message.call_args.kwargs
            assert kwargs["message_thread_id"] is None
            assert kwargs["chat_id"] == "123"

    @pytest.mark.asyncio
    async def test_send_to_chat_failure_returns_none(self):
        """send_to_chat returns None when the underlying send fails."""
        controller = TelegramBotController("test_token")

        with patch('byteforge_telegram.notifier.Bot') as mock_bot_class:
            mock_bot = AsyncMock()
            mock_bot_class.return_value = mock_bot
            mock_bot.send_message = AsyncMock(side_effect=TelegramError("nope"))

            result = await controller.send_to_chat(
                chat_id="123",
                text="hi",
                message_thread_id=7,
            )

            assert result is None

    @pytest.mark.asyncio
    async def test_send_to_chat_forwards_reply_markup(self):
        """send_to_chat passes an inline keyboard dict through untouched."""
        controller = TelegramBotController("test_token")
        keyboard = {"inline_keyboard": [[{"text": "Approve", "callback_data": "ok"}]]}

        with patch('byteforge_telegram.notifier.Bot') as mock_bot_class:
            mock_bot = AsyncMock()
            mock_bot_class.return_value = mock_bot
            mock_bot.send_message = AsyncMock(return_value=Mock(message_id=7))

            result = await controller.send_to_chat(
                chat_id="123",
                text="approve?",
                reply_markup=keyboard,
            )

            assert result == 7
            kwargs = mock_bot.send_message.call_args.kwargs
            assert kwargs["reply_markup"] == keyboard

    @pytest.mark.asyncio
    async def test_send_to_chat_reply_markup_on_last_chunk_only(self):
        """When the text splits into chunks, the keyboard attaches to the last chunk only."""
        controller = TelegramBotController("test_token", rate_limit_seconds=0)
        keyboard = {"inline_keyboard": [[{"text": "Approve", "callback_data": "ok"}]]}
        long_text = "word " * 1500  # > 4096 chars, splits into multiple chunks

        with patch('byteforge_telegram.notifier.Bot') as mock_bot_class:
            mock_bot = AsyncMock()
            mock_bot_class.return_value = mock_bot
            mock_bot.send_message = AsyncMock(
                side_effect=[Mock(message_id=10), Mock(message_id=11)]
            )

            result = await controller.send_to_chat(
                chat_id="123",
                text=long_text,
                reply_markup=keyboard,
            )

            assert mock_bot.send_message.call_count == 2
            first_kwargs = mock_bot.send_message.call_args_list[0].kwargs
            last_kwargs = mock_bot.send_message.call_args_list[1].kwargs
            assert first_kwargs["reply_markup"] is None
            assert last_kwargs["reply_markup"] == keyboard
            # The returned message_id is the last chunk's — the keyboard-bearing message
            assert result == 11

    def test_send_to_chat_sync(self):
        """Sync wrapper returns the message_id and forwards thread id."""
        controller = TelegramBotController("test_token")

        with patch('byteforge_telegram.notifier.Bot') as mock_bot_class:
            mock_bot = AsyncMock()
            mock_bot_class.return_value = mock_bot
            mock_bot.send_message = AsyncMock(return_value=Mock(message_id=321))

            result = controller.send_to_chat_sync(
                chat_id="-1001234567890",
                text="hi",
                message_thread_id=99,
            )

            assert result == 321
            kwargs = mock_bot.send_message.call_args.kwargs
            assert kwargs["message_thread_id"] == 99

    def test_send_to_chat_sync_failure_returns_none(self):
        """Sync wrapper returns None when the send fails."""
        controller = TelegramBotController("test_token")

        with patch('byteforge_telegram.notifier.Bot') as mock_bot_class:
            mock_bot = AsyncMock()
            mock_bot_class.return_value = mock_bot
            mock_bot.send_message = AsyncMock(side_effect=TelegramError("nope"))

            result = controller.send_to_chat_sync(
                chat_id="123",
                text="hi",
            )

            assert result is None

    @pytest.mark.asyncio
    async def test_edit_message_text(self):
        """edit_message_text forwards text, ids, and reply_markup to Bot.edit_message_text."""
        controller = TelegramBotController("test_token")
        keyboard = {"inline_keyboard": [[{"text": "Open", "url": "https://example.com"}]]}

        with patch('byteforge_telegram.notifier.Bot') as mock_bot_class:
            mock_bot = AsyncMock()
            mock_bot_class.return_value = mock_bot
            mock_bot.edit_message_text = AsyncMock()

            result = await controller.edit_message_text(
                chat_id="123",
                message_id=555,
                text="<b>Approved by Jason</b>",
                reply_markup=keyboard,
            )

            assert result is True
            mock_bot.edit_message_text.assert_called_once()
            kwargs = mock_bot.edit_message_text.call_args.kwargs
            assert kwargs["chat_id"] == "123"
            assert kwargs["message_id"] == 555
            assert kwargs["text"] == "<b>Approved by Jason</b>"
            assert kwargs["parse_mode"] == "HTML"
            assert kwargs["reply_markup"] == keyboard

    @pytest.mark.asyncio
    async def test_edit_message_text_strips_keyboard_by_default(self):
        """Omitting reply_markup passes None, which removes an existing keyboard."""
        controller = TelegramBotController("test_token")

        with patch('byteforge_telegram.notifier.Bot') as mock_bot_class:
            mock_bot = AsyncMock()
            mock_bot_class.return_value = mock_bot
            mock_bot.edit_message_text = AsyncMock()

            result = await controller.edit_message_text(
                chat_id="123",
                message_id=555,
                text="done",
            )

            assert result is True
            kwargs = mock_bot.edit_message_text.call_args.kwargs
            assert kwargs["reply_markup"] is None

    @pytest.mark.asyncio
    async def test_edit_message_text_failure(self):
        """edit_message_text returns False on TelegramError."""
        controller = TelegramBotController("test_token")

        with patch('byteforge_telegram.notifier.Bot') as mock_bot_class:
            mock_bot = AsyncMock()
            mock_bot_class.return_value = mock_bot
            mock_bot.edit_message_text = AsyncMock(
                side_effect=TelegramError("message is not modified")
            )

            result = await controller.edit_message_text(
                chat_id="123",
                message_id=555,
                text="same text",
            )

            assert result is False

    def test_edit_message_text_sync(self):
        """Sync wrapper for edit_message_text returns a bool."""
        controller = TelegramBotController("test_token")

        with patch('byteforge_telegram.notifier.Bot') as mock_bot_class:
            mock_bot = AsyncMock()
            mock_bot_class.return_value = mock_bot
            mock_bot.edit_message_text = AsyncMock()

            keyboard = {"inline_keyboard": [[{"text": "Open", "url": "https://example.com"}]]}
            result = controller.edit_message_text_sync(
                chat_id="123",
                message_id=1,
                text="hi",
                reply_markup=keyboard,
            )

            assert result is True
            kwargs = mock_bot.edit_message_text.call_args.kwargs
            assert kwargs["chat_id"] == "123"
            assert kwargs["message_id"] == 1
            assert kwargs["text"] == "hi"
            assert kwargs["reply_markup"] == keyboard

    @pytest.mark.asyncio
    async def test_edit_message_reply_markup(self):
        """edit_message_reply_markup forwards ids and keyboard, leaving text alone."""
        controller = TelegramBotController("test_token")
        keyboard = {"inline_keyboard": [[{"text": "Yes, reject", "callback_data": "confirm"}]]}

        with patch('byteforge_telegram.notifier.Bot') as mock_bot_class:
            mock_bot = AsyncMock()
            mock_bot_class.return_value = mock_bot
            mock_bot.edit_message_reply_markup = AsyncMock()

            result = await controller.edit_message_reply_markup(
                chat_id="123",
                message_id=555,
                reply_markup=keyboard,
            )

            assert result is True
            mock_bot.edit_message_reply_markup.assert_called_once()
            kwargs = mock_bot.edit_message_reply_markup.call_args.kwargs
            assert kwargs["chat_id"] == "123"
            assert kwargs["message_id"] == 555
            assert kwargs["reply_markup"] == keyboard
            assert "text" not in kwargs

    @pytest.mark.asyncio
    async def test_edit_message_reply_markup_strips_keyboard_by_default(self):
        """Omitting reply_markup passes None, which removes the keyboard."""
        controller = TelegramBotController("test_token")

        with patch('byteforge_telegram.notifier.Bot') as mock_bot_class:
            mock_bot = AsyncMock()
            mock_bot_class.return_value = mock_bot
            mock_bot.edit_message_reply_markup = AsyncMock()

            result = await controller.edit_message_reply_markup(
                chat_id="123",
                message_id=555,
            )

            assert result is True
            kwargs = mock_bot.edit_message_reply_markup.call_args.kwargs
            assert kwargs["reply_markup"] is None

    @pytest.mark.asyncio
    async def test_edit_message_reply_markup_failure(self):
        """edit_message_reply_markup returns False on TelegramError."""
        controller = TelegramBotController("test_token")

        with patch('byteforge_telegram.notifier.Bot') as mock_bot_class:
            mock_bot = AsyncMock()
            mock_bot_class.return_value = mock_bot
            mock_bot.edit_message_reply_markup = AsyncMock(
                side_effect=TelegramError("message is not modified")
            )

            result = await controller.edit_message_reply_markup(
                chat_id="123",
                message_id=555,
                reply_markup={"inline_keyboard": []},
            )

            assert result is False

    def test_edit_message_reply_markup_sync(self):
        """Sync wrapper forwards ids and keyboard to Bot.edit_message_reply_markup."""
        controller = TelegramBotController("test_token")
        keyboard = {"inline_keyboard": [[{"text": "Cancel", "callback_data": "cancel"}]]}

        with patch('byteforge_telegram.notifier.Bot') as mock_bot_class:
            mock_bot = AsyncMock()
            mock_bot_class.return_value = mock_bot
            mock_bot.edit_message_reply_markup = AsyncMock()

            result = controller.edit_message_reply_markup_sync(
                chat_id="123",
                message_id=42,
                reply_markup=keyboard,
            )

            assert result is True
            kwargs = mock_bot.edit_message_reply_markup.call_args.kwargs
            assert kwargs["chat_id"] == "123"
            assert kwargs["message_id"] == 42
            assert kwargs["reply_markup"] == keyboard

    @pytest.mark.asyncio
    async def test_answer_callback_query(self):
        """answer_callback_query forwards id, text, and show_alert."""
        controller = TelegramBotController("test_token")

        with patch('byteforge_telegram.notifier.Bot') as mock_bot_class:
            mock_bot = AsyncMock()
            mock_bot_class.return_value = mock_bot
            mock_bot.answer_callback_query = AsyncMock()

            result = await controller.answer_callback_query(
                "query-id-1",
                text="Already handled by Sarah.",
                show_alert=True,
            )

            assert result is True
            mock_bot.answer_callback_query.assert_called_once()
            kwargs = mock_bot.answer_callback_query.call_args.kwargs
            assert kwargs["callback_query_id"] == "query-id-1"
            assert kwargs["text"] == "Already handled by Sarah."
            assert kwargs["show_alert"] is True

    @pytest.mark.asyncio
    async def test_answer_callback_query_failure(self):
        """answer_callback_query returns False on TelegramError."""
        controller = TelegramBotController("test_token")

        with patch('byteforge_telegram.notifier.Bot') as mock_bot_class:
            mock_bot = AsyncMock()
            mock_bot_class.return_value = mock_bot
            mock_bot.answer_callback_query = AsyncMock(
                side_effect=TelegramError("query is too old")
            )

            result = await controller.answer_callback_query("query-id-1")

            assert result is False

    def test_answer_callback_query_sync(self):
        """Sync wrapper for answer_callback_query returns a bool."""
        controller = TelegramBotController("test_token")

        with patch('byteforge_telegram.notifier.Bot') as mock_bot_class:
            mock_bot = AsyncMock()
            mock_bot_class.return_value = mock_bot
            mock_bot.answer_callback_query = AsyncMock()

            result = controller.answer_callback_query_sync(
                "query-id-1", text="Done", show_alert=True
            )

            assert result is True
            kwargs = mock_bot.answer_callback_query.call_args.kwargs
            assert kwargs["callback_query_id"] == "query-id-1"
            assert kwargs["text"] == "Done"
            assert kwargs["show_alert"] is True

    def test_test_connection_sync(self):
        """Test synchronous test_connection method."""
        controller = TelegramBotController("test_token")

        with patch('byteforge_telegram.notifier.Bot') as mock_bot_class:
            mock_bot = AsyncMock()
            mock_bot_class.return_value = mock_bot
            mock_bot.send_message = AsyncMock()

            result = controller.test_connection_sync("123")

            assert isinstance(result, bool)
