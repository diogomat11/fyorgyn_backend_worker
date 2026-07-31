"""
diagnostico_user14.py — Verifica carteirinhas do user_id=14 e amostras do op2
"""
from pathlib import Path
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent.parent / "backend" / ".env")
import os, psycopg2

db_url = os.getenv("DATABASE_URL")
conn = psycopg2.connect(db_url)
cur = conn.cursor()

cur.execute("SELECT COUNT(*) FROM carteirinhas WHERE user_id=14")
print(f"Total carteirinhas user_id=14: {cur.fetchone()[0]}")

cur.execute("SELECT id, carteirinha, id_paciente, paciente, id_convenio, codigo_beneficiario FROM carteirinhas WHERE user_id=14 ORDER BY id LIMIT 10")
print("Amostras:")
for r in cur.fetchall():
    print(f"  id={r[0]} | cart={r[1]} | id_pac={r[2]} | nome={r[3]} | conv={r[4]} | cod_ben={r[5]}")

cur.execute("SELECT COUNT(*) FROM worker.jobs WHERE user_id=14 AND rotina='op2_obterDetalhes' AND status='pending'")
print(f"\nJobs op2 pendentes user_id=14: {cur.fetchone()[0]}")

cur.close()
conn.close()
