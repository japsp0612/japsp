import streamlit as st
import requests
import time
import pandas as pd

# --- Configuração de Chaves ---
try:
    API_KEY = st.secrets["firebase"]["api_key"]
    PROJECT_URL = st.secrets["firebase"]["project_url"]
    STORAGE_BUCKET = st.secrets["firebase"]["storage_bucket"]
except KeyError:
    st.error("As chaves do Firebase não foram encontradas. Adicione ao `.streamlit/secrets.toml`.")
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

# --- Funções auxiliares ---
def show_message(title, message, type="info"):
    if type == "error":
        st.error(f"**{title}**\n\n{message}")
    else:
        st.info(f"**{title}**\n\n{message}")

def navigate_to(page_name):
    st.session_state.page = page_name
    st.experimental_rerun()

# --- Funções Firebase ---
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
        email = st.text_input("E-mail")
        password = st.text_input("Senha", type="password")
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
                # Verificar e-mail
                url_verify = f"https://identitytoolkit.googleapis.com/v1/accounts:lookup?key={API_KEY}"
                payload_verify = {"idToken": st.session_state.id_token}
                response_verify = requests.post(url_verify, json=payload_verify)
                if response_verify.status_code == 200:
                    is_email_verified = response_verify.json()['users'][0]['emailVerified']
                    if is_email_verified:
                        navigate_to('home')
                    else:
                        show_message("Atenção", "Verifique seu e-mail antes de fazer login.", "error")
                        st.session_state.show_resend_button = True
                else:
                    show_message("Erro", "Erro ao verificar e-mail.", "error")
            else:
                show_message("Erro", "Erro ao fazer login. Verifique e-mail e senha.", "error")

    st.markdown("---")
    if st.button("Criar uma conta"):
        navigate_to('cadastro')
    if st.button("Esqueceu a senha?"):
        st.session_state.show_reset_form = True
    if st.session_state.show_reset_form:
        with st.form("reset_form"):
            email_reset = st.text_input("Informe seu e-mail para recuperar a senha:")
            reset_btn = st.form_submit_button("Enviar")
            if reset_btn and email_reset:
                reset_password(email_reset)
                show_message("Sucesso", "E-mail de recuperação enviado!")
                st.session_state.show_reset_form = False

def cadastro_page():
    st.markdown("<h2 style='text-align: center;'>Cadastro</h2>", unsafe_allow_html=True)
    with st.form("cadastro_form"):
        nome = st.text_input("Nome")
        sobrenome = st.text_input("Sobrenome")
        telefone = st.text_input("Telefone (com DDD)")
        email = st.text_input("E-mail")
        senha = st.text_input("Senha", type="password")
        cadastro_btn = st.form_submit_button("Cadastrar")

    if cadastro_btn:
        if not all([nome, sobrenome, telefone, email, senha]):
            show_message("Atenção", "Preencha todos os campos.", "error")
        else:
            response = signup_user(email, senha)
            if response.status_code == 200:
                data = response.json()
                st.session_state.id_token = data['idToken']
                st.session_state.local_id = data['localId']
                save_user_data_to_db(st.session_state.local_id, st.session_state.id_token, {
                    "nome": nome, "sobrenome": sobrenome, "telefone": telefone, "email": email
                })
                send_verification_email(st.session_state.id_token)
                show_message("Sucesso", "Cadastro realizado! Verifique seu e-mail.")
                navigate_to('login')
            else:
                show_message("Erro", "Erro ao cadastrar. E-mail pode já estar em uso.", "error")
    if st.button("Já tem conta? Login"):
        navigate_to('login')

def home_page():
    """Home com painel de ações"""
    # Carregar dados do usuário
    if not st.session_state.user_info and st.session_state.id_token:
        response = get_user_data_from_db(st.session_state.local_id, st.session_state.id_token)
        if response.status_code == 200:
            st.session_state.user_info = response.json()

    user_name = st.session_state.user_info.get('nome', '')
    st.markdown(f"<h2 style='text-align: center; color: #4B0082;'>Bem-vindo, {user_name}!</h2>", unsafe_allow_html=True)

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

    # Painel de Ações
    df = pd.DataFrame({
        'Ações': ['ITUB4', 'PETR4', 'VALE3', 'BBDC4', 'ABEV3'],
        'Preço': [25.3, 30.5, 88.7, 23.1, 15.4]
    })

    lista_acoes = st.sidebar.multiselect(
        "Escolha as ações:",
        options=df['Ações'],
        default=df['Ações'].tolist()
    )
    df_selecionadas = df[df['Ações'].isin(lista_acoes)]

    st.subheader("Resumo das Ações Selecionadas")
    if not df_selecionadas.empty:
        max_cols = 3
        for i in range(0, len(df_selecionadas), max_cols):
            chunk = df_selecionadas.iloc[i:i+max_cols]
            cols = st.columns(len(chunk))
            for col, (_, row) in zip(cols, chunk.iterrows()):
                with col:
                    st.markdown(f"""
                        <div style="background-color:#E6E6FA; padding:15px; border-radius:10px; text-align:center; 
                                    box-shadow:2px 2px 5px rgba(0,0,0,0.2);">
                            <h3 style='margin:0;'>{row['Ações']}</h3>
                            <p style='font-size:20px; color:#4B0082;'><b>R$ {row['Preço']}</b></p>
                        </div>
                    """, unsafe_allow_html=True)
    else:
        st.info("Selecione ao menos uma ação.")

    st.markdown("---")
    st.subheader("Gráfico de Preço das Ações Selecionadas")
    if not df_selecionadas.empty:
        st.bar_chart(df_selecionadas.set_index('Ações')['Preço'], use_container_width=True)
    else:
        st.info("Nenhuma ação selecionada para o gráfico.")

def perfil_page():
    st.markdown("<h2 style='text-align: center;'>Perfil</h2>", unsafe_allow_html=True)

    if not st.session_state.user_info:
        response = get_user_data_from_db(st.session_state.local_id, st.session_state.id_token)
        if response.status_code == 200:
            st.session_state.user_info = response.json()

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
                    display:block;
                    margin:0 auto;
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
            photo_data = uploaded_file.getvalue()
            response = upload_profile_photo(st.session_state.local_id, photo_data)
            if response.status_code in (200,201):
                link_foto = f"https://firebasestorage.googleapis.com/v0/b/{STORAGE_BUCKET}/o/{st.session_state.local_id}.jpg?alt=media&time={int(time.time())}"
                save_user_data_to_db(st.session_state.local_id, st.session_state.id_token, {"foto_perfil": link_foto})
                st.session_state.user_info['foto_perfil'] = link_foto
                show_message("Sucesso", "Foto de perfil atualizada.")

        st.markdown("</div>", unsafe_allow_html=True)

    with st.form("perfil_form"):
        nome = st.text_input("Nome", value=st.session_state.user_info.get('nome',''))
        sobrenome = st.text_input("Sobrenome", value=st.session_state.user_info.get('sobrenome',''))
        telefone = st.text_input("Telefone (com DDD)", value=st.session_state.user_info.get('telefone',''))
        nova_senha = st.text_input("Nova Senha (opcional)", type="password")
        save_btn = st.form_submit_button("Salvar Alterações")

    if save_btn:
        if not all([nome, sobrenome, telefone]):
            show_message("Atenção", "Preencha todos os campos.", "error")
        else:
            save_user_data_to_db(st.session_state.local_id, st.session_state.id_token, {"nome":nome,"sobrenome":sobrenome,"telefone":telefone})
            if nova_senha:
                update_password(st.session_state.id_token, nova_senha)
            st.session_state.user_info.update({"nome":nome,"sobrenome":sobrenome,"telefone":telefone})
            show_message("Sucesso", "Dados atualizados!")

    if st.button("Voltar"):
        navigate_to('home')

# --- Main ---
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
