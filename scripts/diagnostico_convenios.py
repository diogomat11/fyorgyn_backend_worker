from pathlib import Path
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent.parent / "backend" / ".env")
import os, psycopg2

conn = psycopg2.connect(os.getenv("DATABASE_URL"))
cur = conn.cursor()

print("=== Estrutura da tabela convenios ===")
cur.execute("SELECT column_name, data_type FROM information_schema.columns WHERE table_name='convenios' ORDER BY ordinal_position")
for r in cur.fetchall():
    print(" ", r)

print()
print("=== MAX id_convenio ===")
cur.execute("SELECT MAX(id_convenio) FROM convenios")
print("  MAX:", cur.fetchone()[0])

print()
print("=== IDs >= 100 ===")
cur.execute("SELECT id_convenio, nome FROM convenios WHERE id_convenio >= 100 ORDER BY id_convenio")
for r in cur.fetchall():
    print(" ", r)

print()
print("=== Sequencias no PostgreSQL ===")
cur.execute("SELECT sequence_name, last_value FROM information_schema.sequences LEFT JOIN pg_sequences ON sequencename=sequence_name WHERE sequence_schema='public'")
for r in cur.fetchall():
    print(" ", r)

cur.close()
conn.close()
