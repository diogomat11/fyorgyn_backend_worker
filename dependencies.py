import os
import jwt
from datetime import datetime, timedelta
from fastapi import Depends, HTTPException, status, Header
from sqlalchemy.orm import Session
from database import get_db
from models.shared import User

JWT_SECRET = os.getenv("JWT_SECRET", "fyorgyn_jwt_secret_2025_secure_key")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = int(os.getenv("JWT_EXPIRATION_HOURS", "24"))

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

async def get_current_user(authorization: str = Header(None), db: Session = Depends(get_db)):
    if not authorization:
        raise HTTPException(status_code=401, detail="Token de autenticação ausente.")
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Formato de token inválido. Use 'Bearer <token>'.")
    
    token = authorization.split(" ")[1]
    
    # Tentar JWT primeiro
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_id = int(payload.get("sub"))
        user = db.query(User).filter(User.id == user_id).first()
        if user:
            if user.status != "Ativo":
                raise HTTPException(status_code=403, detail="Usuário inativo.")
            if user.validade and user.validade < datetime.now().date():
                raise HTTPException(status_code=403, detail="Acesso expirado.")
            return user
    except (jwt.PyJWTError, ValueError, TypeError):
        pass
    
    # Fallback: API Key (compatibilidade)
    user = db.query(User).filter(User.api_key == token).first()
    if not user:
        raise HTTPException(status_code=401, detail="Token inválido ou usuário não encontrado.")
    if user.status != "Ativo":
        raise HTTPException(status_code=403, detail="Usuário inativo.")
    if user.validade and user.validade < datetime.now().date():
        raise HTTPException(status_code=403, detail="Chave de acesso vencida.")
    return user

def get_allowed_convenio_ids(db: Session, user: User) -> list:
    from models.shared import UserConvenio
    ucs = db.query(UserConvenio).filter(UserConvenio.user_id == user.id).all()
    return [uc.id_convenio for uc in ucs]
