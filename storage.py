# App de Recomendações de Preços (Streamlit)

Abaixo está um MVP completo para você rodar **hoje** com Streamlit. Ele cobre:

* Lista de desejos do usuário (CRUD em UI)
* Busca de preços em sites (scrapers simples e extensíveis)
* Importação de mensagens de **WhatsApp** (via exportação de chat `.txt`) para extrair ofertas
* Banco de dados local **SQLite** para histórico
* Recomendação do melhor mercado por item dentro do raio/área
* Botão **Atualizar agora** e esqueleto de **agendamento** 12:00 e 20:00 (worker dedicado)

> Observações legais/boas práticas: respeite termos de uso de cada site, `robots.txt` e limite de requisições. Para WhatsApp, este MVP usa **arquivo exportado** de chat (com consentimento do grupo). Para automação de WhatsApp em produção, use **WhatsApp Cloud API** (webhook) do Meta.

---

## Estrutura de pastas

```
precos_app/
├─ app.py                # Streamlit UI + chamadas do agente
├─ agent.py              # Orquestrador da coleta
├─ scrapers.py           # Scrapers por fonte/site
├─ whatsapp_ingest.py    # Parser de chats exportados
├─ storage.py            # SQLite + modelos
├─ recommender.py        # Lógica de ranking e melhores mercados
├─ scheduler_worker.py   # Tarefas 12:00 e 20:00 (APScheduler)
├─ requirements.txt
└─ .env                  # Configs (tokens, etc.)
```

---

## requirements.txt

```txt
streamlit==1.37.1
pandas==2.2.2
requests==2.32.3
beautifulsoup4==4.12.3
lxml==5.2.2
python-dotenv==1.0.1
SQLAlchemy==2.0.34
APScheduler==3.10.4
pytz==2024.1
```

---

## storage.py (SQLite + ORM simples)

```python
# storage.py
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, UniqueConstraint
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime
import os

DB_URL = os.environ.get("PRECOS_DB_URL", "sqlite:///precos.db")
engine = create_engine(DB_URL, echo=False, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()

class ItemDesejo(Base):
    __tablename__ = "itens_desejo"
    id = Column(Integer, primary_key=True)
    nome = Column(String, index=True)
    marca = Column(String, nullable=True)
    categoria = Column(String, nullable=True)

class Preco(Base):
    __tablename__ = "precos"
    id = Column(Integer, primary_key=True)
    item = Column(String, index=True)
    marca = Column(String, nullable=True)
    mercado = Column(String, index=True)
    preco = Column(Float)
    unidade = Column(String, default="un")
    url = Column(String, nullable=True)
    origem = Column(String, default="web")  # web | whatsapp
    cep_area = Column(String, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    __table_args__ = (
        UniqueConstraint('item','marca','mercado','timestamp','origem', name='uq_preco_snapshot'),
    )

def init_db():
    Base.metadata.create_all(engine)
```

---

## scrapers.py (exemplos extensíveis)

```python
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
    base_url = "https://example.com/busca?q="  # troque pelo site real, respeitando ToS
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
```

> Dica: crie um scraper por site, com CSS selectors confiáveis. Se o site tiver API pública, prefira.

---

## whatsapp\_ingest.py (parser de chat exportado)

```python
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
```

---

## recommender.py (ranking de melhores mercados)

```python
# recommender.py
import pandas as pd
from typing import List, Dict

def best_prices(df: pd.DataFrame, wishlist: List[Dict]):
    """ Retorna melhor preço por item e um ranking de mercados por lista. """
    if df.empty:
        return df, pd.DataFrame()

    # normalizar nomes p/ matching simples
    df = df.copy()
    df['item_norm'] = df['item'].str.lower()

    wanted = []
    for w in wishlist:
        wanted.append({
            'item': w['nome'],
            'marca': w.get('marca'),
            'key': (w['nome'].lower()),
        })
    wanted_df = pd.DataFrame(wanted)

    # melhor preço por item (aprox por contains)
    best = []
    for _, w in wanted_df.iterrows():
        subset = df[df['item_norm'].str.contains(w['key'], na=False)]
        if subset.empty:
            continue
        best_row = subset.sort_values('preco', ascending=True).iloc[0]
        best.append(best_row)
    best_df = pd.DataFrame(best)

    # ranking de mercados por soma mínima
    if not best_df.empty:
        ranking = best_df.groupby('mercado', as_index=False)['preco'].sum().sort_values('preco')
    else:
        ranking = pd.DataFrame(columns=['mercado','preco'])

    return best_df.drop(columns=['item_norm']) if 'item_norm' in best_df else best_df, ranking
```

---

## agent.py (orquestrador)

```python
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
```

---

## app.py (Streamlit UI)

```python
# app.py
import streamlit as st
import pandas as pd
from storage import init_db, SessionLocal, ItemDesejo, Preco
from agent import Agent
from recommender import best_prices
from datetime import datetime
from io import StringIO

st.set_page_config(page_title="Recomenda Preços", layout="wide")
init_db()

st.title("🛒 IA Recomenda Preços – MVP")
colA, colB = st.columns([2,1])

with colB:
    st.subheader("Configurações")
    cep = st.text_input("CEP/Área (opcional)", value="")
    if 'wishlist' not in st.session_state:
        st.session_state['wishlist'] = []

    with st.form("frm_add"):
        st.markdown("**Adicionar item à lista**")
        nome = st.text_input("Item (ex: Café Melitta 500g)")
        marca = st.text_input("Marca (opcional)")
        categoria = st.text_input("Categoria (opcional)")
        add = st.form_submit_button("Adicionar")
        if add and nome:
            st.session_state['wishlist'].append({'nome': nome, 'marca': marca or None, 'categoria': categoria or None})

    if st.session_state['wishlist']:
        st.markdown("**Sua lista de desejos**")
        dfw = pd.DataFrame(st.session_state['wishlist'])
        st.dataframe(dfw, use_container_width=True)
        if st.button("Limpar lista"):
            st.session_state['wishlist'] = []

    st.divider()
    st.subheader("Importar ofertas de WhatsApp")
    up = st.file_uploader("Envie o .txt exportado do grupo", type=['txt'])
    ingest_whatsapp = st.button("Ingerir arquivo de ofertas")

with colA:
    st.subheader("Coletar preços")
    run_now = st.button("🔄 Atualizar preços agora")

    db = SessionLocal()
    agent = Agent(cep_area=cep or None)

    if ingest_whatsapp and up is not None:
        content = up.read().decode('utf-8', errors='ignore')
        rows = agent.ingest_whatsapp(content)
        saved = agent.persist(rows)
        st.success(f"{saved} ofertas do WhatsApp salvas.")

    if run_now and st.session_state['wishlist']:
        queries = [w['nome'] for w in st.session_state['wishlist']]
        rows = agent.fetch_from_web(queries)
        saved = agent.persist(rows)
        st.success(f"{saved} preços coletados da web.")

    st.markdown("### Últimos preços")
    q = db.query(Preco).order_by(Preco.timestamp.desc()).limit(500).all()
    df = pd.DataFrame([{
        'item': r.item, 'marca': r.marca, 'mercado': r.mercado, 'preco': r.preco,
        'unidade': r.unidade, 'url': r.url, 'origem': r.origem,
        'cep_area': r.cep_area, 'timestamp': r.timestamp
    } for r in q])
    if not df.empty:
        st.dataframe(df, use_container_width=True)

        st.markdown("### Recomendações (melhor preço por item)")
        best_df, ranking = best_prices(df, st.session_state['wishlist'])
        if not best_df.empty:
            st.dataframe(best_df[['item','mercado','preco','origem','url']].reset_index(drop=True), use_container_width=True)
            st.markdown("### Ranking de mercados para sua lista")
            st.dataframe(ranking.rename(columns={'preco':'soma_da_lista'}), use_container_width=True)
        else:
            st.info("Ainda não há correspondências para os itens da lista.")
    else:
        st.info("Nenhum preço coletado ainda. Use 'Atualizar preços agora' ou importe WhatsApp.")

    db.close()
```

---

## scheduler\_worker.py (agendador 12:00 e 20:00)

> Rodar **separado** do Streamlit. Ideal em um serviço/VM ou container.

```python
# scheduler_worker.py
from apscheduler.schedulers.blocking import BlockingScheduler
from datetime import datetime
from agent import Agent
from storage import SessionLocal, Preco, init_db
import pandas as pd
import os

# Configurações
AREA_CEP = os.environ.get('AREA_CEP', '')
WISHLIST = os.environ.get('WISHLIST', 'Café Melitta 500g; Arroz 5kg; Leite 1L').split(';')
WISHLIST = [w.strip() for w in WISHLIST if w.strip()]

init_db()
sched = BlockingScheduler(timezone='America/Sao_Paulo')

@sched.scheduled_job('cron', hour='12,20', minute=0)
def job_coletar():
    print(f"[job] coleta {datetime.now()}")
    agent = Agent(cep_area=AREA_CEP or None)
    rows = agent.fetch_from_web(WISHLIST)
    saved = agent.persist(rows)
    print(f"[job] salvos: {saved}")

if __name__ == '__main__':
    print("Scheduler iniciado (12:00 e 20:00 BRT)…")
    sched.start()
```

---

## .env (exemplo)

```env
# PRECOS_DB_URL=sqlite:///precos.db
# Tokens de APIs (se algum site tiver API)
```

---

## Como rodar

1. **Criar venv e instalar deps**

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

2. **Executar o app**

```bash
streamlit run app.py
```

3. **Agendador (opcional, em paralelo)**

```bash
python scheduler_worker.py
```

> Em produção, use **dois processos**: Streamlit (UI) e o worker (APScheduler). Alternativas: Cloud Run + Cloud Scheduler (HTTP), Railway/Cron, GitHub Actions, etc.

---

## Próximos passos (rápidos)

* **Geolocalização real**: filtrar mercados pela distância (Google Places API, OpenStreetMap/Nominatim + Haversine)
* **Normalização de itens** (NLP) para casar variações de nome
* **Alertas**: enviar e-mail/WhatsApp (via **Cloud API**) quando a soma da lista cair abaixo de um limiar
* **Cache & backoff** nos scrapers para evitar bloqueios
* **Testes unitários** dos scrapers

---

## Notas sobre WhatsApp Cloud API (produção)

* Configure um endpoint webhook que receba mensagens; ao detectar padrões de oferta (preço + item + mercado), salve no mesmo banco.
* Mapeie grupos/lojas com IDs e aplique heurísticas de confiança.

---

## Onde estender scrapers

* Edite `scrapers.py` e adicione classes novas por site com seletores específicos.
* Se existir API oficial de ofertas do mercado, implemente o client e **prefira API** a HTML.

---

Pronto! Isso já te dá um caminho funcional para iterar: wishlist → coleta web/WhatsApp → ranking → histórico → agendamento 12:00/20:00.
