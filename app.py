import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

# --- CONFIGURAÇÃO ---
st.set_page_config(page_title="Sistema TeamBrisa", layout="wide")

# --- CONEXÃO GOOGLE SHEETS ---
def conectar_google_sheets():
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    
    # 1. Carrega as credenciais e corrige a chave
    credenciais_info = dict(st.secrets["gcp_service_account"])
    credenciais_info["private_key"] = credenciais_info["private_key"].replace("\\n", "\n")
    
    # 2. Autoriza
    credentials = Credentials.from_service_account_info(credenciais_info, scopes=scopes)
    gc = gspread.authorize(credentials)
    return gc

def carregar_dados(aba):
    try:
        gc = conectar_google_sheets()
        sh = gc.open("Sistema_Vendas") # Nome da planilha
        worksheet = sh.worksheet(aba)
        dados = worksheet.get_all_records()
        return pd.DataFrame(dados)
    except Exception as e:
        # Se der erro (ex: aba não existe), retorna vazio para não quebrar o site
        return pd.DataFrame()

# --- TELA DE LOGIN ---
def login():
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        st.title("🔒 Acesso TeamBrisa")
        usuario = st.text_input("Usuário")
        senha = st.text_input("Senha", type="password")
        
        if st.button("Entrar"):
            with st.spinner("Verificando acesso..."):
                df_users = carregar_dados("Usuarios")
                
                if not df_users.empty:
                    # Garante que a senha seja lida como texto
                    df_users['Senha'] = df_users['Senha'].astype(str)
                    
                    # Filtra o usuário
                    user = df_users[(df_users['Usuario'] == usuario) & (df_users['Senha'] == str(senha))]
                    
                    if not user.empty:
                        st.session_state['logado'] = True
                        st.session_state['usuario'] = user.iloc[0]['Nome']
                        st.session_state['funcao'] = user.iloc[0]['Funcao']
                        st.rerun()
                    else:
                        st.error("Usuário ou senha incorretos.")
                else:
                    st.error("Erro ao carregar base de usuários.")

# --- PAINEL PRINCIPAL ---
def main():
    # Menu Lateral
    st.sidebar.title(f"Olá, {st.session_state['usuario']} 👋")
    st.sidebar.markdown(f"**Cargo:** {st.session_state['funcao']}")
    
    if st.sidebar.button("Sair"):
        st.session_state['logado'] = False
        st.rerun()

    # Carrega Vendas
    df_vendas = carregar_dados("Vendas")
    
    st.title("📊 Dashboard de Vendas")
    
    if not df_vendas.empty:
        # --- TRATAMENTO DE DADOS (Blindagem) ---
        # Garante que a coluna Valor seja numérica (remove R$ e troca vírgula por ponto)
        if 'Valor' in df_vendas.columns:
            # Converte para string primeiro, remove simbolos, converte para float
            df_vendas['Valor'] = df_vendas['Valor'].astype(str).str.replace('R$', '', regex=False)
            df_vendas['Valor'] = df_vendas['Valor'].str.replace('.', '', regex=False) # Tira ponto de milhar
            df_vendas['Valor'] = df_vendas['Valor'].str.replace(',', '.', regex=False) # Troca vírgula decimal
            df_vendas['Valor'] = pd.to_numeric(df_vendas['Valor'])

        # --- FILTRO DE SEGURANÇA ---
        # Se não for admin, só vê as próprias vendas
        if st.session_state['funcao'].lower() != 'admin':
            df_vendas = df_vendas[df_vendas['Vendedor'] == st.session_state['usuario']]

        # --- VISUALIZAÇÃO ---
        total = df_vendas['Valor'].sum()
        qtde = len(df_vendas)
        
        # Métricas
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Vendido", f"R$ {total:,.2f}")
        col2.metric("Quantidade Vendas", qtde)
        
        st.markdown("---")
        
        # Gráficos e Tabelas
        col_g, col_t = st.columns([2, 1])
        
        with col_g:
            st.subheader("Vendas por Produto")
            st.bar_chart(df_vendas, x='Produto', y='Valor')
            
        with col_t:
            st.subheader("Histórico Recente")
            st.dataframe(df_vendas[['Data', 'Produto', 'Valor']].head(10))
            
    else:
        st.warning("⚠️ Nenhuma venda encontrada. Verifique se a aba 'Vendas' existe na planilha.")
        st.info("Colunas esperadas na planilha: Data, Vendedor, Produto, Valor")

# --- CONTROLE DE FLUXO ---
if 'logado' not in st.session_state:
    st.session_state['logado'] = False

if not st.session_state['logado']:
    login()
else:
    main()
