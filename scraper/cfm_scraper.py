"""
cfm_scraper.py — Scraper do portal CFM nacional (busca-medicos)
Com aguardo limpo e resiliente de resolução manual de captcha
"""

import os
import time
import logging
import json
import re
from pathlib import Path
from typing import Optional

import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException, UnexpectedAlertPresentException, StaleElementReferenceException
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

# ------------------------------------------------------------------------------
# Configurações
# ------------------------------------------------------------------------------

_HERE = Path(__file__).parent
_DEFAULT_PROFILE = str(_HERE / "uc_profile_cfm")

CFM_URL = "https://portal.cfm.org.br/busca-medicos/"
REQUEST_TIMEOUT = 45     # segundos aguardando elementos


# ------------------------------------------------------------------------------
# Driver
# ------------------------------------------------------------------------------

def _build_driver(user_data_dir: Optional[str] = None, headless: bool = False) -> uc.Chrome:
    profile_dir = user_data_dir or _DEFAULT_PROFILE
    Path(profile_dir).mkdir(parents=True, exist_ok=True)

    options = uc.ChromeOptions()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument(f"--user-data-dir={profile_dir}")
    options.add_argument("--profile-directory=Default")
    options.add_argument("--window-size=1280,900")
    options.add_argument(
        "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/150.0.0.0 Safari/537.36"
    )

    driver = uc.Chrome(options=options, headless=headless, version_main=150)
    driver.set_page_load_timeout(REQUEST_TIMEOUT)
    return driver


# ------------------------------------------------------------------------------
# Detecção Inteligente de Bloqueio & Limpeza de Cookies
# ------------------------------------------------------------------------------

def _tem_recaptcha_desafio(driver: uc.Chrome) -> bool:
    try:
        url = driver.current_url.lower()
        if any(b in url for b in ["/cdn-cgi/challenge", "challenge-platform"]):
            return True
    except Exception:
        pass

    try:
        iframes = driver.find_elements(By.TAG_NAME, "iframe")
        for iframe in iframes:
            try:
                src_attr = (iframe.get_attribute("src") or "").lower()
                title_attr = (iframe.get_attribute("title") or "").lower()
                if "challenges.cloudflare.com" in src_attr:
                    return True
                if "recaptcha" in src_attr and ("bframe" in src_attr or "desafio" in title_attr or "challenge" in title_attr):
                    if iframe.is_displayed():
                        return True
            except Exception:
                continue
    except Exception:
        pass

    return False


def _tratar_alertas_nativos(driver: uc.Chrome):
    try:
        alert = driver.switch_to.alert
        logger.info(f"[CFM] Alerta de pop-up do navegador ignorado/fechado: '{alert.text}'")
        alert.accept()
        time.sleep(1.0)
    except Exception:
        pass


def _limpar_cookies_e_recarregar(driver: uc.Chrome, url: str = CFM_URL) -> bool:
    """Estratégia do usuário: ao detectar captcha/bloqueio, exclui cookies, aguarda 1s e recarrega."""
    try:
        logger.info("[CFM] Excluindo cookies e storage local para contornar desafio do Cloudflare...")
        driver.delete_all_cookies()
        try:
            driver.execute_script("window.localStorage.clear(); window.sessionStorage.clear();")
        except Exception:
            pass
        time.sleep(1.0)
        logger.info(f"[CFM] Recarregando página {url} pós-limpeza de cookies...")
        driver.get(url)
        time.sleep(3.0)
        _tratar_alertas_nativos(driver)
        
        forms = driver.find_elements(By.ID, "buscaForm")
        if forms and forms[0].is_displayed() and not _tem_recaptcha_desafio(driver):
            logger.info("[CFM] Sucesso! Formulário liberado após exclusão de cookies e recarga!")
            return True
    except Exception as e:
        logger.warning(f"[CFM] Erro ao limpar cookies e recarregar: {e}")

    return False


def _detectar_captcha(driver: uc.Chrome) -> bool:
    _tratar_alertas_nativos(driver)
    try:
        forms = driver.find_elements(By.ID, "buscaForm")
        cards = driver.find_elements(By.CSS_SELECTOR, ".card-body, .resultado-item")
        if (forms and forms[0].is_displayed()) or len(cards) > 0:
            if not _tem_recaptcha_desafio(driver):
                return False
    except Exception:
        pass

    return _tem_recaptcha_desafio(driver)


def _abrir_com_soft_refresh(driver: uc.Chrome, url: str, max_refreshes: int = 3) -> bool:
    for tentativa in range(1, max_refreshes + 1):
        try:
            logger.info(f"[CFM] [SOFT-REFRESH] Recarregando página {url} (Tentativa {tentativa}/{max_refreshes})...")
            driver.get(url)
            time.sleep(3.5)

            if not _detectar_captcha(driver):
                logger.info(f"[CFM] [SOFT-REFRESH] Formulário #buscaForm liberado com sucesso na tentativa {tentativa}!")
                return True
            
            logger.warning(f"[CFM] Captcha detectado na tentativa {tentativa}. Aplicando estratégia de exclusão de cookies...")
            if _limpar_cookies_e_recarregar(driver, url):
                return True
        except Exception as e:
            logger.warning(f"[CFM] Erro durante soft-refresh tentativa {tentativa}: {e}")

    return False


def _tentar_solver_captcha(driver: uc.Chrome) -> bool:
    api_key = os.getenv("CAPTCHA_SOLVER_API_KEY", "")
    if not api_key:
        return False

    try:
        from twocaptcha import TwoCaptcha  # type: ignore
        solver = TwoCaptcha(api_key)

        try:
            el = driver.find_element(By.CSS_SELECTOR, "[data-sitekey]")
            sitekey = el.get_attribute("data-sitekey")
        except NoSuchElementException:
            return False

        logger.info(f"[CFM] Resolvendo captcha via API 2captcha...")
        result = solver.recaptcha(sitekey=sitekey, url=driver.current_url)
        token = result["code"]
        driver.execute_script(
            f'document.getElementById("g-recaptcha-response").innerHTML = "{token}";'
        )
        logger.info("[CFM] Captcha resolvido via API.")
        return True

    except Exception as e:
        logger.error(f"[CFM] Erro ao resolver captcha via API: {e}")
        return False


def _aguardar_resolucao_manual(driver: uc.Chrome, timeout_s: int = 180) -> bool:
    logger.warning(
        f"[CFM] CAPTCHA DETECTADO — resolva manualmente na janela do Chrome. Aguardando até {timeout_s}s..."
    )
    for i in range(0, timeout_s, 3):
        time.sleep(3)
        _tratar_alertas_nativos(driver)
        if not _detectar_captcha(driver):
            logger.info("[CFM] Captcha resolvido / Formulário liberado! Continuando scraping...")
            return True
        restante = timeout_s - i - 3
        if restante > 0 and restante % 15 == 0:
            logger.info(f"[CFM] Aguardando resolução manual... {restante}s restantes.")
    logger.error("[CFM] Timeout aguardando resolução manual do captcha.")
    return False


# ------------------------------------------------------------------------------
# Preenchimento do formulário específico (#buscaForm)
# ------------------------------------------------------------------------------

def _preencher_formulario(
    driver: uc.Chrome,
    uf: str,
    nome: Optional[str],
    registro: Optional[str],
) -> bool:
    wait = WebDriverWait(driver, REQUEST_TIMEOUT)

    try:
        _tratar_alertas_nativos(driver)

        logger.info("[CFM] Aguardando formulário #buscaForm...")
        wait.until(EC.presence_of_element_located((By.ID, "buscaForm")))
        time.sleep(1.5)

        form = driver.find_element(By.ID, "buscaForm")

        # -- UF --
        try:
            uf_el = form.find_element(By.ID, "uf")
            Select(uf_el).select_by_value(uf.upper())
            logger.info(f"[CFM] UF selecionada: {uf.upper()}")
        except Exception as e:
            logger.error(f"[CFM] Erro ao selecionar UF: {e}")

        # -- Nome --
        if nome:
            try:
                nome_el = form.find_element(By.ID, "nome")
                nome_el.clear()
                nome_el.send_keys(nome)
                logger.info(f"[CFM] Nome preenchido: {nome}")
            except Exception as e:
                logger.warning(f"[CFM] Erro ao preencher nome: {e}")

        # -- CRM --
        if registro:
            try:
                crm_el = form.find_element(By.ID, "crm")
                crm_el.clear()
                crm_el.send_keys(str(registro))
                logger.info(f"[CFM] CRM preenchido: {registro}")
            except Exception as e:
                logger.warning(f"[CFM] Erro ao preencher CRM: {e}")

        # -- Submit --
        btn = form.find_element(By.CSS_SELECTOR, "button.btnPesquisar, button[type='submit']")
        driver.execute_script("arguments[0].click();", btn)
        logger.info("[CFM] Botão .btnPesquisar clicado.")

        try:
            wait_long = WebDriverWait(driver, 10)
            wait_long.until(lambda d: len(d.find_elements(By.CSS_SELECTOR, ".card-body, .resultado-item")) > 0)
        except (TimeoutException, UnexpectedAlertPresentException):
            _tratar_alertas_nativos(driver)
            logger.warning("[CFM] Resultados não renderizaram pós-clique. Aguardando resolução do desafio reCAPTCHA...")
            _aguardar_resolucao_manual(driver, timeout_s=180)
            _tratar_alertas_nativos(driver)
            try:
                form_again = driver.find_element(By.ID, "buscaForm")
                uf_el2 = form_again.find_element(By.ID, "uf")
                Select(uf_el2).select_by_value(uf.upper())
                btn2 = form_again.find_element(By.CSS_SELECTOR, "button.btnPesquisar, button[type='submit']")
                driver.execute_script("arguments[0].click();", btn2)
            except Exception:
                pass
            wait.until(lambda d: len(d.find_elements(By.CSS_SELECTOR, ".card-body, .resultado-item")) > 0)

        time.sleep(3.0)
        logger.info("[CFM] Resultados da busca inicial renderizados com sucesso no DOM.")
        return True

    except Exception as e:
        logger.error(f"[CFM] Erro ao preencher formulário #buscaForm: {e}")
        return False


# ------------------------------------------------------------------------------
# Leitura do Total de Páginas e Extração dos Médicos
# ------------------------------------------------------------------------------

def _obter_total_paginas_portal(driver: uc.Chrome) -> int:
    try:
        elements = driver.find_elements(By.CSS_SELECTOR, ".paginationjs-last, .paginationjs-page[data-num]")
        nums = []
        for el in elements:
            val = el.get_attribute("data-num") or el.text.strip()
            if val and val.isdigit():
                nums.append(int(val))
        if nums:
            max_p = max(nums)
            logger.info(f"[CFM] Total de páginas identificadas no portal: {max_p}")
            return max_p
    except Exception as e:
        logger.debug(f"[CFM] Não foi possível ler total de páginas: {e}")
    
    return 1


def _extrair_medicos_da_pagina(driver: uc.Chrome) -> list:
    medicos = []

    try:
        wait = WebDriverWait(driver, REQUEST_TIMEOUT)
        wait.until(lambda d: (
            len(d.find_elements(By.CSS_SELECTOR, ".card-body, .resultado-item")) > 0
            or "nenhum" in d.page_source.lower()
            or "não encontrado" in d.page_source.lower()
        ))
    except TimeoutException:
        logger.warning("[CFM] Timeout aguardando lista de médicos.")

    time.sleep(1.8)

    try:
        soup = BeautifulSoup(driver.page_source, "html.parser")
        cards = soup.select(".card-body")

        if cards:
            for card in cards:
                medico = _parse_card_bs4(card)
                if medico:
                    medicos.append(medico)
    except Exception as e:
        logger.error(f"[CFM] Erro ao extrair página via BS4: {e}")

    return medicos


def _parse_card_bs4(card_soup) -> Optional[dict]:
    try:
        h4 = card_soup.find("h4")
        if not h4:
            return None
        nome = h4.text.strip().upper()
        if not nome:
            return None

        crm = ""
        uf_val = ""
        situacao = "Regular"
        especialidades = []

        rows = card_soup.select(".row")
        for r in rows:
            text_r = r.text.strip()

            if "CRM:" in text_r:
                m_crm = re.search(r"CRM:\s*(\d+)[/-]?([A-Z]{2})?", text_r, re.IGNORECASE)
                if m_crm:
                    crm = m_crm.group(1)
                    if m_crm.group(2):
                        uf_val = m_crm.group(2).upper()

            if "Situação:" in text_r or "Situacao:" in text_r:
                b_sit = r.find("b", text=re.compile(r"Situa[çc][ãa]o:", re.I))
                if b_sit and b_sit.parent:
                    sit_full = b_sit.parent.text.replace("Situação:", "").replace("Situacao:", "").strip()
                    sit_clean = sit_full.split("\n")[0].split("(")[0].strip()
                    if sit_clean:
                        situacao = sit_clean

            if "Especialidade" in text_r or "Área" in text_r or "Area" in text_r:
                span_esp = r.find("span")
                if span_esp:
                    esp_text = span_esp.text.strip()
                    if "sem especialidade" not in esp_text.lower():
                        partes = re.split(r"[;&,]", esp_text)
                        for p in partes:
                            p_clean = re.sub(r"-\s*RQE.*$", "", p, flags=re.IGNORECASE).strip()
                            p_clean = re.sub(r"\(.*?\)", "", p_clean).strip().upper()
                            if p_clean and len(p_clean) > 2 and "SEM ESPECIALIDADE" not in p_clean:
                                especialidades.append(p_clean)

        crm_limpo = re.sub(r"\D", "", crm)
        if not crm_limpo:
            return None

        return {
            "nome": nome,
            "crm": crm_limpo,
            "uf": uf_val,
            "situacao": situacao,
            "especialidades": especialidades,
            "atualizado_em": None,
        }
    except Exception as e:
        logger.debug(f"[CFM] Erro ao parsear card BS4: {e}")
        return None


# ------------------------------------------------------------------------------
# Paginação Nativa com Salto de Lote Re-Inicializado e Resiliente
# ------------------------------------------------------------------------------

def _ir_para_pagina_especifica(driver: uc.Chrome, pagina_alvo: int, total_paginas: int = 4105) -> bool:
    try:
        _tratar_alertas_nativos(driver)
        primeiro_nome_ant = ""
        try:
            cards_ant = driver.find_elements(By.CSS_SELECTOR, ".card-body h4")
            if cards_ant:
                primeiro_nome_ant = cards_ant[0].text.strip()
        except Exception:
            pass

        # Executar re-init do #paginacao apontando pageNumber para a pagina_alvo
        driver.execute_script("""
            var pageTarget = arguments[0];
            var totalPages = arguments[1] || 4105;
            try {
                if (typeof jQuery !== 'undefined' && jQuery('#paginacao').length) {
                    var $p = jQuery('#paginacao');
                    var arr = [];
                    for (var i = 1; i <= totalPages; i++) arr.push(i);
                    $p.pagination({
                        dataSource: arr,
                        pageSize: 10,
                        pageNumber: pageTarget,
                        callback: function(data, pagination) {
                            if (typeof getInfo === 'function') {
                                getInfo(pagination.pageNumber, false);
                            }
                        }
                    });
                    return 'REINIT_SUCCESS';
                }
                return false;
            } catch(e) {
                return false;
            }
        """, pagina_alvo, total_paginas)

        time.sleep(3.5)
        _tratar_alertas_nativos(driver)

        if _tem_recaptcha_desafio(driver):
            logger.warning(f"[CFM] Captcha detectado após salto para página {pagina_alvo}. Aguardando resolução manual...")
            _aguardar_resolucao_manual(driver, timeout_s=180)
            _tratar_alertas_nativos(driver)

        # Se o primeiro médico ainda não mudou, forçar via pagination('go', pagina_alvo)
        try:
            cards_now = driver.find_elements(By.CSS_SELECTOR, ".card-body h4")
            if cards_now and cards_now[0].text.strip() == primeiro_nome_ant:
                driver.execute_script("jQuery('#paginacao').pagination('go', arguments[0]);", pagina_alvo)
                time.sleep(3.0)
        except Exception:
            pass

        _tratar_alertas_nativos(driver)
        logger.info(f"[CFM] Navegação para a página {pagina_alvo} efetuada.")
        return True
    except Exception as e:
        logger.error(f"[CFM] Erro ao navegar para a página {pagina_alvo}: {e}")
        return False


def _ir_para_proxima_pagina(driver: uc.Chrome, pagina_atual: int, total_paginas: int = 4105) -> bool:
    pagina_alvo = pagina_atual + 1
    try:
        _tratar_alertas_nativos(driver)
        driver.execute_script("jQuery('#paginacao').pagination('go', arguments[0]);", pagina_alvo)
        time.sleep(2.5)
        _tratar_alertas_nativos(driver)
        return True
    except Exception:
        return _ir_para_pagina_especifica(driver, pagina_alvo, total_paginas)


# ------------------------------------------------------------------------------
# Função Principal Pública por Lotes (máximo 49 páginas por chamada)
# ------------------------------------------------------------------------------

def consultar_crm(
    uf: str,
    nome: Optional[str] = None,
    registro: Optional[str] = None,
    pagina_inicial: int = 1,
    max_paginas: int = 49,
    user_data_dir: Optional[str] = None,
) -> dict:
    profile = user_data_dir or os.getenv("CFM_CHROME_PROFILE", "")
    headless_env = os.getenv("CFM_HEADLESS", "false").lower()
    headless = headless_env in ("1", "true", "yes")

    limite_lote = min(max_paginas, 49)

    logger.info(
        f"[CFM] Iniciando consulta | UF={uf} | nome={nome} | registro={registro} | "
        f"pagina_inicial={pagina_inicial} | max_paginas={limite_lote}"
    )

    driver = None
    todos_medicos = []
    paginas_processadas = 0
    total_paginas_portal = 1
    pagina_atual = pagina_inicial

    try:
        driver = _build_driver(user_data_dir=profile or None, headless=headless)

        if not _abrir_com_soft_refresh(driver, CFM_URL, max_refreshes=3):
            resolvido = _tentar_solver_captcha(driver)
            if not resolvido and not headless:
                resolvido = _aguardar_resolucao_manual(driver, timeout_s=180)
            if not resolvido:
                return {
                    "status": "PORTAL_BLOCKED",
                    "uf": uf,
                    "total": 0,
                    "medicos": [],
                    "paginas": 0,
                    "erro": "Captcha não resolvido.",
                }

        ok = _preencher_formulario(driver, uf, nome, registro)
        if not ok:
            return {
                "status": "PARSE_FAIL",
                "uf": uf,
                "total": 0,
                "medicos": [],
                "paginas": 0,
                "erro": "Não foi possível preencher o formulário #buscaForm.",
            }

        total_paginas_portal = _obter_total_paginas_portal(driver)

        # Se pagina_inicial > 1, saltar diretamente para a página inicial do lote após a busca ter retornado
        if pagina_inicial > 1:
            time.sleep(2.5)
            _ir_para_pagina_especifica(driver, pagina_inicial, total_paginas_portal)
            time.sleep(2.0)

        crms_vistos: set = set()

        while paginas_processadas < limite_lote:
            logger.info(f"[CFM] Extraindo página {pagina_atual} (Lote {paginas_processadas + 1}/{limite_lote})...")
            
            try:
                medicos_pagina = _extrair_medicos_da_pagina(driver)
            except Exception as err_page:
                logger.error(f"[CFM] Erro ao extrair página {pagina_atual}: {err_page}. Encerrando lote para salvar progresso.")
                break

            paginas_processadas += 1

            novos = []
            for m in medicos_pagina:
                if not m["uf"]:
                    m["uf"] = uf.upper()
                chave = (m["crm"], m["uf"])
                if chave not in crms_vistos:
                    crms_vistos.add(chave)
                    novos.append(m)

            todos_medicos.extend(novos)
            logger.info(f"[CFM] Página {pagina_atual}: {len(medicos_pagina)} médicos extraídos ({len(novos)} novos).")

            if not medicos_pagina:
                logger.warning(f"[CFM] Nenhum médico retornado na página {pagina_atual}. Encerrando lote.")
                break

            if paginas_processadas >= limite_lote:
                logger.info(f"[CFM] Limite de {limite_lote} páginas atingido para esta sessão do ChromeDriver.")
                break

            try:
                if not _ir_para_proxima_pagina(driver, pagina_atual, total_paginas_portal):
                    logger.warning(f"[CFM] Não foi possível avançar para a próxima página após a página {pagina_atual}.")
                    break
            except Exception as err_nav:
                logger.error(f"[CFM] Erro na navegação pós-página {pagina_atual}: {err_nav}. Encerrando lote.")
                break

            pagina_atual += 1

    except Exception as e:
        logger.error(f"[CFM] Erro inesperado no lote: {e}", exc_info=True)
    finally:
        if driver:
            try:
                driver.quit()
            except Exception:
                pass

    proxima_pagina = pagina_atual + 1
    tem_mais = proxima_pagina <= total_paginas_portal and len(todos_medicos) > 0

    return {
        "status": "success" if todos_medicos else "not_found",
        "uf": uf,
        "total": len(todos_medicos),
        "medicos": todos_medicos,
        "paginas_processadas": paginas_processadas,
        "pagina_inicial": pagina_inicial,
        "pagina_final": pagina_atual,
        "proxima_pagina": proxima_pagina if tem_mais else None,
        "total_paginas_portal": total_paginas_portal,
        "tem_mais_paginas": tem_mais,
    }
