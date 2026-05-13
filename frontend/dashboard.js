const API = "http://localhost:8000";

// ✅ Admin protection
const token = localStorage.getItem("token");
const role = localStorage.getItem("role");

if (!token || role !== "admin") {
  alert("Access denied. Admins only.");
  window.location.href = "login.html";
}

async function loadData() {
  try {
    const res = await fetch(`${API}/dashboard`, {
      headers: { "Authorization": `Bearer ${token}` }
    });
    const data = await res.json();

    document.getElementById("requests").innerText = data.total_requests;
    document.getElementById("errors").innerText = data.total_errors;
    document.getElementById("errorRate").innerText = (data.error_rate * 100).toFixed(2) + "%";
    document.getElementById("avgTime").innerText = data.average_response_time + "s";

    const logsList = document.getElementById("logs");
    logsList.innerHTML = "";
    data.recent_logs.forEach(log => {
      const li = document.createElement("li");
      li.innerText = log;
      logsList.appendChild(li);
    });

    const healthRes = await fetch(`${API}/health`);
    const healthData = await healthRes.json();

    const healthEl = document.getElementById("healthStatus");
    healthEl.innerText = healthData.status + " / DB: " + healthData.database;
    healthEl.className = healthData.status === "healthy" ? "status healthy" : "status unhealthy";

  } catch (err) {
    document.getElementById("healthStatus").innerText = "Failed to connect to API";
    document.getElementById("healthStatus").className = "status unhealthy";
  }
}

loadData();
setInterval(loadData, 5000);