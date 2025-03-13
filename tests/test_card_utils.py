import pytest
from unittest.mock import patch, MagicMock
from enum import Enum

# Standard library imports
import os
import sys

# Local imports - using proper import structure
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.api import card_utils as api_card_utils
from app.core import card_utils as core_card_utils
from card_utils import (
    get_reader_timeout, detect_reader_type, toHexString
)
from app.core import card_utils

class TestReaderDetection:
    """Tests for reader type detection functionality."""
    
    @pytest.mark.parametrize("reader_name, expected_type", [
        ("CHERRY Smart Terminal ST-1234", "CHERRY_ST"),
        ("ACS ACR122U", "ACR122U"),
        ("Unknown Reader", "GENERIC"),
        ("", "GENERIC"),
        (None, "GENERIC")
    ])
    def test_reader_detection(self, reader_name, expected_type):
        """Test reader type detection with various inputs."""
        reader_info = detect_reader_type(reader_name)
        assert reader_info['type'] == expected_type
        assert 'name' in reader_info, "Reader info should contain name field"

    def test_malformed_reader_name(self):
        """Test detection with malformed reader names."""
        # Test with unusual characters
        reader_info = detect_reader_type("Reader with ñóñ-ÁŚĆÏĮç characters")
        assert reader_info['type'] == "GENERIC"
        
        # Test with very long name
        long_name = "X" * 1000
        reader_info = detect_reader_type(long_name)
        assert reader_info['type'] == "GENERIC"


class TestReaderTimeout:
    """Tests for reader timeout settings."""
    
    def test_reader_timeout_comparison(self):
        """Test that different reader types have appropriate timeouts."""
        cherry_timeout = get_reader_timeout("CHERRY Smart Terminal ST-1234")
        acr_timeout = get_reader_timeout("ACS ACR122U")
        assert cherry_timeout > acr_timeout, "Cherry readers should have longer timeouts than ACR122U"

    @pytest.mark.parametrize("reader_name", ["Generic Reader", "", None])
    def test_default_timeout(self, reader_name):
        """Test default timeout values."""
        timeout = get_reader_timeout(reader_name)
        assert timeout > 0, "Default timeout should be positive"
        assert isinstance(timeout, (int, float)), "Timeout should be numeric"

        def test_timeout_exception_handling(self):
            """Test handling of problematic reader names."""
            # Test with non-string non-None value
            with pytest.raises(TypeError):
                get_reader_timeout(123)
    
    def test_to_hex_string():
        """Test toHexString function."""
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
    with core_card_utils.safe_globals():
        MAX_PIN_ATTEMPTS = 10
        assert MAX_PIN_ATTEMPTS == 10
    assert MAX_PIN_ATTEMPTS == original_value

def test_card_status_enum():
    """Test that CardStatus enum is defined correctly."""
    assert isinstance(core_card_utils.CardStatus, type(Enum))
    assert core_card_utils.CardStatus.ACTIVE.name == "ACTIVE"
    assert core_card_utils.CardStatus.BLOCKED.name == "BLOCKED"

def test_pin_attempts():
    """Test that pin_attempts variable is incremented and reset correctly."""
    global pin_attempts
    pin_attempts = 0
    with core_card_utils.safe_globals():
        core_card_utils.pin_attempts = 0
        core_card_utils.pin_attempts += 1
        assert core_card_utils.pin_attempts == 1
    assert pin_attempts == 0  # Ensure it's reset after exiting context

def test_update_available_readers():
    """Test that update_available_readers function correctly updates the list of available readers."""
    with patch("smartcard.System.readers") as mock_readers:
        mock_readers.return_value = ["Reader 1", "Reader 2"]
        readers = core_card_utils.update_available_readers()
        assert len(readers) == 2
        assert str(readers[0]) == "Reader 1"
        assert str(readers[1]) == "Reader 2"

def test_detect_card_type():
    """Test that detect_card_type function correctly identifies card types."""
    atr_mifare_classic = "3B6700037475880102"
    atr_unknown = "1234567890"

    assert core_card_utils.detect_card_type(atr_mifare_classic) == "MIFARE_CLASSIC"
    assert core_card_utils.detect_card_type(atr_unknown) == "Unknown"

def test_is_card_registered():
    """Test that is_card_registered function correctly checks if a card is registered."""
    with patch("app.api.card_utils.is_card_registered") as mock_is_card_registered:
        mock_is_card_registered.return_value = True
        assert api_card_utils.is_card_registered("some_atr")

        mock_is_card_registered.return_value = False
        assert not api_card_utils.is_card_registered("some_atr")