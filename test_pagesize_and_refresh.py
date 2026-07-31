"""
test_pagesize_and_refresh.py — Testa auto-refresh para captcha e injeção de pageSize (100/1000)
"""
import time
import os
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select

_HERE = os.path.dirname(__file__)
profile = os.path.join(_HERE, "scraper", "uc_profile_cfm")

options = uc.ChromeOptions()
options.add_argument("--no-sandbox")
options.add_argument(f"--user-data-dir={profile}")

driver = uc.Chrome(options=options, version_main=150)
url = "https://portal.cfm.org.br/busca-medicos/"

print("=== TESTE 1: SOFT REFRESH PARA EVITAR CAPTCHA ===")
for tentativa in range(1, 4):
    print(f"Tentativa {tentativa}: abrindo {url}...")
    driver.get(url)
    time.sleep(2.5)
    src = driver.page_source.lower()
    has_captcha = any(ind in src for ind in ["cf-challenge", "challenge-form", "recaptcha/bframe"])
    if not has_captcha:
        print(f"Página carregada sem captcha bloqueante na tentativa {tentativa}!")
        break
    else:
        print(f"Captcha bloqueante detectado na tentativa {tentativa}. Aplicando refresh...")

# Preencher formulário #buscaForm
print("\nPreenchendo #buscaForm...")
form = driver.find_element(By.ID, "buscaForm")
Select(form.find_element(By.ID, "uf")).select_by_value("GO")
btn = form.find_element(By.CSS_SELECTOR, "button.btnPesquisar")
driver.execute_script("arguments[0].click();", btn)
time.sleep(4)

print("\n=== TESTE 2: INJEÇÃO DE PAGE SIZE VIA JS NO PAGINATIONJS ===")

# Inspecionar objetos JS na página para ver se o paginationjs ou a API interna do CFM aceitam pageSize
js_script = """
if (window.jQuery && jQuery('#buscaForm').length) {
    // Tentar obter a instância do paginationjs se existir
    var container = jQuery('.paginationjs');
    if (container.length && container.pagination) {
        return 'paginationjs encontrado';
    }
}
return 'jQuery / paginationjs não exposto diretamente no window';
"""
res = driver.execute_script(js_script)
print("Resultado da verificação JS:", res)

# Tentar alterar tamanho da página via JS e disparar re-render
js_change_pagesize = """
try {
    if (window.jQuery) {
        var p = jQuery('.paginationjs').data('pagination');
        if (p) {
            p.state.pageSize = 100;
            return 'pageSize alterado para 100 no estado do paginationjs!';
        }
    }
} catch(e) {
    return 'Erro ao alterar pageSize: ' + e.message;
}
return 'Pagination instance não encontrada via jQuery data';
"""
res_change = driver.execute_script(js_change_pagesize)
print("Resultado tentativa de injeção de pageSize:", res_change)

driver.quit()
