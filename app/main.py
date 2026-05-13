from fastapi import FastAPI
from app.database import Base ,engine
from app.models import User,Project,Task
from app.routes import auth
from fastapi import Depends
from app.dependencies.auth import get_current_user
from app.routes import auth, projects, tasks, users
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi import Request
from fastapi.middleware.cors import CORSMiddleware
from app.core.logging_config import logger
import time
from sqlalchemy.orm import Session
from app.database import get_db
from sqlalchemy import text
from app.core import metrics
from app.dependencies.roles import require_role

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # allow all (for testing)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={
            "message": "Validation Error",
            "details": exc.errors()
        },
    )
Base.metadata.create_all(bind=engine)
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(projects.router)
app.include_router(tasks.router)

@app.get("/")
def root():
    return {"message": "Task Management System API is running successfully"}

@app.get("/me")
def get_me(user = Depends(get_current_user)):
    return user

@app.middleware("http")
async def log_requests(request, call_next):
    import time

    start_time = time.time()
    metrics.increment_request_count()

    try:
        response = await call_next(request)
    except Exception:
        metrics.increment_error_count()
        raise

    process_time = time.time() - start_time
    metrics.add_response_time(process_time)

    logger.info(
        f"{request.method} {request.url.path} "
        f"Status: {response.status_code} "
        f"Time: {process_time:.4f}s"
    )

    log_entry = f"{request.method} {request.url.path} {response.status_code}"
    metrics.add_recent_log(log_entry)

    return response
@app.get("/metrics")
def get_metrics():
    data = metrics.get_metrics()
    avg_response_time = 0
    if data["request_count"] > 0:
        avg_response_time = data["total_response_time"] / data["request_count"]
    return {
        "total_requests": data["request_count"],
        "total_errors": data["error_count"],
        "average_response_time": round(avg_response_time, 4)
    }


@app.get("/health")
def health_check(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))

        return {
            "status": "healthy",
            "database": "connected"
        }

    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")

        return {
            "status": "unhealthy",
            "database": "disconnected"
        }

@app.get("/dashboard")
def dashboard(current_user = Depends(get_current_user)):
    require_role(current_user, ["admin"])  
    
    data = metrics.get_metrics()
    avg_response_time = 0
    error_rate = 0
    if data["request_count"] > 0:
        avg_response_time = data["total_response_time"] / data["request_count"]
        error_rate = data["error_count"] / data["request_count"]
    return {
        "total_requests": data["request_count"],
        "total_errors": data["error_count"],
        "error_rate": round(error_rate, 4),
        "average_response_time": round(avg_response_time, 4),
        "recent_logs": data["recent_logs"],
        "status": "running"
    }
@app.get("/redis-test")
def test_redis():
    from app.core.redis_client import redis_client

    redis_client.set("test", "hello")
    return {"value": redis_client.get("test")}    

@app.get("/cache-benchmark")
def cache_benchmark(db: Session = Depends(get_db)):
    from app.core.redis_client import redis_client
    from app.models import Project
    import time
    import json

    # --- DB query ---
    start = time.time()
    projects = db.query(Project).all()
    db_time = time.time() - start

    # --- Write to cache ---
    data = [{"id": p.id, "name": p.name, "description": p.description, "created_by": p.created_by} for p in projects]
    if redis_client:
        redis_client.set("benchmark:projects", json.dumps(data), ex=30)

    # --- Cache query ---
    start = time.time()
    if redis_client:
        redis_client.get("benchmark:projects")
    cache_time = time.time() - start

    return {
        "db_query_time_seconds": round(db_time, 6),
        "cache_query_time_seconds": round(cache_time, 6),
        "improvement": f"{round((db_time - cache_time) / db_time * 100, 2)}% faster" if db_time > 0 else "N/A"
    }
@app.middleware("http")
async def log_requests(request, call_next):
    import time

    start_time = time.time()
    metrics.increment_request_count()

    response = await call_next(request)

    process_time = time.time() - start_time
    metrics.add_response_time(process_time)

    # ✅ NOW counts any 5xx response as an error
    if response.status_code >= 500:
        metrics.increment_error_count()

    logger.info(
        f"{request.method} {request.url.path} "
        f"Status: {response.status_code} "
        f"Time: {process_time:.4f}s"
    )

    log_entry = f"{request.method} {request.url.path} {response.status_code}"
    metrics.add_recent_log(log_entry)

    return response

from fastapi import HTTPException

@app.get("/test-error")
async def test_error():
    raise HTTPException(
        status_code=500,
        detail="Test error for metrics"
    )


## to run the server  uvicorn app.main:app --reload