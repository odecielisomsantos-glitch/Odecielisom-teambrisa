import streamlit as st
import pandas as pd
import gspread
import plotly.express as px
from google.oauth2.service_account import Credentials
from streamlit_option_menu import option_menu

# --- 1. CONFIGURAÇÃO VISUAL (DARK MODE PROFISSIONAL) ---
st.set_page_config(
    page_title="Painel Tático TeamBrisa", 
    layout="wide", 
    page_icon="☁️",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    /* Fundo Dark Profundo */
    .stApp { background-color: #0E1117; color: #E6EDF3; }
    [data-testid="stSidebar"] { background-color: #161B22; border-right: 1px solid #30363D; }
    
    /* Tipografia */
    h1, h2, h3, h4 { color: #FAFAFA !important; font-family: 'Segoe UI', sans-serif; font-weight: 600; }
    p, label { color: #C9D1D9; }
    
    /* Ajustes de Espaçamento */
    .block-container { padding-top: 2rem; padding-bottom: 5rem; }
</style>
""", unsafe_allow_html=True)

# --- 2. CONEXÃO E DADOS ---

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
    try:
        gc = conectar_google_sheets()
        sh = gc.open("Sistema_Vendas")
        worksheet = sh.worksheet("DADOS-DIA")
        return worksheet.get_all_values()
    except Exception as e:
        st.error(f"Erro na conexão: {e}")
        return []

def tratar_porcentagem(valor):
    """Converte '100%' para 100.0 (float)."""
    if isinstance(valor, str):
        v = valor.replace('%', '').replace(',', '.').strip()
        if v == '' or v == '#N/A' or v == '-': return 0.0
        try: return float(v) 
        except: return 0.0
    return valor

# --- 3. PROCESSAMENTO ---

def processar_matriz_grafico(todos_dados):
    INDICE_CABECALHO = 26 
    if len(todos_dados) > INDICE_CABECALHO:
        cabecalho = todos_dados[INDICE_CABECALHO]
        dados = todos_dados[INDICE_CABECALHO+1:]
        df = pd.DataFrame(dados)
        
        novos_nomes = ['Operador', 'Metrica'] + cabecalho[2:]
        if len(df.columns) >= len(novos_nomes):
            df = df.iloc[:, :len(novos_nomes)]
            df.columns = novos_nomes
        else:
            df.columns = novos_nomes[:len(df.columns)]
            
        df = df[df['Operador'].str.strip() != ""]
        return df
    return pd.DataFrame()

def processar_tabela_ranking(todos_dados, col_nome_idx, col_valor_idx, linhas_range, titulo_coluna):
    lista_limpa = []
    for i in linhas_range:
        if i < len(todos_dados):
            linha = todos_dados[i]
            if len(linha) > col_valor_idx:
                nome = linha[col_nome_idx].strip()
                valor_str = linha[col_valor_idx].strip()
                
                if nome and valor_str and valor_str not in ['-', '#N/A', '']:
                    val_float = tratar_porcentagem(valor_str)
                    lista_limpa.append({
                        'Colaborador': nome,
                        titulo_coluna: val_float
                    })
    
    df = pd.DataFrame(lista_limpa)
    if not df.empty:
        df = df.sort_values(by=titulo_coluna, ascending=False)
    return df

# Função auxiliar para definir cor baseada na nota (Lógica do Ranking Geral)
def definir_cor_pela_nota(valor):
    if valor >= 90: return '#00FF7F' # Verde Neon (N3)
    elif valor >= 70: return '#FFD700' # Amarelo (N2)
    else: return '#FF4B4B' # Vermelho (N1)

# --- 4. FUNÇÃO DE VISUALIZAÇÃO (GRÁFICO DE BARRAS RANKING) ---
def renderizar_ranking_visual(titulo, df, col_val, cor_input, altura_base=250):
    """
    Cria o gráfico de barras. 
    cor_input: Pode ser uma string HEX (ex: '#00FF7F') OU o nome de uma coluna do DF para cor variável.
    """
    st.markdown(f"#### {titulo}")
    
    if not df.empty:
        altura_dinamica = max(altura_base, len(df) * 35)
        
        # Verifica se 'cor_input' é uma cor fixa ou uma coluna dinâmica
        if cor_input.startswith('#'):
            # Cor fixa
            fig = px.bar(
                df, y="Colaborador", x=col_val, text=col_val, orientation='h',
                color_discrete_sequence=[cor_input] 
            )
        else:
            # Cor dinâmica (Baseada em coluna)
            fig = px.bar(
                df, y="Colaborador", x=col_val, text=col_val, orientation='h',
                color=cor_input, # Usa a coluna de cores
                color_discrete_map="identity" # Usa as cores hex reais da coluna
            )
        
        fig.update_traces(
            texttemplate='<b>%{text:.1f}%</b>', # NEGRITO
            textposition='inside',
            insidetextanchor='start',
            textfont_size=18, # <<< FONTE MAIOR AQUI
            textfont_color='black' # Contraste com o neon/amarelo
        )
        
        fig.update_layout(
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font_color='#E6EDF3',
            xaxis=dict(showgrid=False, showticklabels=False, range=[0, 115]), 
            yaxis=dict(autorange="reversed", title=None),
            margin=dict(l=0, r=0, t=0, b=0),
            height=altura_dinamica,
            dragmode=False,
            showlegend=False # Esconde legenda para ficar limpo
        )
        
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
    else:
        st.caption("Sem dados para exibir.")

# --- 5. LOGIN ---
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

# --- 6. PAINEL PRINCIPAL ---
def main():
    dados_brutos = obter_dados_completos()
    if not dados_brutos: st.stop()

    df_grafico = processar_matriz_grafico(dados_brutos)
    
    # Processa Rankings
    df_tam = processar_tabela_ranking(dados_brutos, 0, 1, range(1, 25), 'TAM')
    # Aplica lógica de cores SEMÁFORO no Ranking Geral
    if not df_tam.empty:
        df_tam['Cor_Dinamica'] = df_tam['TAM'].apply(definir_cor_pela_nota)

    df_n3 = processar_tabela_ranking(dados_brutos, 5, 6, range(1, 25), 'Nível 3')
    df_n2 = processar_tabela_ranking(dados_brutos, 8, 9, range(1, 25), 'Nível 2')
    df_n1 = processar_tabela_ranking(dados_brutos, 11, 12, range(1, 25), 'Nível 1')

    # --- BARRA LATERAL ---
    with st.sidebar:
        st.markdown(f"<h2 style='text-align: center; color: #58A6FF;'>☁️ TeamBrisa</h2>", unsafe_allow_html=True)
        st.markdown("---")
        escolha = option_menu(
            menu_title=None, options=["Painel Tático"], icons=["graph-up-arrow"], default_index=0,
            styles={"container": {"background-color": "transparent"}, "nav-link-selected": {"background-color": "#238636"}}
        )
        st.markdown("<br>", unsafe_allow_html=True)
        
        if not df_grafico.empty:
            st.subheader("🔍 Filtros (Gráfico)")
            lista_ops = sorted([op for op in df_grafico['Operador'].unique() if len(op) > 2])
            filtro_op = st.selectbox("👤 Operador:", lista_ops)
            
            # ADICIONA OPÇÃO "GERAL" NA LISTA DE MÉTRICAS
            lista_met = sorted([m for m in df_grafico['Metrica'].unique() if len(m) > 1])
            if "Meta" in lista_met: # Traz Meta pro topo se existir
                lista_met.remove("Meta")
                lista_met.insert(0, "Meta")
            lista_met.insert(0, "Geral") # Insere Geral como primeira opção
            
            filtro_met = st.selectbox("🎯 Métrica:", lista_met, index=0)
        else:
            filtro_op, filtro_met = None, None
            
        st.markdown("---")
        if st.button("Sair", use_container_width=True):
            st.session_state['logado'] = False
            st.rerun()

    # --- TELA ---
    if escolha == "Painel Tático":
        col_tit, col_logo = st.columns([4, 1])
        with col_tit:
            st.title("📊 Painel Tático")
            st.markdown(f"**Visão:** {filtro_op} | **Métrica:** {filtro_met}")
        st.markdown("---")
        
        col_esq, col_dir = st.columns([2, 1.2], gap="large")

        # >>> GRÁFICO EVOLUÇÃO (ESQUERDA) <<<
        with col_esq:
            st.markdown(f"### 📈 Evolução Mensal")
            
            if filtro_op and filtro_met and not df_grafico.empty:
                # Lógica para "Geral" vs "Métrica Específica"
                if filtro_met == "Geral":
                    # Pega TODAS as métricas do operador
                    df_f = df_grafico[df_grafico['Operador'] == filtro_op]
                    cor_linha = 'Metrica' # Plotly define cores automáticas diferentes
                    titulo_legenda = True
                else:
                    # Pega apenas UMA métrica
                    df_f = df_grafico[(df_grafico['Operador'] == filtro_op) & (df_grafico['Metrica'] == filtro_met)]
                    cor_linha = None # Usaremos cor fixa verde
                    titulo_legenda = False

                if not df_f.empty:
                    cols_datas = list(df_grafico.columns[2:])
                    df_long = pd.melt(df_f, id_vars=['Operador', 'Metrica'], value_vars=cols_datas, var_name='Data', value_name='ValorRaw')
                    df_long['Performance'] = df_long['ValorRaw'].apply(tratar_porcentagem)
                    
                    if filtro_met == "Geral":
                        # Gráfico MULTICOLORIDO
                        fig = px.line(df_long, x='Data', y='Performance', color='Metrica', markers=True)
                        fig.update_layout(legend=dict(orientation="h", y=1.1, title=None))
                    else:
                        # Gráfico VERDE NEON (Único)
                        fig = px.line(df_long, x='Data', y='Performance', markers=True)
                        fig.update_traces(line_color='#00FF7F', line_width=4, marker_size=8, marker_color='#FFFFFF')

                    # Layout Comum
                    fig.update_layout(
                        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color='#E6EDF3',
                        yaxis_ticksuffix="%", yaxis_range=[0, 115], hovermode="x unified",
                        margin=dict(l=0, r=0, t=20, b=20), height=500
                    )
                    fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='#30363D')
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("Sem dados gráficos.")

        # >>> RANKINGS COLORIDOS (DIREITA) <<<
        with col_dir:
            # 1. RANKING GERAL (COR DINÂMICA SEMÁFORO)
            # Passamos a coluna 'Cor_Dinamica' que criamos lá em cima
            renderizar_ranking_visual("🏆 Ranking Geral (TAM)", df_tam, "TAM", "Cor_Dinamica")
            
            st.markdown("---")
            
            # 2. NÍVEL 3 -> VERDE NEON
            renderizar_ranking_visual("🥇 Nível 3", df_n3, "Nível 3", "#00FF7F")
            
            # 3. NÍVEL 2 -> AMARELO OURO
            renderizar_ranking_visual("🥈 Nível 2", df_n2, "Nível 2", "#FFD700")
            
            # 4. NÍVEL 1 -> VERMELHO ALERTA
            renderizar_ranking_visual("🥉 Nível 1", df_n1, "Nível 1", "#FF4B4B")

# --- INICIALIZAÇÃO ---
if 'logado' not in st.session_state: st.session_state['logado'] = False
if not st.session_state['logado']: login()
else: main()
