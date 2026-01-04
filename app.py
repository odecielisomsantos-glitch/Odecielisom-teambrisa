import streamlit as st
import pandas as pd
import gspread
import plotly.express as px
from google.oauth2.service_account import Credentials
from streamlit_option_menu import option_menu

# --- 1. CONFIGURAÇÃO VISUAL ---
st.set_page_config(page_title="Painel Tático TeamBrisa", layout="wide", page_icon="☁️", initial_sidebar_state="expanded")

st.markdown("""
<style>
    .stApp { background-color: #0E1117; color: #E6EDF3; }
    [data-testid="stSidebar"] { background-color: #161B22; border-right: 1px solid #30363D; }
    h1, h2, h3, h4 { color: #FAFAFA !important; font-family: 'Segoe UI', sans-serif; font-weight: 600; }
    div[data-testid="stMetric"] { background-color: #161B22; border: 1px solid #30363D; padding: 15px; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.3); }
    div[data-testid="stMetricValue"] { font-size: 28px !important; font-weight: bold; color: #00FF7F !important; }
    div[data-testid="stMetricLabel"] { font-size: 16px !important; color: #C9D1D9; }
    .block-container { padding-top: 2rem; padding-bottom: 5rem; }
</style>
""", unsafe_allow_html=True)

# --- 2. CONFIGURAÇÃO DE USUÁRIOS ---
USUARIOS = {
    "admin": {
        "senha": "123", 
        "nome_planilha": "Gestor Geral", 
        "funcao": "admin"
    },
    "damiao": {
        "senha": "123", 
        "nome_planilha": "DAMIAO EMANUEL DE CARVALHO GOMES", 
        "funcao": "colaborador"
    },
    "aluizio": {
        "senha": "123", 
        "nome_planilha": "ALUIZIO BEZERRA JUNIOR", 
        "funcao": "colaborador"
    },
    # Adicione os outros aqui...
}

# --- 3. CONEXÃO E DADOS ---

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
    if isinstance(valor, str):
        v = valor.replace('%', '').replace(',', '.').strip()
        if v == '' or v == '#N/A' or v == '-': return 0.0
        try: return float(v) 
        except: return 0.0
    return valor

# --- 4. PROCESSAMENTO ---

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

def definir_cor_pela_nota(valor):
    if valor >= 90: return '#00FF7F' # Verde Neon
    elif valor >= 70: return '#FFD700' # Amarelo
    else: return '#FF4B4B' # Vermelho

# --- 5. FUNÇÃO DE VISUALIZAÇÃO ---
def renderizar_ranking_visual(titulo, df, col_val, cor_input, altura_base=250):
    st.markdown(f"#### {titulo}")
    
    if not df.empty:
        altura_dinamica = max(altura_base, len(df) * 35)
        
        if cor_input.startswith('#'):
            fig = px.bar(df, y="Colaborador", x=col_val, text=col_val, orientation='h', color_discrete_sequence=[cor_input])
        else:
            fig = px.bar(df, y="Colaborador", x=col_val, text=col_val, orientation='h', color=cor_input, color_discrete_map="identity")
        
        fig.update_traces(texttemplate='<b>%{text:.1f}%</b>', textposition='inside', insidetextanchor='start', textfont_size=18, textfont_color='black')
        
        fig.update_layout(
            paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color='#E6EDF3',
            xaxis=dict(showgrid=False, showticklabels=False, range=[0, 115]), yaxis=dict(autorange="reversed", title=None),
            margin=dict(l=0, r=0, t=0, b=0), height=altura_dinamica, dragmode=False, showlegend=False
        )
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
    else:
        st.caption("Sem dados para exibir.")

# --- 6. LOGIN ---
def login():
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        st.markdown("<br><br><br>", unsafe_allow_html=True)
        with st.container(border=True):
            st.markdown("<h2 style='text-align: center;'>🔐 Acesso TeamBrisa</h2>", unsafe_allow_html=True)
            usuario_input = st.text_input("Usuário")
            senha_input = st.text_input("Senha", type="password")
            
            if st.button("Entrar", use_container_width=True):
                if usuario_input in USUARIOS:
                    dados_user = USUARIOS[usuario_input]
                    if senha_input == dados_user['senha']:
                        st.session_state['logado'] = True
                        st.session_state['usuario_id'] = usuario_input
                        st.session_state['nome_real'] = dados_user['nome_planilha']
                        st.session_state['funcao'] = dados_user['funcao']
                        st.rerun()
                    else:
                        st.error("Senha incorreta.")
                else:
                    st.error("Usuário não encontrado.")

# --- 7. PAINEL PRINCIPAL ---
def main():
    dados_brutos = obter_dados_completos()
    if not dados_brutos: st.stop()

    df_grafico_total = processar_matriz_grafico(dados_brutos)
    df_tam_total = processar_tabela_ranking(dados_brutos, 0, 1, range(1, 25), 'TAM')
    df_n3_total = processar_tabela_ranking(dados_brutos, 5, 6, range(1, 25), 'Nível 3')
    df_n2_total = processar_tabela_ranking(dados_brutos, 8, 9, range(1, 25), 'Nível 2')
    df_n1_total = processar_tabela_ranking(dados_brutos, 11, 12, range(1, 25), 'Nível 1')

    perfil = st.session_state['funcao']
    nome_usuario = st.session_state['nome_real']

    # Filtro de Permissão
    if perfil == 'admin':
        df_grafico = df_grafico_total
        df_tam = df_tam_total
        df_n3 = df_n3_total
        df_n2 = df_n2_total
        df_n1 = df_n1_total
    else:
        df_grafico = df_grafico_total[df_grafico_total['Operador'] == nome_usuario]
        df_tam = df_tam_total[df_tam_total['Colaborador'] == nome_usuario]
        df_n3 = df_n3_total[df_n3_total['Colaborador'] == nome_usuario]
        df_n2 = df_n2_total[df_n2_total['Colaborador'] == nome_usuario]
        df_n1 = df_n1_total[df_n1_total['Colaborador'] == nome_usuario]

    if not df_tam.empty:
        df_tam['Cor_Dinamica'] = df_tam['TAM'].apply(definir_cor_pela_nota)

    # --- BARRA LATERAL ATUALIZADA ---
    with st.sidebar:
        st.markdown(f"<h2 style='text-align: center; color: #58A6FF;'>☁️ TeamBrisa</h2>", unsafe_allow_html=True)
        st.info(f"Logado como: **{nome_usuario}** ({perfil.upper()})")
        st.markdown("---")
        
        # --- ATUALIZAÇÃO AQUI: NOVAS OPÇÕES ---
        escolha = option_menu(
            menu_title=None, 
            options=["Painel Tático", "Pausas", "Calendário"],  # Novas opções
            icons=["graph-up-arrow", "clock-history", "calendar-week"], # Novos ícones
            default_index=0,
            styles={"container": {"background-color": "transparent"}, "nav-link-selected": {"background-color": "#238636"}}
        )
        st.markdown("<br>", unsafe_allow_html=True)
        
        # Filtros aparecem apenas na tela do Painel Tático
        if escolha == "Painel Tático":
            st.subheader("🔍 Filtros")
            if perfil == 'admin':
                if not df_grafico_total.empty:
                    lista_ops = sorted([op for op in df_grafico_total['Operador'].unique() if len(op) > 2])
                    filtro_op = st.selectbox("👤 Operador:", lista_ops)
                else:
                    filtro_op = None
            else:
                st.markdown(f"**👤 Operador:** {nome_usuario}")
                filtro_op = nome_usuario 

            if not df_grafico_total.empty:
                lista_met = sorted([m for m in df_grafico_total['Metrica'].unique() if len(m) > 1])
                if "Meta" in lista_met:
                    lista_met.remove("Meta")
                    lista_met.insert(0, "Meta")
                lista_met.insert(0, "Geral")
                filtro_met = st.selectbox("🎯 Métrica:", lista_met, index=0)
            else:
                filtro_met = None
            st.markdown("---")

        if st.button("Sair", use_container_width=True):
            st.session_state['logado'] = False
            st.rerun()

    # --- CONTEÚDO DAS PÁGINAS ---
    
    # 1. PÁGINA PAINEL TÁTICO
    if escolha == "Painel Tático":
        st.title("📊 Painel Tático")
        st.markdown("---")
        
        kpi1, kpi2, kpi3 = st.columns(3)
        
        if not df_tam_total.empty:
            media_time = df_tam_total[df_tam_total['TAM'] > 0]['TAM'].mean()
            melhor_op_nome = df_tam_total.iloc[0]['Colaborador']
            melhor_op_valor = df_tam_total.iloc[0]['TAM']
            
            if not df_n1_total.empty:
                qtd_nivel_1 = len(df_n1_total[df_n1_total['Nível 1'] > 0])
            else:
                qtd_nivel_1 = 0
        else:
            media_time, melhor_op_valor, qtd_nivel_1 = 0, 0, 0
            melhor_op_nome = "-"

        kpi1.metric("🎯 Média do Time (Ref.)", f"{media_time:.1f}%")
        kpi2.metric("🏆 Melhor Performance", f"{melhor_op_nome}", f"{melhor_op_valor:.1f}%")
        kpi3.metric("🚨 Zona de Atenção", f"{qtd_nivel_1} Operadores", delta_color="inverse")
        
        st.markdown("---")
        st.markdown(f"**Visão:** {filtro_op}")
        
        col_esq, col_dir = st.columns([2, 1.2], gap="large")

        with col_esq:
            st.markdown(f"### 📈 Evolução Mensal")
            if filtro_op and filtro_met and not df_grafico.empty:
                if filtro_met == "Geral":
                    df_f = df_grafico[df_grafico['Operador'] == filtro_op]
                else:
                    df_f = df_grafico[(df_grafico['Operador'] == filtro_op) & (df_grafico['Metrica'] == filtro_met)]

                if not df_f.empty:
                    cols_datas = list(df_grafico.columns[2:])
                    df_long = pd.melt(df_f, id_vars=['Operador', 'Metrica'], value_vars=cols_datas, var_name='Data', value_name='ValorRaw')
                    df_long['Performance'] = df_long['ValorRaw'].apply(tratar_porcentagem)
                    
                    if filtro_met == "Geral":
                        fig = px.line(df_long, x='Data', y='Performance', color='Metrica', markers=True)
                        fig.update_layout(legend=dict(orientation="h", y=1.1, title=None))
                    else:
                        fig = px.line(df_long, x='Data', y='Performance', markers=True)
                        fig.update_traces(line_color='#00FF7F', line_width=4, marker_size=8, marker_color='#FFFFFF')

                    fig.update_layout(
                        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color='#E6EDF3',
                        yaxis_ticksuffix="%", yaxis_range=[0, 115], hovermode="x unified",
                        margin=dict(l=0, r=0, t=20, b=20), height=500
                    )
                    fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='#30363D')
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("Sem dados para exibir.")

        with col_dir:
            renderizar_ranking_visual("🏆 Resultado Geral", df_tam, "TAM", "Cor_Dinamica")
            st.markdown("---")
            renderizar_ranking_visual("🥇 Nível 3", df_n3, "Nível 3", "#00FF7F")
            renderizar_ranking_visual("🥈 Nível 2", df_n2, "Nível 2", "#FFD700")
            renderizar_ranking_visual("🥉 Nível 1", df_n1, "Nível 1", "#FF4B4B")

    # 2. PÁGINA PAUSAS (PLACEHOLDER)
    elif escolha == "Pausas":
        st.title("⏸️ Controle de Pausas")
        st.markdown("---")
        st.info("🚧 Módulo de Pausas em desenvolvimento.")
        st.markdown("Aqui você poderá registrar pausas, banheiro e almoço futuramente.")

    # 3. PÁGINA CALENDÁRIO (PLACEHOLDER)
    elif escolha == "Calendário":
        st.title("📅 Calendário da Equipe")
        st.markdown("---")
        st.info("🚧 Módulo de Calendário em desenvolvimento.")
        st.markdown("Aqui você verá escalas, feriados e eventos do time.")

# --- INICIALIZAÇÃO ---
if 'logado' not in st.session_state: st.session_state['logado'] = False
if not st.session_state['logado']: login()
else: main()
