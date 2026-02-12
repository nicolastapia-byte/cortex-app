import streamlit as st
import google.generativeai as genai
import pandas as pd
import json
import re
import io
import tempfile
import os
import ast # <--- NUEVA HERRAMIENTA DE REPARACIÓN

# --- 1. CONFIGURACIÓN VISUAL ---
st.set_page_config(
    page_title="Sentinela x Gador - Auditoría",
    page_icon="🛡️",
    layout="centered"
)

st.markdown("""
    <style>
    .stButton>button {
        width: 100%;
        background-color: #004481;
        color: white;
        font-weight: 600;
        border-radius: 6px;
        padding: 0.7rem;
        font-size: 16px;
        border: none;
    }
    .stProgress > div > div > div > div {
        background-color: #004481;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. SIDEBAR ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/2382/2382461.png", width=80)
    st.title("Gador Farma")
    st.success("✅ Sistema Blindado")
    st.info("ℹ️ Versión: V11.0 (Auto-Repair)")

# --- 3. ENCABEZADO ---
st.title("🛡️ Centro de Auditoría de Licitaciones")
st.markdown("Auditoría automática de **Multas, Garantías y Logística**.")

# --- 4. INPUT ---
uploaded_file = st.file_uploader("📂 Cargue las Bases (PDF):", type=["pdf"])

# --- 5. FUNCIÓN DE LIMPIEZA AVANZADA (EL REPARADOR) ---
def limpiar_y_reparar_json(texto):
    """Intenta limpiar el JSON. Si falla, usa ast.literal_eval para reparar errores de sintaxis."""
    try:
        # Paso 1: Limpieza básica Markdown
        texto = re.sub(r'```json', '', texto)
        texto = re.sub(r'```', '', texto)
        
        # Paso 2: Extraer solo lo que está entre llaves {}
        inicio = texto.find('{')
        fin = texto.rfind('}') + 1
        if inicio == -1 or fin == 0:
            return {}
        
        json_str = texto[inicio:fin]
        
        # Paso 3: Intentar carga estricta (Standard JSON)
        return json.loads(json_str, strict=False)
        
    except Exception:
        # Paso 4: PLAN B - REPARACIÓN FORZOSA
        # Si falla por "Invalid control character", usamos Python AST que es más flexible
        try:
            return ast.literal_eval(json_str)
        except:
            # Si todo falla, devolvemos un error controlado para no romper la app
            return {"multas": "Error de lectura - Revise manualmente", "id_licitacion": "Error"}

# --- 6. LÓGICA ---
if uploaded_file is not None:
    
    if st.button("⚡ EJECUTAR ANÁLISIS"):
        
        status_box = st.empty()
        progress_bar = st.progress(0)
        
        try:
            # A. CONEXIÓN
            if "GOOGLE_API_KEY" in st.secrets:
                api_key = st.secrets["GOOGLE_API_KEY"]
                genai.configure(api_key=api_key)
            else:
                st.error("❌ Falta API Key en Secrets.")
                st.stop()
            
            # B. BUSCAR MODELO
            status_box.info("📡 Conectando motores...")
            modelos = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
            modelo_elegido = next((m for m in modelos if 'flash' in m and '1.5' in m), modelos[0] if modelos else None)
            
            if not modelo_elegido:
                st.error("❌ No hay modelos disponibles.")
                st.stop()
                
            progress_bar.progress(20)
            
            # C. SUBIR PDF
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
                tmp_file.write(uploaded_file.getvalue())
                tmp_path = tmp_file.name

            archivo_gemini = genai.upload_file(tmp_path)
            progress_bar.progress(40)
            
            # D. PROMPT "ANTIBALAS" (Instrucción explícita de formato)
            prompt = """
            ACTÚA COMO GERENTE DE GADOR.
            Analiza el PDF y extrae los datos en formato JSON.
            IMPORTANTE: NO USES SALTOS DE LÍNEA (ENTER) DENTRO DE LOS VALORES DEL JSON. Escribe todo el texto seguido.

            JSON ESPERADO:
            {
                "id_licitacion": "ID Propuesta",
                "fechas": "Apertura y Cierre",
                "productos": "Principios Activos",
                "cenabast": "Menciona Faltante/Intermediación (SI/NO)",
                "presupuesto": "Monto Total",
                "garantia_seriedad": "Monto y Vigencia",
                "garantia_cumplimiento": "Monto y Vigencia",
                "duracion_contrato": "Vigencia",
                "reajuste": "IPC (SI/NO)",
                "suscripcion_contrato": "Firma (SI/NO)",
                "plazo_entrega": "Plazos y Urgencias",
                "vencimiento_canje": "Política de Canje",
                "multas": "Resumen de Multas",
                "inadmisibilidad": "Causales Rechazo"
            }
            """
            
            status_box.info(f"🧠 Analizando con {modelo_elegido}...")
            model = genai.GenerativeModel(modelo_elegido)
            response = model.generate_content([prompt, archivo_gemini])
            
            progress_bar.progress(80)
            
            # E. LIMPIEZA Y REPARACIÓN
            status_box.info("🔧 Reparando estructura de datos...")
            datos = limpiar_y_reparar_json(response.text)
            
            progress_bar.progress(100)
            status_box.success("✅ Análisis Completado.")
            
            # F. MOSTRAR RESULTADOS
            c1, c2 = st.columns(2)
            c1.error(f"🚨 **Multas:**\n{datos.get('multas', 'Sin datos')}")
            c2.info(f"📦 **Cenabast:**\n{datos.get('cenabast', 'Sin datos')}")
            
            # G. EXCEL
            df = pd.DataFrame([datos])
            # Asegurar columnas
            cols_orden = ['id_licitacion', 'fechas', 'productos', 'multas', 'garantia_seriedad', 'cenabast']
            cols_finales = [c for c in cols_orden if c in df.columns] + [c for c in df.columns if c not in cols_orden]
            df = df[cols_finales]

            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                df.to_excel(writer, sheet_name='Gador', index=False)
                workbook =
