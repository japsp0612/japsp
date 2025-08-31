import streamlit as st
import requests
import time
from PIL import Image

# 🔥 Dados do Firebase (usando st.secrets)
API_KEY = st.secrets["firebase"]["API_KEY"]
PROJECT_URL = st.secrets["firebase"]["PROJECT_URL"]
STORAGE_BUCKET = st.secrets["firebase"]["STORAGE_BUCKET"]

# --- Inicializando sessão ---
if 'id_token' not in st.session_state:
    st.session_state.id_token = None
if 'local_id' not in st.session_state:
    st.session_state.local_id = None
if 'email_logando' not in st.session_state:
    st.session_state.email_logando = None

# --- Funções ---
def alerta(mensagem):
    st.warning(mensagem)

def login(email, senha):
    if email == "" or senha == "":
        alerta("Preencha todos os campos.")
        return False

    url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={API_KEY}"
    dados = {"email": email, "password": senha, "returnSecureToken": True}
    resposta = requests.post(url, json=dados)

    if resposta.status_code == 200:
        st.session_state.id_token = resposta.json()['idToken']
        st.session_state.local_id = resposta.json()['localId']
        st.session_state.email_logando = email

        # Verificar e-mail
        url_verificar = f"https://identitytoolkit.googleapis.com/v1/accounts:lookup?key={API_KEY}"
        dados_verificar = {"idToken": st.session_state.id_token}
        resposta_verificar = requests.post(url_verificar, json=dados_verificar)
        if resposta_verificar.status_code == 200:
            email_verificado = resposta_verificar.json()['users'][0]['emailVerified']
            if email_verificado:
                return True
            else:
                alerta("Verifique seu e-mail antes de fazer login.")
                return False
        else:
            alerta("Erro ao verificar e-mail.")
            return False
    else:
        alerta("Erro ao fazer login.")
        return False

def cadastrar(nome, sobrenome, telefone, email, senha):
    if "" in (nome, sobrenome, telefone, email, senha):
        alerta("Preencha todos os campos.")
        return False

    url = f"https://identitytoolkit.googleapis.com/v1/accounts:signUp?key={API_KEY}"
    dados = {"email": email, "password": senha, "returnSecureToken": True}
    resposta = requests.post(url, json=dados)

    if resposta.status_code == 200:
        st.session_state.id_token = resposta.json()['idToken']
        st.session_state.local_id = resposta.json()['localId']
        st.session_state.email_logando = email

        info_usuario = {
            "nome": nome,
            "sobrenome": sobrenome,
            "telefone": telefone,
            "email": email,
        }

        url_database = f"{PROJECT_URL}/usuarios/{st.session_state.local_id}.json?auth={st.session_state.id_token}"
        salvar = requests.patch(url_database, json=info_usuario)

        if salvar.status_code == 200:
            enviar_verificacao(st.session_state.id_token)
            alerta("Cadastro realizado! Verifique seu e-mail.")
            return True
        else:
            alerta("Erro ao salvar dados.")
            return False
    else:
        alerta("Erro ao cadastrar.")
        return False

def enviar_verificacao(id_token):
    url = f"https://identitytoolkit.googleapis.com/v1/accounts:sendOobCode?key={API_KEY}"
    dados = {"requestType": "VERIFY_EMAIL", "idToken": id_token}
    requests.post(url, json=dados)

def recuperar_senha(email):
    if email.strip() == "":
        alerta("Informe seu e-mail para recuperar a senha.")
        return

    url = f"https://identitytoolkit.googleapis.com/v1/accounts:sendOobCode?key={API_KEY}"
    dados = {"requestType": "PASSWORD_RESET", "email": email}
    resposta = requests.post(url, json=dados)

    if resposta.status_code == 200:
        alerta("E-mail de recuperação enviado!")
    else:
        alerta("Erro ao enviar e-mail de recuperação.")

def carregar_dados_perfil():
    url = f"{PROJECT_URL}/usuarios/{st.session_state.local_id}.json?auth={st.session_state.id_token}"
    resposta = requests.get(url)
    if resposta.status_code == 200:
        return resposta.json()
    else:
        alerta("Erro ao carregar perfil.")
        return {}

def salvar_dados_perfil(nome, sobrenome, telefone, senha):
    if "" in (nome, sobrenome, telefone):
        alerta("Preencha nome, sobrenome e telefone.")
        return

    url = f"{PROJECT_URL}/usuarios/{st.session_state.local_id}.json?auth={st.session_state.id_token}"
    dados = {"nome": nome, "sobrenome": sobrenome, "telefone": telefone}
    requests.patch(url, json=dados)

    if senha.strip() != "":
        url_senha = f"https://identitytoolkit.googleapis.com/v1/accounts:update?key={API_KEY}"
        dados_senha = {"idToken": st.session_state.id_token, "password": senha, "returnSecureToken": True}
        resposta_senha = requests.post(url_senha, json=dados_senha)
        if resposta_senha.status_code == 200:
            st.session_state.id_token = resposta_senha.json()['idToken']
            alerta("Dados e senha atualizados!")
        else:
            alerta("Erro ao atualizar senha.")
    else:
        alerta("Dados atualizados!")

def upload_foto_perfil(uploaded_file):
    if not uploaded_file:
        alerta("Nenhuma foto selecionada.")
        return

    nome_arquivo = f"{st.session_state.local_id}.jpg"
    url_upload = f"https://firebasestorage.googleapis.com/v0/b/{STORAGE_BUCKET}/o?uploadType=media&name={nome_arquivo}"

    headers = {"Authorization": "Firebase " + st.session_state.id_token, "Content-Type": "image/jpeg"}
    foto_bytes = uploaded_file.read()
    resposta = requests.post(url_upload, headers=headers, data=foto_bytes)

    if resposta.status_code in (200, 201):
        link_foto = f"https://firebasestorage.googleapis.com/v0/b/{STORAGE_BUCKET}/o/{nome_arquivo}?alt=media&time={int(time.time())}"
        url_db = f"{PROJECT_URL}/usuarios/{st.session_state.local_id}.json?auth={st.session_state.id_token}"
        requests.patch(url_db, json={"foto_perfil": link_foto})
        alerta("Foto de perfil atualizada!")
        return link_foto
    else:
        alerta(f"Erro ao enviar foto: {resposta.text}")
        return None

# --- Interface Streamlit ---
st.title("App de Usuário Firebase")

menu = ["Login", "Cadastro", "Perfil"]
if st.session_state.id_token:
    menu = ["Perfil", "Sair"]

choice = st.sidebar.selectbox("Menu", menu)

if choice == "Login":
    st.subheader("Login")
    email = st.text_input("E-mail")
    senha = st.text_input("Senha", type="password")
    if st.button("Entrar"):
        if login(email, senha):
            st.experimental_rerun()
    if st.button("Recuperar senha"):
        recuperar_senha(email)

elif choice == "Cadastro":
    st.subheader("Cadastro")
    nome = st.text_input("Nome")
    sobrenome = st.text_input("Sobrenome")
    telefone = st.text_input("Telefone")
    email = st.text_input("E-mail")
    senha = st.text_input("Senha", type="password")
    if st.button("Cadastrar"):
        if cadastrar(nome, sobrenome, telefone, email, senha):
            st.experimental_rerun()

elif choice == "Perfil":
    st.subheader("Perfil")
    dados = carregar_dados_perfil()
    nome = st.text_input("Nome", value=dados.get("nome",""))
    sobrenome = st.text_input("Sobrenome", value=dados.get("sobrenome",""))
    telefone = st.text_input("Telefone", value=dados.get("telefone",""))
    senha = st.text_input("Nova Senha (opcional)", type="password")

    foto_url = dados.get("foto_perfil")
    if foto_url:
        st.image(foto_url, width=150)
    else:
        st.image("foto_padrao.png", width=150)

    uploaded_file = st.file_uploader("Alterar Foto", type=["jpg", "jpeg", "png"])
    if uploaded_file:
        link = upload_foto_perfil(uploaded_file)
        if link:
            st.image(link, width=150)

    if st.button("Salvar Alterações"):
        salvar_dados_perfil(nome, sobrenome, telefone, senha)

    if st.button("Sair"):
        st.session_state.id_token = None
        st.session_state.local_id = None
        st.session_state.email_logando = None
        st.experimental_rerun()
