"""
limpar_user14.py — Apaga carteirinhas e jobs pendentes (op2/op3) do user_id=14
para reprocessamento limpo do op1_importPacientes.
"""
from pathlib import Path
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent.parent / "backend" / ".env")
import os, psycopg2

conn = psycopg2.connect(os.getenv("DATABASE_URL"))
cur = conn.cursor()

print("=== LIMPEZA user_id=14 ===")

# 1. Jobs pendentes de rotinas internas do Evoluir para user_id=14
cur.execute("""
    DELETE FROM worker.jobs
    WHERE user_id = 14
      AND rotina IN ('op2_obterDetalhes','op3_ListarPTS','op5_ImportCorpoClinico',
                     'op1_importPacientes','op6_baixarFaturados','op4_atualizarDataPTS')
      AND status IN ('pending','error');
""")
print(f"[1] Jobs internos removidos: {cur.rowcount}")

# 2. Carteirinhas do user_id=14 (sem agendamentos vinculados)
cur.execute("""
    SELECT id FROM carteirinhas WHERE user_id = 14
""")
cart_ids = [r[0] for r in cur.fetchall()]
print(f"[2] Carteirinhas encontradas: {len(cart_ids)}")

# Verificar se têm agendamentos
cur.execute("""
    SELECT COUNT(*) FROM agendamentos WHERE id_carteirinha = ANY(%s)
""", (cart_ids,))
ag_count = cur.fetchone()[0]
print(f"    Agendamentos vinculados: {ag_count}")

# Remover carteirinhas
cur.execute("DELETE FROM carteirinhas WHERE user_id = 14")
print(f"[3] Carteirinhas removidas: {cur.rowcount}")

conn.commit()
cur.close()
conn.close()
print("=== CONCLUÍDO ===")
