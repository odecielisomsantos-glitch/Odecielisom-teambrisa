import streamlit as st
import pandas as pd
import gspread
import plotly.express as px
from google.oauth2.service_account import Credentials
from streamlit_option_menu import option_menu
import time 

# --- 1. CONFIGURAÇÃO VISUAL ---
# Define a configuração inicial da página, incluindo título, ícone e layout.
st.set_page_config(page_title="Painel Tático TeamBrisa", layout="wide", page_icon="☁️", initial_sidebar_state="expanded")

# Define o tema padrão como 'Claro' se ainda não estiver definido na sessão.
if 'tema' not in st.session_state: st.session_state['tema'] = 'Claro'
# Inicializa a lista de tarefas se ainda não existir.
if 'tarefas' not in st.session_state: st.session_state['tarefas'] = []

# --- 2. LÓGICA DE TEMAS ---
# Função para aplicar o tema (Claro ou Escuro) escolhido pelo usuário.
def aplicar_tema():
    tema = st.session_state['tema']
    
    # Definição das variáveis de cor baseadas no tema
    if tema == 'Escuro':
        bg_color = "#0E1117"
        sidebar_bg = "#161B22"
        text_color = "#E6EDF3"
        card_bg = "#161B22"
        border_color = "#30363D"
        metric_label = "#E6EDF3"
        shadow = "rgba(0,0,0,0.3)"
        
        st.session_state['chart_bg'] = 'rgba(0,0,0,0)'
        st.session_state['chart_font'] = '#E6EDF3'
        st.session_state['chart_grid'] = '#30363D'
        st.session_state['neon_gradient'] = [(0.0, "rgba(0, 255, 127, 0.4)"), (1.0, "#00FF7F")]
        
        st.session_state['menu_bg'] = "#161B22"
        st.session_state['menu_txt'] = "#E6EDF3"
        
    else: # TEMA CLARO (DEFAULT)
        bg_color = "#F8F9FA" # Cinza bem clarinho pro fundo
        sidebar_bg = "#FFFFFF"
        text_color = "#212529"
        card_bg = "#FFFFFF"
        border_color = "#DEE2E6"
        metric_label = "#495057"
        shadow = "rgba(0,0,0,0.1)"
        
        st.session_state['chart_bg'] = 'rgba(255,255,255,0)'
        st.session_state['chart_font'] = '#212529'
        st.session_state['chart_grid'] = '#E9ECEF'
        st.session_state['neon_gradient'] = [(0.0, "#A8E6CF"), (1.0, "#008000")]
        
        st.session_state['menu_bg'] = "#FFFFFF"
        st.session_state['menu_txt'] = "#212529"

    # Regra de Cores do Monitoramento
    # Define a escala de cores para o gráfico de monitoramento.
    # A imagem mostra a necessidade de uma regra de negócio para travar o máximo em 42 diamantes, o que é refletido na escala de cores que define o verde para valores acima de um certo limiar.
    st.session_state['colorscale_monit'] = [
        [0.0, "#FF6D00"], [0.01, "#FF6D00"], [0.01, "#FF4B4B"], [0.69, "#FF4B4B"], 
        [0.69, "#FFD700"], [0.79, "#FFD700"], [0.79, "#00FF7F"], [1.0, "#00FF7F"]
    ]

    # CSS GLOBAL
    # Aplica estilos CSS globais para a aplicação.
    st.markdown(f"""
    <style>
        /* Fundo e Texto Geral */
        .stApp {{ background-color: {bg_color}; color: {text_color}; }}
        [data-testid="stSidebar"] {{ background-color: {sidebar_bg}; border-right: 1px solid {border_color}; }}
        
        /* Tipografia */
        h1, h2, h3, h4 {{ color: {text_color} !important; font-family: 'Segoe UI', sans-serif; font-weight: 700; }}
        p, label, span {{ color: {text_color}; }}
        
        /* Cards KPI */
        div[data-testid="stMetric"] {{
            background-color: {card_bg}; 
            border: 1px solid {border_color};
            padding: 15px; 
            border-radius: 10px; 
            box-shadow: 0 2px 5px {shadow};
        }}
        div[data-testid="stMetricValue"] {{ font-size: 32px !important; font-weight: 800; color: #00FF7F !important; }}
        div[data-testid="stMetricLabel"] {{ font-size: 18px !important; font-weight: 700 !important; color: {metric_label}; }}
        
        /* Inputs e Selects */
        .stSelectbox div[data-baseweb="select"] > div, .stTextInput input, .stFormSubmitButton > button {{
            background-color: {card_bg}; 
            color: {text_color}; 
            border-color: {border_color}; 
            border-radius: 8px;
        }}
        
        /* Abas (Tabs) */
        .stTabs [data-baseweb="tab"] {{
            background-color: {card_bg}; 
            border: 1px solid {border_color}; 
            color: {text_color};
            font-size: 16px !important; 
            font-weight: 600;
            border-radius: 5px;
        }}
        .stTabs [aria-selected="true"] {{
            background-color: #00FF7F !important; 
            color: #000000 !important;
            border-color: #00FF7F !important;
        }}
        
        /* --- ESTILO DOS CARDS DE RANKING (SCROLL HORIZONTAL) --- */
        /* Container que permite o scroll horizontal dos cards */
        .scrolling-wrapper {{
            display: flex;
            flex-wrap: nowrap;
            overflow-x: auto;
            padding: 20px 10px;
            gap: 20px;
            -webkit-overflow-scrolling: touch; /* Scroll suave no mobile */
        }}
        
        /* Estilo individual de cada card */
        /* As imagens mostram o card de ranking com um layout específico: ícone de medalha, avatar, nome e pontuação colorida. O CSS abaixo define esse estilo. */
        .ranking-card {{
            flex: 0 0 auto; /* Garante que os cards não encolham e fiquem lado a lado */
            width: 200px;
            height: 280px;
            background-color: {card_bg};
            border: 1px solid {border_color};
            border-radius: 15px;
            box-shadow: 0 4px 8px {shadow};
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            padding: 15px;
            transition: transform 0.3s ease; /* Efeito de hover suave */
        }}
        
        .ranking-card:hover {{
            transform: scale(1.05); /* Aumenta ligeiramente o card ao passar o mouse */
            border-color: #00FF7F;
        }}
        
        /* Ícone da medalha no topo do card */
        .medal-icon {{
            font-size: 40px;
            margin-bottom: -15px; /* Sobrepõe levemente o avatar */
            z-index: 10;
            filter: drop-shadow(0 2px 2px rgba(0,0,0,0.2));
        }}
        
        /* Imagem do avatar */
        .avatar-img {{
            width: 100px;
            height: 100px;
            border-radius: 50%; /* Deixa a imagem redonda */
            object-fit: cover;
            border: 4px solid {card_bg};
            box-shadow: 0 3px 6px {shadow};
            margin-bottom: 15px;
        }}
        
        /* Texto com o nome do colaborador */
        .name-text {{
            font-size: 15px;
            font-weight: 700;
            color: {text_color};
            text-align: center;
            line-height: 1.2;
            margin-bottom: 10px;
            height: 40px; /* Altura fixa para alinhar nomes de tamanhos diferentes */
            display: flex;
            align-items: center;
            justify-content: center;
        }}
        
        /* Texto com a pontuação */
        .score-text {{
            font-size: 24px;
            font-weight: 900;
        }}
        
        /* Scrollbar customizada para o container horizontal */
        .scrolling-wrapper::-webkit-scrollbar {{ height: 8px; }}
        .scrolling-wrapper::-webkit-scrollbar-track {{ background: transparent; }}
        .scrolling-wrapper::-webkit-scrollbar-thumb {{ background-color: #cccccc; border-radius: 20px; }}
        
    </style>
    """, unsafe_allow_html=True)

aplicar_tema()

# --- 3. CONFIGURAÇÃO DE USUÁRIOS ---
# Dicionário com os usuários, senhas e informações de acesso.
# O painel mostra o usuário logado, por exemplo, "Gestor Geral (ADMIN)". As informações de login são usadas para autenticação e personalização da visão.
USUARIOS = {
    "admin": {"senha": "123", "nome_planilha": "Gestor Geral", "funcao": "admin"},
    "damiao": {"senha": "123", "nome_planilha": "DAMIAO EMANUEL DE CARVALHO GOMES", "funcao": "colaborador"},
    "aluizio": {"senha": "123", "nome_planilha": "ALUIZIO BEZERRA JUNIOR", "funcao": "colaborador"},
}

# --- 4. CONEXÃO E DADOS ---
# Função para conectar ao Google Sheets usando as credenciais do Streamlit secrets.
@st.cache_resource
def conectar_google_sheets():
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    credenciais_info = dict(st.secrets["gcp_service_account"])
    credenciais_info["private_key"] = credenciais_info["private_key"].replace("\\n", "\n")
    credentials = Credentials.from_service_account_info(credenciais_info, scopes=scopes)
    gc = gspread.authorize(credentials)
    return gc

# Função para obter todos os dados da planilha, com cache para performance.
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

# Funções auxiliares para tratamento de dados (porcentagem, tempo, números inteiros).
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
# Funções para processar os dados brutos da planilha em DataFrames úteis para gráficos e tabelas.

def processar_matriz_grafico(todos_dados):
    # Processa a matriz principal de dados para o gráfico de evolução mensal.
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
    # Processa os dados de TMA (Tempo Médio de Atendimento), lidando com a estrutura complexa da planilha.
    # As imagens mostram gráficos e tabelas de TMA, indicando a necessidade de processar esses dados. O código extrai e trata os dados de TMA de diferentes partes da planilha.
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
    # Processa os dados de monitoramento de performance (diamantes).
    # A imagem mostra um erro relacionado ao processamento de dados de monitoramento, indicando a necessidade desta função.
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
    # Processa os dados para as tabelas de ranking (TAM, Nível 1, 2, 3).
    # A imagem mostra as tabelas de ranking por nível, que são geradas por esta função.
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
    # Define a cor da nota com base em limiares.
    if valor >= 90: return '#00FF7F' # Verde
    elif valor >= 70: return '#FFD700' # Amarelo
    else: return '#FF4B4B' # Vermelho

# --- 6. VISUALIZAÇÃO ---
# Função para renderizar os gráficos de barras horizontais de ranking.
# As imagens mostram os gráficos de ranking visual que são gerados por esta função.
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

# --- 7. TAREFAS ---
# Funções para gerenciar o quadro Kanban de tarefas (adicionar, mover, excluir).
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

# --- 8. LOGIN ---
# Função para exibir a tela de login e autenticar o usuário.
# A imagem mostra um erro relacionado à função de login, indicando a importância desta parte do código.
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

# --- 9. PAINEL PRINCIPAL ---
# Função principal que renderiza o painel após o login.
def main():
    dados_brutos = obter_dados_completos()
    if not dados_brutos: st.stop()

    # Processamento dos dados para os diferentes componentes do painel.
    df_grafico_total = processar_matriz_grafico(dados_brutos)
    df_tma_total = processar_dados_tma_complexo(dados_brutos) 
    df_monit = processar_monitoramento_diamantes(dados_brutos)
    
    df_tam_total = processar_tabela_ranking(dados_brutos, 0, 1, range(1, 25), 'TAM')
    df_n3_total = processar_tabela_ranking(dados_brutos, 5, 6, range(1, 25), 'Nível 3')
    df_n2_total = processar_tabela_ranking(dados_brutos, 8, 9, range(1, 25), 'Nível 2')
    df_n1_total = processar_tabela_ranking(dados_brutos, 11, 12, range(1, 25), 'Nível 1')

    perfil = st.session_state['funcao']
    nome_usuario = st.session_state['nome_real']

    # Filtragem de dados com base no perfil do usuário (admin vê tudo, colaborador vê apenas seus dados).
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

    # Adiciona a coluna de cor dinâmica ao DataFrame de TAM.
    if not df_tam.empty:
        df_tam['Cor_Dinamica'] = df_tam['TAM'].apply(definir_cor_pela_nota)

    # --- BARRA LATERAL ---
    with st.sidebar:
        st.markdown(f"<h2 style='text-align: center; color: #58A6FF;'>☁️ TeamBrisa</h2>", unsafe_allow_html=True)
        # Exibe o usuário logado na barra lateral.
        st.info(f"Logado como: **{nome_usuario}** ({perfil.upper()})")
        st.markdown("---")
        
        # Menu de navegação da barra lateral.
        # A imagem mostra o menu de navegação com as opções "Painel Tático", "Pausas", "Calendário", "Tarefas" e "Gerenciamento".
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
        
        # Filtros do Painel Tático.
        # A imagem mostra os filtros de "Operador" e "Métrica" na barra lateral.
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

        # Botão de Sair.
        # A imagem mostra o botão "Sair" na barra lateral.
        if st.button("Sair", use_container_width=True):
            st.session_state['logado'] = False
            st.rerun()

    # --- PÁGINAS ---
    if escolha == "Painel Tático":
        st.title("📊 Painel Tático")
        st.markdown("---")
        
        # --- KPIs ---
        # As imagens mostram os KPIs (Média do Time, Melhor Performance, Zona de Atenção, TPC, Conformidade) no topo do painel.
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

        kpi1.metric("🎯 Média do Time", f"{media_time:.1f}%")
        kpi2.metric("🏆 Melhor Performance", f"{melhor_op_nome}", f"{melhor_op_valor:.1f}%")
        kpi3.metric("🚨 Zona de Atenção", f"{qtd_nivel_1} Operadores", delta_color="inverse")
        
        st.markdown("<br>", unsafe_allow_html=True)
        kpi4, kpi5 = st.columns(2)
        try:
            val_tpc = dados_brutos[8][14] if len(dados_brutos) > 8 else "0"
            val_conf = dados_brutos[12][14] if len(dados_brutos) > 12 else "0"
        except:
            val_tpc, val_conf = "0", "0"
        kpi4.metric("⏱️ TPC - Geral", val_tpc)
        kpi5.metric("✅ Conformidade - Geral", val_conf)
        st.markdown("---")

        # --- ABAS ---
        # A imagem mostra as abas "Visão Gráfica" e "Ranking Detalhado".
        tab_graficos, tab_ranking = st.tabs(["📈 Visão Gráfica", "🏆 Ranking Detalhado"])

        # --- ABA: VISÃO GRÁFICA ---
        with tab_graficos:
            st.markdown(f"**Visão:** {filtro_op}")
            col_esq, col_dir = st.columns([2, 1.2], gap="large")

            with col_esq:
                # Gráfico de Evolução Mensal.
                # As imagens mostram o gráfico de "Evolução Mensal".
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
                
                # Gráfico de TMA.
                # As imagens mostram o gráfico de "TMA - Voz e Chat (Minutos)".
                st.markdown(f"### 📞 TMA - Voz e Chat (Minutos)")
                if not df_tma_total.empty:
                    fig_tma = px.bar(
                        df_tma_total, x='Data', y='Minutos', color='Minutos',
                        color_continuous_scale=st.session_state['neon_gradient'], text='MinutosRaw'
                    )
                    fig_tma.update_traces(
                        marker_line_width=0, textposition='outside', 
                        textfont_size=20, textfont_weight='bold', 
                        textfont_color='#FFFFFF' if st.session_state['tema'] == 'Escuro' else '#31333F', cliponaxis=False 
                    )
                    fig_tma.update_layout(
                        paper_bgcolor=st.session_state['chart_bg'], plot_bgcolor=st.session_state['chart_bg'], font_color=st.session_state['chart_font'],
                        xaxis_title=None, yaxis_title="Minutos", bargap=0.2, height=350,
                        margin=dict(l=0, r=0, t=20, b=20), coloraxis_showscale=False, hovermode="x unified",
                        xaxis=dict(tickfont=dict(size=14, weight='bold'))
                    )
                    fig_tma.update_yaxes(showgrid=True, gridwidth=1, gridcolor=st.session_state['chart_grid'], zeroline=False)
                    fig_tma.update_xaxes(showgrid=False)
                    st.plotly_chart(fig_tma, use_container_width=True, config={'displayModeBar': False})
                else:
                    st.info("Dados de TMA não encontrados.")

                st.markdown("---")
                # Gráfico de Monitoramento de Performance (Diamantes).
                # A imagem mostra um erro no gráfico de monitoramento, indicando a existência desta seção.
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
                # Rankings Visuais (Geral e por Nível).
                # As imagens mostram os rankings visuais ("Resultado Geral", "Nível 3", "Nível 2", "Nível 1").
                renderizar_ranking_visual("🏆 Resultado Geral", df_tam, "TAM", "Cor_Dinamica")
                st.markdown("---")
                renderizar_ranking_visual("🥇 Nível 3", df_n3, "Nível 3", "#00FF7F")
                renderizar_ranking_visual("🥈 Nível 2", df_n2, "Nível 2", "#FFD700")
                renderizar_ranking_visual("🥉 Nível 1", df_n1, "Nível 1", "#FF4B4B")

        # --- ABA: RANKING DETALHADO (CARDS) ---
        # As imagens mostram o "Ranking do Time (TAM)" na aba "Ranking Detalhado" no formato de cards.
        with tab_ranking:
            st.markdown("### 🏆 Ranking do Time (TAM)")
            if not df_tam_total.empty:
                df_rank_cards = df_tam_total.sort_values(by="TAM", ascending=False).reset_index(drop=True)
                
                # Constrói a string HTML com todos os cards.
                html_cards = '<div class="scrolling-wrapper">'
                
                for idx, row in df_rank_cards.iterrows():
                    nome = row['Colaborador']
                    score = row['TAM']
                    
                    # Define o ícone e a cor da medalha com base na posição no ranking.
                    if idx == 0: icon, cor_score = "👑", "#FFD700" 
                    elif idx == 1: icon, cor_score = "🥈", "#C0C0C0" 
                    elif idx == 2: icon, cor_score = "🥉", "#CD7F32" 
                    else: icon, cor_score = "🎖️", "#00FF7F" 
                    
                    # Define a cor da nota com base no valor.
                    if score >= 90: cor_val = "#00FF7F"
                    elif score >= 70: cor_val = "#FFD700"
                    else: cor_val = "#FF4B4B"
                    
                    # Gera a URL do avatar usando a API UI Avatars.
                    nome_formatado = nome.replace(" ", "+")
                    avatar_url = f"https://ui-avatars.com/api/?name={nome_formatado}&background=random&color=fff&size=128"
                    
                    # Adiciona o HTML do card à string principal.
                    html_cards += f"""
                    <div class="ranking-card">
                        <div class="medal-icon">{icon}</div>
                        <img src="{avatar_url}" class="avatar-img">
                        <div class="name-text">{nome}</div>
                        <div class="score-text" style="color: {cor_val};">{score:.1f}%</div>
                    </div>
                    """
                
                html_cards += '</div>'
                
                # Renderiza o HTML completo dos cards.
                st.markdown(html_cards, unsafe_allow_html=True)
            else:
                st.info("Sem dados para exibir no ranking.")

    # --- OUTRAS PÁGINAS (Em desenvolvimento ou Kanban) ---
    elif escolha == "Pausas":
        st.title("⏸️ Controle de Pausas")
        st.info("🚧 Em desenvolvimento.")

    elif escolha == "Calendário":
        st.title("📅 Calendário")
        st.info("🚧 Em desenvolvimento.")

    elif escolha == "Tarefas":
        st.title("✅ Kanban Board")
        st.markdown("---")
        # Formulário para adicionar nova tarefa.
        with st.expander("➕ Nova Tarefa", expanded=False):
            with st.form("form_tarefa"):
                c1, c2 = st.columns([3, 1])
                with c1: titulo = st.text_input("Descrição")
                with c2: cat = st.selectbox("Categoria", ["Vendas", "Admin", "Reunião", "Urgente"])
                if st.form_submit_button("Criar") and titulo:
                    adicionar_tarefa(titulo, cat, nome_usuario)
                    st.rerun()
        st.markdown("<br>", unsafe_allow_html=True)
        
        # Colunas do Kanban (A Fazer, Em Andamento, Concluído).
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
        # Opção para trocar o tema.
        tema_atual = st.session_state['tema']
        novo_tema = st.radio("Tema:", ["Escuro", "Claro"], index=0 if tema_atual == "Escuro" else 1, horizontal=True)
        if novo_tema != tema_atual:
            st.session_state['tema'] = novo_tema
            st.rerun()

# --- INICIALIZAÇÃO ---
# Verifica se o usuário está logado e direciona para a tela de login ou para o painel principal.
# A imagem mostra um erro na verificação de login, que é tratada aqui.
if 'logado' not in st.session_state: st.session_state['logado'] = False
if not st.session_state['logado']: login()
else: main()
