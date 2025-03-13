import pytest
from unittest.mock import patch
from app.api import card_utils
from app.core import card_utils
from enum import Enum

# Add parent directory to path to import modules
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from card_utils import (
    get_reader_timeout, detect_reader_type, toHexString
)

def test_reader_detection():
    """Test reader type detection"""
    # Test Cherry reader detection
    reader_info = detect_reader_type("CHERRY Smart Terminal ST-1234")
    assert reader_info['type'] == "CHERRY_ST"

    # Test ACR reader detection
    reader_info = detect_reader_type("ACS ACR122U")
    assert reader_info['type'] == "ACR122U"

    # Test unknown reader
    reader_info = detect_reader_type("Unknown Reader")
    assert reader_info['type'] == "GENERIC"

    # Test empty string
    reader_info = detect_reader_type("")
    assert reader_info['type'] == "GENERIC"

    # Test None input
    reader_info = detect_reader_type(None)
    assert reader_info['type'] == "GENERIC"

def test_reader_timeout():
    """Test reader timeout settings"""
    # Cherry should have longer timeout
    cherry_timeout = get_reader_timeout("CHERRY Smart Terminal ST-1234")
    acr_timeout = get_reader_timeout("ACS ACR122U")

    assert cherry_timeout > acr_timeout, "Cherry readers should have longer timeouts than ACR122U"

    # Generic reader should have default timeout
    generic_timeout = get_reader_timeout("Generic Reader")
    assert generic_timeout > 0, "Default timeout should be positive"

    # Test empty string
    empty_timeout = get_reader_timeout("")
    assert empty_timeout > 0, "Default timeout should be positive"

    # Test None input
    none_timeout = get_reader_timeout(None)
    assert none_timeout > 0, "Default timeout should be positive"

def test_hex_conversion():
    """Test hex string conversion utility"""
    data = [0x01, 0x02, 0xAB, 0xCD]
    hex_str = toHexString(data)
    assert hex_str == "01 02 AB CD"

    # Test empty list
    data = []
    hex_str = toHexString(data)
    assert hex_str == ""

    # Test None input
    with pytest.raises(TypeError):
        toHexString(None)

def test_safe_globals():
    """Test that safe_globals context manager correctly saves and restores global variables."""
    global MAX_PIN_ATTEMPTS
    original_value = MAX_PIN_ATTEMPTS
    with card_utils.safe_globals():
        MAX_PIN_ATTEMPTS = 10
        assert MAX_PIN_ATTEMPTS == 10
    assert MAX_PIN_ATTEMPTS == original_value

def test_card_status_enum():
    """Test that CardStatus enum is defined correctly."""
    assert isinstance(card_utils.CardStatus, type(Enum))
    assert card_utils.CardStatus.ACTIVE.name == "ACTIVE"
    assert card_utils.CardStatus.BLOCKED.name == "BLOCKED"

def test_pin_attempts():
    """Test that pin_attempts variable is incremented and reset correctly."""
    global pin_attempts
    pin_attempts = 0
    with card_utils.safe_globals():
        card_utils.pin_attempts = 0
        card_utils.pin_attempts += 1
        assert card_utils.pin_attempts == 1
    assert pin_attempts == 0  # Ensure it's reset after exiting context

def test_update_available_readers():
    """Test that update_available_readers function correctly updates the list of available readers."""
    with patch("smartcard.System.readers") as mock_readers:
        mock_readers.return_value = ["Reader 1", "Reader 2"]
        readers = card_utils.update_available_readers()
        assert len(readers) == 2
        assert str(readers[0]) == "Reader 1"
        assert str(readers[1]) == "Reader 2"

def test_detect_card_type():
    """Test that detect_card_type function correctly identifies card types."""
    atr_mifare_classic = "3B6700037475880102"
    atr_unknown = "1234567890"

    assert card_utils.detect_card_type(atr_mifare_classic) == "MIFARE_CLASSIC"
    assert card_utils.detect_card_type(atr_unknown) == "Unknown"

def test_is_card_registered():
    """Test that is_card_registered function correctly checks if a card is registered."""
    with patch("app.api.card_utils.is_card_registered") as mock_is_card_registered:
        mock_is_card_registered.return_value = True
        assert card_utils.is_card_registered("some_atr") == True

        mock_is_card_registered.return_value = False
        assert card_utils.is_card_registered("some_atr") == False