# tests/test_routes.py
import pytest
from smart import app

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_card_status(client, mocker):
    mocker.patch('smartcard.System.readers', return_value=['Mock Reader'])
    mocker.patch('card_utils.establish_connection', return_value=(None, None))
    response = client.get('/card_status')
    assert response.status_code == 200
    assert response.json['status'] in ['warning', 'error']  # Depends on mock behavior

def test_backup_all(client, mocker):
    mocker.patch('smartcard.System.readers', return_value=['Reader1', 'Reader2'])
    mocker.patch('card_utils.backup_card_data', side_effect=[
        (True, "Backup OK 1", "id1"),
        (True, "Backup OK 2", "id2")
    ])
    response = client.post('/backup_all', json={})
    assert response.status_code == 200
    assert response.json['status'] == 'success'
    assert len(response.json['results']) == 2