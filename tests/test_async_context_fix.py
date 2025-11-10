"""
Tests to verify that *_sync() methods properly block in async contexts.

This test file specifically addresses the bug where send_message_sync()
would return immediately without waiting when called from an async context.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, Mock, patch
from byteforge_telegram.notifier import TelegramBotController


class TestAsyncContextBlocking:
    """Tests to verify *_sync() methods block properly in async contexts."""

    @pytest.mark.asyncio
    async def test_send_message_sync_blocks_in_async_context(self):
        """Test that send_message_sync() blocks until completion when called from async context."""
        controller = TelegramBotController("test_token")

        # Track when the async method completes
        completed = {"value": False}

        async def mock_send_with_delay(*args, **kwargs):
            """Mock send_message that simulates network delay."""
            await asyncio.sleep(0.1)  # Simulate network delay
            completed["value"] = True
            return {"123": True}

        with patch.object(controller, 'send_message', side_effect=mock_send_with_delay):
            # Call from async context
            result = controller.send_message_sync(
                text="Test",
                chat_ids=["123"]
            )

            # If it blocked properly, completed should be True
            assert completed["value"] is True, "send_message_sync should have blocked until completion"
            assert result == {"123": True}

    @pytest.mark.asyncio
    async def test_send_formatted_sync_blocks_in_async_context(self):
        """Test that send_formatted_sync() blocks until completion when called from async context."""
        controller = TelegramBotController("test_token")

        completed = {"value": False}

        async def mock_send_formatted_with_delay(*args, **kwargs):
            """Mock send_formatted that simulates network delay."""
            await asyncio.sleep(0.1)
            completed["value"] = True
            return {"456": True}

        with patch.object(controller, 'send_formatted', side_effect=mock_send_formatted_with_delay):
            result = controller.send_formatted_sync(
                title="Test",
                fields={"key": "value"},
                chat_ids=["456"]
            )

            assert completed["value"] is True, "send_formatted_sync should have blocked until completion"
            assert result == {"456": True}

    @pytest.mark.asyncio
    async def test_test_connection_sync_blocks_in_async_context(self):
        """Test that test_connection_sync() blocks until completion when called from async context."""
        controller = TelegramBotController("test_token")

        completed = {"value": False}

        async def mock_test_connection_with_delay(*args, **kwargs):
            """Mock test_connection that simulates network delay."""
            await asyncio.sleep(0.1)
            completed["value"] = True
            return True

        with patch.object(controller, 'test_connection', side_effect=mock_test_connection_with_delay):
            result = controller.test_connection_sync("789")

            assert completed["value"] is True, "test_connection_sync should have blocked until completion"
            assert result is True

    @pytest.mark.asyncio
    async def test_send_message_sync_returns_actual_results_not_optimistic(self):
        """Test that send_message_sync() returns actual results, not optimistic True."""
        controller = TelegramBotController("test_token")

        # Mock a failure scenario
        async def mock_send_with_failure(*args, **kwargs):
            """Mock send_message that fails."""
            await asyncio.sleep(0.05)
            return {"123": False}  # Actual failure

        with patch.object(controller, 'send_message', side_effect=mock_send_with_failure):
            result = controller.send_message_sync(
                text="Test",
                chat_ids=["123"]
            )

            # Should return actual failure, not optimistic True
            assert result == {"123": False}, "Should return actual result, not optimistic True"

    @pytest.mark.asyncio
    async def test_no_duplicate_messages_from_retries(self):
        """
        Test that verifies the duplicate message bug is fixed.

        The old behavior would:
        1. Return immediately with "success"
        2. Agent sees it as error (because message not actually sent)
        3. Agent retries
        4. Both background tasks complete = duplicate messages

        New behavior:
        1. Blocks until complete
        2. Returns actual result
        3. No false positives = no duplicate retries
        """
        controller = TelegramBotController("test_token")

        call_count = {"value": 0}

        async def mock_send_counting(*args, **kwargs):
            """Mock that counts how many times it's called."""
            call_count["value"] += 1
            await asyncio.sleep(0.05)
            return {"123": True}

        with patch.object(controller, 'send_message', side_effect=mock_send_counting):
            # Simulate what an agent would do:
            # 1. Call send_message_sync
            # 2. Check if it succeeded
            # 3. Only retry if it failed

            result1 = controller.send_message_sync(text="Test", chat_ids=["123"])

            # If result says success, don't retry
            if result1.get("123"):
                # Success - no retry needed
                pass
            else:
                # Failure - retry
                controller.send_message_sync(text="Test", chat_ids=["123"])

            # Should only be called once because first call blocked and returned True
            assert call_count["value"] == 1, "Should only call once, no duplicate from false negative"

    def test_send_message_sync_works_without_event_loop(self):
        """Test that send_message_sync() still works in non-async contexts."""
        controller = TelegramBotController("test_token")

        with patch('byteforge_telegram.notifier.Bot') as mock_bot_class:
            mock_bot = AsyncMock()
            mock_bot_class.return_value = mock_bot
            mock_bot.send_message = AsyncMock()

            # Call from sync context (no event loop)
            result = controller.send_message_sync(
                text="Test",
                chat_ids=["123"]
            )

            assert isinstance(result, dict)
            assert "123" in result
