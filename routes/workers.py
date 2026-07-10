import os
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from dependencies import get_current_user, CurrentUser
from models.worker import Worker, WorkerServer

router = APIRouter()

# --- Pydantic Schemas ---
class WorkerResponse(BaseModel):
    id: int
    hostname: str
    status: str
    last_heartbeat: datetime
    current_job_id: Optional[int]
    command: Optional[str]
    meta: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class WorkerServerResponse(BaseModel):
    id: int
    worker_id: int
    user_id: int
    server_url: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# --- Endpoints ---

@router.get("/api/v1/workers", response_model=List[WorkerResponse])
async def list_workers(db: Session = Depends(get_db), current_user: CurrentUser = Depends(get_current_user)):
    # Admin only
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Apenas administradores podem listar workers."
        )
    workers = db.query(Worker).order_by(Worker.last_heartbeat.desc()).all()
    return workers

@router.post("/api/v1/workers/{worker_id}/restart")
async def restart_worker(
    worker_id: int,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user)
):
    # If not admin, verify if user has a server linked to this worker
    if not current_user.is_admin:
        linked_server = db.query(WorkerServer).filter(
            WorkerServer.worker_id == worker_id,
            WorkerServer.user_id == current_user.id
        ).first()
        if not linked_server:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Acesso negado. Você não gerencia este worker."
            )
            
    worker = db.query(Worker).filter(Worker.id == worker_id).first()
    if not worker:
        raise HTTPException(status_code=404, detail="Worker não encontrado.")
        
    worker.command = "restart"
    worker.updated_at = datetime.now(timezone.utc)
    db.commit()
    return {"message": f"Comando de reinicialização enviado para o worker {worker.hostname}.", "worker_id": worker_id}

@router.get("/api/v1/workers/servers", response_model=List[WorkerServerResponse])
async def list_worker_servers(
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user)
):
    query = db.query(WorkerServer)
    if not current_user.is_admin:
        query = query.filter(WorkerServer.user_id == current_user.id)
        
    servers = query.all()
    return servers
