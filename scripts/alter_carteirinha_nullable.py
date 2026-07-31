from pathlib import Path
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent.parent / "backend" / ".env")
import os, psycopg2

conn = psycopg2.connect(os.getenv("DATABASE_URL"))
cur = conn.cursor()

print("=== Alterando coluna carteirinhas.carteirinha para DROP NOT NULL ===")
cur.execute("ALTER TABLE carteirinhas ALTER COLUMN carteirinha DROP NOT NULL;")
conn.commit()
print("ALTER TABLE executado com sucesso!")

cur.execute("SELECT column_name, is_nullable FROM information_schema.columns WHERE table_name='carteirinhas' AND column_name='carteirinha'")
print("Novo estado:", cur.fetchone())

cur.close()
conn.close()
