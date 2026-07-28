import os
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import func

from database import get_db
from dependencies import get_current_user, CurrentUser
from models.worker import Job, Log

router = APIRouter()

# --- Pydantic Schemas ---
class JobCreate(BaseModel):
    # Campos de rastreamento (opcionais) usados pelo Hub Backend para correlacionar
    # o resultado do webhook. O Worker NÃO consulta esses IDs em nenhuma tabela.
    carteirinha_id: Optional[int] = None  # ID da carteirinha no Hub (apenas rastreamento)
    id_convenio: Optional[int] = None     # ID do convênio no Hub (apenas rastreamento)
    user_id: Optional[int] = None         # ID do usuário no Hub (opcional)
    rotina: str
    priority: int = 0
    max_attempts: int = 3
    # params é OBRIGATÓRIO e deve conter TODOS os dados operacionais que o Worker precisa:
    #   - carteirinha: número do cartão (string)
    #   - login, senha_criptografada: credenciais do portal
    #   - cod_prestador: código do prestador no convênio
    #   - e todos os demais dados específicos de cada rotina
    # O Worker é 100% stateless e não consulta nenhuma tabela do schema public.
    params: dict  # obrigatório — não pode ser None

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
def _create_job_db(db: Session, job_in: JobCreate, fallback_user_id: int) -> Job:
    if not job_in.params:
        raise HTTPException(
            status_code=400,
            detail="O campo 'params' é obrigatório e não pode estar vazio. "
                   "Inclua todos os dados operacionais necessários ao Worker (carteirinha, login, senha_criptografada, etc.)."
        )
    p_dict = dict(job_in.params)

    effective_user_id = job_in.user_id if job_in.user_id is not None else fallback_user_id

    db_job = Job(
        user_id=effective_user_id,
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
async def create_job(job_in: JobCreate, db: Session = Depends(get_db), current_user: CurrentUser = Depends(get_current_user)):
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
async def create_jobs_batch(batch_in: JobBatchCreate, db: Session = Depends(get_db), current_user: CurrentUser = Depends(get_current_user)):
    if not batch_in.jobs:
        raise HTTPException(status_code=400, detail="A lista de jobs não pode estar vazia.")
    
    db_jobs = []
    for job_in in batch_in.jobs:
        db_job = _create_job_db(db, job_in, current_user.id)
        db_jobs.append(db_job)
    
    # Flush to generate job IDs in the database
    db.flush()
    
    # Logs
    for db_job in db_jobs:
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
    status: Optional[str] = Query(None, description="Filtrar por status"),
    rotina: Optional[str] = Query(None, description="Filtrar por rotina"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user)
):
    query = db.query(Job)
    
    # Tenant filter (Admins can see everything)
    if not current_user.is_admin:
        query = query.filter(Job.user_id == current_user.id)
    
    # Optional filters
    if status:
        query = query.filter(Job.status == status)
    if rotina:
        query = query.filter(Job.rotina == rotina)
        
    # Order by priority (desc) and created_at (desc)
    query = query.order_by(Job.priority.desc(), Job.created_at.desc())
    
    # Pagination
    jobs = query.offset(offset).limit(limit).all()
    return jobs

@router.get("/api/v1/jobs/stats", response_model=JobStats)
async def get_job_stats(db: Session = Depends(get_db), current_user: CurrentUser = Depends(get_current_user)):
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
async def get_pending_results(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user)
):
    query = db.query(Job).filter(Job.status == "success", Job.result_consumed == False)
    
    if not current_user.is_admin:
        query = query.filter(Job.user_id == current_user.id)
        
    query = query.order_by(Job.updated_at.desc())
    
    offset = (page - 1) * per_page
    return query.offset(offset).limit(per_page).all()

@router.get("/api/v1/jobs/{job_id}", response_model=JobResponse)
async def get_job(job_id: int, db: Session = Depends(get_db), current_user: CurrentUser = Depends(get_current_user)):
    query = db.query(Job).filter(Job.id == job_id)
    if not current_user.is_admin:
        query = query.filter(Job.user_id == current_user.id)
        
    job = query.first()
    if not job:
        raise HTTPException(status_code=404, detail="Job não encontrado.")
    return job

@router.get("/api/v1/jobs/{job_id}/result")
async def get_job_result(job_id: int, db: Session = Depends(get_db), current_user: CurrentUser = Depends(get_current_user)):
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
async def consume_job_result(job_id: int, db: Session = Depends(get_db), current_user: CurrentUser = Depends(get_current_user)):
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

@router.post("/api/v1/jobs/{job_id}/retry", response_model=JobResponse)
async def retry_job(job_id: int, db: Session = Depends(get_db), current_user: CurrentUser = Depends(get_current_user)):
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

@router.delete("/api/v1/jobs/{job_id}", response_model=dict)
async def cancel_job(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user)
):
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
