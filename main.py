#importa biblioteca
import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import timedelta
@st.cache_data
def carregar_dados(empresas):#definindo uma classe
    texto_tickers = " ".join(empresas) #espaço entre moedas
    dados_acao = yf.Tickers(texto_tickers)
    cotacoes_acao = dados_acao.history(period="1d", start="2010-01-01", end="2025-07-01")#periodo, e tamanho do candles
    cotacoes_acao = cotacoes_acao["Close"]#pegando somente o close(fechamneto)
    return cotacoes_acao
acoes = ["ITUB4.SA", "PETR4.SA", "MGLU3.SA", "VALE3.SA", "ABEV3.SA", "GGBR4.SA"]#acoes que euquero
#Prepara as visualizações
dados = carregar_dados(acoes)#carregando as moedas

st.write("""
# App Preços de Ações
         O Grafico abaixo representa a evolução do preço das ações ao longo do ano
""")#texto do streamlit

#Preparações de visualizações de filtro
st.sidebar.header("Filtros")#sidebar(no canto lateral)
#Filtros de açoes
lista_acoes = st.sidebar.multiselect("Escolhas as ações para visualizar", dados.columns)#Selecinar colunas

if lista_acoes:#condicoies se nao estuiver nada selecionad  
    dados = dados[lista_acoes]
    if len(lista_acoes) == 1:
        acao_unica = lista_acoes[0]
        dados = dados.rename(columns={acao_unica: "Close"})
    
#filtros de data
data_inicial = dados.index.min().to_pydatetime()
data_final = dados.index.max().to_pydatetime()
intervalo_de_datas = st.sidebar.slider("Selecione o periodo", 
                                       min_value=data_inicial, 
                                       max_value=data_final,
                                       value=(data_inicial, data_final),
                                       step=timedelta(days=1))
dados = dados.loc[intervalo_de_datas[0]:intervalo_de_datas[1]]

#Cria Graficos
st.line_chart(dados)
