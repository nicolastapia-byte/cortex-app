import streamlit as st
import google.generativeai as genai
import pandas as pd
import json
import re
import io
import tempfile
import os
import ast
import time

# --- 1. CONFIGURACIÓN VISUAL ---
st.set_page_config(
    page_title="Cortex AI - Auditoría",
    page_icon="🤖",
    layout="centered"
)

# Estilos CSS (Animaciones Avanzadas)
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
        transition: all 0.3s ease;
    }
    .stButton>button:hover {
        background-color: #1F4085;
        transform: scale(1.02);
    }
    
    /* 1. ROBOT ZEN (Flotando suave) */
    .robot-zen {
        font-size: 100px;
        text-align: center;
        animation: float 3s ease-in-out infinite;
    }
    
    /* 2. ROBOT PENSANDO (Pulsando rápido) */
    .robot-thinking {
        font-size: 100px;
        text-align: center;
        animation: pulse 0.8s infinite;
    }

    /* 3. ROBOT FELIZ (Rebote) */
    .robot-success {
        font-size: 100px;
        text-align: center;
        animation: bounce 1s ease infinite;
    }

    /* DEFINICIÓN DE ANIMACIONES */
    @keyframes float {
        0% { transform: translateY(0px); }
        50% { transform: translateY(-10px); }
        100% { transform: translateY(0px); }
    }
    @keyframes pulse {
        0% { transform: scale(1); opacity: 1; }
        50% { transform: scale(1.1); opacity: 0.8; }
        100% { transform: scale(1); opacity: 1; }
    }
    @keyframes bounce {
        0%, 100% { transform: translateY(0); }
        50% { transform: translateY(-20px); }
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. SIDEBAR CON PLACEHOLDER ---
with st.sidebar:
    # Creamos un ESPACIO VACÍO que podemos actualizar después
    robot_placeholder = st.empty()
    # Estado inicial: Robot Zen
    robot_placeholder.markdown('<div class="robot-zen">🤖</div>', unsafe_allow_html=True)
    
    st.title("Cortex AI")
    st.markdown("**Agente Digital de Sentinela**")
    st.markdown("---")
    st.success("✅ Sistema Calibrado")
    st.info("ℹ️ Versión: Alive V21.0")

# --- 3. ENCABEZADO ---
st.title("🤖 Cortex: Auditoría Experta")
st.markdown("Soy **Cortex**, tu agente de IA. He sido actualizado con los criterios de Gador para detectar **Inadmisibilidad y Riesgos**.")

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
    
    if st.button("⚡ ACTIVAR CORTEX"):
        
        # CAMBIO DE ESTADO 1: MODO PENSANDO (Robot vibra)
        robot_placeholder.markdown('<div class="robot-thinking">⚡</div>', unsafe_allow_html=True)
        
        status_box = st.empty()
        bar = st.progress(0)
        
        try:
            # A. CONEXIÓN
            status_box.info("🔐 Conectando cerebro digital...")
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
                st.error("❌ Error de conexión.")
                st.stop()
            
            bar.progress(20)
            
            # C. LECTURA
            status_box.info("👁️ Leyendo y comprendiendo el PDF...")
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
                tmp_file.write(uploaded_file.getvalue())
                tmp_path = tmp_file.name

            archivo_gemini = genai.upload_file(tmp_path)
            bar.progress(40)
            
            # D. PROMPT (CRITERIO GADOR - PILAR)
            prompt = """
            ACTÚA COMO UN EXPERTO EN LICITACIONES PÚBLICAS.
            
            CRITERIOS DE REVISIÓN (GADOR):
            1. FECHAS: Busca "PLAZOS" (días hábiles/corridos) no solo fechas calendario.
            2. VIGENCIA DE OFERTA: Si la oferta tiene MENOR vigencia a la solicitada -> RIESGO DE INADMISIBILIDAD.
            3. GLOSA: Extrae el TEXTO LITERAL exigido para la garantía.
            4. INADMISIBILIDAD: Relaciona errores en Glosa y Vigencia como causales de rechazo.

            Extrae JSON ESTRICTO:
            {
                "id_licitacion": "ID Propuesta",
                "fechas": "Plazos y Fechas Clave",
                "productos": "Resumen Productos",
                "cenabast": "Faltante/Intermediación (SI/NO)",
                "presupuesto": "Monto Total",
                "garantia_seriedad": "Monto, VIGENCIA y GLOSA EXACTA",
                "garantia_cumplimiento": "Monto, VIGENCIA y GLOSA EXACTA",
                "duracion_contrato": "Vigencia contrato",
                "reajuste": "IPC (SI/NO)",
                "suscripcion_contrato": "Plazo firma",
                "plazo_entrega": "Plazos entrega",
                "vencimiento_canje": "Política Canje",
                "multas": "Resumen Multas",
                "inadmisibilidad": "CAUSALES DE RECHAZO (Vigencia, Glosa, etc)"
            }
            """
            
            status_box.info(f"⚡ Analizando riesgos críticos...")
            model = genai.GenerativeModel(modelo_elegido)
            response = model.generate_content([prompt, archivo_gemini])
            
            bar.progress(80)
            
            # E. REPORTE
            status_box.info("📝 Redactando informe...")
            datos = limpiar_y_reparar_json(response.text)
            
            bar.progress(100)
            status_box.success("✅ ¡Análisis Terminado!")
            
            # CAMBIO DE ESTADO 2: MODO ÉXITO (Robot Cool)
            robot_placeholder.markdown('<div class="robot-success">😎</div>', unsafe_allow_html=True)
            
            # DASHBOARD
            with st.container():
                c1, c2 = st.columns(2)
                with c1:
                    st.error(f"🚫 **Inadmisibilidad:**\n\n{datos.get('inadmisibilidad', '-')}")
                with c2:
                    st.warning(f"⚠️ **Garantías:**\n\n{datos.get('garantia_seriedad', '-')}")
            
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
                fmt_alert = workbook.add_format({'bg_color': '#FFEB9C', 'text_wrap': True, 'border': 1, 'valign': 'top'})
                fmt_normal = workbook.add_format({'text_wrap': True, 'border': 1, 'valign': 'top'})
                
                worksheet.set_row(0, 30)
                for col_num, value in enumerate(df.columns.values):
                    worksheet.write(0, col_num, str(value).upper(), fmt_header)
                    col = str(value).lower()
                    if 'inadmisibilidad' in col or 'multas' in col: worksheet.set_column(col_num, col_num, 40, fmt_risk)
                    elif 'garantia' in col: worksheet.set_column(col_num, col_num, 35, fmt_alert)
                    else: worksheet.set_column(col_num, col_num, 25, fmt_normal)

            st.divider()
            st.download_button(
                label="📥 DESCARGAR REPORTE CORTEX (V21)",
                data=buffer,
                file_name=f"Cortex_{datos.get('id_licitacion', 'Reporte')}.xlsx",
                mime="application/vnd.ms-excel"
            )
            os.remove(tmp_path)
            
            # Volver a estado normal después de 5 segundos (opcional, pero da un toque pro)
            time.sleep(5)
            robot_placeholder.markdown('<div class="robot-zen">🤖</div>', unsafe_allow_html=True)

        except Exception as e:
            st.error(f"❌ Error: {e}")
            # Si falla, robot triste o mareado
            robot_placeholder.markdown('<div class="robot-zen">😵</div>', unsafe_allow_html=True)
