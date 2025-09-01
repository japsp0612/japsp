import streamlit as st
import requests
import time
import base64
import pandas as pd

# --- Carregando chaves do Firebase ---
try:
    API_KEY = st.secrets["firebase"]["api_key"]
    PROJECT_URL = st.secrets["firebase"]["project_url"]
    STORAGE_BUCKET = st.secrets["firebase"]["storage_bucket"]
except KeyError:
    st.error("As chaves do Firebase não foram encontradas. Adicione no `.streamlit/secrets.toml`.")
    st.stop()

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

# --- Pagamento USDT ---
BINANCE_USDT_ADDRESS = "TYk2cPzF36pqVvU1dun4P1MLzp6GF5E2mM"  # Substitua pelo seu endereço USDT

def deposit_page():
    st.markdown("<h2 style='text-align: center;'>Depósito em USDT</h2>", unsafe_allow_html=True)
    st.info(f"Deposite USDT na sua carteira Binance usando este endereço:\n\n`{BINANCE_USDT_ADDRESS}`")
    
    with st.form("deposit_form"):
        valor = st.number_input("Valor a depositar (USDT)", min_value=0.0, step=0.01)
        deposit_button = st.form_submit_button("Registrar Depósito")
    
    if deposit_button:
        if valor <= 0:
            show_message("Erro", "Informe um valor válido.", "error")
        else:
            # Simula verificação de depósito (em produção, você usaria webhook ou API da Binance)
            st.session_state.user_info['depositos'] = st.session_state.user_info.get('depositos', [])
            deposito_info = {"valor": valor, "status": "pendente", "timestamp": int(time.time())}
            st.session_state.user_info['depositos'].append(deposito_info)
            save_user_data_to_db(st.session_state.local_id, st.session_state.id_token, {"depositos": st.session_state.user_info['depositos']})
            show_message("Sucesso", f"Depósito de {valor} USDT registrado com status PENDENTE.")
    
    # Exibe depósitos
    st.subheader("Histórico de Depósitos")
    depositos = st.session_state.user_info.get('depositos', [])
    if depositos:
        df = pd.DataFrame(depositos)
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s')
        st.dataframe(df)
    else:
        st.info("Nenhum depósito registrado ainda.")

# --- Telas ---
def login_page():
    st.markdown("<h2 style='text-align: center;'>Login</h2>", unsafe_allow_html=True)
    with st.form("login_form"):
        email = st.text_input("E-mail")
        password = st.text_input("Senha", type="password")
        login_button = st.form_submit_button("Entrar")
    
    if login_button:
        if not email or not password:
            show_message("Atenção", "Preencha todos os campos.", "error")
        else:
            with st.spinner("Entrando..."):
                response = login_user(email, password)
                if response.status_code == 200:
                    data = response.json()
                    st.session_state.id_token = data['idToken']
                    st.session_state.local_id = data['localId']
                    
                    # Carrega dados do usuário
                    user_data_resp = get_user_data_from_db(st.session_state.local_id, st.session_state.id_token)
                    if user_data_resp.status_code == 200:
                        st.session_state.user_info = user_data_resp.json()
                    navigate_to('home')
                else:
                    show_message("Erro", "E-mail ou senha incorretos.", "error")
    
    st.markdown("---")
    if st.button("Criar Conta"):
        navigate_to('cadastro')

def cadastro_page():
    st.markdown("<h2 style='text-align: center;'>Cadastro</h2>", unsafe_allow_html=True)
    with st.form("cadastro_form"):
        nome = st.text_input("Nome")
        sobrenome = st.text_input("Sobrenome")
        telefone = st.text_input("Telefone")
        email = st.text_input("E-mail")
        senha = st.text_input("Senha", type="password")
        cadastro_button = st.form_submit_button("Cadastrar")
    
    if cadastro_button:
        if not all([nome, sobrenome, telefone, email, senha]):
            show_message("Erro", "Preencha todos os campos.", "error")
        else:
            response = signup_user(email, senha)
            if response.status_code == 200:
                data = response.json()
                st.session_state.id_token = data['idToken']
                st.session_state.local_id = data['localId']
                user_data = {"nome": nome, "sobrenome": sobrenome, "telefone": telefone, "email": email, "depositos":[]}
                save_user_data_to_db(st.session_state.local_id, st.session_state.id_token, user_data)
                show_message("Sucesso", "Cadastro realizado!")
                navigate_to('login')
            else:
                show_message("Erro", "Erro ao cadastrar. E-mail pode já estar em uso.", "error")

def home_page():
    st.markdown(f"<h2>Bem-vindo, {st.session_state.user_info.get('nome','')}</h2>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1,1,1])
    with col1:
        if st.button("Perfil"):
            navigate_to('perfil')
    with col2:
        if st.button("Depósito USDT"):
            navigate_to('deposito')
    with col3:
        if st.button("Sair"):
            st.session_state.id_token = None
            st.session_state.local_id = None
            st.session_state.user_info = {}
            navigate_to('login')

def perfil_page():
    st.markdown("<h2>Perfil</h2>", unsafe_allow_html=True)
    user_info = st.session_state.user_info
    st.write(f"Nome: {user_info.get('nome','')}")
    st.write(f"Telefone: {user_info.get('telefone','')}")
    if st.button("Voltar"):
        navigate_to('home')

# --- Lógica Principal ---
def main():
    st.set_page_config(page_title="App Burgos", page_icon=":moneybag:")
    if st.session_state.page == 'login':
        login_page()
    elif st.session_state.page == 'cadastro':
        cadastro_page()
    elif st.session_state.page == 'home' and st.session_state.id_token:
        home_page()
    elif st.session_state.page == 'perfil' and st.session_state.id_token:
        perfil_page()
    elif st.session_state.page == 'deposito' and st.session_state.id_token:
        deposit_page()
    else:
        navigate_to('login')

if __name__ == "__main__":
    main()
