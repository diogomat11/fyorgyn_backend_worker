from pathlib import Path
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent.parent / "backend" / ".env")
import os, psycopg2

conn = psycopg2.connect(os.getenv("DATABASE_URL"))
cur = conn.cursor()

cur.execute("SELECT column_name, is_nullable, data_type FROM information_schema.columns WHERE table_name='carteirinhas' AND column_name='carteirinha'")
print("carteirinha nullable:", cur.fetchone())

cur.execute("SELECT column_name, is_nullable, data_type FROM information_schema.columns WHERE table_name='carteirinhas' AND column_name='id_paciente'")
print("id_paciente nullable:", cur.fetchone())

cur.close()
conn.close()
