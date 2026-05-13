from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.project import Project
from app.schemas.project import ProjectCreate, ProjectResponse, ProjectUpdate
from app.dependencies.auth import get_current_user
from app.dependencies.roles import require_role
from app.core.logging_config import logger
from app.core.redis_client import redis_client
import json
router = APIRouter(prefix="/projects", tags=["Projects"])


@router.post("/", response_model=ProjectResponse, status_code=201)
def create_project(
    project: ProjectCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    logger.debug(f"Create project request by user {current_user.id} with data: {project.dict()}")
     
    
    require_role(current_user, ["admin"])

    logger.info(f"Admin {current_user.id} creating project")

    new_project = Project(
        name=project.name,
        description=project.description,
        created_by=current_user.id
    )

    db.add(new_project)
    db.commit()
    db.refresh(new_project)

    logger.info(f"Project {new_project.id} created successfully")

    # 🔥 CACHE INVALIDATION
    if redis_client:
        try:
            redis_client.delete("projects:all")
            logger.info("Projects cache invalidated after creation")
        except Exception:
            pass

    return new_project

@router.get("/", response_model=list[ProjectResponse])
def get_projects(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    logger.debug(f"User {current_user.id} requesting all projects")

    cache_key = "projects:all"

    # ✅ SAFE CACHE READ
    cached = None
    if redis_client:
        try:
            cached = redis_client.get(cache_key)
        except Exception:
            cached = None

    if cached:
        logger.info("Returning projects from cache")
        return json.loads(cached)

    # 🔥 DB QUERY
    projects = db.query(Project).all()

    logger.info(f"User {current_user.id} fetched {len(projects)} projects from DB")

    # 🔥 SERIALIZE
    data = [
        {
            "id": p.id,
            "name": p.name,
            "description": p.description,
            "created_by": p.created_by
        }
        for p in projects
    ]

    # ✅ SAFE CACHE WRITE
    if redis_client:
        try:
            redis_client.set(cache_key, json.dumps(data), ex=60)
            logger.info("Projects cached")
        except Exception:
            pass

    return projects

@router.get("/{project_id}", response_model=ProjectResponse)
def get_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    logger.debug(f"User {current_user.id} requesting project {project_id}")

    cache_key = f"project:{project_id}"

    # ✅ SAFE CACHE READ
    cached = None
    if redis_client:
        try:
            cached = redis_client.get(cache_key)
        except Exception:
            cached = None

    if cached:
        logger.info(f"Returning project {project_id} from cache")
        return json.loads(cached)

    # 🔥 DB QUERY
    project = db.query(Project).filter(Project.id == project_id).first()

    if not project:
        logger.error(f"Project {project_id} not found")
        raise HTTPException(status_code=404, detail="Project not found")

    logger.info(f"User {current_user.id} fetched project {project_id} from DB")

    # 🔥 SERIALIZE
    data = {
        "id": project.id,
        "name": project.name,
        "description": project.description,
        "created_by": project.created_by
    }

    # ✅ SAFE CACHE WRITE
    if redis_client:
        try:
            redis_client.set(cache_key, json.dumps(data), ex=60)
            logger.info(f"Project {project_id} cached")
        except Exception:
            pass

    return project

@router.put("/{project_id}", response_model=ProjectResponse)
def update_project(
    project_id: int,
    project_update: ProjectUpdate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    logger.debug(f"Update request for project {project_id} with data: {project_update.dict()}")

    
    require_role(current_user, ["admin"])

    project = db.query(Project).filter(Project.id == project_id).first()

    if not project:
        logger.error(f"Project {project_id} not found")
        raise HTTPException(status_code=404, detail="Project not found")

    logger.info(f"Admin {current_user.id} updating project {project_id}")

    if project_update.name:
        project.name = project_update.name

    if project_update.description:
        project.description = project_update.description

    db.commit()
    db.refresh(project)

    logger.info(f"Project {project_id} updated successfully")

    # 🔥 CACHE INVALIDATION
    if redis_client:
        try:
            redis_client.delete("projects:all")
            redis_client.delete(f"project:{project_id}")
            logger.info(f"Cache invalidated for project {project_id}")
        except Exception:
            pass

    return project

@router.delete("/{project_id}", status_code=200)
def delete_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    require_role(current_user, ["admin"])

    project = db.query(Project).filter(Project.id == project_id).first()

    if not project:
        logger.error(f"Project {project_id} not found")
        raise HTTPException(status_code=404, detail="Project not found")

    logger.info(f"User {current_user.id} deleting project {project_id}")

    db.delete(project)
    db.commit()

    logger.info(f"Project {project_id} deleted successfully")

    if redis_client:
        try:
            # project cache
            redis_client.delete("projects:all")
            redis_client.delete(f"project:{project_id}")

            # optional but strong: clear related tasks cache
            keys = redis_client.keys("tasks:*")
            if keys:
                redis_client.delete(*keys)

            keys = redis_client.keys("task:*")
            if keys:
                redis_client.delete(*keys)

            logger.info(f"Cache invalidated after deleting project {project_id}")

        except Exception:
            pass

    return {"message": "project deleted"}