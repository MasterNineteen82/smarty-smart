# tests/test_routes.py
import pytest

@pytest.fixture
def client():
    """Create a test client for the Flask application."""
    pass

class TestCardStatus:
    """Tests for the card_status endpoint."""
    
    def test_card_status_with_reader_no_connection(self, client, mocker):
        """Test card status when reader exists but connection fails."""
        mocker.patch('smartcard.System.readers', return_value=['Mock Reader'])
        mocker.patch('card_utils.establish_connection', return_value=(None, None))
        
        response = client.get('/card_status')
        
        assert response.status_code == 200
        assert response.json['status'] == 'warning'
        assert 'message' in response.json
    
    def test_card_status_with_no_readers(self, client, mocker):
        """Test card status when no readers are available."""
        mocker.patch('smartcard.System.readers', return_value=[])
        
        response = client.get('/card_status')
        
        assert response.status_code == 200
        assert response.json['status'] == 'error'
        assert 'message' in response.json

    def test_card_status_with_exception(self, client, mocker):
        """Test card status handling when exception occurs."""
        mocker.patch('smartcard.System.readers', side_effect=Exception("Mock error"))
        
        response = client.get('/card_status')
        
        assert response.status_code == 500
        assert response.json['status'] == 'error'
        assert 'error' in response.json