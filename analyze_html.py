"""
analyze_html.py — Analisa o HTML de debug salvo para descobrir os seletores exatos dos médicos e da paginação do CFM.
"""
import re
from pathlib import Path
from bs4 import BeautifulSoup

file_path = Path("cfm_debug_page.html")
if not file_path.exists():
    print("Arquivo cfm_debug_page.html não encontrado!")
    exit(1)

html = file_path.read_text(encoding="utf-8")
soup = BeautifulSoup(html, "html.parser")

print("=" * 60)
print("ANÁLISE DO HTML DE DEBUG (cfm_debug_page.html)")
print("=" * 60)
print(f"Tamanho total: {len(html)} bytes")
print(f"Título da página: {soup.title.string if soup.title else 'Sem título'}")

# 1. Formulários
forms = soup.find_all("form")
print(f"\nFormulários encontrados ({len(forms)}):")
for i, f in enumerate(forms, 1):
    action = f.get("action", "")
    method = f.get("method", "")
    f_id = f.get("id", "")
    f_cls = f.get("class", "")
    print(f"  Form #{i}: id='{f_id}' class='{f_cls}' action='{action}' method='{method}'")
    inputs = f.find_all(["input", "select", "button"])
    for inp in inputs:
        print(f"    - <{inp.name}> name='{inp.get('name')}' id='{inp.get('id')}' type='{inp.get('type')}' value='{inp.get('value')}'")

# 2. Busca por elementos com classes suspeitas de resultados
print("\nClasses com 'card', 'item', 'result', 'medico', 'busca':")
selectors = ["[class*='card']", "[class*='item']", "[class*='result']", "[class*='medico']", "[class*='busca']", "table"]
found_classes = set()
for sel in selectors:
    for el in soup.select(sel):
        cls = el.get("class")
        if cls:
            found_classes.add(" ".join(cls))

for c in sorted(found_classes)[:20]:
    print(f"  - class='{c}'")

# 3. Verificar se há divs de resultados específicas
results_divs = soup.select("[class*='resultado'], [class*='busca'], [id*='resultado'], [id*='busca']")
print(f"\nContêineres de resultado ({len(results_divs)}):")
for d in results_divs[:10]:
    print(f"  <{d.name}> id='{d.get('id')}' class='{d.get('class')}'")

# 4. Paginação
paginations = soup.select("[class*='paginat'], [class*='page'], [class*='pagination']")
print(f"\nElementos de paginação ({len(paginations)}):")
for p in paginations:
    print(f"  <{p.name}> id='{p.get('id')}' class='{p.get('class')}' -> texto: {p.text.strip()[:100]}")

# 5. Busca textual por números de CRM ou nomes de médicos no HTML
crms = re.findall(r"CRM[/-]?\s*[A-Z]{2}\s*[:\s]*\d+", html, re.IGNORECASE)
print(f"\nOcorrências textuais de CRM encontradas: {len(crms)}")
if crms:
    print(f"Exemplos: {crms[:5]}")
