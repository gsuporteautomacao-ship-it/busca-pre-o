# whatsapp_ingest.py
import re
from typing import List, Dict


# Espera linhas como: "12/09/2025, 09:14 - Fulano: Café Melitta 500g R$ 16,90 no Mercado XPTO"
LINE_RE = re.compile(r"^(\d{1,2}/\d{1,2}/\d{2,4}),.*?:\s+(.*)$")
PRICE_RE = re.compile(r"(R\$\s*\d+[\.,]\d{2})")


BRL = lambda t: float(t.replace('R$','').replace(' ','').replace('.','').replace(',','.'))


def parse_whatsapp_txt(content: str) -> List[Dict]:
rows = []
for line in content.splitlines():
m = LINE_RE.match(line)
if not m:
continue
text = m.group(2)
pm = PRICE_RE.search(text)
if not pm:
continue
price = BRL(pm.group(1))
# heurística simples: split por " no " para achar mercado
parts = text.split(" no ")
mercado = parts[-1].strip() if len(parts) > 1 else "Grupo WhatsApp"
# item: remove preço
item = PRICE_RE.sub('', text).strip()
rows.append({
'item': item,
'marca': None,
'mercado': mercado,
'preco': price,
'unidade': 'un',
'url': None,
'origem': 'whatsapp',
})
return rows
