import streamlit as st
import requests
import time
import pandas as pd
import base64
from binance.client import Client
from binance.exceptions import BinanceAPIException

# --- Carregando chaves do Firebase e Binance ---
try:
    API_KEY = st.secrets["firebase"]["api_key"]
    PROJECT_URL = st.secrets["firebase"]["project_url"]
    STORAGE_BUCKET = st.secrets["firebase"]["storage_bucket"]

    BINANCE_API_KEY = st.secrets["binance"]["api_key"]
    BINANCE_API_SECRET = st.secrets["binance"]["api_secret"]
except KeyError:
    st.error("As chaves do Firebase ou Binance não foram encontradas. Adicione-as no arquivo `.streamlit/secrets.toml`")
    st.stop()

# --- Inicializa Binance Client ---
binance_client = Client(BINANCE_API_KEY, BINANCE_API_SECRET)

# --- Gerenciamento de Estado ---
if 'page' not in st.session_state:
    st.session_state.page = 'login'
if 'id_token' not in st.session_state:
    st.session_state.id_token = None
if 'local_id' not in st.session_state:
    st.session_state.local_id = None
if 'user_info' not in st.session_state:
    st.session_state.user_info = {}
if 'show_reset_form' not in st.session_state:
    st.session_state.show_reset_form = False

# --- Funções de Ajuda ---
def show_message(title, message, type="info"):
    if type == "error":
        st.error(f"**{title}**\n\n{message}")
    else:
        st.success(f"**{title}**\n\n{message}")

def navigate_to(page_name):
    st.session_state.page = page_name
    st.rerun()

# --- Firebase API ---
def login_user(email, password):
    url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={API_KEY}"
    payload = {"email": email, "password": password, "returnSecureToken": True}
    return requests.post(url, json=payload)

def signup_user(email, password):
    url = f"https://identitytoolkit.googleapis.com/v1/accounts:signUp?key={API_KEY}"
    payload = {"email": email, "password": password, "returnSecureToken": True}
    return requests.post(url, json=payload)

def send_verification_email(id_token):
    url = f"https://identitytoolkit.googleapis.com/v1/accounts:sendOobCode?key={API_KEY}"
    payload = {"requestType": "VERIFY_EMAIL", "idToken": id_token}
    requests.post(url, json=payload)

def update_password(id_token, new_password):
    url = f"https://identitytoolkit.googleapis.com/v1/accounts:update?key={API_KEY}"
    payload = {"idToken": id_token, "password": new_password, "returnSecureToken": True}
    return requests.post(url, json=payload)

def reset_password(email):
    url = f"https://identitytoolkit.googleapis.com/v1/accounts:sendOobCode?key={API_KEY}"
    payload = {"requestType": "PASSWORD_RESET", "email": email}
    requests.post(url, json=payload)

def upload_profile_photo(local_id, photo_data):
    url = f"https://firebasestorage.googleapis.com/v0/b/{STORAGE_BUCKET}/o?uploadType=media&name={local_id}.jpg"
    headers = {"Content-Type": "image/jpeg"}
    return requests.post(url, headers=headers, data=photo_data)

def save_user_data_to_db(local_id, id_token, data):
    url = f"{PROJECT_URL}/usuarios/{local_id}.json?auth={id_token}"
    return requests.patch(url, json=data)

def get_user_data_from_db(local_id, id_token):
    url = f"{PROJECT_URL}/usuarios/{local_id}.json?auth={id_token}"
    return requests.get(url)

# --- Sistema de Pagamento USDT ---
def gerar_endereco_usdt():
    # Aqui estamos simulando um endereço único para cada usuário
    # No mundo real, você poderia criar subcontas ou gerar wallets via Binance Pay ou Blockchain API
    return "ENDERECO_USDT_DO_USUARIO"

def verificar_pagamento(endereco, valor_esperado):
    try:
        # Consulta saldo da conta para simular pagamento
        account_info = binance_client.get_asset_balance(asset='USDT')
        if float(account_info['free']) >= valor_esperado:
            return True
        return False
    except BinanceAPIException as e:
        st.error(f"Erro Binance: {e}")
        return False

# --- Telas ---
def login_page():
    st.markdown("<h2 style='text-align: center;'>Login</h2>", unsafe_allow_html=True)
    with st.form("login_form"):
        email = st.text_input("E-mail", placeholder="E-mail")
        password = st.text_input("Senha", placeholder="Senha", type="password")
        login_button = st.form_submit_button("Entrar")

    if login_button:
        if not email or not password:
            show_message("Atenção", "Preencha todos os campos.", "error")
        else:
            response = login_user(email, password)
            if response.status_code == 200:
                data = response.json()
                st.session_state.id_token = data['idToken']
                st.session_state.local_id = data['localId']
                navigate_to('home')
            else:
                show_message("Erro", "Login inválido", "error")

    if st.button("Criar uma conta"):
        navigate_to('cadastro')
    if st.button("Esqueceu a senha?"):
        st.session_state.show_reset_form = True

def cadastro_page():
    st.markdown("<h2 style='text-align: center;'>Cadastro</h2>", unsafe_allow_html=True)
    with st.form("cadastro_form"):
        nome = st.text_input("Nome")
        email = st.text_input("E-mail")
        senha = st.text_input("Senha", type="password")
        cadastro_button = st.form_submit_button("Cadastrar")

    if cadastro_button:
        if not all([nome,email,senha]):
            show_message("Atenção","Preencha todos os campos","error")
        else:
            response = signup_user(email, senha)
            if response.status_code == 200:
                data = response.json()
                st.session_state.id_token = data['idToken']
                st.session_state.local_id = data['localId']
                user_data = {"nome": nome, "email": email, "saldo": 0}
                save_user_data_to_db(st.session_state.local_id, st.session_state.id_token, user_data)
                show_message("Sucesso","Cadastro realizado!")
                navigate_to('login')
            else:
                show_message("Erro","Erro ao cadastrar", "error")

def home_page():
    st.markdown("<h2 style='text-align: center;'>Home</h2>", unsafe_allow_html=True)
    user_info = get_user_data_from_db(st.session_state.local_id, st.session_state.id_token).json()
    saldo = user_info.get('saldo',0)
    st.markdown(f"**Saldo USDT:** {saldo}")

    st.markdown("---")
    st.subheader("Adicionar USDT")
    valor = st.number_input("Valor em USDT", min_value=1.0)
    endereco = gerar_endereco_usdt()
    st.markdown(f"Envie **{valor} USDT** para o endereço: `{endereco}`")

    if st.button("Verificar Pagamento"):
        pago = verificar_pagamento(endereco, valor)
        if pago:
            novo_saldo = saldo + valor
            save_user_data_to_db(st.session_state.local_id, st.session_state.id_token, {"saldo": novo_saldo})
            show_message("Sucesso", f"Pagamento recebido! Novo saldo: {novo_saldo} USDT")
        else:
            show_message("Aguardando pagamento...", "info")

# --- Lógica Principal ---
def main():
    st.set_page_config(page_title="App Burgos", page_icon=":moneybag:")
    if st.session_state.page == 'login':
        login_page()
    elif st.session_state.page == 'cadastro':
        cadastro_page()
    elif st.session_state.page == 'home' and st.session_state.id_token:
        home_page()
    else:
        navigate_to('login')

if __name__ == "__main__":
    main()
