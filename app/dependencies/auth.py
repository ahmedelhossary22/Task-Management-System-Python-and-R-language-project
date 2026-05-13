from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from app.database import get_db
from app.core.security import decode_access_token
from app.core.logging_config import logger
from app.models.user import User

security = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    token = credentials.credentials

    payload = decode_access_token(token)

    if payload is None or "user_id" not in payload:
        logger.warning("Token validation failed: invalid or expired token")
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    user = db.query(User).filter(User.id == payload["user_id"]).first()

    if user is None:
        logger.warning(f"Token validation failed: user_id {payload['user_id']} not found in DB")
        raise HTTPException(status_code=401, detail="User not found")

    logger.info(f"Token validated successfully for user {user.id} ({user.username}) — role: {user.role}")

    return user
