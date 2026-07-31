"""
extrair_todas_paginas_GO.py — Automação Contínua por Lotes de todas as páginas da UF=GO (CFM)
Salva médicos no PostgreSQL na coluna 'area' com unicidade (conselho, registro, UF) e atualizado_crm.
"""

import sys
import time
import os
import psycopg2
from pathlib import Path
from dotenv import load_dotenv

# Garantir import do backend_worker
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend_worker.scraper.cfm_scraper import consultar_crm

load_dotenv(Path(__file__).parent.parent.parent / "backend" / ".env")

def _obter_total_medicos_banco(uf: str = "GO") -> int:
    try:
        db_url = os.getenv("DATABASE_URL")
        conn = psycopg2.connect(db_url)
        cur = conn.cursor()
        cur.execute('SELECT COUNT(*) FROM corpo_clinico WHERE "UF" = %s;', (uf.upper(),))
        total = cur.fetchone()[0]
        cur.close()
        conn.close()
        return total
    except Exception as e:
        print(f"Aviso ao consultar total no banco: {e}")
        return 0

def _salvar_medicos_no_banco(medicos: list, uf: str = "GO") -> tuple:
    if not medicos:
        return 0, 0

    novos_inseridos = 0
    atualizados = 0

    try:
        db_url = os.getenv("DATABASE_URL")
        conn = psycopg2.connect(db_url)
        cur = conn.cursor()

        for m in medicos:
            crm = m.get("crm")
            uf_m = m.get("uf") or uf.upper()
            nome = m.get("nome", "").strip().upper()
            situacao = m.get("situacao", "Regular")
            especialidades = m.get("especialidades", [])

            if not crm or not nome:
                continue

            area_str = ", ".join(especialidades) if isinstance(especialidades, list) else str(especialidades or "")

            # SQL com ON CONFLICT (conselho, registro, "UF") DO UPDATE
            sql = """
                INSERT INTO corpo_clinico (conselho, registro, "UF", nome, situacao, area, atualizado_crm)
                VALUES ('CRM', %s, %s, %s, %s, %s, NOW())
                ON CONFLICT (conselho, registro, "UF") DO UPDATE SET
                    nome = EXCLUDED.nome,
                    situacao = EXCLUDED.situacao,
                    area = CASE WHEN EXCLUDED.area <> '' THEN EXCLUDED.area ELSE corpo_clinico.area END,
                    atualizado_crm = NOW()
                RETURNING (xmin = 0) AS is_insert;
            """
            cur.execute(sql, (str(crm), str(uf_m), nome, situacao, area_str))
            res = cur.fetchone()
            if res and res[0]:
                novos_inseridos += 1
            else:
                atualizados += 1

        conn.commit()
        cur.close()
        conn.close()

    except Exception as e:
        print(f"Erro ao salvar médicos no PostgreSQL: {e}")

    return novos_inseridos, atualizados

def main():
    uf = "GO"
    lote_tamanho = 49   # Máximo seguro por sessão do ChromeDriver
    
    medicos_no_banco = _obter_total_medicos_banco(uf)
    # Retomar exatamente da página equivalente ao total de médicos divididos por 10
    pagina_inicial = max(1, (medicos_no_banco // 10) + 1)

    print("=" * 70)
    print(f"INICIANDO EXTRAÇÃO TOTAL DE TODAS AS PÁGINAS DO CFM - UF={uf}")
    print("=" * 70)
    print(f"Estado do Banco -> {medicos_no_banco} médicos de {uf} gravados.")
    print(f"Retomando extração a partir da PÁGINA {pagina_inicial} (Lotes de {lote_tamanho} páginas)...\n")

    pagina_atual = pagina_inicial
    total_geral_novos = 0
    total_geral_atualizados = 0
    numero_lote = 1

    while True:
        print("=" * 70)
        print(f"LOTE #{numero_lote} | UF={uf} | Página Inicial: {pagina_atual} | Max Páginas: {lote_tamanho}")
        print("=" * 70)

        res = consultar_crm(
            uf=uf,
            pagina_inicial=pagina_atual,
            max_paginas=lote_tamanho,
        )

        status = res.get("status")
        medicos = res.get("medicos", [])
        total_paginas_portal = res.get("total_paginas_portal", 1)
        proxima_pagina = res.get("proxima_pagina")

        print(f"Status do Lote #{numero_lote}: {status}")
        print(f"Médicos Extraídos no Lote #{numero_lote}: {len(medicos)}")
        print(f"Total de Páginas do Portal: {total_paginas_portal}")
        print(f"Próxima Página Calculada: {proxima_pagina}")

        if medicos:
            novos, atus = _salvar_medicos_no_banco(medicos, uf=uf)
            total_geral_novos += novos
            total_geral_atualizados += atus
            print(f"Lote #{numero_lote} Salvo -> Novos: {novos} | Atualizados: {atus}")
            print(f"Total Geral Acumulado -> Novos: {total_geral_novos} | Atualizados: {total_geral_atualizados}\n")
        else:
            print(f"Nenhum médico retornado no lote #{numero_lote}. Finalizando varredura.")
            break

        if not proxima_pagina or proxima_pagina > total_paginas_portal:
            print("Todas as páginas do portal foram extraídas com sucesso!")
            break

        pagina_atual = proxima_pagina
        numero_lote += 1
        time.sleep(4)

    print("=" * 70)
    print(f"VARREDURA COMPLETA DA UF={uf} CONCLUÍDA COM SUCESSO!")
    print(f"Total Novos Inseridos  : {total_geral_novos}")
    print(f"Total Atualizados      : {total_geral_atualizados}")
    print("=" * 70)

if __name__ == "__main__":
    main()
