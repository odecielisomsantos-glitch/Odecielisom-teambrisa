import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

# --- 1. CONFIGURAÇÃO ---
st.set_page_config(page_title="Sistema TeamBrisa", layout="wide")

# --- 2. CONEXÃO E BANCO DE DADOS ---
def conectar_google_sheets():
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    
    # Corrige a chave privada (\n) para funcionar no Streamlit Cloud
    credenciais_info = dict(st.secrets["gcp_service_account"])
    credenciais_info["private_key"] = credenciais_info["private_key"].replace("\\n", "\n")
    
    credentials = Credentials.from_service_account_info(credenciais_info, scopes=scopes)
    gc = gspread.authorize(credentials)
    return gc

def carregar_dados(aba):
    try:
        gc = conectar_google_sheets()
        sh = gc.open("Sistema_Vendas") # Nome da sua planilha
        worksheet = sh.worksheet(aba)
        dados = worksheet.get_all_records()
        return pd.DataFrame(dados)
    except Exception as e:
        # Retorna vazio se der erro, para não travar o site
        return pd.DataFrame()

def salvar_venda(venda):
    """
    Recebe uma lista com os dados da venda e salva na última linha da planilha.
    Ordem esperada: [Data, Vendedor, Cliente, Produto, Valor, Status]
    """
    try:
        gc = conectar_google_sheets()
        sh = gc.open("Sistema_Vendas")
        worksheet = sh.worksheet("Vendas")
        worksheet.append_row(venda)
        return True
    except Exception as e:
        st.error(f"Erro ao salvar no Google Sheets: {e}")
        return False

# --- 3. TELA DE LOGIN ---
def login():
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        st.title("🔒 Acesso TeamBrisa")
        st.markdown("---")
        usuario = st.text_input("Usuário")
        senha = st.text_input("Senha", type="password")
        
        if st.button("Entrar no Sistema"):
            with st.spinner("Validando credenciais..."):
                df_users = carregar_dados("Usuarios")
                
                if not df_users.empty:
                    # Garante que a senha seja lida como texto para comparar corretamente
                    df_users['Senha'] = df_users['Senha'].astype(str)
                    
                    # Procura o usuário e senha digitados
                    user = df_users[(df_users['Usuario'] == usuario) & (df_users['Senha'] == str(senha))]
                    
                    if not user.empty:
                        st.session_state['logado'] = True
                        st.session_state['usuario'] = user.iloc[0]['Nome']
                        st.session_state['funcao'] = user.iloc[0]['Funcao']
                        st.rerun() # Recarrega a página para entrar
                    else:
                        st.error("Usuário ou senha incorretos.")
                else:
                    st.error("Erro ao conectar com a base de usuários.")

# --- 4. PAINEL PRINCIPAL (CÉREBRO DO SISTEMA) ---
def main():
    # --- BARRA LATERAL (IDENTIDADE) ---
    st.sidebar.title(f"👤 {st.session_state['usuario']}")
    
    # Padroniza o cargo para letras minúsculas para facilitar a comparação
    cargo_atual = st.session_state['funcao'].lower() 
    st.sidebar.markdown(f"**Perfil:** {cargo_atual.upper()}")
    st.sidebar.markdown("---")
    
    if st.sidebar.button("Sair"):
        st.session_state['logado'] = False
        st.rerun()

    # --- CARREGAR DADOS ---
    df_vendas = carregar_dados("Vendas")
    
    # Cria estrutura vazia se a planilha estiver zerada (para não dar erro)
    if df_vendas.empty:
        df_vendas = pd.DataFrame(columns=["Data", "Vendedor", "Cliente", "Produto", "Valor", "Status"])

    # Tratamento numérico (Remove R$, pontos e troca vírgula por ponto)
    if 'Valor' in df_vendas.columns and not df_vendas.empty:
        df_vendas['Valor'] = df_vendas['Valor'].astype(str).str.replace('R$', '', regex=False)
        df_vendas['Valor'] = df_vendas['Valor'].str.replace('.', '', regex=False)
        df_vendas['Valor'] = df_vendas['Valor'].str.replace(',', '.', regex=False)
        df_vendas['Valor'] = pd.to_numeric(df_vendas['Valor'])

    # --- LÓGICA DE PERMISSÃO (ADMIN vs VENDEDOR) ---
    
    # >> CENÁRIO A: GERÊNCIA (ADMIN) <<
    if cargo_atual == 'admin':
        st.title("📊 Painel da Diretoria")
        st.info("Visão Gerencial: Acesso a todos os dados.")
        
        if not df_vendas.empty:
            # Métricas Globais
            total = df_vendas['Valor'].sum()
            col1, col2 = st.columns(2)
            col1.metric("Faturamento Total", f"R$ {total:,.2f}")
            col2.metric("Total de Transações", len(df_vendas))
            
            st.markdown("---")
            
            # Gráficos de Gestão (Barras)
            col_g1, col_g2 = st.columns(2)
            
            with col_g1:
                st.subheader("Performance por Vendedor")
                st.bar_chart(df_vendas, x='Vendedor', y='Valor')
            
            with col_g2:
                st.subheader("Vendas por Produto")
                st.bar_chart(df_vendas, x='Produto', y='Valor')

            st.markdown("---")

            # --- AQUI ESTÁ A MUDANÇA (HISTÓRICO + GRÁFICO DE LINHA) ---
            # Dividimos a tela em duas colunas: Tabela (1 parte) e Gráfico (2 partes)
            col_hist, col_linha = st.columns([1, 2])

            with col_hist:
                st.subheader("Histórico Recente")
                # Mostra apenas as colunas principais para caber no espaço
                st.dataframe(df_vendas[['Data', 'Vendedor', 'Valor']].head(10), use_container_width=True)

            with col_linha:
                st.subheader("Tendência de Vendas (Linha do Tempo)")
                
                # 1. Tratamento de Data para o gráfico funcionar
                try:
                    # Cria uma cópia para não bagunçar o dataframe original
                    df_chart = df_vendas.copy()
                    df_chart['Data_Clean'] = pd.to_datetime(df_chart['Data'], format='%d/%m/%Y', errors='coerce')
                    
                    # 2. Agrupa por data e soma os valores
                    dados_tendencia = df_chart.dropna(subset=['Data_Clean']).groupby('Data_Clean')['Valor'].sum()
                    
                    # 3. Exibe o gráfico de linhas
                    st.line_chart(dados_tendencia)
                except Exception as e:
                    st.warning("Não foi possível gerar o gráfico de linha. Verifique o formato das datas na planilha (DD/MM/AAAA).")

        else:
            st.warning("Ainda não há vendas registradas no sistema.")

    # >> CENÁRIO B: OPERAÇÃO (VENDEDORES) <<
    else:
        st.title("📝 Área do Vendedor")
        
        # --- FORMULÁRIO DE CADASTRO ---
        with st.expander("➕ REGISTRAR NOVA VENDA", expanded=True):
            with st.form("form_venda"):
                col_a, col_b = st.columns(2)
                with col_a:
                    data = st.date_input("Data da Venda")
                    cliente = st.text_input("Nome do Cliente")
                with col_b:
                    produto = st.selectbox("Produto/Serviço", ["Consultoria", "Sistema", "Manutenção", "Outros"])
                    valor = st.number_input("Valor (R$)", min_value=0.0, format="%.2f")
                
                enviar = st.form_submit_button("💾 Salvar Venda")
                
                if enviar:
                    # Monta a linha exata que vai para o Excel
                    nova_venda = [
                        data.strftime("%d/%m/%Y"),     # Coluna A: Data
                        st.session_state['usuario'],   # Coluna B: Vendedor (Automático)
                        cliente,                       # Coluna C: Cliente
                        produto,                       # Coluna D: Produto
                        valor,                         # Coluna E: Valor
                        "Pendente"                     # Coluna F: Status
                    ]
                    
                    if salvar_venda(nova_venda):
                        st.success(f"Venda para {cliente} registrada com sucesso!")
                        st.rerun() # Atualiza a página para mostrar na tabela abaixo

        # --- TABELA FILTRADA (SÓ AS VENDAS DELE) ---
        st.markdown("---")
        st.subheader("Minhas Vendas Recentes")
        
        # Filtra apenas as linhas onde a coluna 'Vendedor' é igual ao usuário logado
        minhas_vendas = df_vendas[df_vendas['Vendedor'] == st.session_state['usuario']]
        
        if not minhas_vendas.empty:
            total_meu = minhas_vendas['Valor'].sum()
            st.metric("Meu Faturamento Acumulado", f"R$ {total_meu:,.2f}")
            st.dataframe(minhas_vendas, use_container_width=True)
        else:
            st.info("Você ainda não registrou nenhuma venda.")

# --- 5. CONTROLE DE FLUXO ---
if 'logado' not in st.session_state:
    st.session_state['logado'] = False

if not st.session_state['logado']:
    login()
else:
    main()
