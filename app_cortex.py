import streamlit as st
import google.generativeai as genai
import pandas as pd
import json
import re
import io
import tempfile
import os
import ast

# --- 1. CONFIGURACIÓN VISUAL ---
st.set_page_config(
    page_title="Cortex AI - Auditoría",
    page_icon="🤖",  # Icono de Robot en la pestaña del navegador
    layout="centered"
)

# Estilos CSS (Azul Tecnológico Cortex)
st.markdown("""
    <style>
    .stButton>button {
        width: 100%;
        background-color: #2E5CB8; /* Azul Cortex */
        color: white;
        font-weight: 600;
        border-radius: 6px;
        padding: 0.7rem;
        font-size: 16px;
        border: none;
        transition: background-color 0.3s ease;
    }
    .stButton>button:hover {
        background-color: #1F4085;
    }
    .stProgress > div > div > div > div {
        background-color: #2E5CB8;
    }
    /* AJUSTE PARA EL ROBOT EN HD */
    [data-testid="stSidebar"] .stImage {
        text-align: center;
        display: block;
        margin-left: auto;
        margin-right: auto;
        width: 100%;
    }
    [data-testid="stSidebar"] img {
        max-width: 220px; 
        border-radius: 15px; /* Bordes redondeados para el avatar */
        box-shadow: 0 4px 6px rgba(0,0,0,0.1); /* Sombra suave */
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. SIDEBAR (IDENTIDAD ROBOT) ---
with st.sidebar:
    # AQUI BUSCAMOS AL ROBOT
    try:
        st.image("robot_cortex.png", use_container_width=True) 
    except:
        st.warning("⚠️ Sube la imagen 'robot_cortex.png' a GitHub.")
        st.header("🤖 Cortex AI")

    st.title("Cortex AI")
    st.markdown("**Agente Digital de Sentinela**")
    st.markdown("---")
    st.success("✅ Sistema Operativo")
    st.info("ℹ️ Versión: Agent V18.0")

# --- 3. ENCABEZADO ---
st.title("🤖 Cortex: Auditoría de Licitaciones")
st.markdown("Soy **Cortex**, tu agente de IA especializado en auditar **Riesgos, Multas y Garantías** en bases públicas.")

# --- 4. INPUT ---
uploaded_file = st.file_uploader("📂 Entrégame las Bases (PDF) para analizar:", type=["pdf"])

# --- 5. LIMPIEZA ---
def limpiar_y_reparar_json(texto):
    try:
        texto = re.sub(r'```json', '', texto)
        texto = re.sub(r'```', '', texto)
        inicio = texto.find('{')
        fin = texto.rfind('}') + 1
        if inicio == -1 or fin == 0: return {}
        json_str = texto[inicio:fin]
        return json.loads(json_str, strict=False)
    except:
        try: return ast.literal_eval(json_str)
        except: return {"multas": "Error de lectura", "id_licitacion": "ERROR"}

# --- 6. LÓGICA ---
if uploaded_file is not None:
    
    if st.button("⚡ ACTIVAR CORTEX"):
        
        status_box = st.empty()
        bar = st.progress(0)
        
        try:
            # A. CONEXIÓN
            status_box.info("🔐 Cortex: Conectando a mis servidores seguros...")
            if "GOOGLE_API_KEY" in st.secrets:
                genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
            else:
                st.error("❌ Falta mi llave de acceso (API Key).")
                st.stop()
            
            # B. MODELO
            status_box.info("🧠 Cortex: Calibrando mis redes neuronales...")
            try:
                modelos = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
                modelo_elegido = next((m for m in modelos if 'flash' in m and '1.5' in m), None)
                if not modelo_elegido: modelo_elegido = next((m for m in modelos if 'pro' in m and '1.5' in m), None)
                if not modelo_elegido: modelo_elegido = modelos[0]
            except Exception as e:
                st.error(f"❌ Error: {e}")
                st.stop()
            
            bar.progress(20)
            
            # C. LECTURA
            status_box.info("👁️ Cortex: Leyendo documento...")
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
                tmp_file.write(uploaded_file.getvalue())
                tmp_path = tmp_file.name

            archivo_gemini = genai.upload_file(tmp_path)
            bar.progress(40)
            
            # D. PROMPT (PERSONALIDAD AGENTE)
            prompt = """
            ERES CORTEX, UN ROBOT AUDITOR EXPERTO DE LA EMPRESA SENTINELA.
            Tu misión es proteger al cliente encontrando riesgos en este PDF.
            
            Extrae datos en JSON ESTRICTO (Sin saltos de línea en valores).
            Si no hay dato, responde "NO INDICA".

            JSON OBJETIVO:
            {
                "id_licitacion": "ID Propuesta",
                "fechas": "Apertura y Cierre",
                "productos": "Resumen Productos",
                "cenabast": "Faltante/Intermediación (SI/NO)",
                "presupuesto": "Monto Total",
                "garantia_seriedad": "Monto, Vigencia, Glosa",
                "garantia_cumplimiento": "Monto, Vigencia, Glosa",
                "duracion_contrato": "Vigencia",
                "reajuste": "IPC (SI/NO)",
                "suscripcion_contrato": "Requiere Firma (SI/NO)",
                "plazo_entrega": "Plazos y Urgencias",
                "vencimiento_canje": "Política Canje",
                "multas": "Resumen Multas",
                "inadmisibilidad": "Causales Rechazo"
            }
            """
            
            status_box.info(f"⚡ Cortex: Analizando riesgos con {modelo_elegido}...")
            model = genai.GenerativeModel(modelo_elegido)
            response = model.generate_content([prompt, archivo_gemini])
            
            bar.progress(80)
            
            # E. REPORTE
            status_box.info("📝 Cortex: Redactando informe...")
            datos = limpiar_y_reparar_json(response.text)
            
            bar.progress(100)
            status_box.success("✅ Cortex: ¡Análisis terminado!")
            
            # DASHBOARD
            with st.container():
                c1, c2 = st.columns(2)
                with c1:
                    st.error(f"🚨 **Multas Detectadas:**\n\n{datos.get('multas', '-')}")
                with c2:
                    st.info(f"📦 **Análisis Logístico:**\n\n{datos.get('cenabast', '-')}")
            
            # F. EXCEL
            df = pd.DataFrame([datos])
            cols_deseadas = ['id_licitacion', 'fechas', 'productos', 'multas', 'garantia_seriedad', 'garantia_cumplimiento', 'cenabast', 'presupuesto']
            cols_finales = [c for c in cols_deseadas if c in df.columns] + [c for c in df.columns if c not in cols_deseadas]
            df = df[cols_finales]

            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                df.to_excel(writer, sheet_name='Reporte_Cortex', index=False)
                workbook = writer.book
                worksheet = writer.sheets['Reporte_Cortex']
                
                fmt_header = workbook.add_format({'bold': True, 'bg_color': '#2E5CB8', 'font_color': 'white', 'border': 1, 'align': 'center', 'valign': 'vcenter'})
                fmt_risk = workbook.add_format({'bg_color': '#FFC7CE', 'text_wrap': True, 'border': 1, 'valign': 'top'})
                fmt_info = workbook.add_format({'bg_color': '#D9E1F2', 'text_wrap': True, 'border': 1, 'valign': 'top'})
                fmt_normal = workbook.add_format({'text_wrap': True, 'border': 1, 'valign': 'top'})
                
                worksheet.set_row(0, 30)
                for col_num, value in enumerate(df.columns.values):
                    worksheet.write(0, col_num, str(value).upper(), fmt_header)
                    col = str(value).lower()
                    if 'multas' in col or 'garantia' in col: worksheet.set_column(col_num, col_num, 35, fmt_risk)
                    elif 'productos' in col or 'cenabast' in col: worksheet.set_column(col_num, col_num, 30, fmt_info)
                    else: worksheet.set_column(col_num, col_num, 22, fmt_normal)

            st.divider()
            st.download_button(
                label="📥 DESCARGAR REPORTE CORTEX",
                data=buffer,
                file_name=f"Cortex_Reporte_{datos.get('id_licitacion', 'General')}.xlsx",
                mime="application/vnd.ms-excel"
            )
            os.remove(tmp_path)

        except Exception as e:
            st.error(f"❌ Error: {e}")
