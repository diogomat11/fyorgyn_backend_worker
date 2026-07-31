"""
test_cfm.py — Testa o scraper do portal CFM nacional
Uso: python test_cfm.py

Executa uma busca por UF=GO com page_size=1000.
Imprime resultado em JSON formatado e grava em cfm_resultado_GO.json.
"""

import sys
import json
import logging
import os
from pathlib import Path

# Adicionar pasta backend_worker ao path
ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

# Carregar .env
from dotenv import load_dotenv
load_dotenv(ROOT / ".env")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
    ]
)

from scraper.cfm_scraper import consultar_crm

def main():
    print("=" * 60)
    print("TESTE CFM SCRAPER — UF=GO | page_size=1000")
    print("=" * 60)

    resultado = consultar_crm(
        uf="GO",
        pagina_inicial=1,
        max_paginas=2,

    )

    print("\n" + "=" * 60)
    print(f"STATUS  : {resultado['status']}")
    print(f"UF      : {resultado['uf']}")
    print(f"TOTAL   : {resultado['total']} médicos")
    print(f"PÁGINAS : {resultado.get('paginas', '?')}")
    if resultado.get("erro"):
        print(f"ERRO    : {resultado['erro']}")
    print("=" * 60)

    if resultado["medicos"]:
        print("\nPrimeiros 5 médicos:")
        for m in resultado["medicos"][:5]:
            print(f"  CRM {m['crm']}/{m['uf']} | {m['nome']} | {m['situacao']}")

        print(f"\nÚltimos 5 médicos:")
        for m in resultado["medicos"][-5:]:
            print(f"  CRM {m['crm']}/{m['uf']} | {m['nome']} | {m['situacao']}")

    # Gravar resultado completo
    out_path = ROOT / "cfm_resultado_GO.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(resultado, f, ensure_ascii=False, indent=2, default=str)
    print(f"\nResultado completo salvo em: {out_path}")

if __name__ == "__main__":
    main()
