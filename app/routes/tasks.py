from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.task import Task
from app.schemas.task import TaskCreate, TaskResponse, TaskUpdate
from app.dependencies.auth import get_current_user
from app.dependencies.roles import require_role
from app.models import Project
from app.models import Task, Project, User
from fastapi import HTTPException
from app.core.logging_config import logger
from app.core.redis_client import redis_client
import json
router = APIRouter(prefix="/tasks", tags=["Tasks"])


@router.post("/", response_model=TaskResponse)
def create_task(
    task: TaskCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    
    logger.debug(f"Create task request by user {current_user.id} with data: {task.dict()}")

    project = db.query(Project).filter(Project.id == task.project_id).first()
    
    if current_user.role not in ["admin", "manager"]:
      logger.warning(f"Unauthorized task creation attempt by user {current_user.id}")
      raise HTTPException(status_code=403, detail="Not allowed")
    
    if not project:
        logger.error(f"Project {task.project_id} not found for task creation")
        raise HTTPException(status_code=400, detail="Project not found")

    user = db.query(User).filter(User.id == task.assigned_to).first()
    if not user:
        logger.error(f"Assigned user {task.assigned_to} not found")
        raise HTTPException(status_code=400, detail="User not found")

    logger.info(f"User {current_user.id} creating task for project {task.project_id}")

    new_task = Task(
        title=task.title,
        description=task.description,
        priority=task.priority,
        project_id=task.project_id,
        assigned_to=task.assigned_to
    )

    db.add(new_task)
    db.commit()
    db.refresh(new_task)

    logger.info(f"Task {new_task.id} created successfully")

    # 🔥 CACHE INVALIDATION
    if redis_client:
        try:
            # delete all tasks cache
            keys = redis_client.keys("tasks:*")
            if keys:
                redis_client.delete(*keys)

            logger.info("Tasks cache invalidated after creation")

        except Exception:
            pass

    return new_task


@router.put("/{task_id}", response_model=TaskResponse)
def update_task(
    task_id: int,
    task_update: TaskUpdate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    logger.debug(f"Update request for task {task_id} with data: {task_update.dict()}")

    task = db.query(Task).filter(Task.id == task_id).first()

    if not task:
        logger.error(f"Task {task_id} not found")
        raise HTTPException(status_code=404, detail="Task not found")

    if current_user.role not in ["admin", "manager"] and task.assigned_to != current_user.id:
        logger.warning(f"Unauthorized update attempt by user {current_user.id}")
        raise HTTPException(status_code=403, detail="Not allowed")

    logger.info(f"User {current_user.id} updating task {task_id}")

    valid_transitions = {
        "To Do": ["In Progress"],
        "In Progress": ["Done"],
        "Done": []
    }

    if task_update.status is not None:
        if task.status not in valid_transitions:
            logger.critical(f"Invalid task status detected in DB: {task.status}")
            raise HTTPException(status_code=400, detail="Invalid current task status")

        allowed = valid_transitions[task.status]
        if task_update.status not in allowed:
            logger.warning(
                f"Invalid transition from {task.status} to {task_update.status} for task {task_id}"
            )
            raise HTTPException(
                status_code=400,
                detail=f"Cannot transition from '{task.status}' to '{task_update.status}'"
            )
        task.status = task_update.status

    if task_update.title is not None:
        task.title = task_update.title

    if task_update.description is not None:
        task.description = task_update.description

    if task_update.priority is not None:
        task.priority = task_update.priority

    db.commit()
    db.refresh(task)

    logger.info(f"Task {task_id} updated successfully")

    # 🔥 CACHE INVALIDATION
    if redis_client:
        try:
            # delete all tasks list cache
            keys = redis_client.keys("tasks:*")
            if keys:
                redis_client.delete(*keys)

            # delete this specific task cache
            keys = redis_client.keys(f"task:{task_id}:*")
            if keys:
                redis_client.delete(*keys)

            logger.info(f"Cache invalidated for task {task_id}")

        except Exception:
            pass

    return task

@router.get("/", response_model=list[TaskResponse])
def get_tasks(
    status: str = Query(None),
    priority: str = Query(None),
    assigned_to: int = Query(None),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    # 🔥 DEBUG
    logger.debug(
        f"User {current_user.id} fetching tasks "
        f"filters: status={status}, priority={priority}, assigned_to={assigned_to}"
    )

    # 🔥 UNIQUE CACHE KEY
    cache_key = f"tasks:{status}:{priority}:{assigned_to}:{current_user.role}:{current_user.id}"

    # ✅ SAFE CACHE READ
    cached_tasks = None
    if redis_client:
        try:
            cached_tasks = redis_client.get(cache_key)
        except Exception:
            cached_tasks = None

    if cached_tasks:
        logger.info("Returning tasks from cache")
        return json.loads(cached_tasks)

    # 🔥 DB QUERY
    query = db.query(Task)

    if current_user.role == "employee":
        query = query.filter(Task.assigned_to == current_user.id)

    if status:
        query = query.filter(Task.status == status)

    if priority:
        query = query.filter(Task.priority == priority)

    if assigned_to:
        if current_user.role == "employee" and assigned_to != current_user.id:
            logger.warning(
                f"Unauthorized filter attempt by user {current_user.id}"
            )
            raise HTTPException(status_code=403, detail="Not allowed")

        query = query.filter(Task.assigned_to == assigned_to)

    # 🔥 GET FROM DB
    tasks = query.all()

    logger.info(f"User {current_user.id} fetched {len(tasks)} tasks from DB")

    # 🔥 SERIALIZE
    tasks_data = [
        {
            "id": t.id,
            "title": t.title,
            "description": t.description,
            "status": t.status,
            "priority": t.priority,
            "project_id": t.project_id,
            "assigned_to": t.assigned_to
        }
        for t in tasks
    ]

    # ✅ SAFE CACHE WRITE
    if redis_client:
        try:
            redis_client.set(cache_key, json.dumps(tasks_data), ex=60)
            logger.info("Tasks cached")
        except Exception:
            pass

    return tasks
    
@router.get("/{task_id}", response_model=TaskResponse)
def get_task_by_id(
    task_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    logger.debug(f"User {current_user.id} requesting task {task_id}")

    # 🔥 UNIQUE CACHE KEY
    cache_key = f"task:{task_id}:{current_user.role}:{current_user.id}"

    # ✅ SAFE CACHE READ
    cached_task = None
    if redis_client:
        try:
            cached_task = redis_client.get(cache_key)
        except Exception:
            cached_task = None

    if cached_task:
        logger.info("Returning task from cache")
        return json.loads(cached_task)

    # 🔥 GET FROM DB
    task = db.query(Task).filter(Task.id == task_id).first()

    if not task:
        logger.error(f"Task {task_id} not found")
        raise HTTPException(status_code=404, detail="Task not found")

    # 🔐 Authorization check
    if current_user.role == "employee" and task.assigned_to != current_user.id:
        logger.warning(
            f"Unauthorized access attempt by user {current_user.id} to task {task_id}"
        )
        raise HTTPException(status_code=403, detail="Not allowed")

    logger.info(f"User {current_user.id} fetched task {task_id} from DB")

    # 🔥 SERIALIZE
    task_data = {
        "id": task.id,
        "title": task.title,
        "description": task.description,
        "status": task.status,
        "priority": task.priority,
        "project_id": task.project_id,
        "assigned_to": task.assigned_to
    }

    # ✅ SAFE CACHE WRITE
    if redis_client:
        try:
            redis_client.set(cache_key, json.dumps(task_data), ex=60)
            logger.info("Task cached")
        except Exception:
            pass

    return task

@router.delete("/{task_id}", status_code=200)
def delete_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    logger.debug(f"Delete request for task {task_id} by user {current_user.id}")

    # 🔐 Only admin can delete
    if current_user.role != "admin":
        logger.warning(f"Unauthorized delete attempt by user {current_user.id}")
        raise HTTPException(status_code=403, detail="Not allowed")

    task = db.query(Task).filter(Task.id == task_id).first()

    if not task:
        logger.error(f"Task {task_id} not found")
        raise HTTPException(status_code=404, detail="Task not found")

    logger.info(f"Admin {current_user.id} deleting task {task_id}")

    db.delete(task)
    db.commit()

    logger.info(f"Task {task_id} deleted successfully")

    # 🔥 CACHE INVALIDATION (SAFE)
    if redis_client:
        try:
            # delete list cache
            keys = redis_client.keys("tasks:*")
            if keys:
                redis_client.delete(*keys)

            # delete this task cache
            keys = redis_client.keys(f"task:{task_id}:*")
            if keys:
                redis_client.delete(*keys)

            logger.info(f"Cache invalidated for task {task_id}")

        except Exception:
            logger.warning("Redis error during cache invalidation")

    return {"message": "task deleted"}