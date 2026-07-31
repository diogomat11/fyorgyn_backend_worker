from pathlib import Path
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent.parent / "backend" / ".env")
import os, psycopg2

conn = psycopg2.connect(os.getenv("DATABASE_URL"))
cur = conn.cursor()

print("=== Pesquisa por ID 5114 ou JOAO MIGUEL ===")
cur.execute("SELECT id, carteirinha, id_paciente, paciente, id_convenio, user_id FROM carteirinhas WHERE id=5114 OR paciente ILIKE '%JOAO MIGUEL RONCATO%'")
for r in cur.fetchall():
    print(r)

print()
print("=== Total de carteirinhas EVOLUIR_ no banco inteiro (todos os user_ids) ===")
cur.execute("SELECT id, carteirinha, paciente, user_id FROM carteirinhas WHERE carteirinha LIKE 'EVOLUIR_%'")
rows = cur.fetchall()
print(f"Total encontradas: {len(rows)}")
for r in rows[:15]:
    print(r)

print()
print("=== Quem é o usuário logado? Verificando users em carteirinhas ===")
cur.execute("SELECT user_id, COUNT(*) FROM carteirinhas GROUP BY user_id")
for r in cur.fetchall():
    print(f"  user_id={r[0]} => {r[1]} carteirinhas")

cur.close()
conn.close()
