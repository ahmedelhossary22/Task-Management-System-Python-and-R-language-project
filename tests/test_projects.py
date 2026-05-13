from fastapi.testclient import TestClient
import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from app.main import app

client = TestClient(app)

def get_admin_token():
    login = client.post("/auth/login", json={"username": "admin", "password": "123456"})
    return login.json()["access_token"]

def get_employee_token():
    client.post("/auth/register", json={
        "username": "emp1",
        "email": "emp1@test.com",
        "password": "123456"
    })
    login = client.post("/auth/login", json={"username": "emp1", "password": "123456"})
    return login.json()["access_token"]

def test_create_project_as_admin():
    token = get_admin_token()
    response = client.post("/projects/", json={
        "name": "Test Project",
        "description": "Test Description"
    }, headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 201
    assert response.json()["name"] == "Test Project"

def test_create_project_as_employee():
    token = get_employee_token()
    response = client.post("/projects/", json={
        "name": "Unauthorized Project",
        "description": "Should fail"
    }, headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 403

def test_get_all_projects():
    token = get_admin_token()
    response = client.get("/projects/", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_get_project_by_id():
    token = get_admin_token()
    # create one first
    create = client.post("/projects/", json={
        "name": "Project For Get",
        "description": "desc"
    }, headers={"Authorization": f"Bearer {token}"})
    project_id = create.json()["id"]

    response = client.get(f"/projects/{project_id}", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json()["id"] == project_id

def test_get_project_not_found():
    token = get_admin_token()
    response = client.get("/projects/99999", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 404

def test_update_project_as_admin():
    token = get_admin_token()
    create = client.post("/projects/", json={
        "name": "Old Name",
        "description": "Old Desc"
    }, headers={"Authorization": f"Bearer {token}"})
    project_id = create.json()["id"]

    response = client.put(f"/projects/{project_id}", json={
        "name": "New Name",
        "description": "Old Desc"
    }, headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json()["name"] == "New Name"
    
def test_delete_project_as_admin():
    token = get_admin_token()
    create = client.post("/projects/", json={
        "name": "To Delete",
        "description": "desc"
    }, headers={"Authorization": f"Bearer {token}"})
    project_id = create.json()["id"]

    response = client.delete(f"/projects/{project_id}", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200

def test_delete_project_as_employee():
    token = get_admin_token()
    create = client.post("/projects/", json={
        "name": "Cannot Delete",
        "description": "desc"
    }, headers={"Authorization": f"Bearer {token}"})
    project_id = create.json()["id"]

    emp_token = get_employee_token()
    response = client.delete(f"/projects/{project_id}", headers={"Authorization": f"Bearer {emp_token}"})
    assert response.status_code == 403