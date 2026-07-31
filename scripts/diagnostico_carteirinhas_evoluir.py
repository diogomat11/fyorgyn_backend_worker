import os, sys
from pathlib import Path
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent.parent / 'backend' / '.env')
import psycopg2

db_url = os.getenv('DATABASE_URL')
conn = psycopg2.connect(db_url)
cur = conn.cursor()

print("=== Pacientes com nome 'Afonso' ===")
cur.execute("""
    SELECT id, carteirinha, id_paciente, paciente, id_convenio, codigo_beneficiario, status
    FROM carteirinhas
    WHERE paciente ILIKE '%afonso%'
    ORDER BY id;
""")
rows = cur.fetchall()
for r in rows:
    print(f"  id={r[0]} | carteirinha={r[1]} | id_paciente={r[2]} | nome={r[3]} | id_conv={r[4]} | cod_ben={r[5]} | status={r[6]}")

print()
print("=== Carteirinhas id_convenio=100 (Evoluir) onde carteirinha == id_paciente (bug) ===")
cur.execute("""
    SELECT id, carteirinha, id_paciente, paciente, id_convenio, codigo_beneficiario
    FROM carteirinhas
    WHERE id_convenio = 100
    ORDER BY id
    LIMIT 20;
""")
rows2 = cur.fetchall()
for r in rows2:
    bug = "BUG" if r[1] == r[2] else "OK"
    print(f"  [{bug}] id={r[0]} | carteirinha={r[1]} | id_paciente={r[2]} | nome={r[3]} | cod_ben={r[5]}")

print()
print("=== Total de carteirinhas por id_convenio ===")
cur.execute("""
    SELECT id_convenio, COUNT(*) 
    FROM carteirinhas
    GROUP BY id_convenio
    ORDER BY id_convenio;
""")
for r in cur.fetchall():
    print(f"  id_convenio={r[0]} => {r[1]} registros")

print()
print("=== Duplicatas de nome+id_convenio em carteirinhas ===")
cur.execute("""
    SELECT paciente, id_convenio, COUNT(*) as cnt
    FROM carteirinhas
    GROUP BY paciente, id_convenio
    HAVING COUNT(*) > 1
    ORDER BY cnt DESC
    LIMIT 20;
""")
for r in cur.fetchall():
    print(f"  nome={r[0]} | id_conv={r[1]} | duplicatas={r[2]}")

cur.close()
conn.close()
