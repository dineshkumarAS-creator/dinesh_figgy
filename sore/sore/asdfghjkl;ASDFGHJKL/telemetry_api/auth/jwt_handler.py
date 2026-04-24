import os
from datetime import datetime, timedelta, timezone

import jwt
import structlog
from fastapi import HTTPException, status

logger = structlog.get_logger()

JWT_SECRET = os.getenv("JWT_SECRET", "dev-secret-change-in-production")
JWT_ALGORITHM = "HS256"
TOKEN_EXPIRY_HOURS = 24


def create_jwt_token(worker_id: str) -> str:
    """Create a JWT token with embedded worker_id."""
    payload = {
        "worker_id": worker_id,
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + timedelta(hours=TOKEN_EXPIRY_HOURS),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def verify_jwt_token(token: str) -> str:
    """Decode JWT token and extract worker_id. Raises HTTPException on invalid token."""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        worker_id = payload.get("worker_id")
        if not worker_id:
            logger.warning("jwt_invalid_worker_id", token_sample=token[:20])
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token: missing worker_id")
        return worker_id
    except jwt.ExpiredSignatureError:
        logger.warning("jwt_token_expired")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")
    except jwt.InvalidTokenError as exc:
        logger.warning("jwt_decode_failed", error=str(exc))
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")


def extract_bearer_token(auth_header: str) -> str:
    """Extract bearer token from Authorization header."""
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing or invalid Authorization header")
    return auth_header[7:]
