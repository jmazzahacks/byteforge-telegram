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
        """Test sending message with different parse modes."""
        controller = TelegramBotController("test_token")

        with patch('byteforge_telegram.notifier.Bot') as mock_bot_class:
            mock_bot = AsyncMock()
            mock_bot_class.return_value = mock_bot
            mock_bot.send_message = AsyncMock()

            await controller.send_message(
                text="<b>Bold</b>",
                chat_ids=["123"],
                parse_mode=ParseMode.HTML
            )

            mock_bot.send_message.assert_called_once_with(
                chat_id="123",
                text="<b>Bold</b>",
                parse_mode="HTML",
                disable_web_page_preview=False,
                disable_notification=False
            )

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

            mock_bot.send_message.assert_called_once_with(
                chat_id="123",
                text="Test",
                parse_mode="HTML",
                disable_web_page_preview=True,
                disable_notification=True
            )

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
                side_effect=[None, TelegramError("Error")]
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

    def test_test_connection_sync(self):
        """Test synchronous test_connection method."""
        controller = TelegramBotController("test_token")

        with patch('byteforge_telegram.notifier.Bot') as mock_bot_class:
            mock_bot = AsyncMock()
            mock_bot_class.return_value = mock_bot
            mock_bot.send_message = AsyncMock()

            result = controller.test_connection_sync("123")

            assert isinstance(result, bool)
