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
        "username": "emp2",
        "email": "emp2@test.com",
        "password": "123456"
    })
    login = client.post("/auth/login", json={"username": "emp2", "password": "123456"})
    return login.json()["access_token"]

def get_admin_id():
    login = client.post("/auth/login", json={"username": "admin", "password": "123456"})
    token = login.json()["access_token"]
    me = client.get("/me", headers={"Authorization": f"Bearer {token}"})
    return me.json()["id"]

def create_test_project():
    token = get_admin_token()
    response = client.post("/projects/", json={
        "name": "Task Test Project",
        "description": "For task tests"
    }, headers={"Authorization": f"Bearer {token}"})
    return response.json()["id"]

def test_create_task_as_admin():
    token = get_admin_token()
    project_id = create_test_project()
    admin_id = get_admin_id()

    response = client.post("/tasks/", json={
        "title": "Test Task",
        "description": "desc",
        "priority": "High",
        "project_id": project_id,
        "assigned_to": admin_id
    }, headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json()["title"] == "Test Task"

def test_create_task_as_employee():
    emp_token = get_employee_token()
    project_id = create_test_project()
    admin_id = get_admin_id()

    response = client.post("/tasks/", json={
        "title": "Unauthorized Task",
        "description": "desc",
        "priority": "Low",
        "project_id": project_id,
        "assigned_to": admin_id
    }, headers={"Authorization": f"Bearer {emp_token}"})
    assert response.status_code == 403

def test_get_all_tasks():
    token = get_admin_token()
    response = client.get("/tasks/", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_task_status_transition_valid():
    token = get_admin_token()
    project_id = create_test_project()
    admin_id = get_admin_id()

    create = client.post("/tasks/", json={
        "title": "Transition Task",
        "description": "desc",
        "priority": "Medium",
        "project_id": project_id,
        "assigned_to": admin_id
    }, headers={"Authorization": f"Bearer {token}"})
    task_id = create.json()["id"]

    # To Do → In Progress (valid)
    response = client.put(f"/tasks/{task_id}", json={
        "status": "In Progress"
    }, headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json()["status"] == "In Progress"

def test_task_status_transition_invalid():
    token = get_admin_token()
    project_id = create_test_project()
    admin_id = get_admin_id()

    create = client.post("/tasks/", json={
        "title": "Invalid Transition Task",
        "description": "desc",
        "priority": "Medium",
        "project_id": project_id,
        "assigned_to": admin_id
    }, headers={"Authorization": f"Bearer {token}"})
    task_id = create.json()["id"]

    # To Do → Done (invalid, must go through In Progress)
    response = client.put(f"/tasks/{task_id}", json={
        "status": "Done"
    }, headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 400

def test_task_not_found():
    token = get_admin_token()
    response = client.get("/tasks/99999", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 404

def test_employee_cannot_update_others_task():
    admin_token = get_admin_token()
    emp_token = get_employee_token()
    project_id = create_test_project()
    admin_id = get_admin_id()

    create = client.post("/tasks/", json={
        "title": "Admin Task",
        "description": "desc",
        "priority": "Low",
        "project_id": project_id,
        "assigned_to": admin_id
    }, headers={"Authorization": f"Bearer {admin_token}"})
    task_id = create.json()["id"]

    response = client.put(f"/tasks/{task_id}", json={
        "title": "Hacked"
    }, headers={"Authorization": f"Bearer {emp_token}"})
    assert response.status_code == 403
    
    #pytest tests/ -v to run all tests 