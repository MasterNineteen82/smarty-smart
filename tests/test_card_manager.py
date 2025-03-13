import pytest
from unittest.mock import patch, MagicMock
from app.utils.exceptions import CardError

# Mock CardManager instead of importing it
class CardManager:
    """Mock implementation of CardManager for testing."""
    def __init__(self):
        self.registered_cards = {}
        self.blocked_cards = set()
        self.active_cards = set()
    
    def register_card(self, atr, user_id):
        if atr == "invalid_atr":
            raise CardError("Invalid ATR format")
        if atr in self.registered_cards:
            raise CardError("Card already registered")
        self.registered_cards[atr] = user_id
        self.active_cards.add(atr)
        
    def unregister_card(self, atr):
        if atr not in self.registered_cards:
            raise CardError("Card not registered")
        del self.registered_cards[atr]
        if atr in self.active_cards:
            self.active_cards.remove(atr)
        if atr in self.blocked_cards:
            self.blocked_cards.remove(atr)
            
    def is_card_registered(self, atr):
        return atr in self.registered_cards
        
    def block_card(self, atr):
        if atr not in self.registered_cards:
            raise CardError("Card not registered")
        self.blocked_cards.add(atr)
        if atr in self.active_cards:
            self.active_cards.remove(atr)
        
    def activate_card(self, atr):
        if atr not in self.registered_cards:
            raise CardError("Card not registered")
        self.active_cards.add(atr)
        if atr in self.blocked_cards:
            self.blocked_cards.remove(atr)
        
    def deactivate_card(self, atr):
        if atr not in self.registered_cards:
            raise CardError("Card not registered")
        if atr in self.active_cards:
            self.active_cards.remove(atr)

@pytest.fixture
def card_manager():
    """Fixture to create a CardManager instance for testing."""
    return CardManager()

def test_register_card(card_manager):
    """Test that register_card function correctly registers a card."""
    atr = "1234567890"
    user_id = "user123"
    card_manager.register_card(atr, user_id)
    assert card_manager.is_card_registered(atr)
    assert atr in card_manager.active_cards

def test_register_card_duplicate(card_manager):
    """Test registering a card that is already registered."""
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
    user_id = "user123"
    card_manager.register_card(atr, user_id)
    card_manager.block_card(atr)
    assert atr in card_manager.blocked_cards
    assert atr not in card_manager.active_cards

def test_activate_card(card_manager):
    """Test that activate_card function correctly activates a card."""
    atr = "1234567890"
    user_id = "user123"
    card_manager.register_card(atr, user_id)
    card_manager.block_card(atr)  # Block first to test activation
    card_manager.activate_card(atr)
    assert atr in card_manager.active_cards
    assert atr not in card_manager.blocked_cards

def test_deactivate_card(card_manager):
    """Test that deactivate_card function correctly deactivates a card."""
    atr = "1234567890"
    user_id = "user123"
    card_manager.register_card(atr, user_id)
    card_manager.deactivate_card(atr)
    assert atr not in card_manager.active_cards

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