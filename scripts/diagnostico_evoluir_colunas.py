"""
diagnostico_evoluir_colunas.py — Analisa padrões de carteirinha malformada no banco
"""
from pathlib import Path
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent.parent / "backend" / ".env")
import os, psycopg2

conn = psycopg2.connect(os.getenv("DATABASE_URL"))
cur = conn.cursor()

print("=== Carteirinhas com EVOLUIR_ placeholder (user_id=14) ===")
cur.execute("""
    SELECT id, carteirinha, id_paciente, paciente, id_convenio, codigo_beneficiario
    FROM carteirinhas
    WHERE user_id=14 AND carteirinha LIKE 'EVOLUIR_%'
    ORDER BY id LIMIT 10
""")
for r in cur.fetchall():
    print(f"  id={r[0]} | cart={r[1][:50]} | id_pac={r[2]} | conv={r[4]} | cod_ben={r[5]}")

print()
print("=== Carteirinhas com JSON/dict cru (user_id=14) ===")
cur.execute("""
    SELECT id, LEFT(carteirinha, 80), id_paciente, LEFT(COALESCE(codigo_beneficiario,''), 80)
    FROM carteirinhas
    WHERE user_id=14 AND carteirinha LIKE '{%'
    ORDER BY id LIMIT 10
""")
for r in cur.fetchall():
    print(f"  id={r[0]} | cart={r[1]} | cod_ben={r[3]}")

print()
print("=== Total por padrão de carteirinha (user_id=14) ===")
cur.execute("""
    SELECT
        CASE
            WHEN carteirinha LIKE 'EVOLUIR_%' THEN 'placeholder EVOLUIR_'
            WHEN carteirinha LIKE '{%' THEN 'JSON/dict cru'
            ELSE 'numero real'
        END as tipo,
        COUNT(*)
    FROM carteirinhas
    WHERE user_id=14
    GROUP BY 1
""")
for r in cur.fetchall():
    print(f"  {r[0]}: {r[1]}")

print()
print("=== Jobs op2 concluidos com result_data (amostras) ===")
cur.execute("""
    SELECT id, LEFT(result_data::text, 200), LEFT(params::text, 150)
    FROM worker.jobs
    WHERE user_id=14 AND rotina='op2_obterDetalhes' AND status='success'
    ORDER BY id DESC LIMIT 5
""")
for r in cur.fetchall():
    print(f"  job_id={r[0]}\n    result={r[1]}\n    params={r[2]}")

cur.close()
conn.close()
