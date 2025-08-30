import streamlit as st
import pandas as pd
from binance.client import Client
from datetime import datetime
import time

# Inicializa client Binance Testnet
API_KEY = st.secrets["BINANCE_TESTNET_API_KEY"]
API_SECRET = st.secrets["BINANCE_TESTNET_API_SECRET"]

client = Client(API_KEY, API_SECRET, testnet=True)

st.title("🤖 Robô Trader Demo - Binance Testnet")

# Escolha do par
symbol = st.selectbox("Escolha o par de negociação", ["BTCUSDT", "ETHUSDT", "BNBUSDT"])

# Botão para atualizar dados
if st.button("Atualizar preços"):
    try:
        # Pega preço atual
        ticker = client.get_symbol_ticker(symbol=symbol)
        preco_atual = float(ticker['price'])
        st.write(f"Preço atual de {symbol}: **{preco_atual:.2f} USD**")

        # Exemplo de cálculo de indicador (simples)
        # Pega histórico dos últimos 10 candles de 1h
        klines = client.get_klines(symbol=symbol, interval=Client.KLINE_INTERVAL_1HOUR, limit=10)
        df = pd.DataFrame(klines, columns=[
            "open_time", "open", "high", "low", "close", "volume",
            "close_time", "quote_asset_volume", "number_of_trades",
            "taker_buy_base", "taker_buy_quote", "ignore"
        ])
        df["close"] = df["close"].astype(float)
        df["EMA5"] = df["close"].ewm(span=5, adjust=False).mean()
        st.line_chart(df[["close", "EMA5"]])

        st.success("✅ Dashboard atualizado com sucesso!")
    except Exception as e:
        st.error(f"❌ Erro ao atualizar dados: {e}")

st.info("Este robô está conectado apenas ao Testnet da Binance. Nenhuma ordem real é executada.")
