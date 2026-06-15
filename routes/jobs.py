import os
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import func

from database import get_db
from dependencies import get_current_user
from models.shared import User
from models.worker import Job, Log

router = APIRouter()

# --- Pydantic Schemas ---
class JobCreate(BaseModel):
    carteirinha_id: Optional[int] = None
    id_convenio: Optional[int] = None
    rotina: str
    priority: int = 0
    params: Optional[dict] = None
    max_attempts: int = 3

class JobBatchCreate(BaseModel):
    jobs: List[JobCreate]

class JobResponse(BaseModel):
    id: int
    user_id: Optional[int]
    carteirinha_id: Optional[int]
    id_convenio: Optional[int]
    rotina: str
    params: Optional[dict]
    result_data: Optional[dict]
    result_consumed: bool
    status: str
    attempts: int
    max_attempts: int
    priority: int
    depending_id: Optional[int]
    locked_by: Optional[str]
    error_message: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class JobStats(BaseModel):
    pending: int
    processing: int
    success: int
    error: int

# --- Helper to create a single job ---
def _create_job_db(db: Session, job_in: JobCreate, user_id: int) -> Job:
    from models.shared import Carteirinha, Convenio, UserConvenio

    # Initialize parameters
    p_dict = dict(job_in.params) if job_in.params else {}

    # 1. Fetch patient and convenio details
    target_conv_id = job_in.id_convenio
    if job_in.carteirinha_id:
        cart = db.query(Carteirinha).filter(Carteirinha.id == job_in.carteirinha_id).first()
        if cart:
            p_dict["Paciente"] = p_dict.get("Paciente") or cart.paciente or ""
            p_dict["Carteira"] = p_dict.get("Carteira") or cart.carteirinha or ""
            p_dict["TarjaMagnetica"] = p_dict.get("TarjaMagnetica") or getattr(cart, "tarja_magnetica", "") or ""
            if not target_conv_id:
                target_conv_id = cart.id_convenio

            conv = db.query(Convenio).filter(Convenio.id_convenio == cart.id_convenio).first()
            if conv:
                p_dict["convenio"] = p_dict.get("convenio") or conv.nome or ""

    # 2. Fetch user credentials for the convenio and inject into params
    if target_conv_id:
        uconv = db.query(UserConvenio).filter(
            UserConvenio.user_id == user_id,
            UserConvenio.id_convenio == target_conv_id
        ).first()
        if uconv:
            p_dict["login"] = p_dict.get("login") or uconv.login
            p_dict["senha_criptografada"] = p_dict.get("senha_criptografada") or uconv.senha_criptografada
            p_dict["cod_prestador"] = p_dict.get("cod_prestador") or uconv.cod_prestador
            p_dict["login_fat"] = p_dict.get("login_fat") or uconv.login_fat
            p_dict["senha_fat_criptografada"] = p_dict.get("senha_fat_criptografada") or uconv.senha_fat_criptografada

    # 3. Set strict_session_affinity (default True for Bradesco OP1 to avoid login conflicts)
    is_bradesco_op1 = False
    if target_conv_id == 1:
        if job_in.rotina in ['1', 'op1_consulta', 'op1_fature', 'op0_login']:
            is_bradesco_op1 = True
    
    p_dict["strict_session_affinity"] = p_dict.get("strict_session_affinity", is_bradesco_op1)

    db_job = Job(
        user_id=user_id,
        carteirinha_id=job_in.carteirinha_id,
        id_convenio=job_in.id_convenio,
        rotina=job_in.rotina,
        priority=job_in.priority,
        params=p_dict,
        status="pending",
        attempts=0,
        max_attempts=job_in.max_attempts,
        result_consumed=False
    )
    db.add(db_job)
    return db_job

# --- Endpoints ---

@router.post("/api/v1/jobs", response_model=JobResponse, status_code=status.HTTP_201_CREATED)
async def create_job(job_in: JobCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    db_job = _create_job_db(db, job_in, current_user.id)
    db.commit()
    db.refresh(db_job)
    
    # Log creation
    log = Log(
        job_id=db_job.id,
        user_id=current_user.id,
        carteirinha_id=db_job.carteirinha_id,
        level="INFO",
        message=f"Job {db_job.id} criado via API para rotina {db_job.rotina}."
    )
    db.add(log)
    db.commit()
    
    return db_job

@router.post("/api/v1/jobs/batch", response_model=List[JobResponse], status_code=status.HTTP_201_CREATED)
async def create_jobs_batch(batch: JobBatchCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if not batch.jobs:
        raise HTTPException(status_code=400, detail="A lista de jobs não pode estar vazia.")
    
    db_jobs = []
    for job_in in batch.jobs:
        db_job = _create_job_db(db, job_in, current_user.id)
        db_jobs.append(db_job)
    
    db.commit()
    
    # Logs and refresh
    for db_job in db_jobs:
        db.refresh(db_job)
        log = Log(
            job_id=db_job.id,
            user_id=current_user.id,
            carteirinha_id=db_job.carteirinha_id,
            level="INFO",
            message=f"Job {db_job.id} criado em lote via API para rotina {db_job.rotina}."
        )
        db.add(log)
    
    db.commit()
    return db_jobs

@router.get("/api/v1/jobs", response_model=List[JobResponse])
async def list_jobs(
    status: Optional[str] = None,
    id_convenio: Optional[int] = None,
    rotina: Optional[str] = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(Job)
    
    # Tenant filter (Admins can see everything)
    if not current_user.is_admin:
        query = query.filter(Job.user_id == current_user.id)
    
    # Optional filters
    if status:
        query = query.filter(Job.status == status)
    if id_convenio:
        query = query.filter(Job.id_convenio == id_convenio)
    if rotina:
        query = query.filter(Job.rotina == rotina)
        
    # Order by priority (desc) and created_at (desc)
    query = query.order_by(Job.priority.desc(), Job.created_at.desc())
    
    # Pagination
    offset = (page - 1) * per_page
    jobs = query.offset(offset).limit(per_page).all()
    return jobs

@router.get("/api/v1/jobs/stats", response_model=JobStats)
async def get_job_stats(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    query = db.query(Job.status, func.count(Job.id))
    
    if not current_user.is_admin:
        query = query.filter(Job.user_id == current_user.id)
        
    stats_raw = query.group_by(Job.status).all()
    stats_dict = {status_: count for status_, count in stats_raw}
    
    return JobStats(
        pending=stats_dict.get("pending", 0),
        processing=stats_dict.get("processing", 0),
        success=stats_dict.get("success", 0),
        error=stats_dict.get("error", 0)
    )

@router.get("/api/v1/jobs/pending-results", response_model=List[JobResponse])
async def list_pending_results(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(Job).filter(Job.status == "success", Job.result_consumed == False)
    
    if not current_user.is_admin:
        query = query.filter(Job.user_id == current_user.id)
        
    query = query.order_by(Job.updated_at.desc())
    
    offset = (page - 1) * per_page
    return query.offset(offset).limit(per_page).all()

@router.get("/api/v1/jobs/{job_id}", response_model=JobResponse)
async def get_job(job_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    query = db.query(Job).filter(Job.id == job_id)
    if not current_user.is_admin:
        query = query.filter(Job.user_id == current_user.id)
        
    job = query.first()
    if not job:
        raise HTTPException(status_code=404, detail="Job não encontrado.")
    return job

@router.get("/api/v1/jobs/{job_id}/result")
async def get_job_result(job_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    query = db.query(Job.result_data, Job.status, Job.error_message).filter(Job.id == job_id)
    if not current_user.is_admin:
        query = query.filter(Job.user_id == current_user.id)
        
    result = query.first()
    if not result:
        raise HTTPException(status_code=404, detail="Job não encontrado.")
    
    return {
        "job_id": job_id,
        "status": result.status,
        "result_data": result.result_data,
        "error_message": result.error_message
    }

@router.put("/api/v1/jobs/{job_id}/consumed")
async def mark_job_consumed(job_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    query = db.query(Job).filter(Job.id == job_id)
    if not current_user.is_admin:
        query = query.filter(Job.user_id == current_user.id)
        
    job = query.first()
    if not job:
        raise HTTPException(status_code=404, detail="Job não encontrado.")
    
    job.result_consumed = True
    job.updated_at = datetime.now(timezone.utc)
    db.commit()
    return {"message": "Resultado do job marcado como consumido.", "job_id": job.id}

@router.post("/api/v1/jobs/{job_id}/retry")
async def retry_job(job_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    query = db.query(Job).filter(Job.id == job_id)
    if not current_user.is_admin:
        query = query.filter(Job.user_id == current_user.id)
        
    job = query.first()
    if not job:
        raise HTTPException(status_code=404, detail="Job não encontrado.")
        
    if job.status not in ["error", "success"]:
        raise HTTPException(status_code=400, detail="Apenas jobs com erro ou sucesso podem ser reprocessados.")
        
    job.status = "pending"
    job.locked_by = None
    job.result_data = None
    job.result_consumed = False
    job.error_message = None
    job.updated_at = datetime.now(timezone.utc)
    
    # Register retry log
    log = Log(
        job_id=job.id,
        user_id=current_user.id,
        carteirinha_id=job.carteirinha_id,
        level="WARNING",
        message=f"Job {job.id} reenviado para reprocessamento via API."
    )
    db.add(log)
    db.commit()
    
    return {"message": "Job reenviado para processamento.", "job_id": job.id}

@router.delete("/api/v1/jobs/{job_id}")
async def cancel_job(job_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    query = db.query(Job).filter(Job.id == job_id)
    if not current_user.is_admin:
        query = query.filter(Job.user_id == current_user.id)
        
    job = query.first()
    if not job:
        raise HTTPException(status_code=404, detail="Job não encontrado.")
        
    if job.status != "pending":
        raise HTTPException(status_code=400, detail="Somente jobs pendentes podem ser cancelados.")
        
    # Cancel by deleting or setting status to error/cancelled.
    # In webscraper contexts, usually we just delete the pending job or change status to 'cancelled'.
    # Let's delete the record.
    db.delete(job)
    
    # Add a global log entry if we can or just commit
    db.commit()
    return {"message": f"Job {job_id} cancelado e removido com sucesso."}
