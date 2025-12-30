import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

# --- CONFIGURAÇÃO ---
st.set_page_config(page_title="Sistema TeamBrisa", layout="wide")

# --- CONEXÃO GOOGLE SHEETS ---
def conectar_google_sheets():
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    credentials = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scopes)
    gc = gspread.authorize(credentials)
    return gc

def carregar_dados(aba):
    try:
        gc = conectar_google_sheets()
        sh = gc.open("Sistema_Vendas") # Nome da sua planilha
        worksheet = sh.worksheet(aba)
        dados = worksheet.get_all_records()
        return pd.DataFrame(dados)
    except Exception as e:
        st.error(f"Erro ao carregar dados: {e}")
        return pd.DataFrame()

# --- TELA DE LOGIN ---
def login():
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        st.title("🔒 Acesso TeamBrisa")
        usuario = st.text_input("Usuário")
        senha = st.text_input("Senha", type="password")
        
        if st.button("Entrar"):
            df_users = carregar_dados("Usuarios")
            if not df_users.empty:
                # Converte senha para string para garantir a comparação
                df_users['Senha'] = df_users['Senha'].astype(str)
                user = df_users[(df_users['Usuario'] == usuario) & (df_users['Senha'] == str(senha))]
                
                if not user.empty:
                    st.session_state['logado'] = True
                    st.session_state['usuario'] = user.iloc[0]['Nome']
                    st.session_state['funcao'] = user.iloc[0]['Funcao']
                    st.rerun()
                else:
                    st.error("Acesso negado.")

# --- PAINEL PRINCIPAL ---
def main():
    st.sidebar.title(f"👤 {st.session_state['usuario']}")
    if st.sidebar.button("Sair"):
        st.session_state['logado'] = False
        st.rerun()

    df_vendas = carregar_dados("Vendas")
    
    # Filtro de Segurança
    if st.session_state['funcao'] != 'admin':
        df_vendas = df_vendas[df_vendas['Vendedor'] == st.session_state['usuario']]
    
    # Dashboard
    st.title("📊 Painel de Controle")
    
    # Métricas
    if not df_vendas.empty:
        total = df_vendas['Valor'].sum()
        st.metric("Total de Vendas", f"R$ {total:,.2f}")
        
        # Gráficos
        col1, col2 = st.columns(2)
        col1.subheader("Vendas por Produto")
        col1.bar_chart(df_vendas, x='Produto', y='Valor')
        
        col2.subheader("Histórico")
        col2.dataframe(df_vendas)
    else:
        st.info("Nenhuma venda encontrada para o seu perfil.")

# --- CONTROLE ---
if 'logado' not in st.session_state:
    st.session_state['logado'] = False

if not st.session_state['logado']:
    login()
else:
    main()
