"""
cadastrar_op15_convenio_operacoes.py — Registra a OP15 (op15_enviar_justificativa)
do IPASGO (convenio/integrador 6) nos catálogos de operações:

- worker.integrador_operacoes  (catálogo runtime, fonte de verdade do dispatcher)
- public.integrador_operacoes  (espelho admin)
- public.convenio_operacoes    (seletor de operações do hub)

Idempotente — pode ser reexecutado.

Uso: python scripts/cadastrar_op15_convenio_operacoes.py (dentro de backend_worker/)
"""
from pathlib import Path
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent.parent / "backend" / ".env")
import os, psycopg2

ROTINA = "op15_enviar_justificativa"
DESCRICAO = "Envio de justificativa/observação para guia no regulador do IPASGO (FacPlan)"

conn = psycopg2.connect(os.getenv("DATABASE_URL"))
cur = conn.cursor()

print(f"=== CADASTRANDO {ROTINA} (IPASGO) ===")

# ── Catálogo runtime do worker ──
cur.execute("""
    SELECT rotina FROM worker.integrador_operacoes
    WHERE id_integrador = 6 AND rotina = %s
""", (ROTINA,))
if not cur.fetchone():
    cur.execute("""
        INSERT INTO worker.integrador_operacoes
            (id_integrador, rotina, descricao, tipo_processamento, ativo, modo_execucao)
        VALUES (6, %s, %s, 'local', TRUE, 'automatico')
        ON CONFLICT (id_integrador, rotina) DO UPDATE SET
            descricao = EXCLUDED.descricao, ativo = EXCLUDED.ativo
    """, (ROTINA, DESCRICAO))
    conn.commit()
    print("worker.integrador_operacoes: operação cadastrada com sucesso!")
else:
    print("worker.integrador_operacoes: operação já cadastrada.")

# ── Espelho admin (public) ──
cur.execute("""
    SELECT rotina FROM public.integrador_operacoes
    WHERE id_integrador = 6 AND rotina = %s
""", (ROTINA,))
if not cur.fetchone():
    cur.execute("""
        INSERT INTO public.integrador_operacoes
            (id_integrador, id_convenio, rotina, descricao, tipo_processamento, ativo)
        VALUES (6, 6, %s, %s, 'local', TRUE)
        ON CONFLICT (id_integrador, rotina) DO UPDATE SET
            descricao = EXCLUDED.descricao, ativo = EXCLUDED.ativo
    """, (ROTINA, DESCRICAO))
    conn.commit()
    print("public.integrador_operacoes: operação cadastrada com sucesso!")
else:
    print("public.integrador_operacoes: operação já cadastrada.")

# ── Seletor de operações do hub (valor = nome do arquivo da OP) ──
cur.execute("""
    SELECT id FROM public.convenio_operacoes
    WHERE id_convenio = 6 AND valor = %s
""", (ROTINA,))
if not cur.fetchone():
    cur.execute("""
        INSERT INTO public.convenio_operacoes (id_convenio, valor, descricao)
        VALUES (6, %s, '15 - Enviar Justificativa (Regulador IPASGO)')
        ON CONFLICT DO NOTHING
    """, (ROTINA,))
    conn.commit()
    print("convenio_operacoes (seletor): operação cadastrada com sucesso!")
else:
    print("convenio_operacoes (seletor): operação já cadastrada.")

cur.close()
conn.close()
