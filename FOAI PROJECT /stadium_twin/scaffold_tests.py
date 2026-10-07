import os

base_dir = r'c:\Users\manis\OneDrive\Desktop\new foai\stadium_twin'

test_auth_content = '''import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.db import Base, engine, get_db
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Use in-memory SQLite for testing
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine_test = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine_test)

Base.metadata.create_all(bind=engine_test)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)

@pytest.fixture(autouse=True)
def cleanup_db():
    Base.metadata.drop_all(bind=engine_test)
    Base.metadata.create_all(bind=engine_test)
    yield

def test_register():
    response = client.post("/auth/register", data={"username": "testuser", "password": "testpassword"})
    assert response.status_code == 200
    assert response.json()["message"] == "User registered successfully"

def test_login():
    client.post("/auth/register", data={"username": "testuser", "password": "testpassword"})
    response = client.post("/auth/login", data={"username": "testuser", "password": "testpassword"})
    assert response.status_code == 200
    assert "access_token" in response.cookies
'''

files = {
    'tests/__init__.py': '',
    'tests/test_auth.py': test_auth_content
}

for path, content in files.items():
    full_path = os.path.join(base_dir, path.replace('/', os.sep))
    with open(full_path, 'w', encoding='utf-8') as f:
        f.write(content)

print("Tests scaffolded.")
