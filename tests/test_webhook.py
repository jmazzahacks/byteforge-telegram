"""
Tests for WebhookManager.
"""

import pytest
from unittest.mock import Mock, patch
import requests
from byteforge_telegram.webhook import WebhookManager


class TestWebhookManager:
    """Tests for WebhookManager class."""

    def test_init_with_valid_token(self):
        """Test WebhookManager initialization with valid token."""
        manager = WebhookManager("test_token_123")
        assert manager.bot_token == "test_token_123"
        assert manager.base_url == "https://api.telegram.org/bottest_token_123"

    def test_init_with_empty_token(self):
        """Test WebhookManager initialization with empty token raises ValueError."""
        with pytest.raises(ValueError, match="bot_token is required"):
            WebhookManager("")

    def test_init_with_none_token(self):
        """Test WebhookManager initialization with None token raises ValueError."""
        with pytest.raises(ValueError, match="bot_token is required"):
            WebhookManager(None)

    @patch('byteforge_telegram.webhook.requests.post')
    def test_set_webhook_success(self, mock_post):
        """Test setting webhook successfully."""
        mock_response = Mock()
        mock_response.json.return_value = {
            'ok': True,
            'description': 'Webhook was set'
        }
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        manager = WebhookManager("test_token")
        result = manager.set_webhook("https://example.com/webhook")

        assert result['success'] is True
        assert result['description'] == 'Webhook was set'
        mock_post.assert_called_once_with(
            "https://api.telegram.org/bottest_token/setWebhook",
            json={'url': 'https://example.com/webhook'},
            timeout=10
        )

    @patch('byteforge_telegram.webhook.requests.post')
    def test_set_webhook_with_custom_timeout(self, mock_post):
        """Test setting webhook with custom timeout."""
        mock_response = Mock()
        mock_response.json.return_value = {'ok': True, 'description': 'Set'}
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        manager = WebhookManager("test_token")
        manager.set_webhook("https://example.com/webhook", timeout=30)

        mock_post.assert_called_once_with(
            "https://api.telegram.org/bottest_token/setWebhook",
            json={'url': 'https://example.com/webhook'},
            timeout=30
        )

    def test_set_webhook_non_https_url(self):
        """Test setting webhook with non-HTTPS URL raises ValueError."""
        manager = WebhookManager("test_token")

        with pytest.raises(ValueError, match="Webhook URL must use HTTPS"):
            manager.set_webhook("http://example.com/webhook")

    @patch('byteforge_telegram.webhook.requests.post')
    def test_set_webhook_api_failure(self, mock_post):
        """Test setting webhook when API returns failure."""
        mock_response = Mock()
        mock_response.json.return_value = {
            'ok': False,
            'description': 'Bad webhook URL'
        }
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        manager = WebhookManager("test_token")
        result = manager.set_webhook("https://example.com/webhook")

        assert result['success'] is False
        assert result['description'] == 'Bad webhook URL'

    @patch('byteforge_telegram.webhook.requests.post')
    def test_set_webhook_request_exception(self, mock_post):
        """Test setting webhook when request raises exception."""
        mock_post.side_effect = requests.exceptions.ConnectionError("Network error")

        manager = WebhookManager("test_token")
        result = manager.set_webhook("https://example.com/webhook")

        assert result['success'] is False
        assert 'Request error' in result['description']
        assert 'Network error' in result['description']

    @patch('byteforge_telegram.webhook.requests.get')
    def test_get_webhook_info_success(self, mock_get):
        """Test getting webhook info successfully."""
        webhook_info = {
            'url': 'https://example.com/webhook',
            'has_custom_certificate': False,
            'pending_update_count': 0
        }
        mock_response = Mock()
        mock_response.json.return_value = {
            'ok': True,
            'result': webhook_info
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        manager = WebhookManager("test_token")
        result = manager.get_webhook_info()

        assert result == webhook_info
        mock_get.assert_called_once_with(
            "https://api.telegram.org/bottest_token/getWebhookInfo",
            timeout=10
        )

    @patch('byteforge_telegram.webhook.requests.get')
    def test_get_webhook_info_with_custom_timeout(self, mock_get):
        """Test getting webhook info with custom timeout."""
        mock_response = Mock()
        mock_response.json.return_value = {'ok': True, 'result': {}}
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        manager = WebhookManager("test_token")
        manager.get_webhook_info(timeout=20)

        mock_get.assert_called_once_with(
            "https://api.telegram.org/bottest_token/getWebhookInfo",
            timeout=20
        )

    @patch('byteforge_telegram.webhook.requests.get')
    def test_get_webhook_info_api_failure(self, mock_get):
        """Test getting webhook info when API returns failure."""
        mock_response = Mock()
        mock_response.json.return_value = {
            'ok': False,
            'description': 'Bot not found'
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        manager = WebhookManager("test_token")
        result = manager.get_webhook_info()

        assert result is None

    @patch('byteforge_telegram.webhook.requests.get')
    def test_get_webhook_info_request_exception(self, mock_get):
        """Test getting webhook info when request raises exception."""
        mock_get.side_effect = requests.exceptions.Timeout("Request timeout")

        manager = WebhookManager("test_token")
        result = manager.get_webhook_info()

        assert result is None

    @patch('byteforge_telegram.webhook.requests.post')
    def test_delete_webhook_success(self, mock_post):
        """Test deleting webhook successfully."""
        mock_response = Mock()
        mock_response.json.return_value = {
            'ok': True,
            'description': 'Webhook was deleted'
        }
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        manager = WebhookManager("test_token")
        result = manager.delete_webhook()

        assert result['success'] is True
        assert result['description'] == 'Webhook was deleted'
        mock_post.assert_called_once_with(
            "https://api.telegram.org/bottest_token/deleteWebhook",
            timeout=10
        )

    @patch('byteforge_telegram.webhook.requests.post')
    def test_delete_webhook_with_custom_timeout(self, mock_post):
        """Test deleting webhook with custom timeout."""
        mock_response = Mock()
        mock_response.json.return_value = {'ok': True}
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        manager = WebhookManager("test_token")
        manager.delete_webhook(timeout=25)

        mock_post.assert_called_once_with(
            "https://api.telegram.org/bottest_token/deleteWebhook",
            timeout=25
        )

    @patch('byteforge_telegram.webhook.requests.post')
    def test_delete_webhook_api_failure(self, mock_post):
        """Test deleting webhook when API returns failure."""
        mock_response = Mock()
        mock_response.json.return_value = {
            'ok': False,
            'description': 'Cannot delete webhook'
        }
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        manager = WebhookManager("test_token")
        result = manager.delete_webhook()

        assert result['success'] is False
        assert result['description'] == 'Cannot delete webhook'

    @patch('byteforge_telegram.webhook.requests.post')
    def test_delete_webhook_request_exception(self, mock_post):
        """Test deleting webhook when request raises exception."""
        mock_post.side_effect = requests.exceptions.RequestException("Connection failed")

        manager = WebhookManager("test_token")
        result = manager.delete_webhook()

        assert result['success'] is False
        assert 'Request error' in result['description']
        assert 'Connection failed' in result['description']
