import os
import pytest
import secrets
import string
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from main import Base, User, UserRole, get_password_hash
import requests


SQLALCHEMY_DATABASE_URL = os.environ.get("SQLALCHEMY_DATABASE_URL", None)
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base.metadata.drop_all(bind=engine)
Base.metadata.create_all(bind=engine)


def generate_password(length: int = 32) -> str:
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*()-_=+"
    return ''.join(secrets.choice(alphabet) for _ in range(length))


@pytest.fixture(scope="module")
def create_admin_user():
    db = TestingSessionLocal()
    password = generate_password()
    user = User(
        email="ci_admin@test.com",
        username="ci_admin",
        hashed_password=get_password_hash(password),
        role=UserRole.ADMIN,
        is_active=True
    )
    db.add(user)
    db.commit()
    db.close()
    return {"username": "ci_admin", "password": password}


def test_login_and_get_token(create_admin_user):
    creds = create_admin_user
    API_URL = os.environ.get("API_URL", "http://localhost:80")

    response = requests.post(
        f"{API_URL}/token",
        data={
            "username": creds["username"],
            "password": creds["password"]
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=5
    )

    assert response.status_code == 200
    token = response.json().get("access_token")
    assert token


    print(f"ADMIN_TOKEN={token}")

