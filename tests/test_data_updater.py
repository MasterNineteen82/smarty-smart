import pytest
from unittest.mock import MagicMock, patch, call
import time
import threading
from app.core.data_manager import SmartcardDataManager, ResponseStatus
from app.core.data_updater import DataUpdater
from app.utils.exceptions import DataUpdateError

@pytest.fixture
def mock_data_manager():
    """Fixture to provide a mock SmartcardDataManager for tests."""
    data_manager = MagicMock(spec=SmartcardDataManager)
    data_manager.update_from_source.return_value = {
        "status": ResponseStatus.SUCCESS.value, 
        "message": "Update successful"
    }
    return data_manager

@pytest.fixture
def mock_update_function():
    """Fixture to provide a mock update function for tests."""
    mock_func = MagicMock()
    mock_func.return_value = {"NewCategory": {"NewKey": "NewValue"}}
    return mock_func

@pytest.fixture
def data_updater(mock_data_manager, mock_update_function):
    """Fixture to provide a DataUpdater instance with a mock data manager and update function."""
    return DataUpdater(mock_data_manager, mock_update_function)

def test_data_updater_initialization(mock_data_manager, mock_update_function):
    """Test that DataUpdater initializes correctly with valid dependencies."""
    updater = DataUpdater(mock_data_manager, mock_update_function)
    assert updater.data_manager == mock_data_manager
    assert updater.update_function == mock_update_function
    assert updater.max_retries == 3
    assert updater.retry_delay == 60
    assert updater._schedule_thread is None
    assert updater._stop_event is not None

def test_data_updater_custom_parameters(mock_data_manager, mock_update_function):
    """Test that DataUpdater initializes correctly with custom parameters."""
    updater = DataUpdater(mock_data_manager, mock_update_function, max_retries=5, retry_delay=30)
    assert updater.max_retries == 5
    assert updater.retry_delay == 30

def test_data_updater_initialization_invalid_data_manager(mock_update_function):
    """Test that DataUpdater raises TypeError when initialized with an invalid data manager."""
    with pytest.raises(TypeError, match="data_manager must be an instance of SmartcardDataManager"):
        DataUpdater("invalid_data_manager", mock_update_function)

def test_data_updater_initialization_invalid_update_function(mock_data_manager):
    """Test that DataUpdater raises TypeError when initialized with an invalid update function."""
    with pytest.raises(TypeError, match="update_function must be callable"):
        DataUpdater(mock_data_manager, "invalid_update_function")

def test_fetch_and_update_data_success(data_updater, mock_data_manager, mock_update_function):
    """Test that _fetch_and_update_data successfully fetches and updates data."""
    result = data_updater._fetch_and_update_data()
    assert result["success"] is True
    assert "timestamp" in result
    mock_update_function.assert_called_once()
    mock_data_manager.update_from_source.assert_called_once_with({"NewCategory": {"NewKey": "NewValue"}})

def test_fetch_and_update_data_update_failure(data_updater, mock_data_manager, mock_update_function):
    """Test that _fetch_and_update_data handles update failure correctly."""
    mock_data_manager.update_from_source.return_value = {
        "status": ResponseStatus.ERROR.value, 
        "message": "Update failed"
    }
    result = data_updater._fetch_and_update_data()
    assert result["success"] is False
    assert "error" in result
    assert result["error"] == "Update failed"

def test_fetch_and_update_data_exception(data_updater, mock_update_function):
    """Test that _fetch_and_update_data handles exceptions during update."""
    mock_update_function.side_effect = Exception("Network error")
    result = data_updater._fetch_and_update_data()
    assert result["success"] is False
    assert "error" in result
    assert "Network error" in result["error"]

def test_fetch_and_update_data_empty_data(data_updater, mock_update_function):
    """Test that _fetch_and_update_data handles empty data correctly."""
    mock_update_function.return_value = {}
    result = data_updater._fetch_and_update_data()
    assert result["success"] is True
    # Empty data is valid, but worth logging

def test_fetch_and_update_data_invalid_data(data_updater, mock_update_function):
    """Test that _fetch_and_update_data handles invalid data from update function correctly."""
    mock_update_function.return_value = "invalid_data"
    with pytest.raises(ValueError, match="Update function must return a dictionary"):
        data_updater._fetch_and_update_data()

def test_retry_mechanism(data_updater, mock_data_manager, mock_update_function):
    """Test retry mechanism works correctly when updates fail."""
    mock_data_manager.update_from_source.side_effect = [
        {"status": ResponseStatus.ERROR.value, "message": "First attempt failed"},
        {"status": ResponseStatus.ERROR.value, "message": "Second attempt failed"},
        {"status": ResponseStatus.SUCCESS.value, "message": "Third attempt succeeded"}
    ]
    
    with patch("time.sleep") as mock_sleep:  # Mock sleep to speed up test
        result = data_updater.update_data_with_retry()
    
    assert result["success"] is True
    assert mock_data_manager.update_from_source.call_count == 3
    assert mock_sleep.call_count == 2

def test_retry_exhaustion(data_updater, mock_data_manager, mock_update_function):
    """Test behavior when all retry attempts fail."""
    mock_data_manager.update_from_source.return_value = {
        "status": ResponseStatus.ERROR.value, 
        "message": "Update failed"
    }
    
    with patch("time.sleep") as mock_sleep:  # Mock sleep to speed up test
        result = data_updater.update_data_with_retry()
    
    assert result["success"] is False
    assert mock_data_manager.update_from_source.call_count == data_updater.max_retries
    assert mock_sleep.call_count == data_updater.max_retries - 1

def test_schedule_data_updates(data_updater):
    """Test that schedule_data_updates schedules data updates correctly."""
    with patch("threading.Thread") as mock_thread:
        data_updater.schedule_data_updates(interval=1)
        mock_thread.assert_called_once()
        assert isinstance(data_updater._schedule_thread, MagicMock)
        data_updater.stop_scheduled_updates()

def test_stop_scheduled_updates(data_updater):
    """Test that stop_scheduled_updates stops scheduled data updates correctly."""
    with patch("threading.Thread"):
        data_updater.schedule_data_updates(interval=1)
        data_updater.stop_scheduled_updates()
        assert data_updater._schedule_thread is None
        assert data_updater._stop_event.is_set()

def test_scheduled_update_error_handling(data_updater, mock_update_function):
    """Test that scheduled updates continue even if an update fails."""
    mock_update_function.side_effect = [
        {"Category": {"Key": "Value"}},  # First call succeeds
        Exception("Update failed"),      # Second call fails
        {"Category": {"Key": "Updated"}} # Third call succeeds
    ]
    
    with patch("threading.Thread") as mock_thread:
        with patch("time.sleep") as mock_sleep:
            # Simulate thread behavior
            data_updater.schedule_data_updates(interval=1)
            thread_target = mock_thread.call_args[1]["target"]
            
            # Call the thread target manually three times
            for _ in range(3):
                thread_target()
            
            assert mock_update_function.call_count == 3
            # Check that the updater continues despite errors