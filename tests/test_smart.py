import pytest
import logging
import os
import time
from unittest.mock import patch, MagicMock, mock_open
from app import smart
from app.config import LOG_FILE, LOG_LEVEL, LOG_FORMAT, MAX_LOG_SIZE, BACKUP_COUNT


@pytest.fixture
def cleanup_logs():
    """Fixture to clean up test log files after tests."""
    yield
    if os.path.exists(LOG_FILE):
        try:
            os.remove(LOG_FILE)
        except (PermissionError, OSError):
            pass  # Ignore cleanup errors


@patch("logging.handlers.RotatingFileHandler")
@patch("logging.StreamHandler")
@patch("logging.getLogger")
def test_setup_logging(mock_get_logger, mock_stream_handler, mock_file_handler):
    """Test that setup_logging function configures logging correctly with proper error handling."""
    # Set up mocks
    mock_logger = MagicMock()
    mock_get_logger.return_value = mock_logger
    
    # Execute function under test
    smart.setup_logging()
    
    # Verify correct logger initialization
    mock_get_logger.assert_called_once_with('smarty')
    mock_logger.setLevel.assert_called_once_with(LOG_LEVEL)
    
    # Verify handlers are added with correct configuration
    assert mock_logger.addHandler.call_count >= 2, "Both handlers should be added"
    
    # Verify file handler configuration
    mock_file_handler.assert_called_once()
    file_handler_args = mock_file_handler.call_args[0]
    assert file_handler_args[0] == LOG_FILE
    assert file_handler_args[1] == MAX_LOG_SIZE
    assert file_handler_args[2] == BACKUP_COUNT
    
    # Verify error handling during setup
    with patch("logging.handlers.RotatingFileHandler", side_effect=PermissionError("Access denied")):
        with patch("logging.getLogger") as mock_get_logger2:
            mock_logger2.return_value = MagicMock()
            # Should handle permission error gracefully
            smart.setup_logging()


def test_log_messages(caplog):
    """Test that log messages are being written and handled correctly at different levels."""
    logger = smart.logger
    
    # Test different log levels
    logger.debug("Debug test message")
    logger.info("Info test message")
    logger.warning("Warning test message")
    logger.error("Error test message")
    logger.critical("Critical test message")
    
    # Verify messages appear in logs based on configured level
    if LOG_LEVEL <= logging.DEBUG:
        assert "Debug test message" in caplog.text
    if LOG_LEVEL <= logging.INFO:
        assert "Info test message" in caplog.text
    if LOG_LEVEL <= logging.WARNING:
        assert "Warning test message" in caplog.text
    assert "Error test message" in caplog.text
    assert "Critical test message" in caplog.text


@pytest.mark.parametrize("test_input,expected", [
    ("A" * 2000, True),  # Very long message
    ("你好世界", True),   # Unicode characters
    ("", True),          # Empty message
    (None, False)        # None value should be handled properly
])
def test_edge_cases_logging(caplog, test_input, expected):
    """Test edge cases for logging with parameterized inputs."""
    logger = smart.logger
    
    if test_input is None:
        with pytest.raises(TypeError):
            logger.info(test_input)
    else:
        logger.info(test_input)
        if expected:
            assert test_input in caplog.text


@patch("logging.handlers.RotatingFileHandler")
def test_file_permissions(mock_handler, cleanup_logs):
    """Test logging behavior when file permissions issues occur."""
    # Simulate permission error on first attempt, then succeed
    mock_handler.side_effect = [PermissionError("Access denied"), MagicMock()]
    
    with patch("app.smart.setup_logging") as mock_setup:
        mock_setup.side_effect = smart.setup_logging  # Call the real function
        
        # Should handle the permission error and retry with a fallback
        with pytest.raises(Exception) as exc_info:
            smart.setup_logging(retry=False)  # Should raise when retry is False
        
        assert "permission" in str(exc_info.value).lower() or "access" in str(exc_info.value).lower()


def test_browser_logger(caplog):
    """Test that browser logger is configured and logs messages correctly."""
    logger = smart.browser_logger
    
    # Test different log levels for browser logger
    logger.info("Browser info message")
    logger.error("Browser error message")
    
    # Verify the messages are properly formatted and contain browser context
    assert "Browser info message" in caplog.text
    assert "Browser error message" in caplog.text
    
    # Verify browser-specific formatting or tags if applicable
    if hasattr(smart, 'BROWSER_LOG_FORMAT'):
        assert any(smart.BROWSER_LOG_FORMAT in record for record in caplog.records)