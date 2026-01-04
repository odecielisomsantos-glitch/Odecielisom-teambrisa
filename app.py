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
    try:
        gc = conectar_google_sheets()
        sh = gc.open("Sistema_Vendas")
        worksheet = sh.worksheet("DADOS-DIA")
        return worksheet.get_all_values()
    except Exception as e:
        st.error(f"Erro na conexão: {e}")
        return []

def tratar_porcentagem(valor):
    """
    Converte '100%' para 100.0 (float) em vez de 1.0.
    Isso corrige o visual do ranking para mostrar 100% corretamente.
    """
    if isinstance(valor, str):
        # Remove % e espaços, troca vírgula por ponto
        v = valor.replace('%', '').replace(',', '.').strip()
        if v == '' or v == '#N/A' or v == '-': return 0.0
        try: 
            # Retorna o valor cheio (ex: 98.5)
            return float(v) 
        except: return 0.0
    return valor

# --- 3. PROCESSAMENTO ESPECÍFICO ---

def processar_matriz_grafico(todos_dados):
    INDICE_CABECALHO = 26 # Linha 27 do Excel
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
                
                # Filtra apenas se tiver nome e valor válido
                if nome and valor_str and valor_str != '-' and valor_str != '#N/A':
                    val_float = tratar_porcentagem(valor_str)
                    lista_limpa.append({
                        'Colaborador': nome,
                        titulo_coluna: val_float
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
    dados_brutos = obter_dados_completos()
    if not dados_brutos: st.stop()

    # Processamento
    df_grafico = processar_matriz_grafico(dados_brutos)
    
    # Processa Rankings (Linhas 2-25 do Excel = Index 1-25 Python)
    # TAM (A:B) -> idx 0, 1
    df_tam = processar_tabela_ranking(dados_brutos, 0, 1, range(1, 25), 'TAM')
    # N3 (F:G) -> idx 5, 6
    df_n3 = processar_tabela_ranking(dados_brutos, 5, 6, range(1, 25), 'Nível 3')
    # N2 (I:J) -> idx 8, 9
    df_n2 = processar_tabela_ranking(dados_brutos, 8, 9, range(1, 25), 'Nível 2')
    # N1 (L:M) -> idx 11, 12
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

    # --- TELA PRINCIPAL ---
    if escolha == "Painel Tático":
        col_tit, col_logo = st.columns([4, 1])
        with col_tit:
            st.title("📊 Painel Tático")
            st.markdown(f"**Visão:** {filtro_op} | **Métrica:** {filtro_met}")
        st.markdown("---")
        
        col_esq, col_dir = st.columns([2, 1.2], gap="large")

        # >>> GRÁFICO (ESQUERDA) <<<
        with col_esq:
            st.markdown(f"### 📈 Evolução Mensal")
            if filtro_op and filtro_met and not df_grafico.empty:
                df_f = df_grafico[(df_grafico['Operador'] == filtro_op) & (df_grafico['Metrica'] == filtro_met)]
                if not df_f.empty:
                    cols_datas = list(df_grafico.columns[2:])
                    df_long = pd.melt(df_f, id_vars=['Operador', 'Metrica'], value_vars=cols_datas, var_name='Data', value_name='ValorRaw')
                    
                    # Converte para float (0-100)
                    df_long['Performance'] = df_long['ValorRaw'].apply(tratar_porcentagem)
                    
                    fig = px.line(df_long, x='Data', y='Performance', markers=True)
                    # Verde Neon no Gráfico
                    fig.update_traces(line_color='#00FF7F', line_width=4, marker_size=8, marker_color='#FFFFFF')
                    fig.update_layout(
                        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color='#FAFAFA',
                        yaxis_ticksuffix="%", # Adiciona % no eixo Y
                        yaxis_range=[0, 110], # Escala até 110 para dar respiro
                        hovermode="x unified",
                        margin=dict(l=0, r=0, t=20, b=20), height=500
                    )
                    fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='#30363D')
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("Sem dados gráficos.")

        # >>> RANKINGS (DIREITA) <<<
        with col_dir:
            # Função para renderizar com CORES DINÂMICAS
            def renderizar_ranking(titulo, df, col_val, cor_barra):
                st.markdown(f"#### {titulo}")
                if not df.empty:
                    st.dataframe(
                        df,
                        use_container_width=True,
                        hide_index=True,
                        height=200,
                        column_config={
                            "Colaborador": st.column_config.TextColumn("Colaborador"),
                            col_val: st.column_config.ProgressColumn(
                                "Perf.", 
                                format="%.1f%%", # Mostra 100.0%
                                min_value=0, 
                                max_value=100,   # Escala 0-100
                                help="Performance Atual",
                            )
                        }
                    )
                    # Hack CSS para injetar a cor específica nesta tabela
                    # Isso aplica a cor correta baseada na ordem de renderização
                    # Nota: O Streamlit nativo limita cores, mas vamos usar um truque visual
                    # definindo a cor globalmente para este bloco ou aceitando a cor padrão se limitar.
                    
                    # Solução Nativa Limpa: Streamlit não deixa passar cor HEX direto na ProgressColumn dinamicamente
                    # Mas podemos injetar CSS para colorir as barras baseadas na posição se necessário.
                    # POREM, o Streamlit aceita 'color' na ProgressColumn em versões novas?
                    # Testando abaixo com argumento não documentado mas funcional em versões recentes ou fallback.
                    
                else:
                    st.caption("Sem dados.")

            # ATENÇÃO: Streamlit ProgressColumn não aceita HEX arbitrário facilmente na API padrão.
            # Vou usar um método mais robusto: Pandas Styler para o fundo OU 
            # Manter o st.dataframe mas sabendo que a cor da barra segue o tema.
            # PARA ATENDER SEU PEDIDO DE COR: 
            # A melhor forma visual garantida no Streamlit atual para cores diferentes 
            # é usar o Pandas Styler (Highlight) em vez de ProgressColumn, OU aceitar uma cor única.
            
            # TENTATIVA V2: Usando config de cor se sua versão suportar, senão fallback.
            # Vou usar a lógica de visualização nativa aprimorada.

            # 1. RANKING GERAL (Verde Neon #00FF7F)
            st.markdown("### 🏆 Ranking Geral (TAM)")
            if not df_tam.empty:
                st.dataframe(
                    df_tam, use_container_width=True, hide_index=True, height=200,
                    column_config={"TAM": st.column_config.ProgressColumn("Perf.", format="%.1f%%", min_value=0, max_value=100)}
                )

            st.markdown("---")
            
            # 2. NÍVEL 3 (Verde Neon #00FF7F)
            st.markdown("#### 🥇 Nível 3")
            if not df_n3.empty:
                st.dataframe(
                    df_n3, use_container_width=True, hide_index=True, height=200,
                    column_config={"Nível 3": st.column_config.ProgressColumn("Perf.", format="%.1f%%", min_value=0, max_value=100)}
                )

            # 3. NÍVEL 2 (Amarelo Profissional #FFD700)
            # Truque CSS para alterar a cor da barra APENAS nos próximos elementos se possível
            # Como o Streamlit compartilha estilos, vamos usar HTML/Pandas para forçar a cor amarela se o nativo falhar
            st.markdown("#### 🥈 Nível 2")
            if not df_n2.empty:
                # Usando Pandas Styler para garantir a cor Amarela na barra de fundo
                st.dataframe(
                    df_n2.style.bar(subset=["Nível 2"], color='#FFD700', vmin=0, vmax=100)
                         .format({"Nível 2": "{:.1f}%"}),
                    use_container_width=True,
                    height=200,
                    hide_index=True
                )

            # 4. NÍVEL 1 (Vermelho #FF4B4B)
            st.markdown("#### 🥉 Nível 1")
            if not df_n1.empty:
                # Usando Pandas Styler para garantir a cor Vermelha
                st.dataframe(
                    df_n1.style.bar(subset=["Nível 1"], color='#FF4B4B', vmin=0, vmax=100)
                         .format({"Nível 1": "{:.1f}%"}),
                    use_container_width=True,
                    height=200,
                    hide_index=True
                )

# --- INICIALIZAÇÃO ---
if 'logado' not in st.session_state: st.session_state['logado'] = False
if not st.session_state['logado']: login()
else: main()
