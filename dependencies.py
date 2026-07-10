import os
import jwt
from datetime import datetime, timedelta
from fastapi import Depends, HTTPException, Header
from pydantic import BaseModel

JWT_SECRET = os.getenv("JWT_SECRET", "fyorgyn_jwt_secret_2025_secure_key")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = int(os.getenv("JWT_EXPIRATION_HOURS", "24"))

class CurrentUser(BaseModel):
    id: int
    username: str
    is_admin: bool = False
    status: str = "Ativo"

def create_access_token(user_id: int, extra_data: dict = None) -> str:
    payload = {
        "sub": str(user_id),
        "exp": datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS),
        "iat": datetime.utcnow(),
    }
    if extra_data:
        payload.update(extra_data)
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

def verify_token(token: str) -> dict:
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expirado.")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Token inválido.")

async def get_current_user(authorization: str = Header(None)) -> CurrentUser:
    if not authorization:
        raise HTTPException(status_code=401, detail="Token de autenticação ausente.")
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Formato de token inválido. Use 'Bearer <token>'.")
    
    token = authorization.split(" ")[1]
    
    # Check static BPO key first for standalone deployment
    bpo_key = os.getenv("BPO_API_KEY", "bpo_secret_api_key_2026")
    if token == bpo_key:
        return CurrentUser(id=1, username="bpo_client", is_admin=True)
    
    # Tentar JWT
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_id = int(payload.get("sub"))
        username = payload.get("username", f"user_{user_id}")
        is_admin = payload.get("is_admin", False)
        return CurrentUser(id=user_id, username=username, is_admin=is_admin)
    except (jwt.PyJWTError, ValueError, TypeError):
        pass
    
    raise HTTPException(status_code=401, detail="Token inválido ou expirado.")

def get_allowed_convenio_ids(user: CurrentUser) -> list:
    return []


