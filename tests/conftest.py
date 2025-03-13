import os
import sys
import pytest
import tempfile
from unittest.mock import patch

# Add parent directory to path so we can import our modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

@pytest.fixture
def mock_card_connection():
    """Create a mock card connection"""
    class MockCardConnection:
        def __init__(self, atr=None):
            self.atr = atr or [0x3B, 0x8F, 0x80, 0x01, 0x80, 0x4F, 0x0C, 0xA0, 0x00, 0x00, 0x03, 0x06]
            
        def getATR(self):
            return self.atr
            
        def transmit(self, apdu):
            # Default success response
            if not isinstance(apdu, list):
                raise ValueError("APDU must be a list")
            return [], 0x90, 0x00
        
        def disconnect(self):
            pass
    
    return MockCardConnection()

@pytest.fixture
def temp_backup_dir():
    """Create a temporary directory for backups during tests"""
    with tempfile.TemporaryDirectory() as temp_dir:
        original_dir = os.environ.get('SMARTY_BACKUP_DIR')
        os.environ['SMARTY_BACKUP_DIR'] = temp_dir
        try:
            yield temp_dir
        finally:
            if original_dir:
                os.environ['SMARTY_BACKUP_DIR'] = original_dir
            else:
                os.environ.pop('SMARTY_BACKUP_DIR', None)

@pytest.fixture
def temp_registered_cards_file():
    """Create a temporary file for registered cards during tests"""
    with tempfile.NamedTemporaryFile(delete=False) as temp_file:
        original_file = os.environ.get('SMARTY_REG_FILE')
        os.environ['SMARTY_REG_FILE'] = temp_file.name
        try:
            yield temp_file.name
        finally:
            os.unlink(temp_file.name)
            if original_file:
                os.environ['SMARTY_REG_FILE'] = original_file
            else:
                os.environ.pop('SMARTY_REG_FILE', None)