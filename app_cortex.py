import streamlit as st
import google.generativeai as genai
import tempfile
import os

st.title("🧪 TEST DE LLAVE DIRECTA")

# --- PEGA TU LLAVE AQUI ABAJO DENTRO DE LAS COMILLAS ---
MI_LLAVE_SECRETA = "AIzaSyCnPj_PxeC5zjPrtTCQOE16YWH5rjm4PfE" 
# -------------------------------------------------------

try:
    genai.configure(api_key=MI_LLAVE_SECRETA)
    st.write("Intentando conectar con modelo flash...")
    model = genai.GenerativeModel('gemini-1.5-flash')
    response = model.generate_content("Si lees esto, la llave funciona.")
    st.success(f"✅ ¡ÉXITO! Google respondió: {response.text}")
    st.info("Ahora sabemos que la llave está buena. El problema era los Secrets.")
except Exception as e:
    st.error(f"❌ LA LLAVE SIGUE FALLANDO: {e}")
