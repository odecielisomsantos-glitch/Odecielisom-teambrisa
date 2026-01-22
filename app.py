import streamlit as st
import pandas as pd
import numpy as np

# Configuração da página
st.set_page_config(page_title="Team Brisa", page_icon="🌊", layout="wide")

# --- BARRA LATERAL (SIDEBAR) ---
st.sidebar.title("Navegação")
pagina = st.sidebar.radio("Ir para:", ["Página Inicial", "Dados", "Sobre"])

# --- CONTEÚDO PRINCIPAL ---
if pagina == "Página Inicial":
    st.title("🌊 Team Brisa - Home")
    st.write("Bem-vindo ao painel oficial da equipe.")
    st.image("https://source.unsplash.com/random/800x400/?ocean", caption="Vibe do time")

elif pagina == "Dados":
    st.title("📊 Nossos Números")
    # Criando dados fictícios para teste
    dados = pd.DataFrame(
        np.random.randn(20, 3),
        columns=['A', 'B', 'C']
    )
    st.line_chart(dados)
    st.write("Acima vemos os dados de performance simulados.")

elif pagina == "Sobre":
    st.title("ℹ️ Quem somos")
    st.write("Nós somos o Team Brisa, focados em desenvolvimento e inovação.")
    st.info("Contato: contato@teambrisa.com")
