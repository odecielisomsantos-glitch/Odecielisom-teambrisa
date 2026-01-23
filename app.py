import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(
    page_title="Team Brisa | Supervisão",
    page_icon="🌊",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- ESTILO CSS ---
st.markdown("""
<style>
    [data-testid="stAppViewContainer"] { background-color: #f8f9fa; }
    .stForm { 
        border: none; padding: 2rem; border-radius: 10px; 
        background-color: white; box-shadow: 0 4px 15px rgba(0,0,0,0.1); 
    }
    .stButton>button { 
        width: 100%; background-color: #004e92; color: white; border-radius: 5px; 
    }
</style>
""", unsafe_allow_html=True)

# --- CONEXÃO SEGURA COM A PLANILHA ---
def carregar_dados():
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        # worksheet="Usuarios" deve ser o nome exato da aba na sua planilha
        return conn.read(worksheet="Usuarios", ttl=0)
    except Exception as e:
        st.error("Erro na conexão com o Banco de Dados.")
        return None

# --- GESTÃO DE SESSÃO ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'user_role' not in st.session_state:
    st.session_state.user_role = None
if 'user_name' not in st.session_state:
    st.session_state.user_name = None

# --- TELA DE LOGIN ---
def login_page():
    col1, col2, col3 = st.columns([1, 0.8, 1])
    with col2:
        st.markdown("<br><br><br>", unsafe_allow_html=True)
        st.title("🌊 Acesso Team Brisa")
        st.write("Portal Corporativo Seguro")
        
        with st.form("login_form"):
            usuario_input = st.text_input("Usuário", placeholder="Seu login corporativo")
            senha_input = st.text_input("Senha", type="password")
            entrar = st.form_submit_button("ACESSAR")

            if entrar:
                df = carregar_dados()
                if df is not None:
                    # Converter tudo para string para evitar erros de comparação
                    df['Usuario'] = df['Usuario'].astype(str)
                    df['Senha'] = df['Senha'].astype(str)
                    
                    user_match = df[
                        (df['Usuario'] == usuario_input) & 
                        (df['Senha'] == senha_input)
                    ]
                    
                    if not user_match.empty:
                        st.session_state.logged_in = True
                        st.session_state.user_name = user_match.iloc[0]['Nome']
                        st.session_state.user_role = user_match.iloc[0]['Funcao']
                        st.rerun()
                    else:
                        st.error("Credenciais inválidas.")

# --- PAINEL GESTOR ---
def painel_gestor():
    with st.sidebar:
        st.title("Team Brisa")
        st.write(f"Olá, **{st.session_state.user_name}**")
        if st.button("Sair"):
            st.session_state.logged_in = False
            st.rerun()
    st.title("📊 Visão Geral da Supervisão")
    st.info("Acesso: Gestor Total")

# --- PAINEL OPERADOR ---
def painel_agente():
    with st.sidebar:
        st.title("Team Brisa")
        st.write(f"Olá, **{st.session_state.user_name}**")
        if st.button("Sair"):
            st.session_state.logged_in = False
            st.rerun()
    st.title("📝 Área do Colaborador")
    st.success("Bem-vindo ao seu turno.")

# --- ROTEADOR ---
if not st.session_state.logged_in:
    login_page()
else:
    role = str(st.session_state.user_role).lower().strip()
    if role == 'gestor':
        painel_gestor()
    else:
        painel_agente()
