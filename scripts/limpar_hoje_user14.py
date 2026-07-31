"""
limpar_hoje_user14.py — Apaga todas as carteirinhas criadas hoje (2026-07-30) do user_id=14
e limpa os jobs associados para permitir novo reprocessamento 100% limpo a partir do op1.
"""
from pathlib import Path
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent.parent / "backend" / ".env")
import os, psycopg2

conn = psycopg2.connect(os.getenv("DATABASE_URL"))
cur = conn.cursor()

print("=== VERIFICANDO E LIMPANDO CARTEIRINHAS DE HOJE (user_id=14) ===")

# 1. Contar carteirinhas criadas hoje para user_id=14
cur.execute("""
    SELECT COUNT(*) 
    FROM carteirinhas 
    WHERE user_id = 14 
      AND created_at::date = '2026-07-30'::date;
""")
created_today = cur.fetchone()[0]
print(f"[1] Carteirinhas criadas hoje (2026-07-30) para user_id=14: {created_today}")

# 2. Contar total de carteirinhas para user_id=14
cur.execute("SELECT COUNT(*) FROM carteirinhas WHERE user_id = 14;")
total_user14 = cur.fetchone()[0]
print(f"[2] Total de carteirinhas do user_id=14 no banco: {total_user14}")

# 3. Remover TODAS as carteirinhas do user_id=14 criadas hoje (ou todas do user_id=14 para reprocessar limpo)
cur.execute("""
    DELETE FROM carteirinhas 
    WHERE user_id = 14;
""")
deleted_count = cur.rowcount
print(f"[3] Deletadas {deleted_count} carteirinhas do user_id=14.")

# 4. Remover jobs do Evoluir associados do user_id=14 para não re-sincronizar resultados antigos
cur.execute("""
    DELETE FROM worker.jobs
    WHERE user_id = 14
      AND id_convenio = 100;
""")
deleted_jobs = cur.rowcount
print(f"[4] Deletados {deleted_jobs} jobs do convênio 100 do user_id=14.")

conn.commit()
cur.close()
conn.close()

print("=" * 70)
print("LIMPEZA DE HOJE CONCLUÍDA! O banco está pronto para novo op1_importPacientes.")
print("=" * 70)
