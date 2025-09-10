# agent.py
from typing import List, Dict, Optional
from storage import SessionLocal, Preco
from scrapers import SCRAPERS
from whatsapp_ingest import parse_whatsapp_txt
from sqlalchemy.exc import IntegrityError
from datetime import datetime


class Agent:
def __init__(self, cep_area: Optional[str] = None):
self.cep_area = cep_area


def fetch_from_web(self, queries: List[str]) -> List[Dict]:
rows = []
for q in queries:
for s in SCRAPERS:
try:
results = s.search(q, cep=self.cep_area)
for r in results:
r['cep_area'] = self.cep_area
rows.append(r)
except Exception as e:
# log simples
print(f"[WARN] {s.name} falhou em '{q}': {e}")
return rows


def ingest_whatsapp(self, txt_content: str) -> List[Dict]:
rows = parse_whatsapp_txt(txt_content)
for r in rows:
r['cep_area'] = self.cep_area
return rows


def persist(self, rows: List[Dict]):
if not rows:
return 0
db = SessionLocal()
saved = 0
try:
for r in rows:
rec = Preco(
item=r.get('item'), marca=r.get('marca'), mercado=r.get('mercado'),
preco=r.get('preco'), unidade=r.get('unidade'), url=r.get('url'),
origem=r.get('origem', 'web'), cep_area=r.get('cep_area'),
timestamp=datetime.utcnow()
)
db.add(rec)
try:
db.commit()
saved += 1
except IntegrityError:
db.rollback()
finally:
db.close()
return saved
