from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from database import get_db
from dependencies import get_current_user, CurrentUser
from models.worker import WorkerIntegrador, WorkerIntegradorOperacao

router = APIRouter()


@router.get("/api/v1/integradores/operacoes")
async def list_operacoes_integradores(
    id_integrador: Optional[int] = Query(None, description="Filtrar por integrador (espaço W)"),
    apenas_ativas: bool = Query(False, description="Somente operações ativas"),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user)
):
    """Espelha o catálogo de operações por integrador (worker.integrador_operacoes),
    incluindo a coluna operacao_canonica (migration 0103). Uso: diagnóstico e
    verificação de capabilities entre Hub ↔ backend_worker."""
    query = db.query(WorkerIntegradorOperacao)
    if id_integrador:
        query = query.filter(WorkerIntegradorOperacao.id_integrador == id_integrador)
    if apenas_ativas:
        query = query.filter(WorkerIntegradorOperacao.ativo == True)  # noqa: E712
    ops = query.order_by(
        WorkerIntegradorOperacao.id_integrador.asc(),
        WorkerIntegradorOperacao.rotina.asc()
    ).all()

    integradores = {
        i.id_integrador: i
        for i in db.query(WorkerIntegrador).all()
    }

    return [
        {
            "id": op.id,
            "id_integrador": op.id_integrador,
            "nome_integrador": integradores[op.id_integrador].nome if op.id_integrador in integradores else None,
            "sigla_integrador": integradores[op.id_integrador].sigla if op.id_integrador in integradores else None,
            "tipo_operacao": integradores[op.id_integrador].tipo_operacao if op.id_integrador in integradores else None,
            "rotina": op.rotina,
            "operacao_canonica": op.operacao_canonica,
            "descricao": op.descricao,
            "tipo_processamento": op.tipo_processamento,
            "modo_execucao": getattr(op, "modo_execucao", "automatico"),
            "ativo": op.ativo,
        }
        for op in ops
    ]
