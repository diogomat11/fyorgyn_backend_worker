import os
import psycopg2
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(Path(__file__).parent.parent.parent / "backend" / ".env")

db_url = os.getenv("DATABASE_URL")
conn = psycopg2.connect(db_url)
cur = conn.cursor()

cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name='corpo_clinico';")
cols = [r[0] for r in cur.fetchall()]
print("Colunas de corpo_clinico:", cols)

cur.execute('SELECT COUNT(*) FROM corpo_clinico WHERE "UF" = \'GO\';')
count_go = cur.fetchone()[0]
print(f"Total de médicos de GO no PostgreSQL: {count_go}")

cur.close()
conn.close()
