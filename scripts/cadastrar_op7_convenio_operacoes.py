"""
cadastrar_op7_convenio_operacoes.py — Registra a operacao OP_consultaDocs no banco de dados para o convenio 100
"""
from pathlib import Path
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent.parent / "backend" / ".env")
import os, psycopg2

conn = psycopg2.connect(os.getenv("DATABASE_URL"))
cur = conn.cursor()

print("=== CADASTRANDO OP_consultaDocs EM convenio_operacoes ===")

# Verificar se já existe
cur.execute("SELECT id FROM convenio_operacoes WHERE id_convenio = 100 AND valor IN ('op7_consultaDocs', 'OP_consultaDocs')")
row = cur.fetchone()

if not row:
    cur.execute("""
        INSERT INTO convenio_operacoes (id_convenio, valor, descricao)
        VALUES (100, 'OP_consultaDocs', '7 - Consultar Relatórios e Planos Terapêuticos (Excel)');
    """)
    conn.commit()
    print("Cadastrada operação '7 - Consultar Relatórios e Planos Terapêuticos (Excel)' com sucesso!")
else:
    print(f"Operação já cadastrada (ID {row[0]}).")

cur.close()
conn.close()
