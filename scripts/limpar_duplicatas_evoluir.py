"""
limpar_duplicatas_evoluir.py — Script para limpar duplicatas e corrigir o bug onde carteirinha == id_paciente
"""

import os
import psycopg2
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent.parent / "backend" / ".env")

def main():
    db_url = os.getenv("DATABASE_URL")
    conn = psycopg2.connect(db_url)
    cur = conn.cursor()

    print("=" * 70)
    print("INICIANDO CORREÇÃO E LIMPEZA DE CARTEIRINHAS EVOLUIR")
    print("=" * 70)

    # 1. Caso 1: Registros onde carteirinha == id_paciente, mas existe um codigo_beneficiario válido
    cur.execute("""
        UPDATE carteirinhas
        SET carteirinha = codigo_beneficiario
        WHERE carteirinha = id_paciente
          AND codigo_beneficiario IS NOT NULL
          AND codigo_beneficiario <> ''
          AND codigo_beneficiario <> id_paciente;
    """)
    res1 = cur.rowcount
    print(f"[1] Atualizadas {res1} carteirinhas onde 'carteirinha' continha UUID mas tinha 'codigo_beneficiario' válido.")

    # 2. Caso 2: Registros duplicados do mesmo paciente e convênio, onde um registro tem a carteirinha real e outro tem o UUID/vazia
    cur.execute("""
        SELECT paciente, id_convenio, user_id
        FROM carteirinhas
        GROUP BY paciente, id_convenio, user_id
        HAVING COUNT(*) > 1;
    """)
    duplicados = cur.fetchall()
    print(f"[2] Encontrados {len(duplicados)} grupos de pacientes duplicados para fusão.")

    removidos_count = 0
    fundidos_count = 0

    for paciente, id_convenio, user_id in duplicados:
        cur.execute("""
            SELECT id, carteirinha, id_paciente, codigo_beneficiario, cid
            FROM carteirinhas
            WHERE paciente = %s AND id_convenio = %s AND user_id = %s
            ORDER BY id ASC;
        """, (paciente, id_convenio, user_id))
        rows = cur.fetchall()

        if len(rows) <= 1:
            continue

        # Identificar o registro principal (o que tem carteirinha real válida, não-UUID e não-vazia)
        principal = None
        secundarios = []

        for r in rows:
            r_id, r_cart, r_id_pac, r_cod_ben, r_cid = r
            # É UUID se r_cart == r_id_pac ou se tem hífens como UUID
            is_uuid = (r_cart == r_id_pac) or ("-" in str(r_cart) and len(str(r_cart)) > 20)
            if not is_uuid and r_cart and r_cart.strip():
                if principal is None:
                    principal = list(r)
                else:
                    secundarios.append(r)
            else:
                secundarios.append(r)

        if not principal:
            principal = list(rows[0])
            secundarios = rows[1:]

        p_id, p_cart, p_id_pac, p_cod_ben, p_cid = principal

        # Mesclar informações dos secundários no principal
        for sec in secundarios:
            s_id, s_cart, s_id_pac, s_cod_ben, s_cid = sec

            if not p_id_pac and s_id_pac:
                p_id_pac = s_id_pac
            if not p_cod_ben and s_cod_ben:
                p_cod_ben = s_cod_ben
            if not p_cid and s_cid:
                p_cid = s_cid

            # Re-vincular agendamentos do secundário para o principal
            cur.execute("""
                UPDATE agendamentos
                SET id_carteirinha = %s
                WHERE id_carteirinha = %s;
            """, (p_id, s_id))

            # Re-vincular base_guias do secundário para o principal
            cur.execute("""
                UPDATE base_guias
                SET carteirinha_id = %s
                WHERE carteirinha_id = %s;
            """, (p_id, s_id))

            # Deletar o registro secundário duplicado
            cur.execute("DELETE FROM carteirinhas WHERE id = %s;", (s_id,))
            removidos_count += 1

        # Atualizar o registro principal com os dados mesclados
        cur.execute("""
            UPDATE carteirinhas
            SET id_paciente = %s,
                codigo_beneficiario = %s,
                cid = %s
            WHERE id = %s;
        """, (p_id_pac, p_cod_ben, p_cid, p_id))

        fundidos_count += 1

    conn.commit()
    cur.close()
    conn.close()

    print(f"[2] Fusão concluída: {fundidos_count} grupos unificados, {removidos_count} registros duplicados removidos.")
    print("=" * 70)

if __name__ == "__main__":
    main()
