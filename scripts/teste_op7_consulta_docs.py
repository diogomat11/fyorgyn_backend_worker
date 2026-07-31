"""
teste_op7_consulta_docs.py — Teste local da operacao op7_consultaDocs para o user_id=14
"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent.parent / "backend" / ".env")

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "Local_worker" / "Worker"))
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "backend"))

from factory import ScraperFactory
from database import SessionLocal

def main():
    print("=== TESTANDO OP_consultaDocs (op7_consultaDocs) ===")
    db = SessionLocal()
    try:
        scraper = ScraperFactory.get_scraper(id_convenio=100, db=db, headless=True, user_id=14)
        
        from models import Job
        test_job = Job(
            status="processing",
            id_convenio=100,
            user_id=14,
            rotina="op7_consultaDocs",
            priority=0
        )
        db.add(test_job)
        db.commit()
        
        job_data = {
            "job_id": test_job.id,
            "id_convenio": 100,
            "rotina": "op7_consultaDocs",
            "user_id": 14
        }

        from server import sel_manager
        driver = sel_manager.get_driver(100, headless=True, user_id=14)
        scraper.driver = driver

        if not scraper.csrf_token or len(scraper.session.cookies) == 0:
            print("Iniciando login no portal Evoluir...")
            scraper.login()

        print("Executando op7_consultaDocs...")
        res = scraper.process_job("op7_consultaDocs", job_data)
        
        print("\n=== RESULTADO ===")
        print(f"Status: {res.get('status')}")
        print(f"Total de documentos encontrados: {res.get('total_documentos')}")
        print(f"Pacientes consultados: {res.get('total_pacientes_consultados')}")
        print(f"Excel URL: {res.get('excel_url')}")
        
        data_list = res.get("data", [])
        if data_list:
            print(f"\nAmostra do primeiro documento extraído:")
            print(data_list[0])
            
    finally:
        db.close()

if __name__ == "__main__":
    main()
