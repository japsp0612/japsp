import streamlit as st
from binance.client import Client
import pandas as pd
import time

API_KEY = st.secrets["BINANCE_API_KEY"]
API_SECRET = st.secrets["BINANCE_API_SECRET"]

client = Client(API_KEY, API_SECRET)

st.title("Robô Trader - Demo")

symbol = st.text_input("Par de negociação", "BTCUSDT")
operar = st.button("Rodar operação")

if operar:
    # pega preço atual
    ticker = client.get_symbol_ticker(symbol=symbol)
    st.write(f"Preço atual de {symbol}: {ticker['price']}")

    # aqui você coloca sua lógica de compra/venda
    # ex: RSI, MACD, EMA
    st.success("Lógica do robô executada (demo)")
