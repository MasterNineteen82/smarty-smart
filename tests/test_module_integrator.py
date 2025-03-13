import pytest
from unittest.mock import MagicMock, patch
from typing import Any, Dict
from app.core.data_manager import SmartcardDataManager, ResponseStatus, ValidationError
from app.core.module_integrator import ModuleIntegrator, ModuleIntegratorError

# Constants for testing
VALID_ATR = "3B9F958131"
VALID_APDU = "9000"
EDGE_CASE_LONG_ATR = "3B" + "FF" * 100  # Very long ATR
EDGE_CASE_LONG_APDU = "90" * 100  # Very long APDU

@pytest.fixture
def mock_data_manager():
    """Fixture to provide a mock SmartcardDataManager for tests."""
    data_manager = MagicMock(spec=SmartcardDataManager)
    data_manager.add_entry.return_value = {"status": ResponseStatus.SUCCESS.value}
    return data_manager

@pytest.fixture
def integrator(mock_data_manager):
    """Fixture to provide a ModuleIntegrator instance with a mock data manager."""
    return ModuleIntegrator(mock_data_manager)

class TestModuleIntegratorInitialization:
    """Tests for ModuleIntegrator initialization."""
    
    def test_valid_initialization(self, mock_data_manager):
        """Test initialization with a valid SmartcardDataManager."""
        integrator = ModuleIntegrator(mock_data_manager)
        assert integrator.data_manager == mock_data_manager
    
    def test_invalid_initialization(self):
        """Test initialization with invalid data manager types."""
        invalid_managers = [
            "invalid_data_manager",
            123,
            None,
            {},
            []
        ]
        for invalid_manager in invalid_managers:
            with pytest.raises(TypeError, match="data_manager must be a SmartcardDataManager instance"):
                ModuleIntegrator(invalid_manager)

class TestLinkToCardValidation:
    """Tests for link_to_card_validation method."""
    
    def test_valid_atr(self, integrator, mock_data_manager):
        """Test linking a valid ATR."""
        response = integrator.link_to_card_validation(VALID_ATR)
        assert response["status"] == ResponseStatus.SUCCESS.value
        mock_data_manager.add_entry.assert_called_once()
        assert VALID_ATR in str(mock_data_manager.add_entry.call_args)
    
    def test_invalid_atr_type(self, integrator):
        """Test validation fails with invalid ATR types."""
        invalid_atrs = [123, None, {}, [], True]
        for invalid_atr in invalid_atrs:
            with pytest.raises(ValidationError, match="ATR must be a string"):
                integrator.link_to_card_validation(invalid_atr)
    
    def test_invalid_atr_format(self, integrator):
        """Test validation fails with invalid ATR formats."""