import streamlit as st
import pandas as pd

# CONFIGURAÇÃO DA PÁGINA
st.set_page_config(page_title="Meu Primeiro Site", layout="centered")

# CABEÇALHO
st.title("🚀 Painel de Controle")
st.write("Site construído com Python e hospedado no Streamlit Cloud!")

# DADOS SIMULADOS
dados = {
    'Nome': ['Hian', 'Luis', 'Renan', 'Ana', 'Carlos'],
    'Status': ['OK', 'ATENÇÃO', 'OK', 'PENDENTE', 'OK'],
    'Vendas': [150, 80, 200, 45, 120]
}

df = pd.DataFrame(dados)

# MOSTRAR TABELA
st.subheader("📋 Tabela de Dados")
st.dataframe(df, use_container_width=True)

# MOSTRAR GRÁFICO
st.subheader("📊 Gráfico de Vendas")
st.bar_chart(df, x='Nome', y='Vendas')
