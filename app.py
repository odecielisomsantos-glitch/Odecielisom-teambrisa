import streamlit as st

# Configuração da página (título na aba do navegador)
st.set_page_config(page_title="Team Brisa", page_icon="🌊")

# Título principal e subtítulo
st.title("Olá, Team Brisa! 🌊")
st.subheader("Nosso site está no ar!")

# Um texto simples
st.write("Este é o começo do nosso projeto desenvolvido com Streamlit e GitHub.")

# Um botão interativo para testar
if st.button('Clique aqui para uma surpresa'):
    st.balloons()
    st.success("Funciona perfeitamente!")
