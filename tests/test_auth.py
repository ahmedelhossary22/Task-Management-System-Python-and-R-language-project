from fastapi.testclient import TestClient
import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from app.main import app

client = TestClient(app)

def get_admin_token():
    login = client.post("/auth/login", json={"username": "admin", "password": "123456"})
    return login.json()["access_token"]

def test_register_new_user():
    response = client.post("/auth/register", json={
        "username": "testemployee",
        "email": "testemployee@test.com",
        "password": "123456"
    })
    assert response.status_code in [201, 400]  # 400 if already exists

def test_register_defaults_to_employee():
    client.post("/auth/register", json={
        "username": "roletest",
        "email": "roletest@test.com",
        "password": "123456"
    })
    login = client.post("/auth/login", json={"username": "roletest", "password": "123456"})
    assert login.json()["role"] == "employee"

def test_login_success():
    response = client.post("/auth/login", json={"username": "admin", "password": "123456"})
    assert response.status_code == 200
    assert "access_token" in response.json()

def test_login_wrong_password():
    response = client.post("/auth/login", json={"username": "admin", "password": "wrongpass"})
    assert response.status_code == 401

def test_login_wrong_username():
    response = client.post("/auth/login", json={"username": "nobody", "password": "123456"})
    assert response.status_code == 401

def test_protected_route_with_token():
    token = get_admin_token()
    response = client.get("/projects", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200

def test_protected_route_without_token():
    response = client.get("/projects")
    assert response.status_code == 401