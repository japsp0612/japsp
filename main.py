import streamlit as st
import pandas as pd
import requests
from datetime import datetime

# função para carregar dados da Brapi
@st.cache_data
def carregar_dados(empresas):
    df_final = pd.DataFrame()
    for empresa in empresas:
        url = f"https://brapi.dev/api/quote/{empresa}?range=5y&interval=1d&fundamental=false"
        r = requests.get(url)
        if r.status_code == 200:
            dados_json = r.json()
            if "results" in dados_json and len(dados_json["results"]) > 0:
                historico = dados_json["results"][0]["historicalDataPrice"]
                df = pd.DataFrame(historico)
                df["date"] = pd.to_datetime(df["date"], unit="s")  # converte timestamp
                df = df.set_index("date")
                df = df[["close"]].rename(columns={"close": empresa})
                if df_final.empty:
                    df_final = df
                else:
                    df_final = df_final.join(df, how="outer")
    return df_final

# lista de ações da B3
acoes = ["ITUB4", "PETR4", "MGLU3", "VALE3", "ABEV3", "GGBR4"]

# carrega os dados
dados = carregar_dados(acoes)

# título
st.write("""
# 📊 App Preços de Ações
O gráfico abaixo mostra a evolução do preço das ações ao longo do tempo.
""")

if not dados.empty:
    # sidebar - filtros
    st.sidebar.header("Filtros")

    lista_acoes = st.sidebar.multiselect(
        "Escolha as ações para visualizar",
        options=dados.columns,
        default=dados.columns[:2]
    )

    if lista_acoes:
        dados = dados[lista_acoes]

    # filtro de datas
    data_inicial = dados.index.min().date()
    data_final = dados.index.max().date()

    intervalo_de_datas = st.sidebar.date_input(
        "Selecione o período",
        value=(data_inicial, data_final),
        min_value=data_inicial,
        max_value=data_final
    )

    if isinstance(intervalo_de_datas, tuple) and len(intervalo_de_datas) == 2:
        dados = dados.loc[str(intervalo_de_datas[0]):str(intervalo_de_datas[1])]

    # gráfico
    st.line_chart(dados)
else:
    st.error("❌ Não foi possível carregar os dados da Brapi.")
