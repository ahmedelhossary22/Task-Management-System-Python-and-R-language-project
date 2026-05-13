from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User
from app.schemas.user import UserResponse
from app.dependencies.auth import get_current_user
from app.schemas.user import UserCreate
from app.core.security import hash_password
from app.schemas.user import UserUpdate
from app.core.security import hash_password
from app.core.logging_config import logger
from app.core.redis_client import redis_client
import json
router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/", response_model=list[UserResponse])
def get_users(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    logger.debug(f"User {current_user.id} requesting all users")

    if current_user.role != "admin":
        logger.warning(f"Unauthorized users list access by user {current_user.id}")
        raise HTTPException(status_code=403, detail="Not allowed")

    cache_key = "users:all"

    # ✅ SAFE CACHE READ
    cached = None
    if redis_client:
        try:
            cached = redis_client.get(cache_key)
        except Exception:
            cached = None

    if cached:
        logger.info("Returning users from cache")
        return json.loads(cached)

    # 🔥 DB
    users = db.query(User).all()

    logger.info(f"Admin {current_user.id} fetched {len(users)} users from DB")

    # 🔥 SERIALIZE
    data = [
        {
            "id": u.id,
            "username": u.username,
            "email": u.email,
            "role": u.role
        }
        for u in users
    ]

    # ✅ SAFE CACHE WRITE
    if redis_client:
        try:
            redis_client.set(cache_key, json.dumps(data), ex=60)
            logger.info("Users cached")
        except Exception:
            pass

    return users

@router.get("/{user_id}", response_model=UserResponse)
def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    logger.debug(f"User {current_user.id} requesting user {user_id}")

    if current_user.role != "admin":
        logger.warning(f"Unauthorized user access attempt by user {current_user.id}")
        raise HTTPException(status_code=403, detail="Not allowed")

    cache_key = f"user:{user_id}"

    # ✅ CACHE READ
    cached = None
    if redis_client:
        try:
            cached = redis_client.get(cache_key)
        except Exception:
            cached = None

    if cached:
        logger.info(f"Returning user {user_id} from cache")
        return json.loads(cached)

    # 🔥 DB
    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        logger.error(f"User {user_id} not found")
        raise HTTPException(status_code=404, detail="User not found")

    logger.info(f"Admin {current_user.id} fetched user {user_id} from DB")

    # 🔥 SERIALIZE
    data = {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "role": user.role
    }

    # ✅ CACHE WRITE
    if redis_client:
        try:
            redis_client.set(cache_key, json.dumps(data), ex=60)
            logger.info(f"User {user_id} cached")
        except Exception:
            pass

    return user
    
@router.post("/", response_model=UserResponse)
def create_user(
    user: UserCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    logger.debug(f"Create user request by user {current_user.id} with data: {user.dict()}")

    if current_user.role != "admin":
        logger.warning(f"Unauthorized user creation attempt by user {current_user.id}")
        raise HTTPException(status_code=403, detail="Not allowed")

    # ✅ Duplicate checks
    if db.query(User).filter(User.username == user.username).first():
        raise HTTPException(status_code=400, detail="Username already exists")

    if db.query(User).filter(User.email == user.email).first():
        raise HTTPException(status_code=400, detail="Email already exists")

    logger.info(f"Admin {current_user.id} creating user")

    new_user = User(
        username=user.username,
        email=user.email,
        password=hash_password(user.password),
        role=user.role.lower()
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    logger.info(f"User {new_user.id} created successfully")

    # 🔥 CACHE INVALIDATION
    if redis_client:
        try:
            redis_client.delete("users:all")
            logger.info("Users cache invalidated after creation")
        except Exception:
            pass

    return new_user
@router.put("/{user_id}", response_model=UserResponse)
def update_user(
    user_id: int,
    user_data: UserUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    logger.debug(f"Update request for user {user_id} with data: {user_data.dict()}")

    if current_user.role != "admin":
        logger.warning(f"Unauthorized user update attempt by user {current_user.id}")
        raise HTTPException(status_code=403, detail="Not allowed")

    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        logger.error(f"User {user_id} not found")
        raise HTTPException(status_code=404, detail="User not found")

    logger.info(f"Admin {current_user.id} updating user {user_id}")

    if user_data.username is not None:
        user.username = user_data.username

    if user_data.email is not None:
        user.email = user_data.email

    if user_data.password is not None:
        user.password = hash_password(user_data.password)

    if user_data.role is not None:
        user.role = user_data.role.lower()

    db.commit()
    db.refresh(user)

    logger.info(f"User {user_id} updated successfully")

    # 🔥 CACHE INVALIDATION
    if redis_client:
        try:
            redis_client.delete("users:all")
            redis_client.delete(f"user:{user_id}")
            logger.info(f"Cache invalidated for user {user_id}")
        except Exception:
            pass

    return user

@router.delete("/{user_id}")
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    logger.debug(f"Delete request for user {user_id} by user {current_user.id}")

    if current_user.role != "admin":
        logger.warning(f"Unauthorized user delete attempt by user {current_user.id}")
        raise HTTPException(status_code=403, detail="Not allowed")

    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        logger.error(f"User {user_id} not found")
        raise HTTPException(status_code=404, detail="User not found")

    # prevent deleting the last admin
    if user.role == "admin":
        admin_count = db.query(User).filter(User.role == "admin").count()
        if admin_count <= 1:
            logger.warning(f"Attempt to delete the last admin by user {current_user.id}")
            raise HTTPException(status_code=400, detail="Cannot delete the last admin")

    logger.info(f"Admin {current_user.id} deleting user {user_id}")

    db.delete(user)
    db.commit()

    logger.info(f"User {user_id} deleted successfully")

    # 🔥 CACHE INVALIDATION
    if redis_client:
        try:
            redis_client.delete("users:all")
            redis_client.delete(f"user:{user_id}")
            logger.info(f"Cache invalidated for user {user_id}")
        except Exception:
            pass

    return {"message": "User deleted"}