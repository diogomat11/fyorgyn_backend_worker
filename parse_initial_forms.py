"""
parse_initial_forms.py — Analisa formulários e seletores em initial_page.html
"""
from bs4 import BeautifulSoup

soup = BeautifulSoup(open("initial_page.html", encoding="utf-8").read(), "html.parser")

print("=" * 60)
print("FORMULÁRIOS DA PÁGINA INICIAL CFM")
print("=" * 60)

forms = soup.find_all("form")
print(f"Total de formulários: {len(forms)}")

for i, form in enumerate(forms, 1):
    f_id = form.get("id")
    f_cls = form.get("class")
    f_act = form.get("action")
    f_meth = form.get("method")
    print(f"\n--- FORM #{i} ---")
    print(f"id     : {f_id}")
    print(f"class  : {f_cls}")
    print(f"action : {f_act}")
    print(f"method : {f_meth}")

    elements = form.find_all(["input", "select", "button", "textarea"])
    for el in elements:
        print(f"  <{el.name}> id='{el.get('id')}' name='{el.get('name')}' type='{el.get('type')}' placeholder='{el.get('placeholder')}' class='{el.get('class')}'")
        if el.name == "select":
            opts = [f"{o.get('value')}:{o.text.strip()}" for o in el.find_all("option")[:5]]
            print(f"    [Sample Options]: {opts}")

print("\n" + "=" * 60)
print("OUTROS INPUTS E SELECTS FORA DE FORMS:")
print("=" * 60)
orphan_inputs = [el for el in soup.find_all(["input", "select", "button"]) if not el.find_parent("form")]
for el in orphan_inputs[:15]:
    print(f"  <{el.name}> id='{el.get('id')}' name='{el.get('name')}' type='{el.get('type')}' placeholder='{el.get('placeholder')}' class='{el.get('class')}'")
