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
    page_icon="🤖",
    layout="centered"
)

# Estilos CSS (Robot Gigante V19)
st.markdown("""
    <style>
    .stButton>button {
        width: 100%;
        background-color: #2E5CB8;
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
    /* ROBOT ANIMADO */
    .robot-avatar {
        font-size: 100px;
        text-align: center;
        margin-bottom: 10px;
        animation: float 3s ease-in-out infinite;
    }
    @keyframes float {
        0% { transform: translateY(0px); }
        50% { transform: translateY(-10px); }
        100% { transform: translateY(0px); }
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. SIDEBAR ---
with st.sidebar:
    st.markdown('<div class="robot-avatar">🤖</div>', unsafe_allow_html=True)
    st.title("Cortex AI")
    st.markdown("**Agente Digital de Sentinela**")
    st.markdown("---")
    st.success("✅ Sistema Calibrado")
    st.info("ℹ️ Versión: Expert V20.0 (Pilar Feedback)")

# --- 3. ENCABEZADO ---
st.title("🤖 Cortex: Auditoría Experta")
st.markdown("Soy **Cortex**, tu agente de IA especializado. He sido actualizado para detectar **Glosas Exactas, Plazos de Vigencia y Causales de Rechazo**.")

# --- 4. INPUT ---
uploaded_file = st.file_uploader("📂 Cargar Bases (PDF):", type=["pdf"])

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
        except: return {"multas": "Error lectura", "id_licitacion": "ERROR"}

# --- 6. LÓGICA ---
if uploaded_file is not None:
    
    if st.button("⚡ ANALIZAR CRITERIOS GADOR"):
        
        status_box = st.empty()
        bar = st.progress(0)
        
        try:
            # A. CONEXIÓN
            status_box.info("🔐 Cortex: Conectando sistemas...")
            if "GOOGLE_API_KEY" in st.secrets:
                genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
            else:
                st.error("❌ Falta API Key.")
                st.stop()
            
            # B. MODELO
            try:
                modelos = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
                modelo_elegido = next((m for m in modelos if 'flash' in m and '1.5' in m), None) or modelos[0]
            except:
                st.error("❌ Error conectando a Google AI.")
                st.stop()
            
            bar.progress(20)
            
            # C. LECTURA
            status_box.info("👁️ Cortex: Leyendo bases técnicas y administrativas...")
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
                tmp_file.write(uploaded_file.getvalue())
                tmp_path = tmp_file.name

            archivo_gemini = genai.upload_file(tmp_path)
            bar.progress(40)
            
            # D. PROMPT (CALIBRADO CON FEEDBACK PILAR)
            prompt = """
            ACTÚA COMO UN EXPERTO EN LICITACIONES PÚBLICAS (CHILE COMPRA).
            Tu objetivo es detectar CAUSALES DE INADMISIBILIDAD y errores en garantías.
            
            INSTRUCCIONES CRÍTICAS (Feedback Gador):
            1. FECHAS: No busques solo fechas calendario. Busca "PLAZOS" (ej: "60 días corridos", "12 meses").
            2. VIGENCIA DE OFERTA: Identifica la vigencia solicitada. Si la oferta tiene MENOR vigencia a la solicitada, repórtalo como RIESGO DE INADMISIBILIDAD.
            3. GLOSA: Debes extraer el TEXTO EXACTO (Glosa) que debe ir en la Garantía. Si la base exige una glosa específica, indícalo claramente.
            4. INADMISIBILIDAD: Relaciona "Error en Glosa" y "Vigencia insuficiente" como causales directas de rechazo.

            Extrae en JSON ESTRICTO (una línea por valor):
            {
                "id_licitacion": "ID Propuesta",
                "fechas": "Plazos claves (Días hábiles/corridos, Apertura, Adjudicación)",
                "productos": "Resumen Productos",
                "cenabast": "Faltante/Intermediación (SI/NO)",
                "presupuesto": "Monto Total",
                "garantia_seriedad": "Monto, VIGENCIA EXACTA y GLOSA REQUERIDA (Literal)",
                "garantia_cumplimiento": "Monto, VIGENCIA EXACTA y GLOSA REQUERIDA (Literal)",
                "duracion_contrato": "Vigencia del contrato",
                "reajuste": "IPC (SI/NO)",
                "suscripcion_contrato": "Plazo para firma (SI/NO)",
                "plazo_entrega": "Plazos de entrega y urgencias",
                "vencimiento_canje": "Política Canje",
                "multas": "Resumen Multas",
                "inadmisibilidad": "LISTA DE CAUSALES: Incluir explícitamente si 'Vigencia menor a la solicitada' o 'Error en Glosa' son motivo de rechazo."
            }
            """
            
            status_box.info(f"⚡ Cortex: Aplicando criterio experto Gador...")
            model = genai.GenerativeModel(modelo_elegido)
            response = model.generate_content([prompt, archivo_gemini])
            
            bar.progress(80)
            
            # E. REPORTE
            status_box.info("📝 Cortex: Redactando informe técnico...")
            datos = limpiar_y_reparar_json(response.text)
            
            bar.progress(100)
            status_box.success("✅ Cortex: Análisis finalizado.")
            
            # DASHBOARD DE RIESGOS
            with st.container():
                c1, c2 = st.columns(2)
                with c1:
                    st.error(f"🚫 **Causales Inadmisibilidad:**\n\n{datos.get('inadmisibilidad', '-')}")
                with c2:
                    st.warning(f"⚠️ **Requisitos Garantías:**\n\nSeriedad: {datos.get('garantia_seriedad', '-')}\n\nCumplimiento: {datos.get('garantia_cumplimiento', '-')}")
            
            # F. EXCEL
            df = pd.DataFrame([datos])
            cols_deseadas = ['id_licitacion', 'inadmisibilidad', 'fechas', 'garantia_seriedad', 'garantia_cumplimiento', 'multas', 'cenabast', 'productos']
            cols_finales = [c for c in cols_deseadas if c in df.columns] + [c for c in df.columns if c not in cols_deseadas]
            df = df[cols_finales]

            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                df.to_excel(writer, sheet_name='Reporte_Cortex', index=False)
                workbook = writer.book
                worksheet = writer.sheets['Reporte_Cortex']
                
                fmt_header = workbook.add_format({'bold': True, 'bg_color': '#2E5CB8', 'font_color': 'white', 'border': 1, 'align': 'center', 'valign': 'vcenter'})
                fmt_risk = workbook.add_format({'bg_color': '#FFC7CE', 'text_wrap': True, 'border': 1, 'valign': 'top'})
                fmt_alert = workbook.add_format({'bg_color': '#FFEB9C', 'text_wrap': True, 'border': 1, 'valign': 'top'}) # Amarillo para garantías
                fmt_normal = workbook.add_format({'text_wrap': True, 'border': 1, 'valign': 'top'})
                
                worksheet.set_row(0, 30)
                for col_num, value in enumerate(df.columns.values):
                    worksheet.write(0, col_num, str(value).upper(), fmt_header)
                    col = str(value).lower()
                    if 'inadmisibilidad' in col or 'multas' in col: 
                        worksheet.set_column(col_num, col_num, 40, fmt_risk)
                    elif 'garantia' in col: 
                        worksheet.set_column(col_num, col_num, 35, fmt_alert)
                    else: 
                        worksheet.set_column(col_num, col_num, 25, fmt_normal)

            st.divider()
            st.download_button(
                label="📥 DESCARGAR REPORTE CORTEX (V20)",
                data=buffer,
                file_name=f"Cortex_Gador_{datos.get('id_licitacion', 'Reporte')}.xlsx",
                mime="application/vnd.ms-excel"
            )
            os.remove(tmp_path)

        except Exception as e:
            st.error(f"❌ Error: {e}")
