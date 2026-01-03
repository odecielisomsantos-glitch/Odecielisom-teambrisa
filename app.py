import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from streamlit_option_menu import option_menu # Importamos a biblioteca nova

# --- 1. CONFIGURAÇÃO ---
st.set_page_config(page_title="Sistema TeamBrisa", layout="wide", page_icon="☁️")

# --- 2. CONEXÃO E BANCO DE DADOS ---
def conectar_google_sheets():
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    
    # Corrige a chave privada (\n) para funcionar no Streamlit Cloud
    credenciais_info = dict(st.secrets["gcp_service_account"])
    credenciais_info["private_key"] = credenciais_info["private_key"].replace("\\n", "\n")
    
    credentials = Credentials.from_service_account_info(credenciais_info, scopes=scopes)
    gc = gspread.authorize(credentials)
    return gc

def carregar_dados(aba):
    try:
        gc = conectar_google_sheets()
        sh = gc.open("Sistema_Vendas") 
        worksheet = sh.worksheet(aba)
        dados = worksheet.get_all_records()
        return pd.DataFrame(dados)
    except Exception as e:
        return pd.DataFrame()

def salvar_venda(venda):
    try:
        gc = conectar_google_sheets()
        sh = gc.open("Sistema_Vendas")
        worksheet = sh.worksheet("Vendas")
        worksheet.append_row(venda)
        return True
    except Exception as e:
        st.error(f"Erro ao salvar no Google Sheets: {e}")
        return False

# --- 3. TELA DE LOGIN ---
def login():
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.title("🔒 Acesso TeamBrisa")
        st.markdown("---")
        usuario = st.text_input("Usuário")
        senha = st.text_input("Senha", type="password")
        
        if st.button("Entrar no Sistema", use_container_width=True):
            with st.spinner("Validando credenciais..."):
                df_users = carregar_dados("Usuarios")
                
                if not df_users.empty:
                    df_users['Senha'] = df_users['Senha'].astype(str)
                    user = df_users[(df_users['Usuario'] == usuario) & (df_users['Senha'] == str(senha))]
                    
                    if not user.empty:
                        st.session_state['logado'] = True
                        st.session_state['usuario'] = user.iloc[0]['Nome']
                        st.session_state['funcao'] = user.iloc[0]['Funcao']
                        st.rerun() 
                    else:
                        st.error("Usuário ou senha incorretos.")
                else:
                    st.error("Erro ao conectar com a base de usuários.")

# --- 4. PAINEL PRINCIPAL (CÉREBRO DO SISTEMA) ---
def main():
    # --- A. CARREGAMENTO E LIMPEZA ---
    df_vendas = carregar_dados("Vendas")
    
    if df_vendas.empty:
        df_vendas = pd.DataFrame(columns=["Data", "Vendedor", "Cliente", "Produto", "Valor", "Status"])
    else:
        df_vendas.columns = df_vendas.columns.str.strip()

    if 'Valor' in df_vendas.columns:
        df_vendas['Valor'] = df_vendas['Valor'].astype(str).str.replace('R$', '', regex=False)
        df_vendas['Valor'] = df_vendas['Valor'].str.replace('.', '', regex=False)
        df_vendas['Valor'] = df_vendas['Valor'].str.replace(',', '.', regex=False)
        df_vendas['Valor'] = pd.to_numeric(df_vendas['Valor'], errors='coerce').fillna(0.0)

    # --- B. BARRA LATERAL (MENU MODERNO) ---
    with st.sidebar:
        # Título Personalizado
        st.markdown(f"<h2 style='text-align: center;'>☁️ TeamBrisa</h2>", unsafe_allow_html=True)
        st.markdown(f"<p style='text-align: center;'>Olá, <b>{st.session_state['usuario']}</b></p>", unsafe_allow_html=True)
        st.markdown("---")

        cargo = st.session_state['funcao'].lower()
        
        # DEFINIÇÃO DOS BOTÕES DO MENU
        # Se for admin, tem 3 opções. Se for vendedor, tem 2.
        if cargo == 'admin':
            opcoes = ["Dashboard", "Nova Venda", "Banco de Dados"]
            icones = ["graph-up", "cart-plus", "table"] # Ícones do Bootstrap
        else:
            opcoes = ["Dashboard", "Nova Venda"]
            icones = ["graph-up", "cart-plus"]

        # O COMPONENTE DE MENU VISUAL
        escolha = option_menu(
            menu_title=None,          # Esconde o título padrão
            options=opcoes,           # As opções que definimos acima
            icons=icones,             # Os ícones
            menu_icon="cast",         # Ícone do menu
            default_index=0,          # Começa no primeiro item
            styles={
                "container": {"padding": "0!important", "background-color": "#f0f2f6"},
                "icon": {"color": "orange", "font-size": "20px"}, 
                "nav-link": {"font-size": "16px", "text-align": "left", "margin":"5px", "--hover-color": "#eee"},
                "nav-link-selected": {"background-color": "#2C3E50"}, # Cor quando selecionado
            }
        )
        
        # Filtros (Só Admin e só na tela de Dashboard)
        st.markdown("---")
        filtro_vendedor = "Todos"
        if escolha == "Dashboard" and cargo == 'admin':
            st.markdown("🔍 **Filtros Avançados**")
            vendedores = ["Todos"] + list(df_vendas['Vendedor'].unique())
            filtro_vendedor = st.selectbox("Vendedor:", vendedores)

        if st.button("Sair", use_container_width=True):
            st.session_state['logado'] = False
            st.rerun()

    # --- C. LÓGICA DAS TELAS ---
    
    # 1. TELA DASHBOARD
    if escolha == "Dashboard":
        st.title("📊 Painel de Controle")
        
        df_filtrado = df_vendas.copy()
        if filtro_vendedor != "Todos":
            df_filtrado = df_filtrado[df_filtrado['Vendedor'] == filtro_vendedor]
        
        if cargo != 'admin':
            df_filtrado = df_filtrado[df_filtrado['Vendedor'] == st.session_state['usuario']]

        if not df_filtrado.empty:
            total = df_filtrado['Valor'].sum()
            
            c1, c2 = st.columns(2)
            c1.metric("Faturamento Total", f"R$ {total:,.2f}")
            c2.metric("Vendas Realizadas", len(df_filtrado))
            
            st.markdown("---")
            
            col_g, col_t = st.columns([2, 1])
            
            with col_g:
                st.subheader("Vendas por Produto")
                dados_prod = df_filtrado.groupby("Produto")["Valor"].sum()
                st.bar_chart(dados_prod)
            
            with col_t:
                st.subheader("Histórico")
                st.dataframe(df_filtrado[['Data', 'Cliente', 'Valor']].head(5), use_container_width=True)
                
                st.markdown("---")
                st.subheader("Tendência")
                try:
                    df_chart = df_filtrado.copy()
                    df_chart['Data_Clean'] = pd.to_datetime(df_chart['Data'], format='%d/%m/%Y', errors='coerce')
                    grafico_linha = df_chart.groupby('Data_Clean')['Valor'].sum()
                    if not grafico_linha.empty:
                        st.line_chart(grafico_linha)
                    else:
                        st.info("Sem dados temporais.")
                except:
                    st.warning("Erro no gráfico de linha.")

        else:
            st.warning("Nenhum dado encontrado.")

    # 2. TELA NOVA VENDA
    elif escolha == "Nova Venda":
        st.title("📝 Registrar Nova Venda")
        
        with st.container(border=True):
            with st.form("form_venda"):
                c1, c2 = st.columns(2)
                data = c1.date_input("Data")
                cliente = c1.text_input("Cliente")
                produto = c2.selectbox("Produto", ["Consultoria", "Sistema", "Manutenção", "Outros"])
                valor = c2.number_input("Valor (R$)", min_value=0.0, format="%.2f")
                
                if st.form_submit_button("💾 Confirmar Venda", use_container_width=True):
                    nova = [
                        data.strftime("%d/%m/%Y"),
                        st.session_state['usuario'],
                        cliente,
                        produto,
                        float(valor),
                        "Pendente"
                    ]
                    if salvar_venda(nova):
                        st.success("Sucesso!")
    
    # 3. TELA BANCO DE DADOS
    elif escolha == "Banco de Dados":
        st.title("📂 Dados Brutos")
        st.dataframe(df_vendas, use_container_width=True)

# --- 5. CONTROLE DE FLUXO ---
if 'logado' not in st.session_state:
    st.session_state['logado'] = False

if not st.session_state['logado']:
    login()
else:
    main()
