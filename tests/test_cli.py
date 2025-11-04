"""
Tests for CLI tool.
"""

import pytest
from unittest.mock import Mock, patch
from io import StringIO
from byteforge_telegram.cli import main, print_webhook_info


class TestPrintWebhookInfo:
    """Tests for print_webhook_info function."""

    def test_print_basic_webhook_info(self, capsys):
        """Test printing basic webhook info."""
        info = {
            'url': 'https://example.com/webhook',
            'has_custom_certificate': False,
            'pending_update_count': 5
        }

        print_webhook_info(info)

        captured = capsys.readouterr()
        assert 'WEBHOOK INFO' in captured.out
        assert 'https://example.com/webhook' in captured.out
        assert 'Has custom certificate: False' in captured.out
        assert 'Pending update count: 5' in captured.out

    def test_print_webhook_info_with_error(self, capsys):
        """Test printing webhook info with error message."""
        info = {
            'url': 'https://example.com/webhook',
            'has_custom_certificate': False,
            'pending_update_count': 0,
            'last_error_message': 'Connection failed',
            'last_error_date': 1234567890
        }

        print_webhook_info(info)

        captured = capsys.readouterr()
        assert 'Last error: Connection failed' in captured.out
        assert 'Last error date: 1234567890' in captured.out

    def test_print_webhook_info_with_max_connections(self, capsys):
        """Test printing webhook info with max connections."""
        info = {
            'url': 'https://example.com/webhook',
            'has_custom_certificate': False,
            'pending_update_count': 0,
            'max_connections': 40
        }

        print_webhook_info(info)

        captured = capsys.readouterr()
        assert 'Max connections: 40' in captured.out

    def test_print_webhook_info_not_set(self, capsys):
        """Test printing webhook info when URL is not set."""
        info = {
            'has_custom_certificate': False,
            'pending_update_count': 0
        }

        print_webhook_info(info)

        captured = capsys.readouterr()
        assert '(not set)' in captured.out


class TestCLIMain:
    """Tests for CLI main function."""

    @patch('byteforge_telegram.cli.WebhookManager')
    @patch('sys.argv', ['prog', '--token', 'test_token', '--url', 'https://example.com/webhook'])
    def test_set_webhook_success(self, mock_manager_class):
        """Test setting webhook via CLI."""
        mock_manager = Mock()
        mock_manager_class.return_value = mock_manager
        mock_manager.set_webhook.return_value = {
            'success': True,
            'description': 'Webhook was set'
        }

        with pytest.raises(SystemExit) as exc_info:
            main()

        assert exc_info.value.code == 0
        mock_manager.set_webhook.assert_called_once_with('https://example.com/webhook')

    @patch('byteforge_telegram.cli.WebhookManager')
    @patch('sys.argv', ['prog', '--token', 'test_token', '--url', 'https://example.com/webhook'])
    def test_set_webhook_failure(self, mock_manager_class):
        """Test setting webhook failure via CLI."""
        mock_manager = Mock()
        mock_manager_class.return_value = mock_manager
        mock_manager.set_webhook.return_value = {
            'success': False,
            'description': 'Invalid URL'
        }

        with pytest.raises(SystemExit) as exc_info:
            main()

        assert exc_info.value.code == 1

    @patch('byteforge_telegram.cli.WebhookManager')
    @patch('sys.argv', ['prog', '--token', 'test_token', '--url', 'http://example.com/webhook'])
    def test_set_webhook_non_https(self, mock_manager_class):
        """Test setting non-HTTPS webhook via CLI."""
        mock_manager = Mock()
        mock_manager_class.return_value = mock_manager
        mock_manager.set_webhook.side_effect = ValueError("Webhook URL must use HTTPS")

        with pytest.raises(SystemExit) as exc_info:
            main()

        assert exc_info.value.code == 1

    @patch('byteforge_telegram.cli.WebhookManager')
    @patch('sys.argv', ['prog', '--token', 'test_token', '--info'])
    def test_get_webhook_info_success(self, mock_manager_class):
        """Test getting webhook info via CLI."""
        mock_manager = Mock()
        mock_manager_class.return_value = mock_manager
        mock_manager.get_webhook_info.return_value = {
            'url': 'https://example.com/webhook',
            'has_custom_certificate': False,
            'pending_update_count': 0
        }

        # When info is successfully retrieved, main() returns None (doesn't exit)
        result = main()

        assert result is None
        mock_manager.get_webhook_info.assert_called_once()

    @patch('byteforge_telegram.cli.WebhookManager')
    @patch('sys.argv', ['prog', '--token', 'test_token', '--info'])
    def test_get_webhook_info_failure(self, mock_manager_class):
        """Test getting webhook info failure via CLI."""
        mock_manager = Mock()
        mock_manager_class.return_value = mock_manager
        mock_manager.get_webhook_info.return_value = None

        with pytest.raises(SystemExit) as exc_info:
            main()

        assert exc_info.value.code == 1

    @patch('byteforge_telegram.cli.WebhookManager')
    @patch('sys.argv', ['prog', '--token', 'test_token', '--delete'])
    def test_delete_webhook_success(self, mock_manager_class):
        """Test deleting webhook via CLI."""
        mock_manager = Mock()
        mock_manager_class.return_value = mock_manager
        mock_manager.delete_webhook.return_value = {
            'success': True,
            'description': 'Webhook was deleted'
        }

        with pytest.raises(SystemExit) as exc_info:
            main()

        assert exc_info.value.code == 0
        mock_manager.delete_webhook.assert_called_once()

    @patch('byteforge_telegram.cli.WebhookManager')
    @patch('sys.argv', ['prog', '--token', 'test_token', '--delete'])
    def test_delete_webhook_failure(self, mock_manager_class):
        """Test deleting webhook failure via CLI."""
        mock_manager = Mock()
        mock_manager_class.return_value = mock_manager
        mock_manager.delete_webhook.return_value = {
            'success': False,
            'description': 'Cannot delete'
        }

        with pytest.raises(SystemExit) as exc_info:
            main()

        assert exc_info.value.code == 1

    @patch('sys.argv', ['prog'])
    def test_no_token_provided(self):
        """Test CLI without token."""
        with pytest.raises(SystemExit) as exc_info:
            main()

        assert exc_info.value.code == 1

    @patch('sys.argv', ['prog', '--token', 'test_token'])
    def test_no_action_provided(self):
        """Test CLI with token but no action."""
        with pytest.raises(SystemExit) as exc_info:
            main()

        assert exc_info.value.code == 1

    @patch.dict('os.environ', {'TELEGRAM_BOT_TOKEN': 'env_token'})
    @patch('byteforge_telegram.cli.WebhookManager')
    @patch('sys.argv', ['prog', '--info'])
    def test_token_from_environment(self, mock_manager_class):
        """Test getting token from environment variable."""
        mock_manager = Mock()
        mock_manager_class.return_value = mock_manager
        mock_manager.get_webhook_info.return_value = {
            'url': 'https://example.com/webhook',
            'has_custom_certificate': False,
            'pending_update_count': 0
        }

        result = main()

        assert result is None
        # Should have created manager with env token
        mock_manager_class.assert_called_once_with('env_token')

    @patch.dict('os.environ', {'TELEGRAM_BOT_TOKEN': 'env_token'})
    @patch('byteforge_telegram.cli.WebhookManager')
    @patch('sys.argv', ['prog', '--token', 'arg_token', '--info'])
    def test_token_from_argument_overrides_env(self, mock_manager_class):
        """Test that argument token overrides environment variable."""
        mock_manager = Mock()
        mock_manager_class.return_value = mock_manager
        mock_manager.get_webhook_info.return_value = {
            'url': 'https://example.com/webhook',
            'has_custom_certificate': False,
            'pending_update_count': 0
        }

        result = main()

        assert result is None
        # Should use arg_token, not env_token
        mock_manager_class.assert_called_once_with('arg_token')
