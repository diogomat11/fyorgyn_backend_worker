"""
inspect_pagination.py — Inspeciona como o CFM renderiza a paginação e como avançar para as páginas seguintes.
"""
import time
import os
import json
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select

_HERE = os.path.dirname(__file__)
profile = os.path.join(_HERE, "scraper", "uc_profile_cfm")

options = uc.ChromeOptions()
options.add_argument("--no-sandbox")
options.add_argument(f"--user-data-dir={profile}")

driver = uc.Chrome(options=options, version_main=150)
driver.get("https://portal.cfm.org.br/busca-medicos/")
time.sleep(3)

# Preencher e submeter buscaForm
form = driver.find_element(By.ID, "buscaForm")
Select(form.find_element(By.ID, "uf")).select_by_value("GO")
btn = form.find_element(By.CSS_SELECTOR, "button.btnPesquisar")
driver.execute_script("arguments[0].click();", btn)
time.sleep(4)

print("=== INSPEÇÃO DE PAGINAÇÃO DA PÁGINA DE RESULTADOS ===")
print("URL atual pós-submit:", driver.current_url)

# Salvar HTML completo dos resultados da busca
with open("search_results_page.html", "w", encoding="utf-8") as f:
    f.write(driver.page_source)

# Procurar elementos de paginação (links, botões, nav)
pag_elements = driver.find_elements(By.CSS_SELECTOR, "ul.pagination, div.pagination, nav, .pagination, [class*='pagina'], [class*='pager']")
print(f"Elementos de paginação encontrados: {len(pag_elements)}")
for i, el in enumerate(pag_elements, 1):
    print(f"\n--- Elemento #{i} ---")
    print("Tag:", el.tag_name, "Class:", el.get_attribute("class"), "ID:", el.get_attribute("id"))
    links = el.find_elements(By.TAG_NAME, "a")
    for l in links:
        print(f"  Link: text='{l.text.strip()}' href='{l.get_attribute('href')}' class='{l.get_attribute('class')}'")

driver.quit()
