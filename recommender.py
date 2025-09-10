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
