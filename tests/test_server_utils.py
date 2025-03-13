import pytest
import os
import signal
import errno
from unittest.mock import patch, mock_open
from app import server_utils
from flask import Flask
from uvicorn import Config, Server

def test_run_server():
    """Test that run_server function starts the server correctly."""
    app = Flask(__name__)
    with patch("uvicorn.run") as mock_uvicorn_run:
        try:
            server_utils.run_server(app)
            mock_uvicorn_run.assert_called_once()
        except Exception as e:
            pytest.fail(f"run_server failed with exception: {e}")

def test_stop_server():
    """Test that stop_server function stops the server correctly, including handling exceptions."""
    with patch("os.kill") as mock_os_kill:
        try:
            server_utils.stop_server()
            mock_os_kill.assert_called_once()
        except OSError as e:
            if e.errno == errno.ESRCH:
                pytest.skip("No process found to kill (this can happen in testing environments).")
            else:
                pytest.fail(f"stop_server failed with OSError: {e}")
        except Exception as e:
            pytest.fail(f"stop_server failed with exception: {e}")

def test_run_server_custom_config():
    """Test that run_server correctly passes custom configuration to uvicorn."""
    app = Flask(__name__)
    host = "127.0.0.1"
    port = 5001
    with patch("uvicorn.run") as mock_uvicorn_run:
        server_utils.run_server(app, host=host, port=port)
        mock_uvicorn_run.assert_called_once_with(app, host=host, port=port, log_level="info")

def test_stop_server_no_pid_file():
    """Test stop_server when no PID file exists."""
    with patch("os.path.exists", return_value=False):
        with pytest.raises(OSError) as excinfo:
            server_utils.stop_server()
        assert excinfo.value.errno == errno.ENOENT

def test_stop_server_invalid_pid():
    """Test stop_server when the PID file contains an invalid PID."""
    with patch("os.path.exists", return_value=True):
        with patch("builtins.open", mock_open(read_data="invalid_pid")):
            with pytest.raises(ValueError):
                server_utils.stop_server()