import streamlit as st
import pandas as pd
import gspread
import plotly.express as px
from google.oauth2.service_account import Credentials
from streamlit_option_menu import option_menu

# --- 1. CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Painel Tático TeamBrisa", layout="wide", page_icon="☁️")

# --- 2. FUNÇÕES DE CONEXÃO E TRATAMENTO DE DADOS ---

@st.cache_resource
def conectar_google_sheets():
    """Conecta ao Google Sheets."""
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    credenciais_info = dict(st.secrets["gcp_service_account"])
    credenciais_info["private_key"] = credenciais_info["private_key"].replace("\\n", "\n")
    
    credentials = Credentials.from_service_account_info(credenciais_info, scopes=scopes)
    gc = gspread.authorize(credentials)
    return gc

@st.cache_data(ttl=600)
def carregar_matriz_dados():
    """
    Lê a aba DADOS-DIA focando no intervalo A27:AG209.
    """
    try:
        gc = conectar_google_sheets()
        sh = gc.open("Sistema_Vendas")
        worksheet = sh.worksheet("DADOS-DIA")
        
        # Pega todos os dados da planilha
        todos_dados = worksheet.get_all_values()
        
        # --- CONFIGURAÇÃO DO INTERVALO (A27:AG209) ---
        # Linha 27 do Excel = Índice 26 no Python
        INDICE_CABECALHO = 26 
        
        if len(todos_dados) > INDICE_CABECALHO:
            # O cabeçalho (Datas) está na linha 27
            cabecalho = todos_dados[INDICE_CABECALHO]
            
            # Os dados começam na linha 28 em diante
            dados_brutos = todos_dados[INDICE_CABECALHO+1:] 
            
            # Cria o DataFrame
            df = pd.DataFrame(dados_brutos, columns=cabecalho)
            
            # Limpeza 1: Remove colunas vazias (caso pegue além da AG)
            df = df.loc[:, df.columns != '']
            
            # Limpeza 2: Garante que estamos pegando apenas linhas com Operadores preenchidos
            # Isso evita linhas vazias após a linha 209
            df = df[df.iloc[:, 0].str.strip() != ""]
            
            return df
        else:
            st.error("Erro: A planilha não possui dados suficientes na linha 27.")
            return pd.DataFrame()
    except Exception as e:
        st.error(f"Erro ao carregar dados: {e}")
        return pd.DataFrame()

def tratar_porcentagem(valor):
    """Transforma '100,00%' ou '98%' em 1.0 ou 0.98"""
    if isinstance(valor, str):
        valor_limpo = valor.replace('%', '').replace(',', '.').strip()
        if valor_limpo == '' or valor_limpo == '#N/A': 
            return 0.0
        try:
            return float(valor_limpo) / 100
        except ValueError:
            return 0.0
    return valor

# --- 3. LOGIN ---
def login():
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        st.markdown("<br><br>", unsafe_allow_html=True)
        with st.container(border=True):
            st.title("🔒 Acesso TeamBrisa")
            usuario = st.text_input("Usuário")
            senha = st.text_input("Senha", type="password")
            
            if st.button("Entrar no Sistema", use_container_width=True):
                # Validação simples (Substitua por sua lógica real)
                if usuario and senha: 
                    st.session_state['logado'] = True
                    st.session_state['usuario'] = "Gestor"
                    st.session_state['funcao'] = 'admin'
                    st.rerun()

# --- 4. SISTEMA PRINCIPAL ---
def main():
    df_matriz = carregar_matriz_dados()
    
    # --- BARRA LATERAL ---
    with st.sidebar:
        st.markdown(f"<h2 style='text-align: center;'>☁️ TeamBrisa</h2>", unsafe_allow_html=True)
        st.markdown(f"<div style='text-align: center;'>Olá, <b>{st.session_state.get('usuario', 'Gestor')}</b></div>", unsafe_allow_html=True)
        st.markdown("---")
        
        escolha = option_menu(
            menu_title=None, options=["Painel Tático"], icons=["graph-up-arrow"], menu_icon="cast", default_index=0,
            styles={"container": {"background-color": "transparent"}, "nav-link-selected": {"background-color": "#FF4B4B"}}
        )
        st.markdown("---")

        # --- FILTROS ---
        st.subheader("🔍 Filtros Operacionais")
        
        if not df_matriz.empty:
            # Filtro 1: Operador (Coluna A)
            lista_operadores = sorted(list(set(df_matriz.iloc[:, 0].unique())))
            filtro_operador = st.selectbox("Filtrar Operador:", lista_operadores)

            # Filtro 2: Métrica (Coluna B) - Tenta selecionar 'Meta' automaticamente
            lista_metricas = sorted(list(set(df_matriz.iloc[:, 1].unique())))
            index_meta = lista_metricas.index('Meta') if 'Meta' in lista_metricas else 0
            filtro_metrica = st.selectbox("Filtrar Métrica:", lista_metricas, index=index_meta)
        else:
            filtro_operador, filtro_metrica = None, None

        st.markdown("---")
        if st.button("Sair"):
            st.session_state['logado'] = False
            st.rerun()

    # --- PAINEL TÁTICO ---
    if escolha == "Painel Tático":
        st.title("📊 Painel Tático")
        st.markdown("<br>", unsafe_allow_html=True)

        if df_matriz.empty:
            st.warning("Verifique a conexão ou a estrutura da aba DADOS-DIA (Linha 27).")
            st.stop()

        # Identifica colunas de data (Assume que datas começam na Coluna C / índice 2)
        colunas_datas = df_matriz.columns[2:].tolist()
        colunas_datas = [c for c in colunas_datas if c and c.strip() != '']

        col_grafico, col_ranking = st.columns([2, 1], gap="large")

        # --- GRÁFICO (ESQUERDA) ---
        with col_grafico:
            st.subheader(f"📈 Evolução: {filtro_metrica}")
            st.caption(f"Operador: {filtro_operador}")

            if filtro_operador and filtro_metrica:
                mask_op = df_matriz.iloc[:, 0] == filtro_operador
                mask_met = df_matriz.iloc[:, 1] == filtro_metrica
                df_filtrado = df_matriz[mask_op & mask_met].copy()

                if not df_filtrado.empty:
                    # Prepara dados para o gráfico
                    df_long = pd.melt(df_filtrado, 
                                      id_vars=[df_matriz.columns[0], df_matriz.columns[1]], 
                                      value_vars=colunas_datas, 
                                      var_name='Data', value_name='ValorBruto')
                    
                    df_long['Valor'] = df_long['ValorBruto'].apply(tratar_porcentagem)
                    
                    # Gráfico Plotly
                    fig = px.line(df_long, x='Data', y='Valor', markers=True, 
                                  labels={'Valor': 'Performance', 'Data': 'Dia'})
                    
                    fig.update_traces(line_color='#FF4B4B', line_width=3, marker_size=8)
                    fig.update_layout(hovermode="x unified", yaxis_tickformat='.0%', 
                                      yaxis_range=[0, 1.1], height=400)
                    
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.warning("Sem dados para a seleção.")

        # --- RANKING (DIREITA) ---
        with col_ranking:
            st.subheader("🏆 Ranking Geral")
            st.caption(f"Top Performance em: **{filtro_metrica}**")

            if filtro_metrica:
                # Pega todos da métrica selecionada
                df_rank = df_matriz[df_matriz.iloc[:, 1] == filtro_metrica].copy()
                
                if not df_rank.empty:
                    # Usa a última data disponível como referência para o Ranking
                    ultima_data = colunas_datas[-1]
                    
                    df_final = pd.DataFrame({
                        'Operador': df_rank.iloc[:, 0],
                        'Performance': df_rank[ultima_data].apply(tratar_porcentagem)
                    })
                    
                    df_final = df_final.sort_values(by='Performance', ascending=False)
                    
                    st.dataframe(
                        df_final,
                        use_container_width=True,
                        hide_index=True,
                        height=400,
                        column_config={
                            "Operador": st.column_config.TextColumn("Colaborador"),
                            "Performance": st.column_config.ProgressColumn(
                                "Atingimento Atual", format="%.1f%%", min_value=0, max_value=1
                            ),
                        }
                    )

# --- INICIALIZAÇÃO ---
if 'logado' not in st.session_state: st.session_state['logado'] = False
if not st.session_state['logado']: login()
else: main()
