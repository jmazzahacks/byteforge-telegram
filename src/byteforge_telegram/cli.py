#!/usr/bin/env python3
"""
Command-line interface for Telegram webhook management.
"""

import sys
import os
import argparse
from byteforge_telegram.webhook import WebhookManager


def print_webhook_info(info: dict) -> None:
    """Pretty-print webhook information."""
    print("\n" + "=" * 80)
    print("WEBHOOK INFO")
    print("=" * 80)
    print(f"URL: {info.get('url', '(not set)')}")
    print(f"Has custom certificate: {info.get('has_custom_certificate', False)}")
    print(f"Pending update count: {info.get('pending_update_count', 0)}")

    last_error = info.get('last_error_message')
    if last_error:
        print(f"Last error: {last_error}")
        print(f"Last error date: {info.get('last_error_date', 'N/A')}")

    max_connections = info.get('max_connections')
    if max_connections:
        print(f"Max connections: {max_connections}")

    print("=" * 80 + "\n")


def main() -> None:
    """Main entry point for CLI."""
    parser = argparse.ArgumentParser(
        description='Setup Telegram webhook',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Set webhook URL
  %(prog)s --token BOT_TOKEN --url https://example.com/telegram/webhook

  # Get current webhook info
  %(prog)s --token BOT_TOKEN --info

  # Delete webhook
  %(prog)s --token BOT_TOKEN --delete

Environment variables:
  TELEGRAM_BOT_TOKEN - Bot token (alternative to --token)
        """
    )

    parser.add_argument(
        '--token',
        help='Telegram bot token (or use TELEGRAM_BOT_TOKEN env var)'
    )

    parser.add_argument(
        '--url',
        help='Webhook URL (must be HTTPS)'
    )

    parser.add_argument(
        '--info',
        action='store_true',
        help='Get current webhook information'
    )

    parser.add_argument(
        '--delete',
        action='store_true',
        help='Delete current webhook'
    )

    args = parser.parse_args()

    # Get bot token from args or environment
    bot_token = args.token or os.getenv('TELEGRAM_BOT_TOKEN')
    if not bot_token:
        print("❌ Error: Bot token required (use --token or TELEGRAM_BOT_TOKEN env var)")
        sys.exit(1)

    # Create webhook manager
    manager = WebhookManager(bot_token)

    # Route to appropriate action
    if args.info:
        info = manager.get_webhook_info()
        if info:
            print_webhook_info(info)
        else:
            print("❌ Failed to get webhook info")
            sys.exit(1)

    elif args.delete:
        result = manager.delete_webhook()
        if result['success']:
            print(f"✅ {result['description']}")
            sys.exit(0)
        else:
            print(f"❌ {result['description']}")
            sys.exit(1)

    elif args.url:
        try:
            result = manager.set_webhook(args.url)
            if result['success']:
                print(f"✅ {result['description']}")
                print(f"Webhook URL: {args.url}")
                sys.exit(0)
            else:
                print(f"❌ {result['description']}")
                sys.exit(1)
        except ValueError as e:
            print(f"❌ Error: {e}")
            sys.exit(1)

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == '__main__':
    main()
