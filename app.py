import streamlit as st
import pandas as pd
import gspread
import plotly.express as px
from google.oauth2.service_account import Credentials
from streamlit_option_menu import option_menu

# --- 1. CONFIGURAÇÃO VISUAL (NEON DARK MODE) ---
st.set_page_config(
    page_title="Painel Tático TeamBrisa", 
    layout="wide", 
    page_icon="☁️",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    /* Fundo Dark */
    .stApp { background-color: #0E1117; color: #FAFAFA; }
    [data-testid="stSidebar"] { background-color: #161B22; border-right: 1px solid #30363D; }
    
    /* Títulos */
    h1, h2, h3, h4, h5 { color: #E6EDF3 !important; font-family: 'Segoe UI', sans-serif; }
    
    /* Tabelas (Dataframes) */
    [data-testid="stDataFrame"] { background-color: #0d1117; }
    
    /* Ajuste de Espaçamento */
    .block-container { padding-top: 2rem; padding-bottom: 5rem; }
    
    /* Destaque Neon para os Rankings */
    .stProgress > div > div > div > div { background-color: #00FF7F; }
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
def obter_dados_completos():
    """Lê a aba inteira de uma vez para separar depois."""
    try:
        gc = conectar_google_sheets()
        sh = gc.open("Sistema_Vendas")
        worksheet = sh.worksheet("DADOS-DIA")
        return worksheet.get_all_values()
    except Exception as e:
        st.error(f"Erro na conexão: {e}")
        return []

def tratar_porcentagem(valor):
    """Converte '98,81%' para 0.9881"""
    if isinstance(valor, str):
        v = valor.replace('%', '').replace(',', '.').strip()
        if v == '' or v == '#N/A' or v == '-': return 0.0
        try: return float(v) / 100
        except: return 0.0
    return valor

# --- 3. PROCESSAMENTO ESPECÍFICO (GRÁFICO vs RANKINGS) ---

def processar_matriz_grafico(todos_dados):
    """Extrai os dados da parte INFERIOR (Linha 27+) para o gráfico."""
    INDICE_CABECALHO = 26 # Linha 27 do Excel
    if len(todos_dados) > INDICE_CABECALHO:
        cabecalho = todos_dados[INDICE_CABECALHO]
        dados = todos_dados[INDICE_CABECALHO+1:]
        df = pd.DataFrame(dados)
        
        # Renomeia colunas A e B forçadamente
        novos_nomes = ['Operador', 'Metrica'] + cabecalho[2:]
        if len(df.columns) >= len(novos_nomes):
            df = df.iloc[:, :len(novos_nomes)]
            df.columns = novos_nomes
        else:
            df.columns = novos_nomes[:len(df.columns)]
            
        # Limpeza
        df = df[df['Operador'].str.strip() != ""]
        return df
    return pd.DataFrame()

def processar_tabela_ranking(todos_dados, col_nome_idx, col_valor_idx, linhas_range, titulo_coluna):
    """
    Extrai e limpa uma tabela de ranking específica.
    col_nome_idx: Índice da coluna do nome (ex: 0 para A)
    col_valor_idx: Índice da coluna do valor (ex: 1 para B)
    linhas_range: range(inicio, fim) das linhas
    """
    lista_limpa = []
    for i in linhas_range:
        if i < len(todos_dados):
            linha = todos_dados[i]
            # Verifica se a coluna existe e se tem nome
            if len(linha) > col_valor_idx:
                nome = linha[col_nome_idx].strip()
                valor_str = linha[col_valor_idx].strip()
                
                if nome and valor_str: # Só adiciona se tiver nome e valor
                    lista_limpa.append({
                        'Colaborador': nome,
                        titulo_coluna: tratar_porcentagem(valor_str)
                    })
    
    df = pd.DataFrame(lista_limpa)
    if not df.empty:
        df = df.sort_values(by=titulo_coluna, ascending=False)
    return df

# --- 4. LOGIN ---
def login():
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        st.markdown("<br><br><br>", unsafe_allow_html=True)
        with st.container(border=True):
            st.markdown("<h2 style='text-align: center;'>🔐 TeamBrisa</h2>", unsafe_allow_html=True)
            usuario = st.text_input("Usuário")
            senha = st.text_input("Senha", type="password")
            if st.button("Entrar", use_container_width=True):
                if usuario and senha: 
                    st.session_state['logado'] = True
                    st.session_state['usuario'] = "Gestor"
                    st.rerun()

# --- 5. PAINEL PRINCIPAL ---
def main():
    # 1. Carrega TUDO de uma vez
    dados_brutos = obter_dados_completos()
    
    if not dados_brutos:
        st.stop()

    # 2. Separa os dados
    df_grafico = processar_matriz_grafico(dados_brutos)
    
    # Processa os 4 Rankings (Intervalos baseados na sua imagem)
    # Ajuste dos índices (Python começa em 0. Excel A=0, B=1, F=5, G=6, I=8, J=9, L=11, M=12)
    # Linhas 2 a 24 do Excel = Índices 1 a 24 do Python
    
    # Ranking TAM (A2:B24)
    df_tam = processar_tabela_ranking(dados_brutos, 0, 1, range(1, 25), 'TAM')
    
    # Nível 3 (F3:G25) -> Índices 5, 6 | Linhas 2 a 25
    df_n3 = processar_tabela_ranking(dados_brutos, 5, 6, range(2, 26), 'Nível 3')
    
    # Nível 2 (I3:J25) -> Índices 8, 9
    df_n2 = processar_tabela_ranking(dados_brutos, 8, 9, range(2, 26), 'Nível 2')
    
    # Nível 1 (L3:M25) -> Índices 11, 12
    df_n1 = processar_tabela_ranking(dados_brutos, 11, 12, range(2, 26), 'Nível 1')

    # --- BARRA LATERAL ---
    with st.sidebar:
        st.markdown(f"<h2 style='text-align: center; color: #58A6FF;'>☁️ TeamBrisa</h2>", unsafe_allow_html=True)
        st.markdown("---")
        
        escolha = option_menu(
            menu_title=None, options=["Painel Tático"], icons=["graph-up-arrow"], default_index=0,
            styles={"container": {"background-color": "transparent"}, "nav-link-selected": {"background-color": "#238636"}}
        )
        st.markdown("<br>", unsafe_allow_html=True)
        st.subheader("🔍 Filtros (Gráfico)")
        
        if not df_grafico.empty:
            lista_ops = sorted([op for op in df_grafico['Operador'].unique() if len(op) > 2])
            filtro_op = st.selectbox("👤 Operador:", lista_ops)
            lista_met = sorted([m for m in df_grafico['Metrica'].unique() if len(m) > 1])
            idx_meta = lista_met.index('Meta') if 'Meta' in lista_met else 0
            filtro_met = st.selectbox("🎯 Métrica:", lista_met, index=idx_meta)
        else:
            filtro_op, filtro_met = None, None
            
        st.markdown("---")
        if st.button("Sair", use_container_width=True):
            st.session_state['logado'] = False
            st.rerun()

    # --- ÁREA PRINCIPAL ---
    if escolha == "Painel Tático":
        col_tit, col_logo = st.columns([4, 1])
        with col_tit:
            st.title("📊 Painel Tático")
            st.markdown(f"**Visão:** {filtro_op} | **Métrica:** {filtro_met}")
        
        st.markdown("---")
        
        # DIVISÃO DA TELA: 2 Colunas (Gráfico Esquerda | Rankings Direita)
        col_esq, col_dir = st.columns([2, 1.2], gap="large")

        # >>> ESQUERDA: GRÁFICO (Mesma lógica de antes) <<<
        with col_esq:
            st.markdown(f"### 📈 Evolução Mensal")
            if filtro_op and filtro_met and not df_grafico.empty:
                df_f = df_grafico[(df_grafico['Operador'] == filtro_op) & (df_grafico['Metrica'] == filtro_met)]
                if not df_f.empty:
                    cols_datas = list(df_grafico.columns[2:])
                    df_long = pd.melt(df_f, id_vars=['Operador', 'Metrica'], value_vars=cols_datas, var_name='Data', value_name='ValorRaw')
                    df_long['Performance'] = df_long['ValorRaw'].apply(tratar_porcentagem)
                    
                    fig = px.line(df_long, x='Data', y='Performance', markers=True)
                    fig.update_traces(line_color='#00FF7F', line_width=4, marker_size=8, marker_color='#FFFFFF')
                    fig.update_layout(
                        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color='#FAFAFA',
                        yaxis_tickformat='.0%', yaxis_range=[0, 1.1], hovermode="x unified",
                        margin=dict(l=0, r=0, t=20, b=20), height=500
                    )
                    fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='#30363D')
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("Sem dados gráficos para a seleção.")

        # >>> DIREITA: 4 RANKINGS EMPILHADOS <<<
        with col_dir:
            # Função auxiliar para renderizar tabelas bonitas
            def renderizar_ranking(titulo, df, col_val):
                st.markdown(f"#### {titulo}")
                if not df.empty:
                    st.dataframe(
                        df,
                        use_container_width=True,
                        hide_index=True,
                        height=200, # Altura controlada para caberem todos
                        column_config={
                            "Colaborador": st.column_config.TextColumn("Colaborador"),
                            col_val: st.column_config.ProgressColumn(
                                "Perf.", 
                                format="%.1f%%", 
                                min_value=0, 
                                max_value=1,
                            )
                        }
                    )
                else:
                    st.caption("Sem dados.")

            # 1. RANKING GERAL (TAM)
            st.markdown("### 🏆 Ranking Geral (TAM)")
            renderizar_ranking("", df_tam, "TAM")
            
            st.markdown("---") # Separador
            
            # 2. NÍVEL 3
            renderizar_ranking("🥇 Nível 3", df_n3, "Nível 3")
            
            # 3. NÍVEL 2
            renderizar_ranking("🥈 Nível 2", df_n2, "Nível 2")
            
            # 4. NÍVEL 1
            renderizar_ranking("🥉 Nível 1", df_n1, "Nível 1")

# --- INICIALIZAÇÃO ---
if 'logado' not in st.session_state: st.session_state['logado'] = False
if not st.session_state['logado']: login()
else: main()
