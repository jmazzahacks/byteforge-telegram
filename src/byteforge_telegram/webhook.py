"""
Telegram webhook management utilities.

Provides functions to set, get, and delete Telegram bot webhooks.
"""

import logging
from typing import Optional, Dict, Any
import requests

logger = logging.getLogger(__name__)


class WebhookManager:
    """Manages Telegram bot webhook configuration."""

    def __init__(self, bot_token: str):
        """
        Initialize webhook manager.

        Args:
            bot_token: Telegram bot token from BotFather
        """
        if not bot_token:
            raise ValueError("bot_token is required")
        self.bot_token = bot_token
        self.base_url = f"https://api.telegram.org/bot{bot_token}"

    def set_webhook(self, webhook_url: str, timeout: int = 10) -> Dict[str, Any]:
        """
        Set the webhook URL for the Telegram bot.

        Args:
            webhook_url: Full HTTPS URL for webhook endpoint
            timeout: Request timeout in seconds (default: 10)

        Returns:
            Dict with 'success' (bool) and 'description' (str)

        Raises:
            ValueError: If webhook_url is not HTTPS
        """
        if not webhook_url.startswith('https://'):
            raise ValueError("Webhook URL must use HTTPS")

        api_url = f"{self.base_url}/setWebhook"
        payload = {'url': webhook_url}

        try:
            response = requests.post(api_url, json=payload, timeout=timeout)
            response.raise_for_status()
            result = response.json()

            if result.get('ok'):
                logger.info(f"Webhook set successfully: {webhook_url}")
                return {
                    'success': True,
                    'description': result.get('description', 'Webhook was set')
                }
            else:
                error_msg = result.get('description', 'Unknown error')
                logger.error(f"Failed to set webhook: {error_msg}")
                return {
                    'success': False,
                    'description': error_msg
                }

        except requests.exceptions.RequestException as e:
            logger.error(f"Error making API request: {e}")
            return {
                'success': False,
                'description': f"Request error: {str(e)}"
            }

    def get_webhook_info(self, timeout: int = 10) -> Optional[Dict[str, Any]]:
        """
        Get current webhook information.

        Args:
            timeout: Request timeout in seconds (default: 10)

        Returns:
            Dict with webhook info, or None on error
        """
        api_url = f"{self.base_url}/getWebhookInfo"

        try:
            response = requests.get(api_url, timeout=timeout)
            response.raise_for_status()
            result = response.json()

            if result.get('ok'):
                info = result.get('result', {})
                logger.debug(f"Webhook info retrieved: {info.get('url', '(not set)')}")
                return info
            else:
                logger.error(f"Failed to get webhook info: {result.get('description')}")
                return None

        except requests.exceptions.RequestException as e:
            logger.error(f"Error making API request: {e}")
            return None

    def delete_webhook(self, timeout: int = 10) -> Dict[str, Any]:
        """
        Delete the current webhook.

        Args:
            timeout: Request timeout in seconds (default: 10)

        Returns:
            Dict with 'success' (bool) and 'description' (str)
        """
        api_url = f"{self.base_url}/deleteWebhook"

        try:
            response = requests.post(api_url, timeout=timeout)
            response.raise_for_status()
            result = response.json()

            if result.get('ok'):
                logger.info("Webhook deleted successfully")
                return {
                    'success': True,
                    'description': 'Webhook was deleted'
                }
            else:
                error_msg = result.get('description', 'Unknown error')
                logger.error(f"Failed to delete webhook: {error_msg}")
                return {
                    'success': False,
                    'description': error_msg
                }

        except requests.exceptions.RequestException as e:
            logger.error(f"Error making API request: {e}")
            return {
                'success': False,
                'description': f"Request error: {str(e)}"
            }
