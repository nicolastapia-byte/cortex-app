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
    st.success("✅ Conexión Establecida")
    st.info("ℹ️ Versión: V8.0 (Auto-Scan)")

# --- 4. TÍTULO ---
st.title("💊 Cortex AI: Auditoría Inteligente")
st.markdown("""
Esta herramienta detecta **Riesgos Críticos** en bases de licitación:
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

# --- 7. LÓGICA PRINCIPAL ---
if uploaded_file is not None:
    
    if st.button("⚡ AUDITAR DOCUMENTO AHORA"):
        
        status = st.empty()
        bar = st.progress(0)
        
        try:
            # A. OBTENER LLAVE (Desde Secrets)
            if "GOOGLE_API_KEY" in st.secrets:
                api_key = st.secrets["GOOGLE_API_KEY"]
            else:
                st.error("❌ Falta la API Key en los Secrets de Streamlit.")
                st.stop()
                
            genai.configure(api_key=api_key)
            
            # --- B. ESCÁNER AUTOMÁTICO DE MODELOS (La Solución) ---
            status.text("📡 Preguntando a Google qué modelos tienes disponibles...")
            
            # Listamos TODOS los modelos disponibles para TU llave
            modelos_disponibles = []
            for m in genai.list_models():
                if 'generateContent' in m.supported_generation_methods:
                    modelos_disponibles.append(m.name)
            
            if not modelos_disponibles:
                st.error("❌ Tu llave funciona, pero Google dice que no tienes acceso a ningún modelo. Verifica si habilitaste la API en Google Cloud.")
                st.stop()

            # ELEGIR EL MEJOR (Preferencia: Flash -> Pro -> Cualquiera)
            modelo_elegido = None
            
            # 1. Buscar Flash 1.5
            for m in modelos_disponibles:
                if 'flash' in m and '1.5' in m:
                    modelo_elegido = m
                    break
            
            # 2. Si no hay Flash, buscar Pro 1.5
            if not modelo_elegido:
                for m in modelos_disponibles:
                    if 'pro' in m and '1.5' in m:
                        modelo_elegido = m
                        break
            
            # 3. Si no hay, usar el primero que encontró (ej: gemini-1.0-pro)
            if not modelo_elegido:
                modelo_elegido = modelos_disponibles[0]

            status.text(f"✅ Conectado exitosamente con: {modelo_elegido}")
            # -------------------------------------------------------

            # C. SUBIR ARCHIVO
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
                tmp_file.write(uploaded_file.getvalue())
                tmp_path = tmp_file.name

            archivo_gemini = genai.upload_file(tmp_path)
            bar.progress(30)
            
            # D. PROMPT GADOR
            prompt = """
            ACTÚA COMO GERENTE DE GADOR. Extrae en JSON estricto:
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
            
            status.text("⚡ Analizando riesgos...")
            
            # Usamos el nombre EXACTO que nos dio Google
            model_instance = genai.GenerativeModel(modelo_elegido)
            response = model_instance.generate_content([prompt, archivo_gemini])
            
            bar.progress(80)
            status.text("📊 Generando Excel...")
            
            # E. RESULTADOS
            json_str = limpiar_json(response.text)
            datos = json.loads(json_str)
            
            st.success("✅ ¡Auditoría Completada!")
            
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
                file_name=f"Reporte_{datos.get('id_licitacion', 'Gador')}.xlsx",
                mime="application/vnd.ms-excel"
            )
            
            bar.progress(100)
            os.remove(tmp_path)

        except Exception as e:
            st.error(f"❌ Error Técnico: {e}")
