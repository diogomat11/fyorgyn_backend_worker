"""
limpar_e_reprocessar_evoluir.py — Limpa carteirinhas com dicts cru e reprocessa jobs op2 com sucesso
"""
from pathlib import Path
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent.parent / "backend" / ".env")
import os, json, psycopg2

conn = psycopg2.connect(os.getenv("DATABASE_URL"))
cur = conn.cursor()

print("=" * 70)
print("INICIANDO LIMPEZA E REPROCESSAMENTO EVOLUIR")
print("=" * 70)

# 1. Limpar carteirinhas com dicts cru em formato string '{'
cur.execute("""
    DELETE FROM carteirinhas
    WHERE carteirinha LIKE '{%' OR codigo_beneficiario LIKE '{%';
""")
print(f"[1] Removidas {cur.rowcount} carteirinhas corrompidas com JSON/dict cru.")

# 2. Resetar result_consumed=False para todos os jobs op2_obterDetalhes concluídos com sucesso para user_id=14
cur.execute("""
    UPDATE worker.jobs
    SET result_consumed = False
    WHERE user_id = 14
      AND rotina = 'op2_obterDetalhes'
      AND status = 'success';
""")
print(f"[2] Resetados {cur.rowcount} jobs op2_obterDetalhes para reprocessamento de resultado pelo backend.")

conn.commit()
cur.close()
conn.close()

# 3. Executar o guias_sync_service para reprocessar os resultados
print("[3] Disparando guias_sync_service...")
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "backend"))
from database import SessionLocal
from services.guias_sync_service import sync_completed_worker_jobs

db = SessionLocal()
try:
    res = sync_completed_worker_jobs(db)
    print(f"    Sincronização concluída: {res}")
finally:
    db.close()

print("=" * 70)
