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
