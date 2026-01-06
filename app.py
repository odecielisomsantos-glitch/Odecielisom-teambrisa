import streamlit as st
import pandas as pd
import gspread
import plotly.express as px
from google.oauth2.service_account import Credentials
from streamlit_option_menu import option_menu
import time 

# --- 1. CONFIGURAÇÃO VISUAL ---
st.set_page_config(page_title="Painel Tático TeamBrisa", layout="wide", page_icon="☁️", initial_sidebar_state="expanded")

if 'tema' not in st.session_state: st.session_state['tema'] = 'Escuro'
if 'tarefas' not in st.session_state: st.session_state['tarefas'] = []

# --- 2. LÓGICA DE TEMAS ---
def aplicar_tema():
    tema = st.session_state['tema']
    
    if tema == 'Escuro':
        bg_color = "#0E1117"
        sidebar_bg = "#161B22"
        text_color = "#E6EDF3"
        card_bg = "#161B22"
        border_color = "#30363D"
        metric_label = "#C9D1D9"
        
        st.session_state['chart_bg'] = 'rgba(0,0,0,0)'
        st.session_state['chart_font'] = '#E6EDF3'
        st.session_state['chart_grid'] = '#30363D'
        st.session_state['bar_color'] = '#00B4D8' # Azul Cyan para TMA
        
    else:
        bg_color = "#FFFFFF"
        sidebar_bg = "#F0F2F6"
        text_color = "#31333F"
        card_bg = "#FFFFFF"
        border_color = "#E0E0E0"
        metric_label = "#555555"
        
        st.session_state['chart_bg'] = 'rgba(255,255,255,0)'
        st.session_state['chart_font'] = '#31333F'
        st.session_state['chart_grid'] = '#E0E0E0'
        st.session_state['bar_color'] = '#0077B6'

    st.markdown(f"""
    <style>
        .stApp {{ background-color: {bg_color}; color: {text_color}; }}
        [data-testid="stSidebar"] {{ background-color: {sidebar_bg}; border-right: 1px solid {border_color}; }}
        h1, h2, h3, h4 {{ color: {text_color} !important; font-family: 'Segoe UI', sans-serif; font-weight: 600; }}
        p, label, span {{ color: {metric_label}; }}
        
        div[data-testid="stMetric"] {{
            background-color: {card_bg}; border: 1px solid {border_color};
            padding: 15px; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }}
        div[data-testid="stMetricValue"] {{ font-size: 28px !important; font-weight: bold; color: #00FF7F !important; }}
        div[data-testid="stMetricLabel"] {{ font-size: 16px !important; color: {metric_label}; }}
        
        .block-container {{ padding-top: 2rem; padding-bottom: 5rem; }}
        
        .stSelectbox div[data-baseweb="select"] > div, .stTextInput input {{
            background-color: {card_bg}; color: {text_color}; border-color: {border_color};
        }}
    </style>
    """, unsafe_allow_html=True)

aplicar_tema()

# --- 3. CONFIGURAÇÃO DE USUÁRIOS ---
USUARIOS = {
    "admin": {"senha": "123", "nome_planilha": "Gestor Geral", "funcao": "admin"},
    "damiao": {"senha": "123", "nome_planilha": "DAMIAO EMANUEL DE CARVALHO GOMES", "funcao": "colaborador"},
    "aluizio": {"senha": "123", "nome_planilha": "ALUIZIO BEZERRA JUNIOR", "funcao": "colaborador"},
    # Adicione os outros aqui...
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
    """
    Converte valores de tempo para FLOAT (Minutos).
    Aceita: "5,30" (5.3 min) ou "00:05:30" (converte para 5.5 min) ou inteiros.
    """
    if not isinstance(valor, str):
        return float(valor) if valor else 0.0
    
    v = valor.strip()
    if v == '' or v == '-' or v == '#N/A': return 0.0
    
    if ':' in v:
        partes = v.split(':')
        try:
            if len(partes) == 3: # HH:MM:SS
                h, m, s = map(float, partes)
                return (h * 60) + m + (s / 60)
            elif len(partes) == 2: # MM:SS
                m, s = map(float, partes)
                return m + (s / 60)
        except:
            return 0.0
            
    v = v.replace(',', '.')
    try:
        return float(v)
    except:
        return 0.0

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

def processar_dados_tma(todos_dados):
    try:
        # Fatiamento: Linhas 0 a 6, Colunas 14 a 30 (exclusivo)
        bloco_tma = [linha[14:30] for linha in todos_dados[0:6]]
        if bloco_tma:
            cabecalho = bloco_tma[0] 
            dados = bloco_tma[1:]   
            df = pd.DataFrame(dados)
            nomes_colunas = ['Operador'] + cabecalho[1:]
            if len(df.columns) == len(nomes_colunas):
                df.columns = nomes_colunas
            else:
                df.columns = nomes_colunas[:len(df.columns)]
            return df
        return pd.DataFrame()
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

# --- 6. VISUALIZAÇÃO ---
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
            paper_bgcolor=st.session_state['chart_bg'], plot_bgcolor=st.session_state['chart_bg'], font_color=st.session_state['chart_font'],
            xaxis=dict(showgrid=False, showticklabels=False, range=[0, 115]), yaxis=dict(autorange="reversed", title=None),
            margin=dict(l=0, r=0, t=0, b=0), height=altura_dinamica, dragmode=False, showlegend=False
        )
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
    else:
        st.caption("Sem dados.")

# --- 7. TAREFAS ---
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

# --- 8. LOGIN (A PARTE QUE FALTAVA) ---
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

# --- 9. PAINEL PRINCIPAL ---
def main():
    dados_brutos = obter_dados_completos()
    if not dados_brutos: st.stop()

    # Processamento de Dados
    df_grafico_total = processar_matriz_grafico(dados_brutos)
    df_tma_total = processar_dados_tma(dados_brutos) 
    
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
        df_tma = df_tma_total
    else:
        df_grafico = df_grafico_total[df_grafico_total['Operador'] == nome_usuario]
        df_tma = df_tma_total[df_tma_total['Operador'] == nome_usuario]
        df_tam = df_tam_total[df_tam_total['Colaborador'] == nome_usuario]
        df_n3 = df_n3_total[df_n3_total['Colaborador'] == nome_usuario]
        df_n2 = df_n2_total[df_n2_total['Colaborador'] == nome_usuario]
        df_n1 = df_n1_total[df_n1_total['Colaborador'] == nome_usuario]

    if not df_tam.empty:
        df_tam['Cor_Dinamica'] = df_tam['TAM'].apply(definir_cor_pela_nota)

    # --- BARRA LATERAL ---
    with st.sidebar:
        st.markdown(f"<h2 style='text-align: center; color: #58A6FF;'>☁️ TeamBrisa</h2>", unsafe_allow_html=True)
        st.info(f"Logado como: **{nome_usuario}** ({perfil.upper()})")
        st.markdown("---")
        
        escolha = option_menu(
            menu_title=None, 
            options=["Painel Tático", "Pausas", "Calendário", "Tarefas", "Gerenciamento"], 
            icons=["graph-up-arrow", "clock-history", "calendar-week", "list-check", "gear"], 
            default_index=0,
            styles={"container": {"background-color": "transparent"}, "nav-link-selected": {"background-color": "#238636"}}
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

    # --- PÁGINAS ---
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

        kpi1.metric("🎯 Média do Time", f"{media_time:.1f}%")
        kpi2.metric("🏆 Melhor Performance", f"{melhor_op_nome}", f"{melhor_op_valor:.1f}%")
        kpi3.metric("🚨 Zona de Atenção", f"{qtd_nivel_1} Operadores", delta_color="inverse")
        
        st.markdown("---")
        st.markdown(f"**Visão:** {filtro_op}")
        
        col_esq, col_dir = st.columns([2, 1.2], gap="large")

        with col_esq:
            # 1. GRÁFICO DE EVOLUÇÃO
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
                        paper_bgcolor=st.session_state['chart_bg'], plot_bgcolor=st.session_state['chart_bg'], font_color=st.session_state['chart_font'],
                        yaxis_ticksuffix="%", yaxis_range=[0, 115], hovermode="x unified",
                        margin=dict(l=0, r=0, t=20, b=20), height=400
                    )
                    fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor=st.session_state['chart_grid'])
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("Sem dados.")

            st.markdown("---")
            
            # 2. NOVO GRÁFICO: TMA (COLUNAS)
            st.markdown(f"### 📞 TMA - Voz e Chat (Minutos)")
            if filtro_op and not df_tma.empty:
                # Filtra o operador selecionado na tabela de TMA (O1:AD6)
                df_tma_op = df_tma[df_tma['Operador'] == filtro_op]
                
                if not df_tma_op.empty:
                    # Prepara os dados
                    cols_tma = list(df_tma.columns[1:]) # Colunas de data
                    df_tma_long = pd.melt(df_tma_op, id_vars=['Operador'], value_vars=cols_tma, var_name='Data', value_name='MinutosRaw')
                    
                    # Converte para minutos numéricos
                    df_tma_long['Minutos'] = df_tma_long['MinutosRaw'].apply(tratar_tempo_tma)
                    
                    # Cria Gráfico de Barras
                    fig_tma = px.bar(df_tma_long, x='Data', y='Minutos', text='Minutos')
                    
                    fig_tma.update_traces(
                        marker_color=st.session_state['bar_color'], # Azul Cyan do Tema
                        texttemplate='%{text:.1f}', textposition='outside'
                    )
                    
                    fig_tma.update_layout(
                        paper_bgcolor=st.session_state['chart_bg'], plot_bgcolor=st.session_state['chart_bg'], font_color=st.session_state['chart_font'],
                        yaxis_title="Minutos",
                        margin=dict(l=0, r=0, t=20, b=20), height=350
                    )
                    fig_tma.update_yaxes(showgrid=True, gridwidth=1, gridcolor=st.session_state['chart_grid'])
                    
                    st.plotly_chart(fig_tma, use_container_width=True)
                else:
                    st.warning(f"O operador {filtro_op} não possui dados na tabela de TMA (O1:AD6).")
            else:
                 st.info("Dados de TMA não carregados ou não encontrados.")

        with col_dir:
            renderizar_ranking_visual("🏆 Resultado Geral", df_tam, "TAM", "Cor_Dinamica")
            st.markdown("---")
            renderizar_ranking_visual("🥇 Nível 3", df_n3, "Nível 3", "#00FF7F")
            renderizar_ranking_visual("🥈 Nível 2", df_n2, "Nível 2", "#FFD700")
            renderizar_ranking_visual("🥉 Nível 1", df_n1, "Nível 1", "#FF4B4B")

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
