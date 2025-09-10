# app.py


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
