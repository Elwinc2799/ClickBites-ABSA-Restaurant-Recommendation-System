import os
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "super-secret-key")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_DAYS = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
bearer_scheme = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    try:
        return pwd_context.hash(password)
    except Exception:
        # Fallback for passlib 1.7.4 + bcrypt>=4.0 incompatibility
        import bcrypt as _bcrypt
        return _bcrypt.hashpw(password.encode("utf-8"), _bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    # Try passlib first
    try:
        return pwd_context.verify(plain, hashed)
    except Exception:
        pass
    # Fallback: use bcrypt directly (handles $2a$ hashes from pgcrypto,
    # and passlib 1.7.4 + bcrypt>=4.0 __about__ incompatibility)
    try:
        import bcrypt as _bcrypt
        return _bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return False


def create_token(user_id: str) -> str:
    expire = datetime.utcnow() + timedelta(days=ACCESS_TOKEN_EXPIRE_DAYS)
    return jwt.encode({"sub": user_id, "exp": expire}, JWT_SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> Optional[str]:
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[ALGORITHM])
        return payload.get("sub")
    except JWTError:
        return None


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)) -> str:
    if not credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    user_id = decode_token(credentials.credentials)
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    return user_id


def get_optional_user(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)) -> Optional[str]:
    if not credentials:
        return None
    return decode_token(credentials.credentials)
