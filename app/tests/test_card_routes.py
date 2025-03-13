import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.db import Base, Card, get_db

# Database URL for testing
TEST_DATABASE_URL = "sqlite:///./test.db"

# Create a test engine
engine = create_engine(TEST_DATABASE_URL)

# Create a test session
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Override the get_db dependency
def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

# Create a test client
client = TestClient(app)

# Create the database tables
@pytest.fixture()
def test_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

# Test cases
def test_register_card(test_db):
    response = client.post(
        "/cards/register",
        json={"atr": "test_atr", "user_id": 1, "status": "inactive"},
    )
    assert response.status_code == 201
    assert response.json()["atr"] == "test_atr"

def test_get_card(test_db):
    # Create a card in the test database
    db = TestingSessionLocal()
    card = Card(atr="test_atr", user_id=1, status="inactive")
    db.add(card)
    db.commit()
    db.refresh(card)
    db.close()

    # Get the card
    response = client.get("/cards/test_atr")
    assert response.status_code == 200
    assert response.json()["atr"] == "test_atr"

def test_get_card_not_found(test_db):
    response = client.get("/cards/nonexistent_atr")
    assert response.status_code == 404
    assert response.json()["detail"] == "Card not found"

def test_activate_card(test_db):
    # Create a card in the test database
    db = TestingSessionLocal()
    card = Card(atr="test_atr", user_id=1, status="inactive")
    db.add(card)
    db.commit()
    db.refresh(card)
    db.close()

    # Activate the card
    response = client.post("/cards/test_atr/activate")
    assert response.status_code == 200
    assert response.json()["status"] == "active"

def test_deactivate_card(test_db):
    # Create a card in the test database
    db = TestingSessionLocal()
    card = Card(atr="test_atr", user_id=1, status="active")
    db.add(card)
    db.commit()
    db.refresh(card)
    db.close()

    # Deactivate the card
    response = client.post("/cards/test_atr/deactivate")
    assert response.status_code == 200
    assert response.json()["status"] == "inactive"

def test_block_card(test_db):
    # Create a card in the test database
    db = TestingSessionLocal()
    card = Card(atr="test_atr", user_id=1, status="active")
    db.add(card)
    db.commit()
    db.refresh(card)
    db.close()

    # Block the card
    response = client.post("/cards/test_atr/block")
    assert response.status_code == 200
    assert response.json()["status"] == "blocked"

def test_unblock_card(test_db):
    # Create a card in the test database
    db = TestingSessionLocal()
    card = Card(atr="test_atr", user_id=1, status="blocked")
    db.add(card)
    db.commit()
    db.refresh(card)
    db.close()

    # Unblock the card
    response = client.post("/cards/test_atr/unblock")
    assert response.status_code == 200
    assert response.json()["status"] == "inactive"