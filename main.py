import streamlit as st
import requests
import time
import pandas as pd
import base64
from binance.client import Client
from binance.exceptions import BinanceAPIException
import qrcode
from io import BytesIO

# --- Chaves do Firebase ---
try:
    API_KEY = st.secrets["firebase"]["api_key"]
    PROJECT_URL = st.secrets["firebase"]["project_url"]
    STORAGE_BUCKET = st.secrets["firebase"]["storage_bucket"]
except KeyError:
    st.error("As chaves do Firebase não foram encontradas.")
    st.stop()

# --- Chaves da Binance ---
try:
    BINANCE_API_KEY = st.secrets["binance"]["api_key"]
    BINANCE_API_SECRET = st.secrets["binance"]["secret"]
except KeyError:
    st.error("Chaves da Binance não encontradas no secrets.toml")
    st.stop()

client = Client(BINANCE_API_KEY, BINANCE_API_SECRET)

# --- Gerenciamento de Estado ---
if 'page' not in st.session_state: st.session_state.page = 'login'
if 'id_token' not in st.session_state: st.session_state.id_token = None
if 'local_id' not in st.session_state: st.session_state.local_id = None
if 'user_info' not in st.session_state: st.session_state.user_info = {}
if 'show_reset_form' not in st.session_state: st.session_state.show_reset_form = False

# --- Funções Auxiliares ---
def show_message(title, message, type="info"):
    if type=="error": st.error(f"**{title}**\n\n{message}")
    else: st.info(f"**{title}**\n\n{message}")

def navigate_to(page_name):
    st.session_state.page = page_name
    st.rerun()

# --- Firebase ---
def login_user(email, password):
    url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={API_KEY}"
    payload = {"email":email, "password":password, "returnSecureToken":True}
    return requests.post(url,json=payload)

def signup_user(email,password):
    url = f"https://identitytoolkit.googleapis.com/v1/accounts:signUp?key={API_KEY}"
    payload = {"email":email, "password":password, "returnSecureToken":True}
    return requests.post(url,json=payload)

def send_verification_email(id_token):
    url = f"https://identitytoolkit.googleapis.com/v1/accounts:sendOobCode?key={API_KEY}"
    payload = {"requestType":"VERIFY_EMAIL","idToken":id_token}
    requests.post(url,json=payload)

def reset_password(email):
    url = f"https://identitytoolkit.googleapis.com/v1/accounts:sendOobCode?key={API_KEY}"
    payload = {"requestType":"PASSWORD_RESET","email":email}
    requests.post(url,json=payload)

def update_password(id_token,new_password):
    url = f"https://identitytoolkit.googleapis.com/v1/accounts:update?key={API_KEY}"
    payload = {"idToken":id_token, "password":new_password, "returnSecureToken":True}
    return requests.post(url,json=payload)

def save_user_data_to_db(local_id,id_token,data):
    url = f"{PROJECT_URL}/usuarios/{local_id}.json?auth={id_token}"
    return requests.patch(url,json=data)

def get_user_data_from_db(local_id,id_token):
    url = f"{PROJECT_URL}/usuarios/{local_id}.json?auth={id_token}"
    return requests.get(url)

# --- Pagamentos ---
def criar_pagamento_usdt(user_id, valor):
    """
    Cria um pagamento Binance Pay em USDT e retorna URL/QR.
    """
    try:
        # Criação simples usando a API REST da Binance Pay
        # Para simplificação, vamos simular link de pagamento
        order_id = f"PAY-{user_id}-{int(time.time())}"
        pagamento_info = {
            "order_id": order_id,
            "valor": valor,
            "status": "pendente"
        }
        # Salvar pagamento no Firebase
        save_user_data_to_db(user_id, st.session_state.id_token, {"ultimo_pagamento": pagamento_info})
        # Gerar QR code do pagamento (simulado)
        qr = qrcode.QRCode(box_size=10, border=2)
        qr.add_data(f"Pagamento USDT {valor} - {order_id}")
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        buf = BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
        return buf, pagamento_info
    except Exception as e:
        show_message("Erro","Não foi possível criar pagamento: "+str(e),"error")
        return None, None

def checar_pagamento(user_id):
    """
    Checa se o pagamento foi concluído.
    Aqui é simulado: sempre aprova depois de 10s
    """
    info = st.session_state.user_info.get("ultimo_pagamento",{})
    if not info: return
    if info.get("status")=="pendente":
        # Simula aprovação
        if time.time() % 10 < 5:  # aprova parcialmente
            info["status"]="concluido"
            # Atualiza saldo do usuário
            saldo_atual = st.session_state.user_info.get("saldo",0)
            saldo_atual += info["valor"]
            info["valor_creditado"]=info["valor"]
            st.session_state.user_info["saldo"]=saldo_atual
            save_user_data_to_db(user_id, st.session_state.id_token, {"saldo":saldo_atual, "ultimo_pagamento":info})
        st.session_state.user_info["ultimo_pagamento"]=info

# --- Telas ---
def login_page():
    st.markdown("<h2 style='text-align:center;'>Login</h2>", unsafe_allow_html=True)
    with st.form("login_form"):
        email = st.text_input("E-mail")
        senha = st.text_input("Senha", type="password")
        btn = st.form_submit_button("Entrar")
    if btn:
        resp = login_user(email,senha)
        if resp.status_code==200:
            data=resp.json()
            st.session_state.id_token=data['idToken']
            st.session_state.local_id=data['localId']
            # Puxar dados do usuário
            r = get_user_data_from_db(st.session_state.local_id,st.session_state.id_token)
            if r.status_code==200:
                st.session_state.user_info = r.json()
            navigate_to('home')
        else: show_message("Erro","Login incorreto","error")

def cadastro_page():
    st.markdown("<h2 style='text-align:center;'>Cadastro</h2>", unsafe_allow_html=True)
    with st.form("form_cadastro"):
        nome = st.text_input("Nome")
        sobrenome = st.text_input("Sobrenome")
        email = st.text_input("E-mail")
        senha = st.text_input("Senha", type="password")
        btn = st.form_submit_button("Cadastrar")
    if btn:
        resp = signup_user(email,senha)
        if resp.status_code==200:
            data=resp.json()
            st.session_state.id_token=data['idToken']
            st.session_state.local_id=data['localId']
            save_user_data_to_db(st.session_state.local_id, st.session_state.id_token, {"nome":nome,"sobrenome":sobrenome,"saldo":0})
            show_message("Sucesso","Conta criada!","info")
            navigate_to('login')
        else: show_message("Erro","Erro ao cadastrar","error")

def home_page():
    st.markdown(f"<h2 style='text-align:center;'>Bem-vindo {st.session_state.user_info.get('nome','')}</h2>", unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Ver Perfil"): navigate_to('perfil')
    with col2:
        if st.button("Sair"):
            st.session_state.id_token=None
            st.session_state.local_id=None
            st.session_state.user_info={}
            navigate_to('login')
    
    st.markdown("---")
    # --- Painel de Pagamento ---
    st.subheader("Adicionar saldo via USDT")
    valor = st.number_input("Valor em USDT", min_value=1.0, step=1.0)
    if st.button("Gerar pagamento"):
        qr_buf, info = criar_pagamento_usdt(st.session_state.local_id, valor)
        if qr_buf:
            st.image(qr_buf, caption="Escaneie o QR Code para pagar")
            st.success(f"Pagamento criado: {info['order_id']} (pendente)")
    if st.session_state.user_info.get("ultimo_pagamento"):
        checar_pagamento(st.session_state.local_id)
        pag = st.session_state.user_info["ultimo_pagamento"]
        st.info(f"Último pagamento: {pag['order_id']}, Status: {pag['status']}")
    st.write(f"Saldo atual: {st.session_state.user_info.get('saldo',0)} USDT")

def perfil_page():
    st.markdown("<h2 style='text-align:center;'>Perfil</h2>", unsafe_allow_html=True)
    st.write(st.session_state.user_info)
    if st.button("Voltar"): navigate_to('home')

# --- Principal ---
def main():
    st.set_page_config(page_title="App Burgos USDT", page_icon=":money_with_wings:")
    if st.session_state.page=="login": login_page()
    elif st.session_state.page=="cadastro": cadastro_page()
    elif st.session_state.page=="home" and st.session_state.id_token: home_page()
    elif st.session_state.page=="perfil" and st.session_state.id_token: perfil_page()
    else: navigate_to('login')

if __name__=="__main__":
    main()
