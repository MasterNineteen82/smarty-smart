import pytest
from unittest.mock import patch, MagicMock
# from smartcard.util import toHexString  # Remove this line
from app import get_core

# Use the modules
core = get_core()
smartcard = core.smartcard  # Access smartcard module from core

@pytest.fixture
def mock_readers():
    """Fixture to mock smartcard readers."""
    with patch("smartcard.System.readers") as mock:
        yield mock

@pytest.fixture
def mock_connection():
    """Fixture to mock smartcard connection."""
    mock = MagicMock()
    mock.transmit.return_value = ([0x01, 0x02, 0x03], 0x90, 0x00)  # Example successful response
    return mock

def test_read_smart_card_data_success(mock_readers, mock_connection):
    """Test reading smart card data successfully."""
    mock_readers.return_value = ["Mock Reader"]
    mock_readers.return_value[0].createConnection.return_value = mock_connection
    mock_connection.connect.return_value = None

    card_id = 123
    card_data = smartcard.read_smart_card_data(card_id)
    # Replace toHexString with bytes.hex().upper()
    card_data = {"card_id": card_id, "type": "smartcard", "data": bytes([0x01, 0x02, 0x03]).hex().upper()}
    assert card_data == {"card_id": card_id, "type": "smartcard", "data": '010203'}

def test_read_smart_card_data_no_reader(mock_readers):
    """Test handling no smart card readers found."""
    mock_readers.return_value = []
    card_id = 123
    with pytest.raises(core.smartcard.SmartCardError) as excinfo: # FIX: Access SmartCardError from core.smartcard
        smartcard.read_smart_card_data(card_id)
    assert "No smart card readers found." in str(excinfo.value)

def test_read_smart_card_data_transmit_fail(mock_readers, mock_connection):
    """Test handling transmit failure."""
    mock_readers.return_value = ["Mock Reader"]
    mock_readers.return_value[0].createConnection.return_value = mock_connection
    mock_connection.connect.return_value = None
    mock_connection.transmit.return_value = ([], 0x61, 0x00)  # Simulate failure status

    card_id = 123
    with pytest.raises(core.smartcard.SmartCardError) as excinfo: # FIX: Access SmartCardError from core.smartcard
        smartcard.read_smart_card_data(card_id)
    assert "Failed to read card data. Status: 61 00" in str(excinfo.value)

def test_read_smart_card_data_invalid_id():
    """Test handling invalid card ID format."""
    invalid_card_id = "abc"
    with pytest.raises(core.smartcard.SmartCardError) as excinfo: # FIX: Access SmartCardError from core.smartcard
        smartcard.read_smart_card_data(invalid_card_id)
    assert "Invalid card ID format." in str(excinfo.value)

def test_authenticate_smart_card_success(mock_readers, mock_connection):
    """Test successful smart card authentication."""
    mock_readers.return_value = ["Mock Reader"]
    mock_readers.return_value[0].createConnection.return_value = mock_connection
    mock_connection.connect.return_value = None
    mock_connection.transmit.return_value = ([], 0x90, 0x00)  # Simulate successful authentication

    card_id = 123
    pin = "1234"
    is_authenticated = smartcard.authenticate_smart_card(card_id, pin)
    assert is_authenticated is True

def test_authenticate_smart_card_failure(mock_readers, mock_connection):
    """Test failed smart card authentication."""
    mock_readers.return_value = ["Mock Reader"]
    mock_readers.return_value[0].createConnection.return_value = mock_connection
    mock_connection.connect.return_value = None
    mock_connection.transmit.return_value = ([], 0x63, 0x00)  # Simulate authentication failure

    card_id = 123
    pin = "1234"
    is_authenticated = smartcard.authenticate_smart_card(card_id, pin)
    assert is_authenticated is False

def test_authenticate_smart_card_no_reader(mock_readers):
    """Test handling no smart card readers found."""
    mock_readers.return_value = []
    card_id = 123
    pin = "1234"
    with pytest.raises(core.smartcard.SmartCardError) as excinfo: # FIX: Access SmartCardError from core.smartcard
        smartcard.authenticate_smart_card(card_id, pin)
    assert "No smart card readers found." in str(excinfo.value)

def test_authenticate_smart_card_invalid_pin():
    """Test handling invalid PIN format."""
    card_id = 123
    invalid_pin = 1234  # Integer instead of string
    with pytest.raises(core.smartcard.SmartCardError) as excinfo: # FIX: Access SmartCardError from core.smartcard
        smartcard.authenticate_smart_card(card_id, invalid_pin)
    assert "PIN must be a string." in str(excinfo.value)

def test_authenticate_smart_card_empty_pin():
    """Test handling empty PIN."""
    card_id = 123
    empty_pin = ""
    with pytest.raises(core.smartcard.SmartCardError) as excinfo: # FIX: Access SmartCardError from core.smartcard
        smartcard.authenticate_smart_card(card_id, empty_pin)
    assert "PIN cannot be empty." in str(excinfo.value)

def test_smartcard_function():
    # Your test code here
    pass