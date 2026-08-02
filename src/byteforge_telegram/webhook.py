"""
Telegram webhook management utilities.

Provides functions to set, get, and delete Telegram bot webhooks.
"""

import logging
from typing import Optional, Dict, Any, List
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

    def set_webhook(
        self,
        webhook_url: str,
        timeout: int = 10,
        allowed_updates: Optional[List[str]] = None,
        secret_token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Set the webhook URL for the Telegram bot.

        Args:
            webhook_url: Full HTTPS URL for webhook endpoint
            timeout: Request timeout in seconds (default: 10)
            allowed_updates: Update types to receive, e.g.
                ['message', 'callback_query']. NOTE: Telegram treats an
                omitted allowed_updates as "keep the previous setting" —
                not "use the default" — so if the webhook was ever
                registered with a narrow list, only passing this parameter
                can widen it. Pass an empty list to reset to Telegram's
                default set.
            secret_token: Value Telegram will send in the
                X-Telegram-Bot-Api-Secret-Token header on every webhook
                request. Unlike allowed_updates this is NOT sticky:
                omitting it on setWebhook clears any existing secret, so
                re-supply it on every call if your endpoint validates it.

        Returns:
            Dict with 'success' (bool) and 'description' (str)

        Raises:
            ValueError: If webhook_url is not HTTPS
        """
        if not webhook_url.startswith('https://'):
            raise ValueError("Webhook URL must use HTTPS")

        api_url = f"{self.base_url}/setWebhook"
        payload: Dict[str, Any] = {'url': webhook_url}
        if allowed_updates is not None:
            payload['allowed_updates'] = allowed_updates
        if secret_token is not None:
            payload['secret_token'] = secret_token

        try:
            response = requests.post(api_url, json=payload, timeout=timeout)
            response.raise_for_status()
            result = response.json()

            if result.get('ok'):
                logger.info(f"Webhook set successfully: {webhook_url}")
                # "ok: true" doesn't reveal which update types are actually
                # registered, so surface the effective setting.
                info = self.get_webhook_info(timeout=timeout)
                if info is not None:
                    effective = info.get('allowed_updates')
                    logger.info(
                        f"Effective allowed_updates: {effective if effective else '(Telegram default: all except chat_member, message_reaction, message_reaction_count)'}"
                    )
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
