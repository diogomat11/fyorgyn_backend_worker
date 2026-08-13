"""
backend_worker/routes/crm.py — Endpoint síncrono para consulta ao portal CFM via undetected-chromedriver
"""

import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from dependencies import get_current_user

# scraper.cfm_scraper (Selenium/undetected-chromedriver) e importado de forma lazy
# no handler: assim o worker sobe mesmo sem Chrome instalado (Render free / cloud).
# O CFM esta em migracao para o Local_worker (IP residencial + captcha manual).
# Ver DEPLOY.md - Fase 3.

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/crm", tags=["CRM"])


class ConsultaCRMRequest(BaseModel):
    uf: str = Field(..., description="UF de busca (obrigatório, ex: GO)", min_length=2, max_length=2)
    nome: Optional[str] = Field(None, description="Nome do médico (opcional)")
    registro: Optional[str] = Field(None, description="Número do CRM (opcional)")
    pagina_inicial: int = Field(1, description="Página inicial para fatiamento de lotes (padrão 1)", ge=1)
    max_paginas: int = Field(50, description="Quantidade máxima de páginas a varrer no lote (padrão 50)", ge=1, le=100)


@router.post("/consulta", status_code=status.HTTP_200_OK)
def consultar_crm_endpoint(
    req: ConsultaCRMRequest,
    current_user=Depends(get_current_user),
):
    """
    Endpoint de consulta ao portal CFM.
    Autenticação via BPO_API_KEY ou JWT Bearer Token (Depends(get_current_user)).
    """
    logger.info(
        f"[Worker CRM] Solicitação recebida do usuário id={current_user.id} | "
        f"UF={req.uf} | nome={req.nome} | registro={req.registro} | "
        f"pagina_inicial={req.pagina_inicial} | max_paginas={req.max_paginas}"
    )

    # Import lazy: o scraper depende de undetected-chromedriver + Chrome.
    # Em ambiente sem Chrome (Render free / cloud) retorna 503 em vez de quebrar o boot.
    try:
        from scraper.cfm_scraper import consultar_crm
    except Exception as import_err:
        logger.warning(f"[Worker CRM] Scraper CFM indisponível neste ambiente: {import_err}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Consulta ao CFM indisponível neste ambiente (scraper em migração para o worker local).",
        )

    resultado = consultar_crm(
        uf=req.uf.upper(),
        nome=req.nome,
        registro=req.registro,
        pagina_inicial=req.pagina_inicial,
        max_paginas=req.max_paginas,
    )

    if resultado.get("status") == "PORTAL_BLOCKED":
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=resultado.get("erro", "Portal CFM bloqueado por captcha."),
        )

    if resultado.get("status") == "PARSE_FAIL":
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=resultado.get("erro", "Falha no parse dos resultados do CFM."),
        )

    return resultado
