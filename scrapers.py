# scrapers.py
import re
import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Optional


Headers = {"User-Agent": "Mozilla/5.0 (compatible; PrecosBot/1.0)"}


class ScraperBase:
name = "base"
def search(self, query: str, cep: Optional[str] = None) -> List[Dict]:
raise NotImplementedError


class ExemploMercado1(ScraperBase):
name = "Mercado Exemplo 1"
base_url = "https://example.com/busca?q=" # troque pelo site real, respeitando ToS
def search(self, query: str, cep: Optional[str] = None) -> List[Dict]:
url = self.base_url + requests.utils.quote(query)
r = requests.get(url, headers=Headers, timeout=20)
r.raise_for_status()
soup = BeautifulSoup(r.text, 'lxml')
# Exemplo: buscar cards .product-card
results = []
for card in soup.select('.product-card'):
name = card.select_one('.title').get_text(strip=True)
price_txt = card.select_one('.price').get_text(strip=True)
m = re.search(r"([0-9]+,[0-9]{2})", price_txt)
if not m:
continue
price = float(m.group(1).replace(',', '.'))
url_item = card.select_one('a')
results.append({
'item': name,
'marca': None,
'mercado': self.name,
'preco': price,
'unidade': 'un',
'url': url_item['href'] if url_item else None,
'origem': 'web',
})
return results


class ExemploMercado2(ScraperBase):
name = "Mercado Exemplo 2"
search_url = "https://example2.com/search?q="
def search(self, query: str, cep: Optional[str] = None) -> List[Dict]:
# Estrutura similar, adaptando seletores
return []


SCRAPERS = [ExemploMercado1(), ExemploMercado2()]
