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
    st.error("As chaves do Firebase não foram encontradas. Por favor, adicione-as ao arquivo `.streamlit/secrets.toml`.")
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
        st.info(f"**{title}**\n\n{message}")

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
            with st.spinner("Entrando..."):
                response = login_user(email, password)
                if response.status_code == 200:
                    data = response.json()
                    st.session_state.id_token = data['idToken']
                    st.session_state.local_id = data['localId']
                    
                    # Verifica e-mail
                    url_verify = f"https://identitytoolkit.googleapis.com/v1/accounts:lookup?key={API_KEY}"
                    payload_verify = {"idToken": st.session_state.id_token}
                    response_verify = requests.post(url_verify, json=payload_verify)
                    if response_verify.status_code == 200:
                        is_email_verified = response_verify.json()['users'][0]['emailVerified']
                        if is_email_verified:
                            navigate_to('home')
                        else:
                            show_message("Atenção", "Verifique seu e-mail antes de fazer login.", "error")
                    else:
                        show_message("Erro", "Erro ao verificar e-mail.", "error")
                else:
                    show_message("Erro", "Erro ao fazer login. Verifique seu e-mail e senha.", "error")

    st.markdown("---")
    if st.button("Criar uma conta"):
        navigate_to('cadastro')
    if st.button("Esqueceu a senha?"):
        st.session_state.show_reset_form = True

    if st.session_state.show_reset_form:
        with st.form("reset_password_form"):
            email_to_reset = st.text_input("Informe seu e-mail para recuperar a senha:", key="reset_email_input")
            reset_button = st.form_submit_button("Enviar e-mail de recuperação")
            if reset_button:
                if not email_to_reset:
                    show_message("Atenção", "Informe seu e-mail.")
                else:
                    with st.spinner("Enviando e-mail..."):
                        reset_password(email_to_reset)
                        show_message("Sucesso", "E-mail de recuperação enviado! Verifique sua caixa de entrada.")
                        st.session_state.show_reset_form = False

def cadastro_page():
    st.markdown("<h2 style='text-align: center;'>Cadastro</h2>", unsafe_allow_html=True)
    with st.form("cadastro_form"):
        nome = st.text_input("Nome", placeholder="Nome")
        sobrenome = st.text_input("Sobrenome", placeholder="Sobrenome")
        telefone = st.text_input("Telefone (com DDD)", placeholder="Telefone (com DDD)")
        email = st.text_input("E-mail", placeholder="E-mail")
        senha = st.text_input("Senha", placeholder="Senha", type="password")
        cadastro_button = st.form_submit_button("Cadastrar")

    if cadastro_button:
        if not all([nome, sobrenome, telefone, email, senha]):
            show_message("Atenção", "Preencha todos os campos.", "error")
        else:
            with st.spinner("Cadastrando..."):
                response = signup_user(email, senha)
                if response.status_code == 200:
                    data = response.json()
                    st.session_state.id_token = data['idToken']
                    st.session_state.local_id = data['localId']
                    
                    user_data = {"nome": nome, "sobrenome": sobrenome, "telefone": telefone, "email": email}
                    save_response = save_user_data_to_db(st.session_state.local_id, st.session_state.id_token, user_data)
                    if save_response.status_code == 200:
                        send_verification_email(st.session_state.id_token)
                        show_message("Sucesso", "Cadastro realizado! Verifique seu e-mail para continuar.")
                        navigate_to('login')
                    else:
                        show_message("Erro", "Erro ao salvar dados do usuário.", "error")
                else:
                    show_message("Erro", "Erro ao cadastrar. Verifique se o e-mail já está em uso.", "error")

    if st.button("Já tem uma conta? Login"):
        navigate_to('login')

def home_page():
    """Home com painel de ações"""
    user_name = st.session_state.user_info.get('nome', '')
    st.markdown(f"<h2 style='text-align: center;'>Bem-vindo, {user_name}!</h2>", unsafe_allow_html=True)
    
    col1, col2 = st.columns([1,1])
    with col1:
        if st.button("Ver Perfil"):
            navigate_to('perfil')
    with col2:
        if st.button("Sair"):
            st.session_state.id_token = None
            st.session_state.local_id = None
            st.session_state.user_info = {}
            navigate_to('login')

    st.markdown("---")

    # --- Painel de Ações ---
    df = pd.DataFrame({
        'Ações': ['ITUB4', 'PETR4', 'VALE3', 'BBDC4', 'ABEV3'],
        'Preço': [25.3, 30.5, 88.7, 23.1, 15.4]
    })

    lista_acoes = st.sidebar.multiselect(
        "Escolha as ações que deseja visualizar:",
        options=df['Ações'],
        default=df['Ações'].tolist()
    )

    df_selecionadas = df[df['Ações'].isin(lista_acoes)]
    st.subheader("Ações Selecionadas")
    st.dataframe(df_selecionadas)
    st.subheader("Gráfico de Preço das Ações Selecionadas")
    st.bar_chart(df_selecionadas.set_index('Ações')['Preço'])

def perfil_page():
    st.markdown("<h2 style='text-align: center;'>Perfil</h2>", unsafe_allow_html=True)

    if not st.session_state.user_info:
        with st.spinner("Carregando perfil..."):
            response = get_user_data_from_db(st.session_state.local_id, st.session_state.id_token)
            if response.status_code == 200:
                st.session_state.user_info = response.json()
            else:
                show_message("Erro", "Erro ao carregar perfil.", "error")
                st.session_state.user_info = {}

    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        st.markdown("<div style='text-align: center;'>", unsafe_allow_html=True)
        photo_url = st.session_state.user_info.get('foto_perfil')
        css_style = """
            <style>
                .profile-picture {
                    border-radius: 50%;
                    width: 200px;
                    height: 200px;
                    object-fit: cover;
                    border: 3px solid #ddd;
                    box-shadow: 0 4px 8px rgba(0,0,0,0.1);
                    display: block;
                    margin: 0 auto;
                }
            </style>
        """
        st.markdown(css_style, unsafe_allow_html=True)
        if photo_url:
            st.markdown(f'<img src="{photo_url}" class="profile-picture">', unsafe_allow_html=True)
        else:
            st.markdown('<img src="https://placehold.co/200x200?text=Sem+Foto" class="profile-picture">', unsafe_allow_html=True)

        full_name = f"{st.session_state.user_info.get('nome','')} {st.session_state.user_info.get('sobrenome','')}"
        st.markdown(f"<h3 style='text-align:center;'>{full_name}</h3>", unsafe_allow_html=True)
        uploaded_file = st.file_uploader("Alterar Foto de Perfil", type=["jpg","jpeg","png"])
        if uploaded_file:
            with st.spinner("Enviando foto..."):
                photo_data = uploaded_file.getvalue()
                response = upload_profile_photo(st.session_state.local_id, photo_data)
                if response.status_code in (200,201):
                    link_foto = f"https://firebasestorage.googleapis.com/v0/b/{STORAGE_BUCKET}/o/{st.session_state.local_id}.jpg?alt=media&time={int(time.time())}"
                    save_response = save_user_data_to_db(st.session_state.local_id, st.session_state.id_token, {"foto_perfil": link_foto})
                    if save_response.status_code == 200:
                        st.session_state.user_info['foto_perfil'] = link_foto
                        show_message("Sucesso", "Foto de perfil atualizada.")
                    else:
                        show_message("Erro", "Erro ao salvar link da foto no banco.", "error")
                else:
                    show_message("Erro", f"Erro ao enviar foto: {response.text}", "error")
        st.markdown("</div>", unsafe_allow_html=True)

    with st.form("perfil_form"):
        nome = st.text_input("Nome", value=st.session_state.user_info.get('nome',''))
        sobrenome = st.text_input("Sobrenome", value=st.session_state.user_info.get('sobrenome',''))
        telefone = st.text_input("Telefone (com DDD)", value=st.session_state.user_info.get('telefone',''))
        nova_senha = st.text_input("Nova Senha (opcional)", type="password")
        save_button = st.form_submit_button("Salvar Alterações")

    if save_button:
        if not all([nome,sobrenome,telefone]):
            show_message("Atenção","Preencha nome, sobrenome e telefone.","error")
        else:
            with st.spinner("Salvando dados..."):
                updated_data = {"nome":nome,"sobrenome":sobrenome,"telefone":telefone}
                save_response = save_user_data_to_db(st.session_state.local_id, st.session_state.id_token, updated_data)
                if save_response.status_code == 200:
                    if nova_senha:
                        update_response = update_password(st.session_state.id_token, nova_senha)
                        if update_response.status_code == 200:
                            st.session_state.id_token = update_response.json()['idToken']
                            show_message("Sucesso","Dados e senha atualizados!")
                        else:
                            show_message("Erro","Erro ao atualizar senha.","error")
                    else:
                        show_message("Sucesso","Dados atualizados!")
                    st.session_state.user_info.update(updated_data)
                else:
                    show_message("Erro","Erro ao salvar dados.","error")

    if st.button("Voltar"):
        navigate_to('home')

# --- Lógica Principal ---
def main():
    st.set_page_config(page_title="App Burgos", page_icon=":shield:")
    st.markdown("<style> .stButton>button { width: 100%; } </style>", unsafe_allow_html=True)

    if st.session_state.page == 'login':
        login_page()
    elif st.session_state.page == 'cadastro':
        cadastro_page()
    elif st.session_state.page == 'home' and st.session_state.id_token:
        home_page()
    elif st.session_state.page == 'perfil' and st.session_state.id_token:
        perfil_page()
    else:
        navigate_to('login')

if __name__ == "__main__":
    main()
