import streamlit as st
import requests
import time
import base64

# Carregando as chaves do Firebase de forma segura usando st.secrets
# Para isso, você deve criar um arquivo .streamlit/secrets.toml com as chaves.
try:
    API_KEY = st.secrets["firebase"]["api_key"]
    PROJECT_URL = st.secrets["firebase"]["project_url"]
    STORAGE_BUCKET = st.secrets["firebase"]["storage_bucket"]
except KeyError:
    st.error("As chaves do Firebase não foram encontradas. Por favor, adicione-as ao arquivo `.streamlit/secrets.toml`.")
    st.stop()


# --- Gerenciamento de Estado (Substituindo o Gerenciador de Telas do Kivy) ---
# Este dicionário armazena variáveis que persistem entre as execuções do aplicativo.
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
    """Exibe uma caixa de mensagem na página."""
    if type == "error":
        st.error(f"**{title}**\n\n{message}")
    else:
        st.info(f"**{title}**\n\n{message}")

def navigate_to(page_name):
    """Muda a página atual e re-executa o aplicativo."""
    st.session_state.page = page_name
    st.rerun()

# --- Chamadas da API do Firebase ---
def login_user(email, password):
    """Lida com o login do usuário usando a Autenticação do Firebase."""
    url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={API_KEY}"
    payload = {"email": email, "password": password, "returnSecureToken": True}
    response = requests.post(url, json=payload)
    return response

def signup_user(email, password):
    """Lida com o registro de usuário usando a Autenticação do Firebase."""
    url = f"https://identitytoolkit.googleapis.com/v1/accounts:signUp?key={API_KEY}"
    payload = {"email": email, "password": password, "returnSecureToken": True}
    response = requests.post(url, json=payload)
    return response

def send_verification_email(id_token):
    """Envia um e-mail de verificação para o usuário."""
    url = f"https://identitytoolkit.googleapis.com/v1/accounts:sendOobCode?key={API_KEY}"
    payload = {"requestType": "VERIFY_EMAIL", "idToken": id_token}
    requests.post(url, json=payload)

def update_password(id_token, new_password):
    """Atualiza a senha do usuário."""
    url = f"https://identitytoolkit.googleapis.com/v1/accounts:update?key={API_KEY}"
    payload = {"idToken": id_token, "password": new_password, "returnSecureToken": True}
    response = requests.post(url, json=payload)
    return response

def reset_password(email):
    """Envia um e-mail de redefinição de senha."""
    url = f"https://identitytoolkit.googleapis.com/v1/accounts:sendOobCode?key={API_KEY}"
    payload = {"requestType": "PASSWORD_RESET", "email": email}
    requests.post(url, json=payload)

def upload_profile_photo(local_id, photo_data):
    """Envia uma foto de perfil para o Firebase Storage."""
    url = f"https://firebasestorage.googleapis.com/v0/b/{STORAGE_BUCKET}/o?uploadType=media&name={local_id}.jpg"
    headers = {"Content-Type": "image/jpeg"}
    response = requests.post(url, headers=headers, data=photo_data)
    return response

def save_user_data_to_db(local_id, id_token, data):
    """Salva ou atualiza os dados do usuário no Firebase Realtime Database."""
    url = f"{PROJECT_URL}/usuarios/{local_id}.json?auth={id_token}"
    response = requests.patch(url, json=data)
    return response

def get_user_data_from_db(local_id, id_token):
    """Busca os dados do usuário no Firebase Realtime Database."""
    url = f"{PROJECT_URL}/usuarios/{local_id}.json?auth={id_token}"
    response = requests.get(url)
    return response

# --- Telas do Aplicativo ---
def login_page():
    """Renderiza a página de login."""
    st.markdown("<h2 style='text-align: center;'>Login</h2>", unsafe_allow_html=True)
    with st.form("login_form"):
        email = st.text_input("E-mail", placeholder="E-mail")
        password = st.text_input("Senha", placeholder="Senha", type="password")
        login_button = st.form_submit_button("Entrar")

    # Botões fora do formulário para evitar o erro "StreamlitAPIException"
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
                    
                    # Verifica o status do e-mail
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
                    show_message("Erro", "Erro ao fazer login. Verifique seu e-mail e senha.", "error")

    # Botões de navegação e recuperação de senha fora do formulário de login
    st.markdown("---") # Separador visual para melhor organização
    if st.button("Criar uma conta"):
        navigate_to('cadastro')

    if st.button("Reenviar verificação de e-mail"):
        if st.session_state.id_token:
            send_verification_email(st.session_state.id_token)
            show_message("Sucesso", "E-mail de verificação reenviado.")
        else:
            show_message("Atenção", "Faça login primeiro para reenviar o e-mail.")

    if st.button("Esqueceu a senha?"):
        st.session_state.show_reset_form = True

    if st.session_state.show_reset_form:
        email_to_reset = st.text_input("Informe seu e-mail para recuperar a senha:")
        if st.button("Enviar e-mail de recuperação"):
            if not email_to_reset:
                show_message("Atenção", "Informe seu e-mail.")
            else:
                reset_password(email_to_reset)
                show_message("Sucesso", "E-mail de recuperação enviado! Verifique sua caixa de entrada.")
                st.session_state.show_reset_form = False

def cadastro_page():
    """Renderiza a página de cadastro."""
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
                    
                    user_data = {
                        "nome": nome,
                        "sobrenome": sobrenome,
                        "telefone": telefone,
                        "email": email,
                    }
                    
                    save_response = save_user_data_to_db(st.session_state.local_id, st.session_state.id_token, user_data)
                    if save_response.status_code == 200:
                        send_verification_email(st.session_state.id_token)
                        show_message("Sucesso", "Cadastro realizado! Verifique seu e-mail para continuar.")
                        navigate_to('login')
                    else:
                        show_message("Erro", "Erro ao salvar dados do usuário.", "error")
                else:
                    show_message("Erro", "Erro ao cadastrar. Verifique se o e-mail já está em uso.", "error")

    # Botão de navegação fora do formulário de cadastro
    if st.button("Já tem uma conta? Login"):
        navigate_to('login')

def home_page():
    """Renderiza a página inicial."""
    user_name = st.session_state.user_info.get('nome', '')
    st.markdown(f"<h2 style='text-align: center;'>Bem-vindo, {user_name}!</h2>", unsafe_allow_html=True)
    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("Ver Perfil"):
            navigate_to('perfil')
    with col2:
        if st.button("Sair"):
            st.session_state.id_token = None
            st.session_state.local_id = None
            st.session_state.user_info = {}
            navigate_to('login')

def perfil_page():
    """Renderiza a página de perfil do usuário."""
    st.markdown("<h2 style='text-align: center;'>Perfil</h2>", unsafe_allow_html=True)

    # Carrega os dados do usuário
    if not st.session_state.user_info:
        with st.spinner("Carregando perfil..."):
            response = get_user_data_from_db(st.session_state.local_id, st.session_state.id_token)
            if response.status_code == 200:
                st.session_state.user_info = response.json()
            else:
                show_message("Erro", "Erro ao carregar perfil.", "error")
                st.session_state.user_info = {}

    # Seção da foto de perfil
    # Usando o st.container para centralizar os elementos
    with st.container():
        st.markdown("<div style='text-align: center;'>", unsafe_allow_html=True)
        photo_url = st.session_state.user_info.get('foto_perfil')
        
        # CSS para a imagem redonda e maior
        css_style = """
            <style>
                .profile-picture {
                    border-radius: 50%;
                    width: 200px; /* Aumenta o tamanho da imagem */
                    height: 200px; /* Aumenta o tamanho da imagem */
                    object-fit: cover;
                    border: 3px solid #ddd;
                    box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
                }
            </style>
        """
        st.markdown(css_style, unsafe_allow_html=True)

        # Exibe a foto de perfil com a classe CSS
        if photo_url:
            st.markdown(f'<img src="{photo_url}" class="profile-picture" alt="Foto de Perfil">', unsafe_allow_html=True)
        else:
            st.markdown('<img src="https://placehold.co/200x200?text=Sem+Foto" class="profile-picture" alt="Sem Foto">', unsafe_allow_html=True)
        
        # Exibe o nome completo do usuário
        full_name = f"{st.session_state.user_info.get('nome', '')} {st.session_state.user_info.get('sobrenome', '')}"
        st.markdown(f"<h3 style='text-align: center;'>{full_name}</h3>", unsafe_allow_html=True)
        
        st.markdown("</div>", unsafe_allow_html=True)

        # Move a opção de carregar a foto para baixo da imagem de perfil
        uploaded_file = st.file_uploader("Alterar Foto de Perfil", type=["jpg", "jpeg", "png"])
        if uploaded_file:
            with st.spinner("Enviando foto..."):
                photo_data = uploaded_file.getvalue()
                response = upload_profile_photo(st.session_state.local_id, photo_data)
                if response.status_code in (200, 201):
                    link_foto = f"https://firebasestorage.googleapis.com/v0/b/{STORAGE_BUCKET}/o/{st.session_state.local_id}.jpg?alt=media&time={int(time.time())}"
                    save_response = save_user_data_to_db(st.session_state.local_id, st.session_state.id_token, {"foto_perfil": link_foto})
                    if save_response.status_code == 200:
                        st.session_state.user_info['foto_perfil'] = link_foto
                        show_message("Sucesso", "Foto de perfil atualizada.")
                    else:
                        show_message("Erro", "Erro ao salvar link da foto no banco.", "error")
                else:
                    show_message("Erro", f"Erro ao enviar foto: {response.text}", "error")

    # Formulário de dados do perfil
    with st.form("perfil_form"):
        nome = st.text_input("Nome", value=st.session_state.user_info.get('nome', ''))
        sobrenome = st.text_input("Sobrenome", value=st.session_state.user_info.get('sobrenome', ''))
        telefone = st.text_input("Telefone (com DDD)", value=st.session_state.user_info.get('telefone', ''))
        nova_senha = st.text_input("Nova Senha (opcional)", type="password")
        
        save_button = st.form_submit_button("Salvar Alterações")

    if save_button:
        if not all([nome, sobrenome, telefone]):
            show_message("Atenção", "Preencha nome, sobrenome e telefone.", "error")
        else:
            with st.spinner("Salvando dados..."):
                updated_data = {
                    "nome": nome,
                    "sobrenome": sobrenome,
                    "telefone": telefone,
                }
                save_response = save_user_data_to_db(st.session_state.local_id, st.session_state.id_token, updated_data)
                
                if save_response.status_code == 200:
                    if nova_senha:
                        update_response = update_password(st.session_state.id_token, nova_senha)
                        if update_response.status_code == 200:
                            st.session_state.id_token = update_response.json()['idToken']
                            show_message("Sucesso", "Dados e senha atualizados!")
                        else:
                            show_message("Erro", "Erro ao atualizar senha.", "error")
                    else:
                        show_message("Sucesso", "Dados atualizados!")
                    st.session_state.user_info = updated_data
                else:
                    show_message("Erro", "Erro ao salvar dados.", "error")
    
    if st.button("Voltar"):
        navigate_to('home')


# --- Lógica Principal do Aplicativo ---
def main():
    """Função principal para renderizar a página atual."""
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
        # Redireciona para o login se não estiver autenticado ou a página for inválida
        navigate_to('login')

if __name__ == "__main__":
    main()
