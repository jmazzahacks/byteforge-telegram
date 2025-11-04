"""
Tests for TelegramResponse model.
"""

import pytest
from byteforge_telegram.models import TelegramResponse


class TestTelegramResponse:
    """Tests for TelegramResponse dataclass."""

    def test_basic_response_creation(self):
        """Test creating a basic TelegramResponse."""
        response = TelegramResponse(
            method='sendMessage',
            chat_id=12345,
            text='Hello, World!'
        )

        assert response.method == 'sendMessage'
        assert response.chat_id == 12345
        assert response.text == 'Hello, World!'
        assert response.parse_mode == 'HTML'  # default
        assert response.reply_markup is None
        assert response.disable_web_page_preview is False
        assert response.disable_notification is False

    def test_response_with_all_fields(self):
        """Test creating a TelegramResponse with all fields."""
        reply_markup = {
            'inline_keyboard': [[
                {'text': 'Button', 'callback_data': 'button_1'}
            ]]
        }

        response = TelegramResponse(
            method='sendMessage',
            chat_id=67890,
            text='<b>Bold text</b>',
            parse_mode='HTML',
            reply_markup=reply_markup,
            disable_web_page_preview=True,
            disable_notification=True
        )

        assert response.method == 'sendMessage'
        assert response.chat_id == 67890
        assert response.text == '<b>Bold text</b>'
        assert response.parse_mode == 'HTML'
        assert response.reply_markup == reply_markup
        assert response.disable_web_page_preview is True
        assert response.disable_notification is True

    def test_to_dict_basic(self):
        """Test converting basic TelegramResponse to dict."""
        response = TelegramResponse(
            method='sendMessage',
            chat_id=12345,
            text='Test message'
        )

        result = response.to_dict()

        assert isinstance(result, dict)
        assert result['method'] == 'sendMessage'
        assert result['chat_id'] == 12345
        assert result['text'] == 'Test message'
        assert result['parse_mode'] == 'HTML'
        assert 'reply_markup' not in result
        assert 'disable_web_page_preview' not in result
        assert 'disable_notification' not in result

    def test_to_dict_with_all_fields(self):
        """Test converting TelegramResponse with all fields to dict."""
        reply_markup = {'keyboard': [['Yes', 'No']]}

        response = TelegramResponse(
            method='sendMessage',
            chat_id=99999,
            text='Choose an option',
            parse_mode='Markdown',
            reply_markup=reply_markup,
            disable_web_page_preview=True,
            disable_notification=True
        )

        result = response.to_dict()

        assert result['method'] == 'sendMessage'
        assert result['chat_id'] == 99999
        assert result['text'] == 'Choose an option'
        assert result['parse_mode'] == 'Markdown'
        assert result['reply_markup'] == reply_markup
        assert result['disable_web_page_preview'] is True
        assert result['disable_notification'] is True

    def test_to_dict_only_includes_true_boolean_flags(self):
        """Test that to_dict only includes boolean flags when True."""
        response = TelegramResponse(
            method='sendMessage',
            chat_id=12345,
            text='Test',
            disable_web_page_preview=False,
            disable_notification=False
        )

        result = response.to_dict()

        # False values should not be included
        assert 'disable_web_page_preview' not in result
        assert 'disable_notification' not in result

    def test_to_dict_with_none_reply_markup(self):
        """Test that to_dict excludes reply_markup when None."""
        response = TelegramResponse(
            method='sendMessage',
            chat_id=12345,
            text='Test',
            reply_markup=None
        )

        result = response.to_dict()

        assert 'reply_markup' not in result

    def test_to_dict_with_empty_reply_markup(self):
        """Test that to_dict excludes reply_markup when empty dict."""
        response = TelegramResponse(
            method='sendMessage',
            chat_id=12345,
            text='Test',
            reply_markup={}
        )

        result = response.to_dict()

        # Empty dict is falsy in Python, so it won't be included
        assert 'reply_markup' not in result

    def test_different_parse_modes(self):
        """Test TelegramResponse with different parse modes."""
        modes = ['HTML', 'Markdown', 'MarkdownV2']

        for mode in modes:
            response = TelegramResponse(
                method='sendMessage',
                chat_id=12345,
                text='Test',
                parse_mode=mode
            )

            assert response.parse_mode == mode
            result = response.to_dict()
            assert result['parse_mode'] == mode

    def test_response_immutability_check(self):
        """Test that TelegramResponse fields can be modified (dataclass is mutable by default)."""
        response = TelegramResponse(
            method='sendMessage',
            chat_id=12345,
            text='Original text'
        )

        # Dataclass is mutable by default
        response.text = 'Modified text'
        assert response.text == 'Modified text'
