import streamlit as st
import pandas as pd
import gspread
import plotly.express as px
from google.oauth2.service_account import Credentials
from streamlit_option_menu import option_menu

# --- 1. CONFIGURAÇÃO VISUAL DA PÁGINA ---
st.set_page_config(
    page_title="Painel Tático TeamBrisa", 
    layout="wide", 
    page_icon="☁️",
    initial_sidebar_state="expanded"
)

# Estilo CSS Personalizado para "Dar Vida" ao dashboard
st.markdown("""
<style>
    /* Fundo geral e fontes */
    .stApp {
        background-color: #0E1117;
        color: #FAFAFA;
    }
    /* Estilização da Barra Lateral */
    [data-testid="stSidebar"] {
        background-color: #161B22;
        border-right: 1px solid #30363D;
    }
    /* Títulos e Subtítulos */
    h1, h2, h3 {
        color: #E6EDF3 !important;
        font-family: 'Segoe UI', sans-serif;
    }
    /* Ajuste dos Cards de Métricas (Se houver) */
    div[data-testid="stMetricValue"] {
        font-size: 20px;
    }
</style>
""", unsafe_allow_html=True)

# --- 2. CONEXÃO E TRATAMENTO DE DADOS ---

@st.cache_resource
def conectar_google_sheets():
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    credenciais_info = dict(st.secrets["gcp_service_account"])
    credenciais_info["private_key"] = credenciais_info["private_key"].replace("\\n", "\n")
    credentials = Credentials.from_service_account_info(credenciais_info, scopes=scopes)
    gc = gspread.authorize(credentials)
    return gc

@st.cache_data(ttl=600)
def carregar_matriz_dados():
    """
    Lê a aba DADOS-DIA focando na Matriz (A27 em diante).
    Força a nomeação das colunas A e B para evitar erros de leitura.
    """
    try:
        gc = conectar_google_sheets()
        sh = gc.open("Sistema_Vendas")
        worksheet = sh.worksheet("DADOS-DIA")
        
        # Pega todos os dados da planilha
        todos_dados = worksheet.get_all_values()
        
        # --- LÓGICA DE CORTE PRECISA ---
        # A linha 27 do Excel (índice 26) contém as DATAS a partir da Coluna C
        INDICE_CABECALHO = 26 
        
        if len(todos_dados) > INDICE_CABECALHO:
            # 1. Identifica a linha de cabeçalho (Datas)
            linha_cabecalho = todos_dados[INDICE_CABECALHO] # Linha 27 original
            
            # 2. Pega os dados brutos (Linha 28 em diante)
            dados_brutos = todos_dados[INDICE_CABECALHO+1:] 
            
            # 3. Cria o DataFrame
            df = pd.DataFrame(dados_brutos)
            
            # 4. --- RENOMEAÇÃO MANUAL DAS COLUNAS (O PULO DO GATO) ---
            # Como a A27 e B27 estão vazias, vamos dar nomes fixos para elas.
            novos_nomes = ['Operador', 'Metrica'] + linha_cabecalho[2:]
            
            # Ajusta o tamanho da lista de nomes para bater com o nº de colunas do DF
            if len(df.columns) >= len(novos_nomes):
                # Se o DF tiver mais colunas (lixo no final), cortamos
                df = df.iloc[:, :len(novos_nomes)]
                df.columns = novos_nomes
            else:
                # Se o DF tiver menos colunas, ajustamos os nomes
                df.columns = novos_nomes[:len(df.columns)]

            # 5. Limpeza Final
            # Remove linhas onde 'Operador' ou 'Metrica' estejam vazios
            df = df[df['Operador'].str.strip() != ""]
            df = df[df['Metrica'].str.strip() != ""]
            
            # Remove possíveis colunas de data vazias
            df = df.loc[:, df.columns != '']
            
            return df
        else:
            return pd.DataFrame()
    except Exception as e:
        st.error(f"Erro na conexão: {e}")
        return pd.DataFrame()

def tratar_porcentagem(valor):
    if isinstance(valor, str):
        v = valor.replace('%', '').replace(',', '.').strip()
        if v == '' or v == '#N/A': return 0.0
        try: return float(v) / 100
        except: return 0.0
    return valor

# --- 3. LOGIN ---
def login():
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        st.markdown("<br><br><br>", unsafe_allow_html=True)
        with st.container(border=True):
            st.markdown("<h2 style='text-align: center;'>🔐 Acesso TeamBrisa</h2>", unsafe_allow_html=True)
            usuario = st.text_input("Usuário")
            senha = st.text_input("Senha", type="password")
            if st.button("Acessar Painel", use_container_width=True):
                if usuario and senha: 
                    st.session_state['logado'] = True
                    st.session_state['usuario'] = "Gestor"
                    st.rerun()

# --- 4. PAINEL TÁTICO PROFISSIONAL ---
def main():
    df = carregar_matriz_dados()
    
    # --- BARRA LATERAL (FILTROS) ---
    with st.sidebar:
        st.markdown(f"<h2 style='text-align: center; color: #58A6FF;'>☁️ TeamBrisa</h2>", unsafe_allow_html=True)
        st.markdown("---")
        
        escolha = option_menu(
            menu_title=None, 
            options=["Painel Tático"], 
            icons=["graph-up-arrow"], 
            default_index=0,
            styles={
                "container": {"background-color": "transparent"},
                "nav-link": {"font-size": "14px", "text-align": "left", "margin":"0px"},
                "nav-link-selected": {"background-color": "#238636"},
            }
        )
        st.markdown("<br>", unsafe_allow_html=True)

        st.subheader("🔍 Filtros Operacionais")
        
        if not df.empty:
            # FILTRO 1: OPERADOR (Coluna 'Operador' limpa)
            lista_ops = sorted(df['Operador'].unique())
            # Remove eventuais sujeiras da lista
            lista_ops = [op for op in lista_ops if len(op) > 2]
            filtro_op = st.selectbox("Filtrar Operador:", lista_ops)

            # FILTRO 2: MÉTRICA (Coluna 'Metrica' limpa)
            lista_met = sorted(df['Metrica'].unique())
            # Remove sujeiras e tenta focar em 'Meta'
            lista_met = [m for m in lista_met if len(m) > 1]
            index_padrao = lista_met.index('Meta') if 'Meta' in lista_met else 0
            filtro_met = st.selectbox("Filtrar Métrica:", lista_met, index=index_padrao)
        else:
            st.warning("Carregando base de dados...")
            filtro_op, filtro_met = None, None

        st.markdown("---")
        if st.button("Sair", use_container_width=True):
            st.session_state['logado'] = False
            st.rerun()

    # --- ÁREA PRINCIPAL ---
    if escolha == "Painel Tático":
        # Cabeçalho Principal
        col_tit, col_logo = st.columns([4, 1])
        with col_tit:
            st.title("📊 Painel Tático")
            st.markdown(f"**Visão detalhada:** {filtro_op} | **Foco:** {filtro_met}")
        
        st.markdown("---")

        if df.empty:
            st.error("Erro ao ler dados. Verifique se a planilha DADOS-DIA tem datas na linha 27.")
            st.stop()

        # Identifica colunas de Data (Da coluna 2 em diante)
        cols_datas = list(df.columns[2:])
        
        # Layout 2 Colunas: Gráfico (Esq) e Ranking (Dir)
        col_graf, col_rank = st.columns([2.5, 1.2], gap="medium")

        # >>> ESQUERDA: GRÁFICO DINÂMICO <<<
        with col_graf:
            st.markdown(f"### 📈 Evolução: {filtro_met}")
            
            if filtro_op and filtro_met:
                # Filtra DF
                df_f = df[(df['Operador'] == filtro_op) & (df['Metrica'] == filtro_met)]
                
                if not df_f.empty:
                    # Derrete (Melt) para formato de gráfico
                    df_long = pd.melt(df_f, id_vars=['Operador', 'Metrica'], value_vars=cols_datas, var_name='Data', value_name='ValorRaw')
                    df_long['Performance'] = df_long['ValorRaw'].apply(tratar_porcentagem)
                    
                    # Gráfico Plotly Neon/Dark
                    fig = px.line(df_long, x='Data', y='Performance', markers=True)
                    
                    # Estilização Profissional
                    fig.update_traces(line_color='#00FF7F', line_width=4, marker_size=8, marker_color='#FFFFFF')
                    fig.update_layout(
                        paper_bgcolor='rgba(0,0,0,0)',
                        plot_bgcolor='rgba(0,0,0,0)',
                        font_color='#FAFAFA',
                        yaxis_tickformat='.0%',
                        yaxis_range=[0, 1.1],
                        hovermode="x unified",
                        margin=dict(l=0, r=0, t=20, b=20),
                        height=450
                    )
                    # Adiciona linha de grade sutil
                    fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='#30363D')
                    fig.update_xaxes(showgrid=False)
                    
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info(f"Sem dados de '{filtro_met}' para este operador.")

        # >>> DIREITA: RANKING GERAL (DINÂMICO) <<<
        with col_rank:
            st.markdown("### 🏆 Ranking Geral")
            st.caption(f"Melhores em **{filtro_met}** (Hoje)")

            if filtro_met:
                # Filtra todos os operadores naquela métrica
                df_rank = df[df['Metrica'] == filtro_met].copy()
                
                if not df_rank.empty:
                    # Pega a última data disponível
                    ultima_data = cols_datas[-1]
                    
                    # Monta tabela
                    ranking = pd.DataFrame({
                        'Colaborador': df_rank['Operador'],
                        'Res': df_rank[ultima_data].apply(tratar_porcentagem)
                    }).sort_values('Res', ascending=False)
                    
                    # Exibe Tabela Estilizada
                    st.dataframe(
                        ranking,
                        use_container_width=True,
                        hide_index=True,
                        height=450,
                        column_config={
                            "Colaborador": st.column_config.TextColumn("Operador"),
                            "Res": st.column_config.ProgressColumn(
                                "Atingimento", 
                                format="%.1f%%", 
                                min_value=0, 
                                max_value=1,
                            )
                        }
                    )

# --- INICIALIZAÇÃO ---
if 'logado' not in st.session_state: st.session_state['logado'] = False
if not st.session_state['logado']: login()
else: main()
