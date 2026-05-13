const API = "http://localhost:8000";

// ================= AUTH =================

async function register() {
    const res = await fetch(`${API}/auth/register`, {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({
            username: username.value,
            email: email.value,
            password: password.value
        })
    });

    const data = await res.json();

    if (res.status === 201) {
        alert("Registered ");
        window.location.href = "login.html";
    } else {
        message.innerText = data.detail;
    }
}
async function login() {
    const res = await fetch(`${API}/auth/login`, {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({
            username: username.value,
            password: password.value
        })
    });

    const data = await res.json();

    if (res.status === 200) {
        localStorage.setItem("token", data.access_token);
        localStorage.setItem("role", data.role);

        if (data.role === "admin") window.location.href = "admin.html";
        else if (data.role === "manager") window.location.href = "manager.html";
        else window.location.href = "employee.html";
    } else {
        message.innerText = data.detail;
    }
}

function logout() {
    localStorage.clear();
    window.location.href = "login.html";
}

// ================= PROJECTS =================

async function createProject() {
    const token = localStorage.getItem("token");

    const name = prompt("Project name:");
    if (!name || name.trim() === "") {
        alert("Project name is required");
        return;
    }

    const description = prompt("Description:");
    if (description === null) return; 

    const res = await fetch(`${API}/projects/`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            "Authorization": `Bearer ${token}`
        },
        body: JSON.stringify({ name, description })
    });

    if (res.status === 200 || res.status === 201) {
        alert("Project created ");
    } else {
        const data = await res.json();
        alert(data.detail || "Failed to create project");
    }
}
let projectsVisible = false;
let projectsInterval = null;

async function loadProjects() {
    const token = localStorage.getItem("token");
    const list = document.getElementById("projects");
    if (!list) return;

    
    if (projectsVisible) {
        list.innerHTML = "";
        projectsVisible = false;
        clearInterval(projectsInterval);
        projectsInterval = null;
        return;
    }

    
    projectsVisible = true;

    const fetchProjects = async () => {
        const res = await fetch(`${API}/projects/`, {
            headers: { "Authorization": `Bearer ${localStorage.getItem("token")}` }
        });

        const data = await res.json();

        list.innerHTML = `
            <table style="
                width: 60%;
                border-collapse: collapse;
                font-size: 13px;
            ">
                <thead>
                    <tr style="background-color: #f0f0f0;">
                        <th style="padding: 6px 10px; border: 1px solid #ccc;">ID</th>
                        <th style="padding: 6px 10px; border: 1px solid #ccc;">Name</th>
                        <th style="padding: 6px 10px; border: 1px solid #ccc;">Description</th>
                    </tr>
                </thead>
                <tbody id="project-tbody"></tbody>
            </table>
        `;

        const tbody = document.getElementById("project-tbody");

        data.forEach(p => {
            const tr = document.createElement("tr");
            tr.innerHTML = `
                <td style="padding: 5px 10px; border: 1px solid #ccc;">${p.id}</td>
                <td style="padding: 5px 10px; border: 1px solid #ccc;">${p.name}</td>
                <td style="padding: 5px 10px; border: 1px solid #ccc;">${p.description || "—"}</td>
            `;
            tbody.appendChild(tr);
        });
    };

    await fetchProjects();
    projectsInterval = setInterval(fetchProjects, 5000);
}
// ================= TASKS =================

async function createTask() {
    const token = localStorage.getItem("token");

    const title = prompt("Title");
    const description = prompt("Description");
    const priority = prompt("Priority");
    const project_id = parseInt(prompt("Project ID"));
    const assigned_to = parseInt(prompt("User ID"));

    
    if (!title || !description || !priority || isNaN(project_id) || isNaN(assigned_to)) {
        alert(" Invalid input");
        return;
    }

    const res = await fetch("http://localhost:8000/tasks/", {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            "Authorization": `Bearer ${token}`
        },
        body: JSON.stringify({
            title,
            description,
            priority,
            project_id,
            assigned_to
        })
    });

    const data = await res.json();

    
    if (!res.ok) {
        alert(data.detail || data.message || "Error ");
        return;
    }

    alert("Task created ");
}
let tasksVisible = false;
let tasksInterval = null;

async function loadTasks() {
    const token = localStorage.getItem("token");
    const role = localStorage.getItem("role");
    const list = document.getElementById("tasks");
    if (!list) return;


    if (tasksVisible) {
        list.innerHTML = "";
        tasksVisible = false;
        clearInterval(tasksInterval);
        tasksInterval = null;
        return;
    }

    
    tasksVisible = true;

    const fetchTasks = async () => {
        const res = await fetch(`${API}/tasks`, {
            headers: { "Authorization": `Bearer ${localStorage.getItem("token")}` }
        });

        const data = await res.json();

        list.innerHTML = `
            <table style="
                width: 60%;
                border-collapse: collapse;
                font-size: 13px;
            ">
                <thead>
                    <tr style="background-color: #f0f0f0;">
                        <th style="padding: 6px 10px; border: 1px solid #ccc;">ID</th>
                        <th style="padding: 6px 10px; border: 1px solid #ccc;">Name</th>
                        <th style="padding: 6px 10px; border: 1px solid #ccc;">Status</th>
                        <th style="padding: 6px 10px; border: 1px solid #ccc;">Actions</th>
                    </tr>
                </thead>
                <tbody id="task-tbody"></tbody>
            </table>
        `;

        const tbody = document.getElementById("task-tbody");

        data.forEach(task => {
            const tr = document.createElement("tr");
            tr.innerHTML = `
                <td style="padding: 5px 10px; border: 1px solid #ccc;">${task.id}</td>
                <td style="padding: 5px 10px; border: 1px solid #ccc;">${task.title}</td>
                <td style="padding: 5px 10px; border: 1px solid #ccc;">${task.status}</td>
                <td style="padding: 5px 10px; border: 1px solid #ccc;">
                    <button onclick="getTask(${task.id})">View</button>
                    ${(role === "employee" || role === "manager") ? `<button onclick="updateTask(${task.id})">Update</button>` : ""}
                </td>
            `;
            tbody.appendChild(tr);
        });
    };

    await fetchTasks();
    tasksInterval = setInterval(fetchTasks, 5000);
}
async function getTask(id) {
    const token = localStorage.getItem("token");

    const res = await fetch(`${API}/tasks/${id}`, {
        headers: {
            "Authorization": `Bearer ${token}`
        }
    });

    const task = await res.json();

    
    if (!res.ok) {
        alert(task.detail || "Error ");
        return;
    }

    alert(`
Title: ${task.title || "N/A"}
Description: ${task.description || "N/A"}
Priority: ${task.priority || "N/A"}
Status: ${task.status || "N/A"}
Project ID: ${task.project_id || "N/A"}
Assigned To: ${task.assigned_to || "N/A"}
    `);
}

async function updateTask(id) {
    const token = localStorage.getItem("token");

    const field = prompt("What do you want to update?\n1. status\n2. title\n3. priority");

    
    if (field === null) return;

    let body = {};

    if (field === "1") {
        const status = prompt("Enter status: To Do / In Progress / Done");
        if (status === null) return;       
        body.status = status;

    } else if (field === "2") {
        const title = prompt("Enter new title");
        if (title === null) return;
        body.title = title;

    } else if (field === "3") {
        const priority = prompt("Enter priority");
        if (priority === null) return;
        body.priority = priority;

    } else {
        alert("Invalid choice");
        return;
    }

    try {
        const res = await fetch(`http://localhost:8000/tasks/${id}`, {
            method: "PUT",
            headers: {
                "Content-Type": "application/json",
                "Authorization": `Bearer ${token}`
            },
            body: JSON.stringify(body)
        });

        const data = await res.json();

        if (res.status === 200) {
            alert("Updated ");
            loadTasks();
        } else {
            alert(data.detail || "Update failed");
        }

    } catch (err) {
        alert("Network error — is the server running?");
        console.error(err);
    }
}                                              
async function deleteTask(id) {
    const token = localStorage.getItem("token");

    const res = await fetch(`${API}/tasks/${id}`, {
        method: "DELETE",
        headers: { "Authorization": `Bearer ${token}` }
    });

    if (res.status === 204) {
        alert("Deleted ");
        loadTasks();
    } else {
        const data = await res.json();
        alert(data.detail || "Delete failed");
    }
}

async function getTaskPrompt() {
    const id = prompt("Enter Task ID:");
    if (!id) return;
    getTask(id);
}

async function deleteTaskPrompt() {
    const id = prompt("Enter Task ID to delete:");
    if (!id) return;

    const token = localStorage.getItem("token");

    const res = await fetch(`${API}/tasks/${id}`, {
        method: "DELETE",
        headers: { "Authorization": `Bearer ${token}` }
    });

    if (res.status === 204) {
        alert("Task deleted ");
        loadTasks();
    } else {
        const data = await res.json();
        alert(data.detail || "Delete failed");
    }
}async function updateTaskPrompt() {
    const id = prompt("Enter Task ID:");
    if (!id) return;

    updateTask(id); 
}

async function getProjectPrompt() {
    const id = prompt("Enter Project ID:");
    if (!id) return;

    const token = localStorage.getItem("token");

    const res = await fetch(`${API}/projects/${id}`, {
        headers: {
            "Authorization": `Bearer ${token}`
        }
    });

    const data = await res.json();

    alert(`
Project: ${data.name}
Description: ${data.description}
    `);
}

async function deleteProjectPrompt() {
    const id = prompt("Enter Project ID to delete:");
    if (!id) return;

    const token = localStorage.getItem("token");

    await fetch(`${API}/projects/${id}`, {
        method: "DELETE",
        headers: {
            "Authorization": `Bearer ${token}`
        }
    });

    alert("Project deleted ");
    loadProjects();
}
async function updateProjectPrompt() {
    const id = prompt("Enter Project ID:");
    if (!id) return;

    const token = localStorage.getItem("token");

    const name = prompt("New name:");
    const description = prompt("New description:");

    await fetch(`${API}/projects/${id}`, {
        method: "PUT",
        headers: {
            "Content-Type": "application/json",
            "Authorization": `Bearer ${token}`
        },
        body: JSON.stringify({
            name,
            description
        })
    });

    alert("Project updated ");
    loadProjects();
}
async function showFilterForm() {
    const list = document.getElementById("tasks");
    if (!list) return;

    
    const existing = document.getElementById("filter-results");
    if (existing) {
        list.innerHTML = "";
        return;
    }

    
    list.innerHTML = `
        <div style="margin-bottom: 10px; font-size: 13px;">
            <select id="filter-status" style="padding: 5px; margin-right: 8px;">
                <option value="">All Status</option>
                <option value="To Do">To Do</option>
                <option value="In Progress">In Progress</option>
                <option value="Done">Done</option>
            </select>
            <select id="filter-priority" style="padding: 5px; margin-right: 8px;">
                <option value="">All Priority</option>
                <option value="Low">Low</option>
                <option value="Medium">Medium</option>
                <option value="High">High</option>
            </select>
            <input id="filter-assigned" type="number" placeholder="Assigned To (ID)" style="padding: 5px; margin-right: 8px; width: 150px;" />
            <button onclick="applyFilter()">Search</button>
            <button onclick="applyFilter(true)">Clear</button>
        </div>
        <div id="filter-results"></div>
    `;
}
async function applyFilter(clear = false) {
    const token = localStorage.getItem("token");
    const role = localStorage.getItem("role");

    let status = "";
    let priority = "";
    let assigned = "";

    if (!clear) {
        status   = document.getElementById("filter-status")?.value || "";
        priority = document.getElementById("filter-priority")?.value || "";
        assigned = document.getElementById("filter-assigned")?.value || "";
    } else {
        // Reset dropdowns
        document.getElementById("filter-status").value = "";
        document.getElementById("filter-priority").value = "";
        document.getElementById("filter-assigned").value = "";
    }

    const params = new URLSearchParams();
    if (status)   params.append("status", status);
    if (priority) params.append("priority", priority);
    if (assigned) params.append("assigned_to", assigned);

    const url = `${API}/tasks${params.toString() ? "?" + params.toString() : ""}`;

    const res = await fetch(url, {
        headers: { "Authorization": `Bearer ${token}` }
    });

    const data = await res.json();

    const results = document.getElementById("filter-results");
    if (!results) return;

    results.innerHTML = `
        <table style="width: 60%; border-collapse: collapse; font-size: 13px;">
            <thead>
                <tr style="background-color: #f0f0f0;">
                    <th style="padding: 6px 10px; border: 1px solid #ccc;">ID</th>
                    <th style="padding: 6px 10px; border: 1px solid #ccc;">Name</th>
                    <th style="padding: 6px 10px; border: 1px solid #ccc;">Description</th>
                    <th style="padding: 6px 10px; border: 1px solid #ccc;">Status</th>
                    <th style="padding: 6px 10px; border: 1px solid #ccc;">Priority</th>
                    <th style="padding: 6px 10px; border: 1px solid #ccc;">Actions</th>
                </tr>
            </thead>
            <tbody id="filter-tbody"></tbody>
        </table>
    `;

    const tbody = document.getElementById("filter-tbody");

    if (data.length === 0) {
        tbody.innerHTML = `<tr><td colspan="6" style="text-align:center; padding: 10px;">No tasks found</td></tr>`;
        return;
    }

    data.forEach(task => {
        const tr = document.createElement("tr");
        tr.innerHTML = `
            <td style="padding: 5px 10px; border: 1px solid #ccc;">${task.id}</td>
            <td style="padding: 5px 10px; border: 1px solid #ccc;">${task.title}</td>
            <td style="padding: 5px 10px; border: 1px solid #ccc;">${task.description || "—"}</td>
            <td style="padding: 5px 10px; border: 1px solid #ccc;">${task.status}</td>
            <td style="padding: 5px 10px; border: 1px solid #ccc;">${task.priority}</td>
            <td style="padding: 5px 10px; border: 1px solid #ccc;">
                <button onclick="getTask(${task.id})">View</button>
                ${(role === "employee" || role === "manager") ? `<button onclick="updateTask(${task.id})">Update</button>` : ""}
            </td>
        `;
        tbody.appendChild(tr);
    });
}
// ----------------------user 

let usersVisible = false;

async function loadUsers() {
    const token = localStorage.getItem("token");
    const list = document.getElementById("users");
    if (!list) return;

    // If visible, close it
    if (usersVisible) {
        list.innerHTML = "";
        usersVisible = false;
        return;
    }

    // If hidden, open it
    usersVisible = true;

    const res = await fetch(`${API}/users/`, {
        headers: { "Authorization": `Bearer ${token}` }
    });

    const data = await res.json();

    if (!res.ok) {
        alert(data.detail || "Error loading users");
        usersVisible = false;
        return;
    }

    list.innerHTML = `
        <table style="width: 60%; border-collapse: collapse; font-size: 13px;">
            <thead>
                <tr style="background-color: #f0f0f0;">
                    <th style="padding: 6px 10px; border: 1px solid #ccc;">ID</th>
                    <th style="padding: 6px 10px; border: 1px solid #ccc;">Username</th>
                    <th style="padding: 6px 10px; border: 1px solid #ccc;">Email</th>
                    <th style="padding: 6px 10px; border: 1px solid #ccc;">Role</th>
                    <th style="padding: 6px 10px; border: 1px solid #ccc;">Actions</th>
                </tr>
            </thead>
            <tbody id="users-tbody"></tbody>
        </table>
    `;

    const tbody = document.getElementById("users-tbody");

    if (data.length === 0) {
        tbody.innerHTML = `<tr><td colspan="5" style="text-align:center; padding: 10px;">No users found</td></tr>`;
        return;
    }

    data.forEach(u => {
        const tr = document.createElement("tr");
        tr.innerHTML = `
            <td style="padding: 5px 10px; border: 1px solid #ccc;">${u.id}</td>
            <td style="padding: 5px 10px; border: 1px solid #ccc;">${u.username}</td>
            <td style="padding: 5px 10px; border: 1px solid #ccc;">${u.email}</td>
            <td style="padding: 5px 10px; border: 1px solid #ccc;">${u.role}</td>
            <td style="padding: 5px 10px; border: 1px solid #ccc;">
                <button onclick="deleteUser(${u.id})">Delete</button>
            </td>
        `;
        tbody.appendChild(tr);
    });
}
async function getUserPrompt() {
    const id = prompt("Enter User ID:");
    if (!id) return;

    const token = localStorage.getItem("token");

    const res = await fetch(`${API}/users/${id}`, {
        headers: {
            "Authorization": `Bearer ${token}`
        }
    });

    const data = await res.json();

    if (!res.ok) {
        alert(data.detail || "Error ");
        return;
    }

    alert(`Username: ${data.username}\nEmail: ${data.email}\nRole: ${data.role}`);
}
async function deleteUser(id) {
    const token = localStorage.getItem("token");

    const res = await fetch(`${API}/users/${id}`, {
        method: "DELETE",
        headers: {
            "Authorization": `Bearer ${token}`
        }
    });

    // If delete failed
    if (!res.ok) {
        const data = await res.json();

        // Custom message from backend
        alert(data.detail || "User cannot be deleted");

        return;
    }

    alert("User deleted ");
    loadUsers();
}
async function deleteUserPrompt() {
    const id = prompt("Enter User ID:");
    if (!id) return;

    deleteUser(id);
}

async function createUser() {
    const token = localStorage.getItem("token");

    const username = prompt("Username:");
    const email = prompt("Email:");
    const password = prompt("Password:");
    const role = prompt("Role (admin/manager/employee):");

    if (!username || !email || !password || !role) {
        alert(" All fields required");
        return;
    }

    const res = await fetch(`${API}/users/`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            "Authorization": `Bearer ${token}`
        },
        body: JSON.stringify({ username, email, password, role })
    });

    const data = await res.json();

    if (!res.ok) {
        alert(data.detail || "Error ");
        return;
    }

    alert("User created ");
    loadUsers();
}

async function updateUserPrompt() {
    const id = prompt("User ID:");
    if (!id) return;

    const token = localStorage.getItem("token");

    const username = prompt("New username (optional):");
    const email = prompt("New email (optional):");
    const role = prompt("New role (optional):");
    const password = prompt("New password (optional):");
    const body = {};

    if (username) body.username = username;
    if (email) body.email = email;
    if (role) body.role = role;
    if (password) body.password = password;
    if (Object.keys(body).length === 0) {
        alert("No fields updated");
        return;
    }
    const res = await fetch(`${API}/users/${id}`, {
        method: "PUT",
        headers: {
            "Content-Type": "application/json",
            "Authorization": `Bearer ${token}`
        },
        body: JSON.stringify(body)
    });

    const data = await res.json();

    if (!res.ok) {
        alert(data.detail || "Error ");
        return;
    }

    alert("User updated ");
    loadUsers();
}
function goToDashboard() {
    window.location.href = "dashboard.html";
}