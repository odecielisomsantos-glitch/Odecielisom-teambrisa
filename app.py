import streamlit as st
import pandas as pd
import gspread
import plotly.express as px
import plotly.graph_objects as go
from google.oauth2.service_account import Credentials
from streamlit_option_menu import option_menu
import time 

# --- 1. CONFIGURAÇÃO VISUAL ---
st.set_page_config(page_title="Painel Tático TeamBrisa", layout="wide", page_icon="☁️", initial_sidebar_state="expanded")

if 'tema' not in st.session_state: st.session_state['tema'] = 'Claro'
if 'tarefas' not in st.session_state: st.session_state['tarefas'] = []

# --- 2. LÓGICA DE TEMAS ---
def aplicar_tema():
    tema = st.session_state['tema']
    
    if tema == 'Escuro':
        bg_color = "#0E1117"
        sidebar_bg = "#161B22"
        text_color = "#E6EDF3"
        card_bg = "#161B22"
        border_color = "rgba(48, 54, 61, 0.5)"
        metric_label = "#E6EDF3"
        shadow = "rgba(0,0,0,0.4)"
        
        st.session_state['chart_bg'] = 'rgba(0,0,0,0)'
        st.session_state['chart_font'] = '#E6EDF3'
        st.session_state['chart_grid'] = '#30363D'
        st.session_state['neon_gradient'] = [(0.0, "rgba(0, 255, 127, 0.4)"), (1.0, "#00FF7F")]
        st.session_state['menu_bg'] = "#161B22"
        st.session_state['menu_txt'] = "#E6EDF3"
        
    else: # TEMA CLARO
        bg_color = "#F8F9FA" 
        sidebar_bg = "#FFFFFF"
        text_color = "#212529"
        card_bg = "#FFFFFF"
        border_color = "rgba(0,0,0,0.05)"
        metric_label = "#495057"
        shadow = "rgba(0,0,0,0.08)"
        
        st.session_state['chart_bg'] = 'rgba(255,255,255,0)'
        st.session_state['chart_font'] = '#212529'
        st.session_state['chart_grid'] = '#E9ECEF'
        st.session_state['neon_gradient'] = [(0.0, "#A8E6CF"), (1.0, "#008000")]
        st.session_state['menu_bg'] = "#FFFFFF"
        st.session_state['menu_txt'] = "#212529"

    st.session_state['colorscale_monit'] = [
        [0.0, "#FF6D00"], [0.01, "#FF6D00"], [0.01, "#FF4B4B"], [0.69, "#FF4B4B"], 
        [0.69, "#FFD700"], [0.79, "#FFD700"], [0.79, "#00FF7F"], [1.0, "#00FF7F"]
    ]

    st.markdown(f"""
    <style>
        /* ANIMAÇÕES */
        @keyframes fadeInUp {{ from {{ opacity: 0; transform: translate3d(0, 20px, 0); }} to {{ opacity: 1; transform: translate3d(0, 0, 0); }} }}
        .block-container {{ animation: fadeInUp 0.8s cubic-bezier(0.2, 0.8, 0.2, 1) both; }}

        .stApp {{ background-color: {bg_color}; color: {text_color}; }}
        [data-testid="stSidebar"] {{ background-color: {sidebar_bg}; border-right: 1px solid {border_color}; }}
        h1, h2, h3, h4 {{ color: {text_color} !important; font-family: 'Segoe UI', sans-serif; font-weight: 700; }}
        p, label, span {{ color: {text_color}; }}
        
        /* KPI Cards */
        div[data-testid="stMetric"] {{
            background-color: {card_bg}; 
            border: 1px solid {border_color};
            padding: 20px; 
            border-radius: 12px; 
            box-shadow: 0 4px 6px {shadow};
            height: 100%;
            transition: transform 0.2s ease, box-shadow 0.2s ease;
        }}
        div[data-testid="stMetric"]:hover {{ transform: translateY(-3px); box-shadow: 0 10px 15px {shadow}; }}
        div[data-testid="stMetricValue"] {{ font-size: 32px !important; font-weight: 800; color: #00FF7F !important; }}
        div[data-testid="stMetricLabel"] {{ font-size: 16px !important; font-weight: 700 !important; color: {metric_label}; opacity: 0.8; }}
        
        /* Inputs */
        .stSelectbox div[data-baseweb="select"] > div, .stTextInput input, .stFormSubmitButton > button {{
            background-color: {card_bg}; color: {text_color}; border-color: {border_color}; border-radius: 8px;
        }}
        
        /* Tabs */
        .stTabs [data-baseweb="tab"] {{
            background-color: {card_bg}; border: 1px solid {border_color}; color: {text_color};
            font-size: 16px !important; font-weight: 600; border-radius: 5px;
        }}
        .stTabs [aria-selected="true"] {{
            background-color: #00FF7F !important; color: #000000 !important; border-color: #00FF7F !important;
        }}
        
        /* RANKING CARD VISUAL */
        .ranking-card-inner {{
            width: 100%;
            background-color: {card_bg};
            border: 1px solid {border_color};
            border-radius: 16px;
            box-shadow: 0 4px 12px {shadow};
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            padding: 20px 10px;
            position: relative;
            margin-top: 15px;
            margin-bottom: 10px;
        }}
        
        .medal-icon {{ font-size: 40px; position: absolute; top: -20px; z-index: 10; filter: drop-shadow(0 2px 2px rgba(0,0,0,0.2)); }}
        .avatar-img {{
            width: 90px; height: 90px; border-radius: 50%; object-fit: cover;
            border: 4px solid {card_bg}; box-shadow: 0 5px 15px {shadow};
            margin-bottom: 10px; margin-top: 10px;
        }}
        .name-text {{
            font-size: 13px; font-weight: 700; color: {text_color}; text-align: center;
            line-height: 1.2; margin-bottom: 5px; height: 35px; display: flex; align-items: center; justify-content: center; text-transform: uppercase;
        }}
        .score-text {{ font-size: 22px; font-weight: 900; letter-spacing: -1px; }}
        
        /* Botão Personalizado */
        .stButton button {{
            width: 100%;
            border-radius: 20px;
            border: 1px solid {border_color};
            background-color: transparent;
            color: {text_color};
            font-size: 12px;
        }}
        .stButton button:hover {{
            border-color: #00FF7F;
            color: #00FF7F;
            background-color: {card_bg};
        }}
        
        /* CSS 3D Flip Card */
        .flip-card {{
            background-color: transparent;
            width: 220px;
            height: 300px;
            perspective: 1000px;
            margin-top: 15px;
        }}
        .flip-card-inner {{
            position: relative;
            width: 100%;
            height: 100%;
            text-align: center;
            transition: transform 0.8s cubic-bezier(0.175, 0.885, 0.32, 1.275);
            transform-style: preserve-3d;
            border-radius: 16px;
            box-shadow: 0 4px 8px {shadow};
        }}
        .flip-card:hover .flip-card-inner {{ transform: rotateY(180deg); }}
        .flip-card-front, .flip-card-back {{
            position: absolute; width: 100%; height: 100%; -webkit-backface-visibility: hidden; backface-visibility: hidden;
            border-radius: 16px; border: 1px solid {border_color}; background-color: {card_bg};
            display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 15px;
        }}
        .flip-card-front {{ z-index: 2; }}
        .flip-card-back {{
            transform: rotateY(180deg); background-color: {card_bg}; border: 1px solid #00FF7F;
            box-shadow: 0 0 15px rgba(0, 255, 127, 0.1);
        }}
        .metrics-list {{ width: 100%; text-align: left; font-size: 13px; color: {text_color}; margin-top: 10px; }}
        .metric-row {{ display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid {border_color}; }}
        .metric-row:last-child {{ border-bottom: none; }}
        .metric-label {{ font-weight: 600; opacity: 0.8; }}
        .metric-val {{ font-weight: 800; color: #00FF7F; }}

    </style>
    """, unsafe_allow_html=True)

aplicar_tema()

# --- 3. CONFIGURAÇÃO DE USUÁRIOS ---
USUARIOS = {
    "admin": {"senha": "123", "nome_planilha": "Gestor Geral", "funcao": "admin"},
    "damiao": {"senha": "123", "nome_planilha": "DAMIAO EMANUEL DE CARVALHO GOMES", "funcao": "colaborador"},
    "aluizio": {"senha": "123", "nome_planilha": "ALUIZIO BEZERRA JUNIOR", "funcao": "colaborador"},
}

# --- 4. CONEXÃO E DADOS ---
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

def tratar_tempo_tma(valor):
    if not isinstance(valor, str): return float(valor) if valor else 0.0
    v = valor.strip()
    if v == '' or v == '-' or v == '#N/A': return 0.0
    if ':' in v:
        partes = v.split(':')
        try:
            if len(partes) == 3: return (float(partes[0]) * 60) + float(partes[1]) + (float(partes[2]) / 60)
            elif len(partes) == 2: return float(partes[0]) + (float(partes[1]) / 60)
        except: return 0.0
    v = v.replace(',', '.')
    try: return float(v)
    except: return 0.0

def tratar_numero_inteiro(valor):
    if not isinstance(valor, str): return valor
    v = valor.strip()
    if v == '' or v == '-' or v == '#N/A' or v == '': return 0
    try: return int(float(v.replace(',', '.')))
    except: return 0

# --- 5. PROCESSAMENTO ---
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

def processar_dados_tma_complexo(todos_dados):
    try:
        datas_p1 = todos_dados[1][14:30] 
        vals_p1 = todos_dados[2][14:30]
        datas_p2 = todos_dados[4][14:30]
        vals_p2 = todos_dados[5][14:30]
        datas_full = datas_p1 + datas_p2
        vals_full = vals_p1 + vals_p2
        df = pd.DataFrame({'Data': datas_full, 'MinutosRaw': vals_full})
        df = df[df['Data'].str.strip() != ""]
        df['Minutos'] = df['MinutosRaw'].apply(tratar_tempo_tma)
        return df
    except Exception as e:
        return pd.DataFrame()

def processar_monitoramento_diamantes(todos_dados):
    try:
        bloco = [linha[14:46] for linha in todos_dados[15:18]] 
        if not bloco: return pd.DataFrame()
        datas = bloco[0][1:] 
        dados_processados = []
        for linha in bloco[1:]:
            nome = linha[0]
            valores = linha[1:]
            for data, val in zip(datas, valores):
                if data.strip() != "":
                    dados_processados.append({
                        'Operador': nome,
                        'Data': data,
                        'Diamantes': tratar_numero_inteiro(val)
                    })
        return pd.DataFrame(dados_processados)
    except Exception as e:
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
                    lista_limpa.append({'Colaborador': nome, titulo_coluna: val_float})
    df = pd.DataFrame(lista_limpa)
    if not df.empty:
        df = df.sort_values(by=titulo_coluna, ascending=False)
    return df

def definir_cor_pela_nota(valor):
    if valor >= 90: return '#00FF7F' 
    elif valor >= 70: return '#FFD700' 
    else: return '#FF4B4B'

# --- 6. FUNÇÃO PARA EXTRAIR MÉTRICAS DO OPERADOR ---
def extrair_metricas_resumo(nome, df_completo):
    metricas = {
        "CSAT": "-", "TPC": "-", "Interação": "-", "IR": "-", "Pontualidade": "-", "Meta": "-"
    }
    
    if not df_completo.empty:
        df_op = df_completo[df_completo['Operador'] == nome]
        if not df_op.empty:
            for m in metricas.keys():
                linha = df_op[df_op['Metrica'].str.contains(m, case=False, na=False)]
                if not linha.empty:
                    vals = linha.iloc[0, 2:].values
                    vals_validos = [v for v in vals if v != "" and v != "-"]
                    if vals_validos:
                        metricas[m] = vals_validos[-1]
    return metricas

# --- 7. VISUALIZAÇÃO ---
def renderizar_ranking_visual(titulo, df, col_val, cor_input, altura_base=250):
    st.markdown(f"#### {titulo}")
    if not df.empty:
        altura_dinamica = max(altura_base, len(df) * 35)
        if cor_input.startswith('#'):
            fig = px.bar(df, y="Colaborador", x=col_val, text=col_val, orientation='h', color_discrete_sequence=[cor_input])
        else:
            fig = px.bar(df, y="Colaborador", x=col_val, text=col_val, orientation='h', color=cor_input, color_discrete_map="identity")
        
        fig.update_traces(
            texttemplate='<b>%{text:.1f}%</b>', textposition='inside', insidetextanchor='start', 
            textfont_size=18, textfont_weight='bold', textfont_color='black'
        )
        fig.update_layout(
            paper_bgcolor=st.session_state['chart_bg'], plot_bgcolor=st.session_state['chart_bg'], font_color=st.session_state['chart_font'],
            xaxis=dict(showgrid=False, showticklabels=False, range=[0, 115]), 
            yaxis=dict(autorange="reversed", title=None, tickfont=dict(size=15, family="Segoe UI", weight="bold")),
            margin=dict(l=0, r=0, t=0, b=0), height=altura_dinamica, dragmode=False, showlegend=False
        )
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
    else:
        st.caption("Sem dados.")

# --- 8. TAREFAS ---
def adicionar_tarefa(titulo, categoria, responsavel):
    nova_tarefa = {'id': int(time.time() * 1000), 'titulo': titulo, 'categoria': categoria, 'responsavel': responsavel, 'status': 'Não Iniciado'}
    st.session_state['tarefas'].append(nova_tarefa)

def mover_tarefa(id_tarefa, novo_status):
    for t in st.session_state['tarefas']:
        if t['id'] == id_tarefa:
            t['status'] = novo_status
            break

def excluir_tarefa(id_tarefa):
    st.session_state['tarefas'] = [t for t in st.session_state['tarefas'] if t['id'] != id_tarefa]

# --- 9. LOGIN ---
def login():
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        st.markdown("<br><br><br>", unsafe_allow_html=True)
        with st.container(border=True):
            st.markdown("<h2 style='text-align: center; color: #212529;'>🔐 Acesso TeamBrisa</h2>", unsafe_allow_html=True)
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

# --- 10. PAINEL PRINCIPAL ---
def main():
    dados_brutos = obter_dados_completos()
    if not dados_brutos: st.stop()

    df_grafico_total = processar_matriz_grafico(dados_brutos)
    df_tma_total = processar_dados_tma_complexo(dados_brutos) 
    df_monit = processar_monitoramento_diamantes(dados_brutos)
    df_tam_total = processar_tabela_ranking(dados_brutos, 0, 1, range(1, 25), 'TAM')
    df_n3_total = processar_tabela_ranking(dados_brutos, 5, 6, range(1, 25), 'Nível 3')
    df_n2_total = processar_tabela_ranking(dados_brutos, 8, 9, range(1, 25), 'Nível 2')
    df_n1_total = processar_tabela_ranking(dados_brutos, 11, 12, range(1, 25), 'Nível 1')

    perfil = st.session_state['funcao']
    nome_usuario = st.session_state['nome_real']

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

    with st.sidebar:
        st.markdown(f"<h2 style='text-align: center; color: #58A6FF;'>☁️ TeamBrisa</h2>", unsafe_allow_html=True)
        st.info(f"Logado como: **{nome_usuario}** ({perfil.upper()})")
        st.markdown("---")
        
        escolha = option_menu(
            menu_title=None, 
            options=["Painel Tático", "Pausas", "Calendário", "Tarefas", "Gerenciamento"], 
            icons=["graph-up-arrow", "clock-history", "calendar-week", "list-check", "gear"], 
            default_index=0,
            styles={
                "container": {"background-color": st.session_state['menu_bg'], "padding": "0!important"}, 
                "icon": {"color": st.session_state['menu_txt'], "font-size": "16px"},
                "nav-link": {
                    "font-size": "14px", "text-align": "left", "margin":"0px", "color": st.session_state['menu_txt'] 
                },
                "nav-link-selected": {"background-color": "#238636", "color": "white"},
            }
        )
        st.markdown("<br>", unsafe_allow_html=True)
        
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

    if escolha == "Painel Tático":
        st.title("📊 Painel Tático")
        st.markdown("---")
        
        # --- LINHA 1 DE KPIS ---
        kpi1, kpi2, kpi3 = st.columns(3)
        if not df_tam_total.empty:
            media_time = df_tam_total[df_tam_total['TAM'] > 0]['TAM'].mean()
            melhor_op_nome = df_tam_total.iloc[0]['Colaborador']
            melhor_op_valor = df_tam_total.iloc[0]['TAM']
            
            # --- CONTAGEM DE RISCO (IGNORA ZERADOS) ---
            df_risco_real = df_tam_total[(df_tam_total['TAM'] < 70) & (df_tam_total['TAM'] > 0.01)]
            qtd_nivel_1 = len(df_risco_real)
            
        else:
            media_time, melhor_op_valor, qtd_nivel_1 = 0, 0, 0
            melhor_op_nome = "-"

        kpi1.metric("🎯 Média do Time", f"{media_time:.1f}%")
        kpi2.metric("🏆 Melhor Performance", f"{melhor_op_nome}", f"{melhor_op_valor:.1f}%")
        kpi3.metric("🚨 Zona de Atenção", f"{qtd_nivel_1} Operadores", delta_color="inverse")
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        # --- LINHA 2 DE KPIS EXPANDIDA (5 COLUNAS) ---
        kpi4, kpi5, kpi6, kpi7, kpi8 = st.columns(5)
        try:
            val_tpc = dados_brutos[8][14] if len(dados_brutos) > 8 else "0"
            val_conf = dados_brutos[12][14] if len(dados_brutos) > 12 else "0"
        except:
            val_tpc, val_conf = "0", "0"
            
        kpi4.metric("⏱️ TPC - Geral", val_tpc)
        kpi5.metric("✅ Conformidade", val_conf)
        kpi6.metric("🗣️ Conversação", "🚧 Em breve")
        kpi7.metric("💬 Tratamento", "🚧 Em breve")
        kpi8.metric("⏳ Espera Média", "🚧 Em breve")
        
        st.markdown("---")

        tab_graficos, tab_ranking = st.tabs(["📈 Visão Gráfica", "🏆 Ranking Detalhado"])

        with tab_graficos:
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
                            fig.update_layout(legend=dict(orientation="h", y=1.1, title=None, font=dict(size=14)))
                        else:
                            fig = px.line(df_long, x='Data', y='Performance', markers=True)
                            fig.update_traces(line_color='#00FF7F', line_width=4, marker_size=8, marker_color='#FFFFFF')

                        fig.update_layout(
                            paper_bgcolor=st.session_state['chart_bg'], plot_bgcolor=st.session_state['chart_bg'], font_color=st.session_state['chart_font'],
                            yaxis_ticksuffix="%", yaxis_range=[0, 115], hovermode="x unified",
                            margin=dict(l=0, r=0, t=20, b=20), height=400,
                            xaxis=dict(tickfont=dict(size=14)), yaxis=dict(tickfont=dict(size=14))
                        )
                        fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor=st.session_state['chart_grid'])
                        st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.info("Sem dados.")

                st.markdown("---")
                
                # --- GRÁFICO DE RADAR (ARANHA) ---
                st.markdown(f"### 🕸️ Perfil do Operador (Média)")
                if filtro_op and not df_grafico.empty:
                    
                    df_op_radar = df_grafico[df_grafico['Operador'] == filtro_op]
                    
                    if not df_op_radar.empty:
                        metricas_radar = ['CSAT', 'TPC', 'Interação', 'IR', 'Pontualidade']
                        valores_radar = []
                        meta_radar = []
                        
                        for m in metricas_radar:
                            linha = df_op_radar[df_op_radar['Metrica'].str.contains(m, case=False, na=False)]
                            if not linha.empty:
                                vals_str = linha.iloc[0, 2:].values
                                vals_num = [tratar_porcentagem(v) for v in vals_str if v != '' and v != '-']
                                if vals_num:
                                    media = sum(vals_num) / len(vals_num)
                                else:
                                    media = 0
                                valores_radar.append(media)
                            else:
                                valores_radar.append(0)
                            
                            if m == 'TPC': meta_radar.append(15) 
                            else: meta_radar.append(100)
                        
                        fig_radar = go.Figure()

                        fig_radar.add_trace(go.Scatterpolar(
                            r=[100, 100, 100, 100, 100],
                            theta=metricas_radar,
                            fill=None,
                            name='Meta Alvo',
                            line_color='#FF4B4B',
                            line_dash='dash'
                        ))

                        fig_radar.add_trace(go.Scatterpolar(
                            r=valores_radar,
                            theta=metricas_radar,
                            fill='toself',
                            name=f'Realizado ({filtro_op})',
                            line_color='#00B4D8',
                            fillcolor='rgba(0, 180, 216, 0.3)'
                        ))

                        fig_radar.update_layout(
                            polar=dict(
                                radialaxis=dict(
                                    visible=True,
                                    range=[0, 100],
                                    gridcolor=st.session_state['chart_grid'],
                                    linecolor=st.session_state['chart_grid'],
                                    tickfont=dict(color=st.session_state['menu_txt'], size=15) # AUMENTO FONTE
                                ),
                                angularaxis=dict(
                                    tickfont=dict(size=22, color=st.session_state['menu_txt'], weight='bold') # AUMENTO FONTE RÓTULOS
                                )
                            ),
                            showlegend=True,
                            legend=dict(font=dict(size=16)), # AUMENTO FONTE LEGENDA
                            paper_bgcolor=st.session_state['chart_bg'],
                            plot_bgcolor=st.session_state['chart_bg'],
                            font_color=st.session_state['chart_font'],
                            margin=dict(l=60, r=60, t=20, b=20),
                            height=450
                        )
                        
                        st.plotly_chart(fig_radar, use_container_width=True)
                    else:
                        st.info("Dados insuficientes para gerar o radar.")
                else:
                    st.info("Selecione um operador para ver o perfil.")

                st.markdown("---")
                st.markdown("### 💎 Monitoramento de Performance (Diamantes)")
                
                if not df_monit.empty:
                    fig_monit = px.density_heatmap(
                        df_monit, x='Data', y='Operador', z='Diamantes', text_auto=True,
                        color_continuous_scale=st.session_state['colorscale_monit'], range_color=[0, 42]
                    )
                    fig_monit.update_layout(
                        paper_bgcolor=st.session_state['chart_bg'], plot_bgcolor=st.session_state['chart_bg'], font_color=st.session_state['chart_font'],
                        xaxis_title=None, yaxis_title=None, coloraxis_showscale=False, height=250, margin=dict(l=0, r=0, t=30, b=10),
                        yaxis=dict(tickfont=dict(size=15, weight='bold'))
                    )
                    fig_monit.update_xaxes(showgrid=False)
                    fig_monit.update_yaxes(showgrid=False)
                    st.plotly_chart(fig_monit, use_container_width=True, config={'displayModeBar': False})
                else:
                    st.info("Sem dados de monitoramento.")

            with col_dir:
                renderizar_ranking_visual("🏆 Resultado Geral", df_tam, "TAM", "Cor_Dinamica")
                st.markdown("---")
                renderizar_ranking_visual("🥇 Nível 3", df_n3, "Nível 3", "#00FF7F")
                renderizar_ranking_visual("🥈 Nível 2", df_n2, "Nível 2", "#FFD700")
                renderizar_ranking_visual("🥉 Nível 1", df_n1, "Nível 1", "#FF4B4B")

        with tab_ranking:
            st.markdown("### 🏆 Ranking do Time (TAM)")
            
            f1, f2, f3 = st.columns(3)
            with f1: check_high = st.checkbox("🟢 Acima de 90%", value=True)
            with f2: check_med = st.checkbox("🟡 70% a 89%", value=True)
            with f3: check_low = st.checkbox("🔴 Abaixo de 70%", value=True)
            
            if not df_tam_total.empty:
                df_rank_cards = df_tam_total.sort_values(by="TAM", ascending=False).reset_index(drop=True)
                
                filtro_indices = []
                for i, row in df_rank_cards.iterrows():
                    v = row['TAM']
                    keep = False
                    if v >= 90 and check_high: keep = True
                    elif 70 <= v < 90 and check_med: keep = True
                    elif v < 70 and check_low: keep = True
                    if keep: filtro_indices.append(i)
                
                df_filtered = df_rank_cards.loc[filtro_indices]
                
                if not df_filtered.empty:
                    html_cards = '<div class="ranking-grid">'
                    
                    for idx, row in df_filtered.iterrows():
                        nome = row['Colaborador']
                        score = row['TAM']
                        
                        original_idx = df_rank_cards[df_rank_cards['Colaborador'] == nome].index[0]
                        if original_idx == 0: icon = "👑"
                        elif original_idx == 1: icon = "🥈"
                        elif original_idx == 2: icon = "🥉"
                        else: icon = "🎖️"
                        
                        if score >= 90: cor_val = "#00FF7F"
                        elif score >= 70: cor_val = "#FFD700"
                        else: cor_val = "#FF4B4B"
                        
                        nome_formatado = nome.replace(" ", "+")
                        avatar_url = f"https://ui-avatars.com/api/?name={nome_formatado}&background=random&color=fff&size=128"
                        
                        # --- RECUPERA AS MÉTRICAS REAIS DO OPERADOR ---
                        dados_op = extrair_metricas_resumo(nome, df_grafico_total)
                        
                        # HTML DO CARD FLIP 3D SEM INDENTAÇÃO
                        html_cards += f"""<div class="flip-card" onclick="void(0)"><div class="flip-card-inner"><div class="flip-card-front"><div class="medal-icon">{icon}</div><img src="{avatar_url}" class="avatar-img"><div class="name-text">{nome}</div><div class="score-text" style="color: {cor_val};">{score:.1f}%</div><div style="font-size: 10px; opacity: 0.7; margin-top: 5px;">👆 Passe o mouse</div></div><div class="flip-card-back"><h4 style="margin-bottom: 10px; color: {st.session_state['menu_txt']};">Métricas</h4><div class="metrics-list"><div class="metric-row"><span class="metric-label">CSAT:</span> <span class="metric-val">{dados_op['CSAT']}</span></div><div class="metric-row"><span class="metric-label">TPC:</span> <span class="metric-val">{dados_op['TPC']}</span></div><div class="metric-row"><span class="metric-label">Interação:</span> <span class="metric-val">{dados_op['Interação']}</span></div><div class="metric-row"><span class="metric-label">IR:</span> <span class="metric-val">{dados_op['IR']}</span></div><div class="metric-row"><span class="metric-label">Pontualidade:</span> <span class="metric-val">{dados_op['Pontualidade']}</span></div><div class="metric-row"><span class="metric-label">Meta:</span> <span class="metric-val">{dados_op['Meta']}</span></div></div></div></div></div>"""
                    
                    html_cards += '</div>'
                    st.markdown(html_cards, unsafe_allow_html=True)
                else:
                    st.warning("Nenhum operador encontrado com os filtros selecionados.")
            else:
                st.info("Sem dados para exibir no ranking.")

    elif escolha == "Pausas":
        st.title("⏸️ Controle de Pausas")
        st.info("🚧 Em desenvolvimento.")

    elif escolha == "Calendário":
        st.title("📅 Calendário")
        st.info("🚧 Em desenvolvimento.")

    elif escolha == "Tarefas":
        st.title("✅ Kanban Board")
        st.markdown("---")
        with st.expander("➕ Nova Tarefa", expanded=False):
            with st.form("form_tarefa"):
                c1, c2 = st.columns([3, 1])
                with c1: titulo = st.text_input("Descrição")
                with c2: cat = st.selectbox("Categoria", ["Vendas", "Admin", "Reunião", "Urgente"])
                if st.form_submit_button("Criar") and titulo:
                    adicionar_tarefa(titulo, cat, nome_usuario)
                    st.rerun()
        st.markdown("<br>", unsafe_allow_html=True)
        col_nao, col_ini, col_conc = st.columns(3)
        minhas_tarefas = [t for t in st.session_state['tarefas'] if t['responsavel'] == nome_usuario]

        with col_nao:
            st.markdown(f"<div style='border:1px solid #FF4B4B; padding:5px; border-radius:5px; text-align:center; color:#FF4B4B'><b>🔴 A Fazer</b></div><br>", unsafe_allow_html=True)
            for t in minhas_tarefas:
                if t['status'] == 'Não Iniciado':
                    with st.container(border=True):
                        st.markdown(f"**{t['titulo']}**")
                        st.caption(f"{t['categoria']}")
                        if st.button("▶️ Iniciar", key=f"go_{t['id']}", use_container_width=True):
                            mover_tarefa(t['id'], 'Iniciado')
                            st.rerun()
                        if st.button("🗑️", key=f"del_{t['id']}"):
                            excluir_tarefa(t['id'])
                            st.rerun()

        with col_ini:
            st.markdown(f"<div style='border:1px solid #FFD700; padding:5px; border-radius:5px; text-align:center; color:#FFD700'><b>🟡 Em Andamento</b></div><br>", unsafe_allow_html=True)
            for t in minhas_tarefas:
                if t['status'] == 'Iniciado':
                    with st.container(border=True):
                        st.markdown(f"**{t['titulo']}**")
                        st.caption(f"{t['categoria']}")
                        if st.button("✅ Concluir", key=f"fin_{t['id']}", use_container_width=True):
                            mover_tarefa(t['id'], 'Concluído')
                            st.rerun()
                        if st.button("⏪ Voltar", key=f"back_{t['id']}"):
                            mover_tarefa(t['id'], 'Não Iniciado')
                            st.rerun()

        with col_conc:
            st.markdown(f"<div style='border:1px solid #00FF7F; padding:5px; border-radius:5px; text-align:center; color:#00FF7F'><b>🟢 Concluído</b></div><br>", unsafe_allow_html=True)
            for t in minhas_tarefas:
                if t['status'] == 'Concluído':
                    with st.container(border=True):
                        st.markdown(f"~~{t['titulo']}~~")
                        if st.button("🗑️ Arquivar", key=f"arc_{t['id']}", use_container_width=True):
                            excluir_tarefa(t['id'])
                            st.rerun()
                        if st.button("⏪ Reabrir", key=f"reopen_{t['id']}"):
                            mover_tarefa(t['id'], 'Iniciado')
                            st.rerun()

    elif escolha == "Gerenciamento":
        st.title("⚙️ Gerenciamento")
        st.markdown("---")
        st.subheader("🎨 Aparência")
        tema_atual = st.session_state['tema']
        novo_tema = st.radio("Tema:", ["Escuro", "Claro"], index=0 if tema_atual == "Escuro" else 1, horizontal=True)
        if novo_tema != tema_atual:
            st.session_state['tema'] = novo_tema
            st.rerun()

# --- INICIALIZAÇÃO ---
if 'logado' not in st.session_state: st.session_state['logado'] = False
if not st.session_state['logado']: login()
else: main()
