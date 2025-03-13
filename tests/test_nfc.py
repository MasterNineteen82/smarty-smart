import pytest
from unittest.mock import patch, MagicMock
from app import get_core
from app.core.nfc import nfc_manager

# Use the modules
core = get_core()
nfc = core.nfc  # Access nfc module from core

@pytest.fixture
def mock_nfc_context(mocker):
    """
    A fixture that mocks the NFC contactless frontend and tag connection.
    This simplifies testing by providing a controlled NFC environment.
    """
    mock_clf = MagicMock()
    mock_tag = MagicMock()
    mock_clf.connect.return_value = mock_tag
    mocker.patch("nfc.ContactlessFrontend", return_value=mock_clf)
    return mock_clf, mock_tag

def test_read_nfc_card_data_success(mocker, mock_nfc_context):
    """Test reading NFC card data successfully."""
    mocker.patch("app.core.nfc.logger.info")
    mock_clf, mock_tag = mock_nfc_context
    mock_tag.dump.return_value = "some NFC data"  # Simulate tag data

    card_data = nfc.read_nfc_card_data(123)

    assert card_data["card_id"] == 123
    assert card_data["type"] == "nfc"
    assert "str" in card_data["tag_type"] # Check if tag type is a string
    assert card_data["data"] is not None
    mock_clf.connect.assert_called_once()
    nfc.logger.info.assert_called()


def test_read_nfc_card_data_no_tag(mocker, mock_nfc_context):
    """Test handling no NFC tag found."""
    mocker.patch("app.core.nfc.logger.info")
    mock_clf, mock_tag = mock_nfc_context
    mock_clf.connect.return_value = None  # Simulate no tag found

    with pytest.raises(nfc.NFCError) as excinfo:
        nfc.read_nfc_card_data(123)

    assert "No NFC tag found" in str(excinfo.value)
    mock_clf.connect.assert_called_once()
    nfc.logger.info.assert_called()


def test_read_nfc_card_data_communication_error(mocker, mock_nfc_context):
    """Test handling NFC communication error."""
    mocker.patch("app.core.nfc.logger.error")
    mock_clf, mock_tag = mock_nfc_context
    mock_clf.connect.side_effect = nfc.clf.CommunicationError("Simulated communication error")

    with pytest.raises(nfc.NFCError) as excinfo:
        nfc.read_nfc_card_data(123)

    assert "Communication error with NFC card" in str(excinfo.value)
    mock_clf.connect.assert_called_once()
    nfc.logger.error.assert_called()


def test_write_nfc_card_data_success(mocker, mock_nfc_context):
    """Test writing NFC card data successfully."""
    mocker.patch("app.core.nfc.logger.info")
    mock_clf, mock_tag = mock_nfc_context

    message = nfc.write_nfc_card_data(123, "some data")

    assert message == {"message": "Data written to NFC card 123 successfully (placeholder)"}
    mock_clf.connect.assert_called_once()
    nfc.logger.info.assert_called()


def test_write_nfc_card_data_no_tag(mocker, mock_nfc_context):
    """Test handling no NFC tag found."""
    mocker.patch("app.core.nfc.logger.info")
    mock_clf, mock_tag = mock_nfc_context
    mock_clf.connect.return_value = None

    with pytest.raises(nfc.NFCError) as excinfo:
        nfc.write_nfc_card_data(123, "some data")

    assert "No NFC tag found" in str(excinfo.value)
    mock_clf.connect.assert_called_once()
    nfc.logger.info.assert_called()

def test_write_nfc_card_data_communication_error(mocker, mock_nfc_context):
    """Test handling NFC communication error during write."""
    mocker.patch("app.core.nfc.logger.error")
    mock_clf, mock_tag = mock_nfc_context
    mock_clf.connect.side_effect = nfc.clf.CommunicationError("Simulated communication error")

    with pytest.raises(nfc.NFCError) as excinfo:
        nfc.write_nfc_card_data(123, "some data")

    assert "Communication error with NFC card" in str(excinfo.value)
    mock_clf.connect.assert_called_once()
    nfc.logger.error.assert_called()

def test_nfc_function():
    # Your test code here
    pass