"""
limpar_placeholders_evoluir.py — Substitui qualquer carteirinha com EVOLUIR_ por NULL no banco de dados
e desativa o uso de qualquer string sintética.
"""
from pathlib import Path
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent.parent / "backend" / ".env")
import os, psycopg2

conn = psycopg2.connect(os.getenv("DATABASE_URL"))
cur = conn.cursor()

print("=== LIMPANDO PLACEHOLDERS 'EVOLUIR_' DA COLUNA CARTEIRINHA ===")

cur.execute("""
    UPDATE carteirinhas
    SET carteirinha = NULL
    WHERE carteirinha LIKE 'EVOLUIR_%';
""")
print(f"Atualizadas {cur.rowcount} carteirinhas removendo o valor sintético 'EVOLUIR_' para NULL.")

conn.commit()

cur.execute("SELECT COUNT(*) FROM carteirinhas WHERE carteirinha LIKE 'EVOLUIR_%'")
print(f"Total restante de EVOLUIR_ no banco: {cur.fetchone()[0]}")

cur.close()
conn.close()

# Invalidar cache de todos os tenants
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "backend"))
from cache import cache
for uid in [14, 1, 15, 2, 3, 4, 5, 6, 7, 8, 9, 10]:
    cache.invalidate_tenant(uid)
print("Cache dos tenants invalidado com sucesso!")
