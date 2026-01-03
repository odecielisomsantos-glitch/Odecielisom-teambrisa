import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from streamlit_option_menu import option_menu

# --- 1. CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Sistema TeamBrisa", layout="wide", page_icon="☁️")

# --- 2. FUNÇÕES DE BANCO DE DADOS ---

def conectar_google_sheets():
    """Conecta ao Google Sheets usando as credenciais do Streamlit Secrets."""
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    
    credenciais_info = dict(st.secrets["gcp_service_account"])
    credenciais_info["private_key"] = credenciais_info["private_key"].replace("\\n", "\n")
    
    credentials = Credentials.from_service_account_info(credenciais_info, scopes=scopes)
    gc = gspread.authorize(credentials)
    return gc

def carregar_dados(aba):
    """Carrega todos os dados de uma aba específica."""
    try:
        gc = conectar_google_sheets()
        sh = gc.open("Sistema_Vendas") 
        worksheet = sh.worksheet(aba)
        dados = worksheet.get_all_records()
        return pd.DataFrame(dados)
    except Exception:
        return pd.DataFrame()

def carregar_ranking():
    """Busca o ranking específico na aba DADOS-DIA, intervalo F3:G25."""
    try:
        gc = conectar_google_sheets()
        sh = gc.open("Sistema_Vendas")
        # Pega o intervalo fixo
        dados = sh.worksheet("DADOS-DIA").get("F3:G25")
        # Cria DataFrame manual
        df = pd.DataFrame(dados, columns=["Operador", "Performance"])
        return df
    except Exception:
        return pd.DataFrame()

def salvar_venda(venda):
    """Salva uma nova venda na aba 'Vendas'."""
    try:
        gc = conectar_google_sheets()
        sh = gc.open("Sistema_Vendas")
        worksheet = sh.worksheet("Vendas")
        worksheet.append_row(venda)
        return True
    except Exception as e:
        st.error(f"Erro ao salvar: {e}")
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
            with st.spinner("Verificando..."):
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
                        st.error("Dados incorretos.")
                else:
                    st.error("Erro na conexão com usuários.")

# --- 4. SISTEMA PRINCIPAL ---
def main():
    # --- A. PREPARAÇÃO DOS DADOS ---
    df_vendas = carregar_dados("Vendas")
    
    if df_vendas.empty:
        df_vendas = pd.DataFrame(columns=["Data", "Vendedor", "Cliente", "Produto", "Valor", "Status"])
    else:
        # Limpeza de nomes de colunas (Remove espaços extras)
        df_vendas.columns = df_vendas.columns.str.strip()

    # Tratamento da coluna Valor (R$ -> Número)
    if 'Valor' in df_vendas.columns:
        df_vendas['Valor'] = df_vendas['Valor'].astype(str).str.replace('R$', '', regex=False)
        df_vendas['Valor'] = df_vendas['Valor'].str.replace('.', '', regex=False)
        df_vendas['Valor'] = df_vendas['Valor'].str.replace(',', '.', regex=False)
        df_vendas['Valor'] = pd.to_numeric(df_vendas['Valor'], errors='coerce').fillna(0.0)

    # --- B. BARRA LATERAL (MENU) ---
    with st.sidebar:
        st.markdown(f"<h2 style='text-align: center;'>☁️ TeamBrisa</h2>", unsafe_allow_html=True)
        st.markdown(f"<div style='text-align: center;'>Olá, <b>{st.session_state['usuario']}</b></div>", unsafe_allow_html=True)
        st.markdown("---")

        cargo = st.session_state['funcao'].lower()
        
        # Definição das opções
        if cargo == 'admin':
            opcoes = ["Dashboard", "Nova Venda", "Banco de Dados"]
            icones = ["graph-up", "cart-plus", "table"] 
        else:
            opcoes = ["Dashboard", "Nova Venda"]
            icones = ["graph-up", "cart-plus"]

        # Componente Visual do Menu
        escolha = option_menu(
            menu_title=None,          
            options=opcoes,           
            icons=icones,             
            menu_icon="cast",         
            default_index=0,          
            styles={
                "container": {"padding": "0!important", "background-color": "#f0f2f6"},
                "icon": {"color": "orange", "font-size": "20px"}, 
                "nav-link": {"font-size": "16px", "text-align": "left", "margin":"5px", "--hover-color": "#eee"},
                "nav-link-selected": {"background-color": "#2C3E50"},
            }
        )
        
        # Filtros (Apenas Admin e no Dashboard)
        st.markdown("---")
        filtro_vendedor = "Todos"
        if escolha == "Dashboard" and cargo == 'admin':
            st.caption("Filtros Gerenciais")
            if 'Vendedor' in df_vendas.columns:
                vendedores = ["Todos"] + list(df_vendas['Vendedor'].unique())
                filtro_vendedor = st.selectbox("Filtrar Vendedor:", vendedores)

        if st.button("Sair", use_container_width=True):
            st.session_state['logado'] = False
            st.rerun()

    # --- C. TELAS DO SISTEMA ---
    
    # >> TELA 1: DASHBOARD (Gráficos + Ranking)
    if escolha == "Dashboard":
        st.title("📊 Painel de Controle")
        
        # Aplica filtros
        df_filtrado = df_vendas.copy()
        if filtro_vendedor != "Todos":
            df_filtrado = df_filtrado[df_filtrado['Vendedor'] == filtro_vendedor]
        
        if cargo != 'admin':
            df_filtrado = df_filtrado[df_filtrado['Vendedor'] == st.session_state['usuario']]

        if not df_filtrado.empty:
            # Cards KPI
            total = df_filtrado['Valor'].sum()
            c1, c2 = st.columns(2)
            c1.metric("Faturamento Total", f"R$ {total:,.2f}")
            c2.metric("Vendas Realizadas", len(df_filtrado))
            
            st.markdown("---")
            
            # LAYOUT: Esquerda (Gráficos) | Direita (Ranking)
            col_g, col_rank = st.columns([1.5, 1]) 
            
            with col_g:
                st.subheader("Performance de Vendas")
                # Gráfico de Barras
                dados_prod = df_filtrado.groupby("Produto")["Valor"].sum()
                st.bar_chart(dados_prod)
                
                st.markdown("<br>", unsafe_allow_html=True)
                
                # Gráfico de Linha (Tendência)
                st.subheader("Tendência Temporal")
                try:
                    df_chart = df_filtrado.copy()
                    df_chart['Data_Clean'] = pd.to_datetime(df_chart['Data'], format='%d/%m/%Y', errors='coerce')
                    grafico_linha = df_chart.groupby('Data_Clean')['Valor'].sum()
                    if not grafico_linha.empty:
                        st.line_chart(grafico_linha)
                    else:
                        st.info("Cadastre vendas em dias diferentes para ver a evolução.")
                except:
                    st.warning("Dados insuficientes para tendência.")

            with col_rank:
                st.subheader("🏆 Ranking (DADOS-DIA)")
                
                # Carrega e trata o Ranking
                df_ranking = carregar_ranking()
                
                if not df_ranking.empty:
                    # Remove erros do Excel (#N/A)
                    df_ranking = df_ranking[df_ranking['Operador'] != '#N/A']
                    df_ranking = df_ranking[df_ranking['Performance'] != '']
                    
                    # Converte porcentagem texto para número (ex: "98%" -> 0.98)
                    df_ranking['Performance'] = df_ranking['Performance'].astype(str).str.replace('%', '').str.replace(',', '.')
                    df_ranking['Performance'] = pd.to_numeric(df_ranking['Performance'], errors='coerce') / 100
                    
                    # Ordena
                    df_ranking = df_ranking.sort_values(by="Performance", ascending=False)

                    # Exibe Tabela Profissional
                    st.dataframe(
                        df_ranking,
                        use_container_width=True,
                        hide_index=True,
                        column_config={
                            "Operador": st.column_config.TextColumn("Colaborador"),
                            "Performance": st.column_config.ProgressColumn(
                                "Meta Atingida", 
                                format="%.1f%%", 
                                min_value=0, 
                                max_value=1
                            ),
                        }
                    )
                else:
                    st.info("Aguardando dados da aba DADOS-DIA...")

        else:
            st.warning("Nenhum dado de venda encontrado.")

    # >> TELA 2: NOVA VENDA
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
                        st.success("Venda registrada com sucesso!")
    
    # >> TELA 3: BANCO DE DADOS (Admin)
    elif escolha == "Banco de Dados":
        st.title("📂 Base de Dados Completa")
        st.info("Visualização bruta da aba 'Vendas'.")
        st.dataframe(df_vendas, use_container_width=True)

# --- 5. INICIALIZAÇÃO ---
if 'logado' not in st.session_state:
    st.session_state['logado'] = False

if not st.session_state['logado']:
    login()
else:
    main()
