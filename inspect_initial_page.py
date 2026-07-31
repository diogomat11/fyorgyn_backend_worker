"""
inspect_initial_page.py — Abre a página inicial de busca de médicos do CFM e salva o HTML.
"""
import time
import os
import undetected_chromedriver as uc

_HERE = os.path.dirname(__file__)
profile = os.path.join(_HERE, "scraper", "uc_profile_cfm")

options = uc.ChromeOptions()
options.add_argument("--no-sandbox")
options.add_argument(f"--user-data-dir={profile}")

print("Abrindo https://portal.cfm.org.br/busca-medicos/ ...")
driver = uc.Chrome(options=options, version_main=150)
driver.get("https://portal.cfm.org.br/busca-medicos/")
time.sleep(5)

print("URL atual:", driver.current_url)
print("Título atual:", driver.title)

with open("initial_page.html", "w", encoding="utf-8") as f:
    f.write(driver.page_source)

print("Página inicial salva em initial_page.html")
driver.quit()
