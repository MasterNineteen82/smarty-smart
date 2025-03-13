import pytest
import logging
from unittest.mock import patch, mock_open
from app import smart
from app.config import LOG_FILE, LOG_LEVEL, LOG_FORMAT

def test_setup_logging():
    """Test that setup_logging function configures logging correctly, including exception handling."""
    with patch("logging.getLogger") as mock_get_logger:
        mock_logger = mock_get_logger.return_value
        try:
            smart.setup_logging()
        except Exception as e:
            pytest.fail(f"setup_logging raised an exception: {e}")

        mock_get_logger.assert_called_once_with('smarty')
        mock_logger.setLevel.assert_called_once_with(LOG_LEVEL)

        # Check if RotatingFileHandler is added
        file_handler_added = any(
            isinstance(handler, logging.handlers.RotatingFileHandler)
            for handler in mock_logger.handlers
        )
        assert file_handler_added, "RotatingFileHandler not added"

        # Check if StreamHandler is added
        console_handler_added = any(
            isinstance(handler, logging.StreamHandler)
            for handler in mock_logger.handlers
        )
        assert console_handler_added, "StreamHandler not added"

        # Check log format
        log_formatter_correct = all(
            hasattr(handler, 'formatter') and
            hasattr(handler.formatter, '_fmt') and
            handler.formatter._fmt == LOG_FORMAT
            for handler in mock_logger.handlers
            if isinstance(handler, (logging.handlers.RotatingFileHandler, logging.StreamHandler))
        )
        assert log_formatter_correct, "Log format is incorrect"

def test_log_messages(caplog):
    """Test that log messages are being written and handled correctly."""
    logger = smart.logger
    try:
        logger.info("Test log message")
        assert "Test log message" in caplog.text
    except Exception as e:
        pytest.fail(f"Logging failed: {e}")

def test_edge_cases_logging(caplog):
    """Test edge cases for logging, such as very long messages or unicode characters."""
    logger = smart.logger
    long_message = "A" * 2000  # Very long message
    unicode_message = "你好世界"  # Unicode characters

    logger.info(long_message)
    logger.info(unicode_message)

    assert long_message in caplog.text
    assert unicode_message in caplog.text

def test_browser_logger(caplog):
    """Test that browser logger is configured and logs messages correctly."""
    logger = smart.browser_logger
    logger.error("Browser test log message")
    assert "Browser test log message" in caplog.text