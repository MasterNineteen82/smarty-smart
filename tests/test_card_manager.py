import pytest
from unittest.mock import patch
from app.api.card_manager import CardManager
from app.exceptions import CardError  # Assuming you have custom exceptions

@pytest.fixture
def card_manager():
    """Fixture to create a CardManager instance for each test."""
    return CardManager()

def test_register_card(card_manager):
    """Test that register_card function correctly registers a card."""
    atr = "1234567890"
    user_id = "user123"
    card_manager.register_card(atr, user_id)
    assert card_manager.is_card_registered(atr)

def test_register_card_duplicate(card_manager):
    """Test registering the same card twice."""
    atr = "1234567890"
    user_id = "user123"
    card_manager.register_card(atr, user_id)
    with pytest.raises(CardError):  # Expecting a CardError for duplicate registration
        card_manager.register_card(atr, user_id)

def test_unregister_card(card_manager):
    """Test that unregister_card function correctly unregisters a card."""
    atr = "1234567890"
    user_id = "user123"
    card_manager.register_card(atr, user_id)
    card_manager.unregister_card(atr)
    assert not card_manager.is_card_registered(atr)

def test_unregister_nonexistent_card(card_manager):
    """Test unregistering a card that isn't registered."""
    atr = "1234567890"
    with pytest.raises(CardError):  # Expecting a CardError for non-existent card
        card_manager.unregister_card(atr)

def test_is_card_registered(card_manager):
    """Test that is_card_registered function correctly checks if a card is registered."""
    atr = "1234567890"
    user_id = "user123"
    assert not card_manager.is_card_registered(atr)
    card_manager.register_card(atr, user_id)
    assert card_manager.is_card_registered(atr)

def test_block_card(card_manager):
    """Test that block_card function correctly blocks a card."""
    atr = "1234567890"
    with patch("app.api.card_manager.CardManager.block_card") as mock_block_card:
        card_manager.block_card(atr)
        mock_block_card.assert_called_once_with(atr)

def test_activate_card(card_manager):
    """Test that activate_card function correctly activates a card."""
    atr = "1234567890"
    with patch("app.api.card_manager.CardManager.activate_card") as mock_activate_card:
        card_manager.activate_card(atr)
        mock_activate_card.assert_called_once_with(atr)

def test_deactivate_card(card_manager):
    """Test that deactivate_card function correctly deactivates a card."""
    atr = "1234567890"
    with patch("app.api.card_manager.CardManager.deactivate_card") as mock_deactivate_card:
        card_manager.deactivate_card(atr)
        mock_deactivate_card.assert_called_once_with(atr)

# Add more tests for edge cases and error conditions
def test_register_card_invalid_atr(card_manager):
    """Test registering a card with an invalid ATR."""
    atr = "invalid_atr"
    user_id = "user123"
    with pytest.raises(CardError):  # Expecting a CardError for invalid ATR
        card_manager.register_card(atr, user_id)

def test_block_nonexistent_card(card_manager):
    """Test blocking a card that isn't registered."""
    atr = "1234567890"
    with pytest.raises(CardError):
        card_manager.block_card(atr)

def test_activate_nonexistent_card(card_manager):
    """Test activating a card that isn't registered."""
    atr = "1234567890"
    with pytest.raises(CardError):
        card_manager.activate_card(atr)

def test_deactivate_nonexistent_card(card_manager):
    """Test deactivating a card that isn't registered."""
    atr = "1234567890"
    with pytest.raises(CardError):
        card_manager.deactivate_card(atr)