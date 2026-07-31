from pathlib import Path
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent.parent / "backend" / ".env")
import os, psycopg2, json

conn = psycopg2.connect(os.getenv("DATABASE_URL"))
cur = conn.cursor()

print("=== Pesquisa YASMIN VICTORIA ===")
cur.execute("SELECT id, carteirinha, id_paciente, paciente, id_convenio, codigo_beneficiario, user_id FROM carteirinhas WHERE paciente ILIKE '%YASMIN VICTORIA%'")
for r in cur.fetchall():
    print(f"  id={r[0]} | cart={r[1]} | id_pac={r[2]} | nome={r[3]} | conv={r[4]} | cod_ben={r[5]} | user_id={r[6]}")

print()
print("=== Jobs do op2 para YASMIN VICTORIA ===")
cur.execute("""
    SELECT id, status, result_consumed, result_data, params
    FROM worker.jobs
    WHERE rotina='op2_obterDetalhes' AND params::text ILIKE '%35aa7f62-e52c-4795-ac64-da90e7e1dd2a%'
""")
for r in cur.fetchall():
    print(f"  job_id={r[0]} | status={r[1]} | consumed={r[2]}")
    print(f"    result={r[3]}")
    print(f"    params={r[4]}")

cur.close()
conn.close()
