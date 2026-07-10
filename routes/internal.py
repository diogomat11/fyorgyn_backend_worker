import os
import requests
import logging
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, Header, HTTPException, status, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

def send_webhook_task(webhook_url: str, payload: dict):
    try:
        headers = {"Content-Type": "application/json"}
        # Add BPO authorization header if client provided a token in params
        auth_token = (payload.get("params") or {}).get("bpo_webhook_token")
        if auth_token:
            headers["Authorization"] = f"Bearer {auth_token}"
            
        response = requests.post(webhook_url, json=payload, headers=headers, timeout=20)
        if response.status_code in [200, 201, 204]:
            logger.info(f"Webhook successfully delivered to {webhook_url} for job {payload.get('job_id')}")
        else:
            logger.warning(f"Webhook to {webhook_url} returned status code {response.status_code} for job {payload.get('job_id')}")
    except Exception as e:
        logger.error(f"Failed to deliver webhook to {webhook_url} for job {payload.get('job_id')}: {e}")

from database import get_db
from models.worker import Job, Log, Worker, JobExecution

router = APIRouter()

INTERNAL_TOKEN = os.getenv("API_TOKEN", "webscraping_api_token_2025")

def verify_internal_token(x_api_token: str = Header(None)):
    if x_api_token != INTERNAL_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Token interno inválido."
        )

# --- Pydantic Schemas ---
class HeartbeatRequest(BaseModel):
    hostname: str
    status: str
    current_job_id: Optional[int] = None
    meta: Optional[str] = None

class JobCompleteRequest(BaseModel):
    result_data: dict
    items_found: int = 0
    duration_seconds: Optional[int] = None
    meta: Optional[dict] = None

class JobFailRequest(BaseModel):
    error_message: str
    error_category: Optional[str] = None
    duration_seconds: Optional[int] = None
    meta: Optional[dict] = None

# --- Endpoints ---

@router.post("/internal/heartbeat", dependencies=[Depends(verify_internal_token)])
async def worker_heartbeat(
    heartbeat: HeartbeatRequest,
    db: Session = Depends(get_db)
):
    hostname = heartbeat.hostname.title() if heartbeat.hostname else "Unknown"
    worker = db.query(Worker).filter(Worker.hostname.ilike(hostname)).first()
    if not worker:
        worker = Worker(hostname=hostname)
        db.add(worker)
        
    worker.status = heartbeat.status
    worker.current_job_id = heartbeat.current_job_id
    worker.meta = heartbeat.meta
    worker.last_heartbeat = datetime.now(timezone.utc)
    worker.updated_at = datetime.now(timezone.utc)
    
    db.commit()
    db.refresh(worker)
    
    # Check if there is a pending command for this worker
    command = worker.command
    if command:
        # Clear command once it is read
        worker.command = None
        db.commit()
        
    return {"command": command}

@router.post("/internal/jobs/{job_id}/complete", dependencies=[Depends(verify_internal_token)])
async def complete_job(
    job_id: int,
    req: JobCompleteRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job não encontrado.")
        
    job.status = "success"
    job.result_data = req.result_data
    job.result_consumed = False
    job.locked_by = None
    job.attempts += 1
    job.error_message = None
    job.updated_at = datetime.now(timezone.utc)
    
    # Write Execution log
    execution = JobExecution(
        job_id=job.id,
        id_convenio=job.id_convenio,
        rotina=job.rotina,
        status="success",
        start_time=job.updated_at,  # rough estimate or request provided
        end_time=datetime.now(timezone.utc),
        duration_seconds=req.duration_seconds or 0,
        items_found=req.items_found,
        meta=req.meta or {}
    )
    db.add(execution)
    
    # Write system log
    log = Log(
        job_id=job.id,
        user_id=job.user_id,
        carteirinha_id=job.carteirinha_id,
        level="INFO",
        message=f"Job {job.id} concluído com sucesso. {req.items_found} itens processados."
    )
    db.add(log)
    
    db.commit()
    
    # Dispatch webhook if webhook_url is specified in params
    if job.params and isinstance(job.params, dict):
        webhook_url = job.params.get("webhook_url")
        if webhook_url:
            payload = {
                "job_id": job.id,
                "status": job.status,
                "result_data": job.result_data,
                "error_message": job.error_message,
                "attempts": job.attempts,
                "rotina": job.rotina,
                "id_convenio": job.id_convenio,
                "params": job.params
            }
            background_tasks.add_task(send_webhook_task, webhook_url, payload)
            
    return {"message": f"Job {job_id} marcado como concluído com sucesso."}

@router.post("/internal/jobs/{job_id}/fail", dependencies=[Depends(verify_internal_token)])
async def fail_job(
    job_id: int,
    req: JobFailRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job não encontrado.")
        
    job.attempts = (job.attempts or 0) + 1
    job.error_message = req.error_message
    job.locked_by = None
    job.updated_at = datetime.now(timezone.utc)
    
    if job.attempts >= (job.max_attempts or 3):
        job.status = "error"
        message_prefix = f"Job {job.id} falhou definitivamente"
    else:
        job.status = "pending"
        message_prefix = f"Job {job.id} falhou temporariamente"
        
    # Write Execution log
    execution = JobExecution(
        job_id=job.id,
        id_convenio=job.id_convenio,
        rotina=job.rotina,
        status="error",
        start_time=job.updated_at,
        end_time=datetime.now(timezone.utc),
        duration_seconds=req.duration_seconds or 0,
        error_category=req.error_category or "unknown",
        error_message=req.error_message,
        meta=req.meta or {}
    )
    db.add(execution)
    
    # Write system log
    log = Log(
        job_id=job.id,
        user_id=job.user_id,
        carteirinha_id=job.carteirinha_id,
        level="ERROR",
        message=f"{message_prefix} (tentativa {job.attempts}/{job.max_attempts}): {req.error_message}"
    )
    db.add(log)
    
    db.commit()
    
    # Dispatch webhook if webhook_url is specified in params
    if job.params and isinstance(job.params, dict):
        webhook_url = job.params.get("webhook_url")
        if webhook_url:
            payload = {
                "job_id": job.id,
                "status": job.status,
                "result_data": job.result_data,
                "error_message": job.error_message,
                "attempts": job.attempts,
                "rotina": job.rotina,
                "id_convenio": job.id_convenio,
                "params": job.params
            }
            background_tasks.add_task(send_webhook_task, webhook_url, payload)
            
    return {
        "message": f"Falha registrada no Job {job_id}.",
        "attempts": job.attempts,
        "max_attempts": job.max_attempts,
        "new_status": job.status
    }
