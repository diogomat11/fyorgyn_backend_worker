# services/job_service.py
from sqlalchemy.orm import Session
from models.worker import Job, PriorityRule

def resolve_job_priority(db: Session, id_convenio: int, rotina: str, requested_priority: int) -> int:
    """
    Resolve a prioridade do job com base nas regras cadastradas ou na prioridade solicitada.
    """
    if requested_priority > 0:
        return requested_priority
        
    rule = db.query(PriorityRule).filter(
        PriorityRule.id_convenio == id_convenio,
        PriorityRule.rotina == rotina,
        PriorityRule.is_active == 1
    ).first()
    
    if rule:
        return rule.base_priority
        
    # Default priority if no rule matches
    return 0
