"""patch_captcha_blocks.py — corrige os dois blocos de verificacao de captcha em consultar_crm."""
import re

TARGET = r"c:\dev\Agenda_hub_MultiConv\backend_worker\scraper\cfm_scraper.py"

with open(TARGET, encoding="utf-8") as f:
    content = f.read()

# Usar regex para substituir ambos os blocos de captcha dentro de consultar_crm
# O padrao corresponde ao bloco original (com ou sem acentos, pois o arquivo pode ter sido salvo de formas diferentes)

PATTERN = re.compile(
    r'# .*?Verificar captcha.*?\n'
    r'        if _detectar_captcha\(driver\):\n'
    r'            logger\.warning\(.*?\)\n'
    r'            resolvido = _tentar_solver_captcha\(driver\)\n'
    r'            if not resolvido:\n'
    r'                return \{\n'
    r'.*?"status": "PORTAL_BLOCKED",\n'
    r'.*?"uf": uf,\n'
    r'.*?"total": 0,\n'
    r'.*?"medicos": \[\],\n'
    r'.*?"paginas": 0,\n'
    r'.*?"erro": ".*?",\n'
    r'                \}',
    re.DOTALL,
)

REPLACEMENT = """# Verificar captcha (so bloqueia challenge real, nao reCAPTCHA invisible)
        if _detectar_captcha(driver):
            logger.warning("[CFM] Captcha bloqueante detectado.")
            resolvido = _tentar_solver_captcha(driver)
            if not resolvido and not headless:
                resolvido = _aguardar_resolucao_manual(driver, timeout_s=90)
            if not resolvido:
                return {
                    "status": "PORTAL_BLOCKED",
                    "uf": uf,
                    "total": 0,
                    "medicos": [],
                    "paginas": 0,
                    "erro": "Captcha nao resolvido. Resolva no browser ou configure CAPTCHA_SOLVER_API_KEY.",
                }"""

matches = PATTERN.findall(content)
count = len(matches)
print(f"Encontrados {count} blocos de captcha para substituir.")

new_content = PATTERN.sub(REPLACEMENT, content)

if new_content == content:
    print("AVISO: nenhuma substituicao realizada. Verificar regex.")
else:
    with open(TARGET, "w", encoding="utf-8") as f:
        f.write(new_content)
    print(f"OK: {count} blocos substituidos. Arquivo salvo.")
    print(f"Total linhas: {len(new_content.splitlines())}")
