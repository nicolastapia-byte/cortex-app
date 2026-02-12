import streamlit as st
import google.generativeai as genai
import pandas as pd
import json
import re
import io
import tempfile
import os

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="Cortex AI - Gador", page_icon="💊", layout="centered")

# --- 2. ESTILOS ---
st.markdown("""
    <style>
    .stButton>button {
        width: 100%;
        background-color: #004481;
        color: white;
        font-weight: bold;
        border-radius: 8px;
        padding: 0.5rem;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 3. SIDEBAR ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/3063/3063822.png", width=60)
    st.title("Gador Farma")
    st.success("✅ Sistema Operativo")
    st.info("ℹ️ Versión: V6.0 (Multi-Key)")

# --- 4. TITULO ---
st.title("💊 Cortex AI: Auditoría de Licitaciones")
st.markdown("""
Esta herramienta audita Bases Administrativas buscando **Riesgos Críticos**:
* 🚨 **Multas y Sanciones**
* 💰 **Garantías**
* 📦 **Cenabast y Canjes**
""")

# --- 5. INPUT ---
uploaded_file = st.file_uploader("📂 Sube las Bases (PDF) aquí:", type=["pdf"])

# --- 6. FUNCIONES ---
def limpiar_json(texto):
    texto = re.sub(r'```json', '', texto)
    texto = re.sub(r'```', '', texto)
    inicio = texto.find('{')
    fin = texto.rfind('}') + 1
    if inicio != -1 and fin != 0:
        return texto[inicio:fin]
    return "{}"

# --- 7. LÓGICA DE PROCESAMIENTO ---
if uploaded_file is not None:
    
    if st.button("⚡ AUDITAR DOCUMENTO AHORA"):
        
        status_text = st.empty()
        bar = st.progress(0)
        
        try:
            # A. API KEY
            if "GOOGLE_API_KEY" in st.secrets:
                genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
            else:
                st.error("❌ Falta la API Key en Secrets.")
                st.stop()
            
            # B. SUBIR ARCHIVO
            status_text.text("🧠 Subiendo documento a la nube...")
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
                tmp_file.write(uploaded_file.getvalue())
                tmp_path = tmp_file.name

            archivo_gemini = genai.upload_file(tmp_path)
            bar.progress(30)
            
            # C. EL PROMPT MAESTRO
            prompt = """
            ACTÚA COMO GERENTE DE GADOR. Extrae en JSON:
            {
                "id_licitacion": "ID",
                "fechas": "Cierre",
                "productos": "Principios Activos",
                "cenabast": "SI/NO faltante",
                "presupuesto": "Monto",
                "garantia_seriedad": "Detalle",
                "garantia_cumplimiento": "Detalle",
                "duracion_contrato": "Tiempo",
                "reajuste": "SI/NO IPC",
                "suscripcion_contrato": "SI/NO",
                "plazo_entrega": "Plazos",
                "vencimiento_canje": "Politica Canje",
                "multas": "Detalle Multas",
                "inadmisibilidad": "Causales"
            }
            """
            
            # D. FUERZA BRUTA INTELIGENTE (LA SOLUCIÓN AL ERROR 404)
            # Probamos esta lista de modelos uno por uno hasta que uno funcione.
            lista_modelos = [
                "gemini-1.5-flash",
                "gemini-1.5-flash-001",
                "gemini-1.5-flash-latest",
                "gemini-1.5-pro",
                "gemini-1.5-pro-001",
                "gemini-pro"
            ]
            
            respuesta_exitosa = None
            modelo_usado = ""
            
            status_text.text("⚡ Analizando riesgos (Probando modelos)...")
            
            for modelo in lista_modelos:
                try:
                    # Intentar con el modelo actual
                    model_instance = genai.GenerativeModel(modelo)
                    response = model_instance.generate_content([prompt, archivo_gemini])
                    
                    # Si llega aquí, funcionó!
                    respuesta_exitosa = response
                    modelo_usado = modelo
                    break # Salir del loop
                except Exception as e:
                    # Si falla, intentamos el siguiente silenciosamente
                    continue
            
            if not respuesta_exitosa:
                st.error("❌ Error Crítico: Ningún modelo de IA respondió. Verifica tu API Key o intenta más tarde.")
                st.stop()
                
            bar.progress(80)
            status_text.text(f"✅ ¡Éxito! Procesado con {modelo_usado}")
            
            # E. RESULTADOS
            json_str = limpiar_json(respuesta_exitosa.text)
            datos = json.loads(json_str)
            
            c1, c2 = st.columns(2)
            c1.error(f"🚨 **Multas:**\n{datos.get('multas')}")
            c2.warning(f"💰 **Garantías:**\n{datos.get('garantia_seriedad')}")
            
            # F. EXCEL
            df = pd.DataFrame([datos])
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                df.to_excel(writer, index=False)
                
            st.download_button(
                label="📥 DESCARGAR EXCEL",
                data=buffer,
                file_name=f"Reporte_{datos.get('id_licitacion')}.xlsx",
                mime="application/vnd.ms-excel"
            )
            
            bar.progress(100)
            os.remove(tmp_path)

        except Exception as e:
            st.error(f"❌ Error Técnico Global: {e}")
