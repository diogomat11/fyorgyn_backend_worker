"""
invalidar_cache.py — Invalida cache no Redis e no TenantCache para todos os usuários
"""
from pathlib import Path
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent.parent / "backend" / ".env")
import os, sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "backend"))
from cache import cache

print("=== INVALIDANDO CACHE DE TODOS OS TENANTS ===")

# Invalidar para user_id=14 e outros
for uid in [14, 1, 15, 2, 3, 4, 5, 6, 7, 8, 9, 10]:
    res = cache.invalidate_tenant(uid)
    print(f"  Cache user_id={uid} invalidado: {res}")

print("=" * 70)
