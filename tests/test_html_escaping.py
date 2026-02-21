"""
Tests for HTML entity escaping functionality.

Verifies that special characters (<, >, &) are properly escaped
to prevent Telegram HTML parsing errors.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from telegram.error import TelegramError
from byteforge_telegram.notifier import TelegramBotController, ParseMode, repair_html_tags


@pytest.mark.asyncio
async def test_send_message_escapes_html_entities():
    """Test that send_message escapes HTML entities when using HTML parse mode."""
    controller = TelegramBotController("test_token")

    with patch("byteforge_telegram.notifier.Bot") as mock_bot_class:
        mock_bot = AsyncMock()
        mock_bot_class.return_value = mock_bot
        mock_bot.send_message = AsyncMock()

        # Send message with special characters
        await controller.send_message(
            text="Value <10% and >5% with & symbol",
            chat_ids=["123"],
            parse_mode=ParseMode.HTML
        )

        # Verify the text was escaped
        mock_bot.send_message.assert_called_once()
        call_args = mock_bot.send_message.call_args
        assert call_args.kwargs["text"] == "Value &lt;10% and &gt;5% with &amp; symbol"


@pytest.mark.asyncio
async def test_send_message_no_escape_when_not_html_mode():
    """Test that send_message doesn't escape when not using HTML parse mode."""
    controller = TelegramBotController("test_token")

    with patch("byteforge_telegram.notifier.Bot") as mock_bot_class:
        mock_bot = AsyncMock()
        mock_bot_class.return_value = mock_bot
        mock_bot.send_message = AsyncMock()

        # Send message with special characters using MARKDOWN mode
        await controller.send_message(
            text="Value <10%",
            chat_ids=["123"],
            parse_mode=ParseMode.MARKDOWN
        )

        # Verify the text was NOT escaped
        mock_bot.send_message.assert_called_once()
        call_args = mock_bot.send_message.call_args
        assert call_args.kwargs["text"] == "Value <10%"


@pytest.mark.asyncio
async def test_send_formatted_escapes_title():
    """Test that send_formatted escapes the title."""
    controller = TelegramBotController("test_token")

    with patch("byteforge_telegram.notifier.Bot") as mock_bot_class:
        mock_bot = AsyncMock()
        mock_bot_class.return_value = mock_bot
        mock_bot.send_message = AsyncMock()

        # Send formatted message with special characters in title
        await controller.send_formatted(
            title="Performance <10%",
            fields={},
            chat_ids=["123"]
        )

        # Verify the title was escaped but HTML tags are preserved
        mock_bot.send_message.assert_called_once()
        call_args = mock_bot.send_message.call_args
        assert "&lt;10%" in call_args.kwargs["text"]
        assert "<b>" in call_args.kwargs["text"]  # HTML tags preserved


@pytest.mark.asyncio
async def test_send_formatted_escapes_field_values():
    """Test that send_formatted escapes field keys and values."""
    controller = TelegramBotController("test_token")

    with patch("byteforge_telegram.notifier.Bot") as mock_bot_class:
        mock_bot = AsyncMock()
        mock_bot_class.return_value = mock_bot
        mock_bot.send_message = AsyncMock()

        # Send formatted message with special characters in fields
        await controller.send_formatted(
            title="Test",
            fields={
                "Key<1": "Value >5%",
                "Rate": "<10% & improving"
            },
            chat_ids=["123"]
        )

        # Verify the fields were escaped
        mock_bot.send_message.assert_called_once()
        call_args = mock_bot.send_message.call_args
        message_text = call_args.kwargs["text"]
        assert "Key&lt;1" in message_text
        assert "Value &gt;5%" in message_text
        assert "&lt;10% &amp; improving" in message_text
        # HTML tags preserved
        assert "<b>" in message_text


@pytest.mark.asyncio
async def test_send_formatted_escapes_footer():
    """Test that send_formatted escapes the footer."""
    controller = TelegramBotController("test_token")

    with patch("byteforge_telegram.notifier.Bot") as mock_bot_class:
        mock_bot = AsyncMock()
        mock_bot_class.return_value = mock_bot
        mock_bot.send_message = AsyncMock()

        # Send formatted message with special characters in footer
        await controller.send_formatted(
            title="Test",
            fields={},
            chat_ids=["123"],
            footer="Success rate >90% & <100%"
        )

        # Verify the footer was escaped
        mock_bot.send_message.assert_called_once()
        call_args = mock_bot.send_message.call_args
        message_text = call_args.kwargs["text"]
        assert "&gt;90% &amp; &lt;100%" in message_text
        assert "<i>" in message_text  # HTML tags preserved


@pytest.mark.asyncio
async def test_send_formatted_preserves_emoji():
    """Test that send_formatted preserves emoji characters."""
    controller = TelegramBotController("test_token")

    with patch("byteforge_telegram.notifier.Bot") as mock_bot_class:
        mock_bot = AsyncMock()
        mock_bot_class.return_value = mock_bot
        mock_bot.send_message = AsyncMock()

        # Send formatted message with emoji
        await controller.send_formatted(
            title="Performance <10%",
            fields={},
            chat_ids=["123"],
            emoji="🎯"
        )

        # Verify emoji is preserved
        mock_bot.send_message.assert_called_once()
        call_args = mock_bot.send_message.call_args
        message_text = call_args.kwargs["text"]
        assert "🎯" in message_text


def test_send_message_sync_escapes_html():
    """Test that send_message_sync also escapes HTML entities."""
    controller = TelegramBotController("test_token")

    with patch("byteforge_telegram.notifier.Bot") as mock_bot_class:
        mock_bot = AsyncMock()
        mock_bot_class.return_value = mock_bot
        mock_bot.send_message = AsyncMock()

        # Send message with special characters using sync method
        controller.send_message_sync(
            text="Value <10% and >5%",
            chat_ids=["123"]
        )

        # Verify the text was escaped
        mock_bot.send_message.assert_called_once()
        call_args = mock_bot.send_message.call_args
        assert call_args.kwargs["text"] == "Value &lt;10% and &gt;5%"


def test_send_formatted_sync_escapes_html():
    """Test that send_formatted_sync also escapes HTML entities."""
    controller = TelegramBotController("test_token")

    with patch("byteforge_telegram.notifier.Bot") as mock_bot_class:
        mock_bot = AsyncMock()
        mock_bot_class.return_value = mock_bot
        mock_bot.send_message = AsyncMock()

        # Send formatted message with special characters using sync method
        controller.send_formatted_sync(
            title="Performance >90%",
            fields={"Rate": "<10%"},
            chat_ids=["123"]
        )

        # Verify the content was escaped
        mock_bot.send_message.assert_called_once()
        call_args = mock_bot.send_message.call_args
        message_text = call_args.kwargs["text"]
        assert "&gt;90%" in message_text
        assert "&lt;10%" in message_text


@pytest.mark.asyncio
async def test_send_message_preserves_formatting_tags():
    """Test that send_message preserves intentional HTML formatting tags."""
    controller = TelegramBotController("test_token")

    with patch("byteforge_telegram.notifier.Bot") as mock_bot_class:
        mock_bot = AsyncMock()
        mock_bot_class.return_value = mock_bot
        mock_bot.send_message = AsyncMock()

        # Send message with HTML formatting tags (bold, italic)
        await controller.send_message(
            text="<b>Bold Title</b>\n<i>Italic text</i>",
            chat_ids=["123"],
            parse_mode=ParseMode.HTML
        )

        # Verify formatting tags are preserved
        mock_bot.send_message.assert_called_once()
        call_args = mock_bot.send_message.call_args
        assert call_args.kwargs["text"] == "<b>Bold Title</b>\n<i>Italic text</i>"


@pytest.mark.asyncio
async def test_send_message_preserves_tags_and_escapes_literals():
    """Test that formatting tags are preserved while literal < > & are escaped."""
    controller = TelegramBotController("test_token")

    with patch("byteforge_telegram.notifier.Bot") as mock_bot_class:
        mock_bot = AsyncMock()
        mock_bot_class.return_value = mock_bot
        mock_bot.send_message = AsyncMock()

        # Send message with both formatting tags AND special characters
        await controller.send_message(
            text="<b>Score: <70%</b> and <i>Rate: >90% & improving</i>",
            chat_ids=["123"],
            parse_mode=ParseMode.HTML
        )

        # Verify: tags preserved, literals escaped
        mock_bot.send_message.assert_called_once()
        call_args = mock_bot.send_message.call_args
        result = call_args.kwargs["text"]

        # Formatting tags should be preserved
        assert "<b>" in result
        assert "</b>" in result
        assert "<i>" in result
        assert "</i>" in result

        # Literal < > & should be escaped
        assert "&lt;70%" in result
        assert "&gt;90%" in result
        assert "&amp; improving" in result


@pytest.mark.asyncio
async def test_send_message_preserves_all_telegram_tags():
    """Test that all allowed Telegram HTML tags are preserved."""
    controller = TelegramBotController("test_token")

    with patch("byteforge_telegram.notifier.Bot") as mock_bot_class:
        mock_bot = AsyncMock()
        mock_bot_class.return_value = mock_bot
        mock_bot.send_message = AsyncMock()

        # Test various Telegram HTML tags
        await controller.send_message(
            text=(
                "<b>bold</b> <strong>strong</strong> "
                "<i>italic</i> <em>em</em> "
                "<u>underline</u> <s>strike</s> "
                "<code>code</code> <pre>pre</pre> "
                '<a href="url">link</a>'
            ),
            chat_ids=["123"],
            parse_mode=ParseMode.HTML
        )

        # Verify all tags are preserved
        mock_bot.send_message.assert_called_once()
        call_args = mock_bot.send_message.call_args
        result = call_args.kwargs["text"]

        assert "<b>bold</b>" in result
        assert "<strong>strong</strong>" in result
        assert "<i>italic</i>" in result
        assert "<em>em</em>" in result
        assert "<u>underline</u>" in result
        assert "<s>strike</s>" in result
        assert "<code>code</code>" in result
        assert "<pre>pre</pre>" in result
        assert '<a href="url">link</a>' in result


@pytest.mark.asyncio
async def test_bug_report_scenario():
    """Test the exact scenario from the bug report."""
    controller = TelegramBotController("test_token")

    with patch("byteforge_telegram.notifier.Bot") as mock_bot_class:
        mock_bot = AsyncMock()
        mock_bot_class.return_value = mock_bot
        mock_bot.send_message = AsyncMock()

        # The exact message from bug report
        message = """<b>🎯 High-Scoring Config Found!</b>

Found 1 config scoring ≥ 70

<b>Config 2488</b> (Score: 80, B-)
• TRX/WETH - TRX_WETH_TrendFollowingStrategy
• 2,866.45% return, 88.33% CAGR
• 15.15% max drawdown, 69.23% win rate
• Alpha vs baseline: +2,775.31% 🚀"""

        await controller.send_message(
            text=message,
            chat_ids=["123"],
            parse_mode=ParseMode.HTML
        )

        # Verify formatting tags are preserved (not escaped)
        mock_bot.send_message.assert_called_once()
        call_args = mock_bot.send_message.call_args
        result = call_args.kwargs["text"]

        # Tags should NOT be escaped
        assert "<b>" in result
        assert "</b>" in result
        # Should NOT see escaped versions
        assert "&lt;b&gt;" not in result
        assert "&lt;/b&gt;" not in result
        # Content should be preserved
        assert "🎯 High-Scoring Config Found!" in result
        assert "TRX/WETH" in result


# --- repair_html_tags tests ---


class TestRepairHtmlTags:
    """Tests for repair_html_tags() tag balancing."""

    def test_already_balanced_unchanged(self):
        """Balanced tags should pass through unchanged."""
        text = "<b>hello</b> <i>world</i>"
        assert repair_html_tags(text) == text

    def test_orphaned_closing_tag_removed(self):
        """Orphaned closing tags should be removed."""
        result = repair_html_tags("Hello </b>world")
        assert "</b>" not in result
        assert "Hello" in result
        assert "world" in result

    def test_unclosed_tag_auto_closed(self):
        """Unclosed tags should be auto-closed at end."""
        result = repair_html_tags("<b>Hello")
        assert result == "<b>Hello</b>"

    def test_multiple_unclosed_tags(self):
        """Multiple unclosed tags should all be auto-closed in reverse order."""
        result = repair_html_tags("<b><i>text")
        assert result == "<b><i>text</i></b>"

    def test_nested_mismatch_repaired(self):
        """Misnested tags should be repaired to proper nesting."""
        result = repair_html_tags("<b><i>text</b></i>")
        # bs4 should produce properly nested output
        assert "<b>" in result
        assert "<i>" in result
        assert "text" in result
        # Verify it's parseable (no orphaned tags)
        repaired_again = repair_html_tags(result)
        assert repaired_again == result

    def test_plain_text_unchanged(self):
        """Plain text with no tags should pass through unchanged."""
        text = "Just plain text with no tags"
        assert repair_html_tags(text) == text

    def test_escaped_entities_preserved(self):
        """Already-escaped HTML entities should not be double-escaped."""
        text = "<b>Score: &lt;70%</b>"
        result = repair_html_tags(text)
        assert "&lt;70%" in result
        assert "<b>" in result
        assert "</b>" in result

    def test_multiple_orphaned_closing_tags(self):
        """Multiple orphaned closing tags should all be removed."""
        result = repair_html_tags("Hello </b></i></u> world")
        assert "</b>" not in result
        assert "</i>" not in result
        assert "</u>" not in result
        assert "Hello" in result
        assert "world" in result

    def test_mixed_valid_and_invalid_tags(self):
        """Valid balanced tags preserved, orphaned ones removed."""
        result = repair_html_tags("<b>bold</b> </i>orphan <i>italic</i>")
        assert "<b>bold</b>" in result
        assert "<i>italic</i>" in result
        # Orphaned </i> should be gone
        assert result.count("</i>") == 1

    def test_link_tag_preserved(self):
        """Anchor tags with href should be preserved and balanced."""
        text = '<a href="https://example.com">link</a>'
        assert repair_html_tags(text) == text

    def test_unclosed_link_tag_closed(self):
        """Unclosed anchor tag should be auto-closed."""
        result = repair_html_tags('<a href="https://example.com">link')
        assert "</a>" in result

    def test_empty_string(self):
        """Empty string should return empty string."""
        assert repair_html_tags("") == ""

    def test_real_world_llm_output(self):
        """Simulate a real LLM-generated message with unbalanced tags."""
        text = (
            "<b>Config Analysis</b>\n\n"
            "Found <b>3 configs scoring above threshold\n"  # unclosed <b>
            "<i>Processing complete</i>\n"
            "Extra closing tag follows:</b>"  # orphaned </b>
        )
        result = repair_html_tags(text)
        # Should be parseable — repair again and ensure stable
        repaired_again = repair_html_tags(result)
        assert repaired_again == result


# --- Plain text fallback tests ---


class TestPlainTextFallback:
    """Tests for plain text fallback when HTML parsing fails."""

    @pytest.mark.asyncio
    async def test_fallback_on_parse_error(self):
        """When Telegram rejects HTML, message should be retried as plain text."""
        controller = TelegramBotController("test_token")

        with patch("byteforge_telegram.notifier.Bot") as mock_bot_class:
            mock_bot = AsyncMock()
            mock_bot_class.return_value = mock_bot

            # First call fails with parse error, subsequent calls succeed
            mock_bot.send_message = AsyncMock(
                side_effect=[
                    TelegramError("Can't parse entities: unexpected end tag at byte offset 585"),
                    None,  # plain text retry succeeds
                ]
            )

            result = await controller.send_message(
                text="<b>Hello</b> world",
                chat_ids=["123"],
                parse_mode=ParseMode.HTML,
            )

            assert result == {"123": True}
            assert mock_bot.send_message.call_count == 2
            # Second call should have parse_mode=None (plain text)
            retry_call = mock_bot.send_message.call_args_list[1]
            assert retry_call.kwargs["parse_mode"] is None
            # Tags should be stripped in the plain text version
            assert "<b>" not in retry_call.kwargs["text"]
            assert "Hello" in retry_call.kwargs["text"]

    @pytest.mark.asyncio
    async def test_fallback_also_fails(self):
        """When both HTML and plain text fail, result should be False."""
        controller = TelegramBotController("test_token")

        with patch("byteforge_telegram.notifier.Bot") as mock_bot_class:
            mock_bot = AsyncMock()
            mock_bot_class.return_value = mock_bot

            mock_bot.send_message = AsyncMock(
                side_effect=[
                    TelegramError("Can't parse entities: unexpected end tag"),
                    TelegramError("Chat not found"),
                ]
            )

            result = await controller.send_message(
                text="<b>Hello</b>",
                chat_ids=["123"],
                parse_mode=ParseMode.HTML,
            )

            assert result == {"123": False}

    @pytest.mark.asyncio
    async def test_non_parse_error_no_fallback(self):
        """Non-parse TelegramErrors should not trigger fallback retry."""
        controller = TelegramBotController("test_token")

        with patch("byteforge_telegram.notifier.Bot") as mock_bot_class:
            mock_bot = AsyncMock()
            mock_bot_class.return_value = mock_bot

            mock_bot.send_message = AsyncMock(
                side_effect=TelegramError("Forbidden: bot was blocked by the user")
            )

            result = await controller.send_message(
                text="<b>Hello</b>",
                chat_ids=["123"],
                parse_mode=ParseMode.HTML,
            )

            assert result == {"123": False}
            # Should only be called once — no retry
            assert mock_bot.send_message.call_count == 1
