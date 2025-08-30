# importa bibliotecas
import streamlit as st
import pandas as pd
import yfinance as yf

# função para carregar dados
@st.cache_data
def carregar_dados(empresas):
    texto_tickers = " ".join(empresas)  # junta tickers separados por espaço
    dados_acao = yf.Tickers(texto_tickers)
    cotacoes_acao = dados_acao.history(
        period="1d",
        start="2010-01-01",
        end="2025-07-01"
    )
    if cotacoes_acao.empty:
        return pd.DataFrame()
    cotacoes_acao = cotacoes_acao["Close"]  # pega apenas preços de fechamento
    return cotacoes_acao

# lista de ações
acoes = ["ITUB4.SA", "PETR4.SA", "MGLU3.SA", "VALE3.SA", "ABEV3.SA", "GGBR4.SA"]

# carrega os dados
dados = carregar_dados(acoes)

# título e descrição
st.write("""
# 📈 App Preços de Ações  
O gráfico abaixo mostra a evolução do preço das ações ao longo do tempo.
""")

# sidebar - filtros
st.sidebar.header("Filtros")

if not dados.empty:
    # filtro de ações
    lista_acoes = st.sidebar.multiselect(
        "Escolha as ações para visualizar",
        options=dados.columns,
        default=dados.columns[:2]  # seleciona 2 por padrão
    )

    if lista_acoes:
        dados = dados[lista_acoes]
        # se só tiver 1 ação, renomeia a coluna
        if len(lista_acoes) == 1:
            acao_unica = lista_acoes[0]
            dados = dados.rename(columns={acao_unica: "Close"})

    # garante que ainda tem dados
    if not dados.empty:
        data_inicial = dados.index.min().date()
        data_final = dados.index.max().date()

        intervalo_de_datas = st.sidebar.date_input(
            "Selecione o período",
            value=(data_inicial, data_final),
            min_value=data_inicial,
            max_value=data_final
        )

        # garante que sempre seja tupla de duas datas
        if isinstance(intervalo_de_datas, tuple) and len(intervalo_de_datas) == 2:
            dados = dados.loc[str(intervalo_de_datas[0]):str(intervalo_de_datas[1])]

        # gráfico
        st.line_chart(dados)
    else:
        st.warning("⚠️ Nenhum dado disponível para o período selecionado.")
else:
    st.error("❌ Não foi possível carregar os dados das ações.")
