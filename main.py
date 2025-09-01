import streamlit as st
import requests
import time
import pandas as pd
from binance.client import Client
from binance.exceptions import BinanceAPIException

# --- Carregando chaves ---
try:
    API_KEY = st.secrets["firebase"]["api_key"]
    PROJECT_URL = st.secrets["firebase"]["project_url"]
    STORAGE_BUCKET = st.secrets["firebase"]["storage_bucket"]

    BINANCE_API_KEY = st.secrets["binance"]["api_key"]
    BINANCE_API_SECRET = st.secrets["binance"]["api_secret"]
except KeyError:
    st.error("As chaves não foram encontradas no secrets.toml")
    st.stop()

# --- Inicializar cliente Binance Testnet ---
try:
    client_binance = Client(BINANCE_API_KEY, BINANCE_API_SECRET, testnet=True)
except BinanceAPIException as e:
    st.error(f"Erro na conexão com Binance: {e}")
    st.stop()

# --- Estado do Streamlit ---
if 'page' not in st.session_state:
    st.session_state.page = 'login'
if 'id_token' not in st.session_state:
    st.session_state.id_token = None
if 'local_id' not in st.session_state:
    st.session_state.local_id = None
if 'user_info' not in st.session_state:
    st.session_state.user_info = {}

# --- Funções auxiliares ---
def show_message(title, message, type="info"):
    if type=="error":
        st.error(f"**{title}**\n\n{message}")
    else:
        st.info(f"**{title}**\n\n{message}")

def navigate_to(page_name):
    st.session_state.page = page_name
    st.rerun()

# --- Firebase ---
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

# --- Páginas ---
def login_page():
    st.title("Login")
    with st.form("login_form"):
        email = st.text_input("E-mail")
        senha = st.text_input("Senha", type="password")
        btn = st.form_submit_button("Entrar")
    if btn:
        if not email or not senha:
            show_message("Erro", "Preencha todos os campos.", "error")
        else:
            r = login_user(email, senha)
            if r.status_code==200:
                data = r.json()
                st.session_state.id_token = data["idToken"]
                st.session_state.local_id = data["localId"]
                navigate_to("home")
            else:
                show_message("Erro", "E-mail ou senha inválidos", "error")
    if st.button("Criar conta"):
        navigate_to("cadastro")

def cadastro_page():
    st.title("Cadastro")
    with st.form("cad_form"):
        nome = st.text_input("Nome")
        email = st.text_input("E-mail")
        senha = st.text_input("Senha", type="password")
        btn = st.form_submit_button("Cadastrar")
    if btn:
        if not nome or not email or not senha:
            show_message("Erro", "Preencha todos os campos", "error")
        else:
            r = signup_user(email, senha)
            if r.status_code==200:
                data = r.json()
                st.session_state.id_token = data["idToken"]
                st.session_state.local_id = data["localId"]
                user_data = {"nome": nome, "email": email, "saldo": 0}
                save_user_data_to_db(st.session_state.local_id, st.session_state.id_token, user_data)
                send_verification_email(st.session_state.id_token)
                show_message("Sucesso", "Cadastro feito! Verifique seu e-mail")
                navigate_to("login")
            else:
                show_message("Erro", "Erro ao cadastrar, email já existe?", "error")

def home_page():
    st.title(f"Bem-vindo, {st.session_state.user_info.get('nome','Usuário')}")

    # --- Saldo Firebase ---
    r = get_user_data_from_db(st.session_state.local_id, st.session_state.id_token)
    if r.status_code==200:
        user_data = r.json()
        st.session_state.user_info = user_data
        st.write(f"Saldo atual: ${user_data.get('saldo',0)}")

    # --- Saldo Binance Testnet ---
    st.subheader("Saldo Binance Testnet")
    try:
        balances = client_binance.get_account()["balances"]
        df = [{"Moeda":b["asset"], "Livre":float(b["free"]), "Bloqueado":float(b["locked"])} for b in balances if float(b["free"])>0 or float(b["locked"])>0]
        st.dataframe(pd.DataFrame(df))
    except BinanceAPIException as e:
        st.error(f"Erro: {e}")

    # --- Monitorar depósitos ---
    st.subheader("Depósitos USDT")
    if st.button("Atualizar depósitos"):
        try:
            deposits = client_binance.get_deposit_history(asset="USDT")
            df_dep = pd.DataFrame(deposits["depositList"])
            st.dataframe(df_dep)
            # Exemplo: Atualizar saldo do usuário automaticamente com depósitos
            total_deposit = sum(float(d["amount"]) for d in deposits["depositList"])
            st.write(f"Total de depósitos: {total_deposit} USDT")
            # Atualiza saldo no Firebase
            save_user_data_to_db(st.session_state.local_id, st.session_state.id_token, {"saldo": total_deposit})
        except BinanceAPIException as e:
            st.error(f"Erro ao buscar depósitos: {e}")

    if st.button("Sair"):
        st.session_state.page="login"
        st.session_state.id_token=None
        st.session_state.local_id=None
        st.session_state.user_info={}

# --- Lógica principal ---
def main():
    if st.session_state.page=="login":
        login_page()
    elif st.session_state.page=="cadastro":
        cadastro_page()
    elif st.session_state.page=="home" and st.session_state.id_token:
        home_page()
    else:
        navigate_to("login")

if __name__=="__main__":
    main()
