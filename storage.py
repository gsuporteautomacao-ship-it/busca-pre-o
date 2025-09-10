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
origem = Column(String, default="web") # web | whatsapp
cep_area = Column(String, nullable=True)
timestamp = Column(DateTime, default=datetime.utcnow)
__table_args__ = (
UniqueConstraint('item','marca','mercado','timestamp','origem', name='uq_preco_snapshot'),
)


def init_db():
Base.metadata.create_all(engine)
