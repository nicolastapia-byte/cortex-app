import streamlit as st
import google.generativeai as genai
import pandas as pd
import json
import re
import io
import tempfile
import os
import ast

# --- 1. CONFIGURACIÓN VISUAL (IDENTIDAD CORTEX) ---
st.set_page_config(
    page_title="Cortex AI - Auditoría",
    page_icon="🧠",
    layout="centered"
)

# Estilos CSS (Azul Tecnológico Cortex)
st.markdown("""
    <style>
    .stButton>button {
        width: 100%;
        background-color: #2E5CB8; /* Azul Cortex Tech */
        color: white;
        font-weight: 600;
        border-radius: 6px;
        padding: 0.7rem;
        font-size: 16px;
        border: none;
        transition: background-color 0.3s ease;
    }
    .stButton>button:hover {
        background-color: #1F4085; /* Azul más oscuro al pasar el mouse */
    }
    .stProgress > div > div > div > div {
        background-color: #2E5CB8;
    }
    /* Ajuste para que el logo del sidebar respire */
    [data-testid="stSidebar"] .stImage {
        margin-bottom: 20px;
        margin-top: 10px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. SIDEBAR (CORTEX) ---
with st.sidebar:
    # Busca el logo 'logo_cortex.png'. Si no está, avisa amablemente.
    try:
        st.image("logo_cortex.png", width=120) 
    except:
        st.warning("⚠️ Sube tu imagen 'logo_cortex.png' a GitHub.")
        st.header("🧠 Cortex AI")

    st.markdown("---")
    st.markdown("**Powered by Sentinela**")
    st.success("✅ Sistema Operativo")
    st.info("ℹ️ Versión: Cortex Prime V16.0")

# --- 3. ENCABEZADO PRINCIPAL ---
st.title("🧠 Cortex: Auditoría de Licitaciones")
st.markdown("Agente de IA especializado en la detección de **Riesgos, Multas y Garantías** en bases públicas.")

# --- 4. INPUT DE ARCHIVO ---
uploaded_file = st.file_uploader("📂 Cargue las Bases Administrativas (PDF):", type=["pdf"], help="Arrastra tu archivo aquí.")

# --- 5. FUNCIONES DE LIMPIEZA Y REPARACIÓN (ROBUSTAS) ---
def limpiar_y_reparar_json(texto):
    """Limpia la respuesta de la IA y repara errores de sintaxis JSON."""
    try:
        # Paso 1: Eliminar bloques de código Markdown
        texto = re.sub(r'```json', '', texto)
        texto = re.sub(r'```', '', texto)
        # Paso 2: Extraer el objeto JSON
        inicio = texto.find('{')
        fin = texto.rfind('}') + 1
        if inicio == -1 or fin == 0: return {}
        json_str = texto[inicio:fin]
        # Paso 3: Parsear
        return json.loads(json_str, strict=False)
    except:
        # Paso 4: Plan B (AST) para errores de comillas o saltos de línea
        try:
            return ast.literal_eval(json_str)
        except:
            return {"multas": "Error de lectura - Revise PDF", "id_licitacion": "ERROR"}

# --- 6. LÓGICA PRINCIPAL ---
if uploaded_file is not None:
    
    if st.button("⚡ INICIAR CORTEX"):
        
        status_box = st.empty()
        bar = st.progress(0)
        
        try:
            # A. CONEXIÓN
            status_box.info("🔐 Conectando red neuronal Cortex...")
            if "GOOGLE_API_KEY" in st.secrets:
                genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
            else:
                st.error("❌ Falta API Key en Secrets.")
                st.stop()
            
            # B. MODELO INTELIGENTE
            status_box.info("🧠 Activando lóbulos frontales...")
            try:
                modelos = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
                # Prioridad: Flash 1.5 -> Pro 1.5 -> Cualquiera
                modelo_elegido = next((m for m in modelos if 'flash' in m and '1.5' in m), None)
                if not modelo_elegido:
                    modelo_elegido = next((m for m in modelos if 'pro' in m and '1.5' in m), None)
                if not modelo_elegido and modelos:
                    modelo_elegido = modelos[0]
                
                if not modelo_elegido: raise Exception("Sin modelos disponibles.")
            except Exception as e:
                st.error(f"❌ Error de conexión: {e}")
                st.stop()
            
            bar.progress(20)
            
            # C. PROCESAMIENTO
            status_box.info("📄 Escaneando documento PDF...")
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
                tmp_file.write(uploaded_file.getvalue())
                tmp_path = tmp_file.name

            archivo_gemini = genai.upload_file(tmp_path)
            bar.progress(40)
            
            # D. PROMPT CORTEX (EL CEREBRO)
            prompt = """
            ACTÚA COMO CORTEX, EL AGENTE DE IA EXPERTO EN LICITACIONES DE SENTINELA.
            Analiza el PDF y extrae los datos en JSON ESTRICTO.
            
            REGLAS CRÍTICAS:
            1. NO uses "Enter" (saltos de línea) dentro de los valores de texto.
            2. Si no encuentras un dato, pon "NO INDICA".
            3. Sé técnico y preciso.

            JSON A EXTRAER:
            {
                "id_licitacion": "ID Propuesta",
                "fechas": "Apertura y Cierre",
                "productos": "Resumen de Productos/Servicios",
                "cenabast": "Mención a Faltante/Intermediación (SI/NO)",
                "presupuesto": "Monto Total",
                "garantia_seriedad": "Monto, Vigencia y Glosa",
                "garantia_cumplimiento": "Monto, Vigencia y Glosa",
                "duracion_contrato": "Vigencia",
                "reajuste": "IPC (SI/NO)",
                "suscripcion_contrato": "Requiere Firma (SI/NO)",
                "plazo_entrega": "Plazos y Urgencias",
                "vencimiento_canje": "Política de Canje",
                "multas": "Resumen de Multas y Sanciones",
                "inadmisibilidad": "Causales de Rechazo"
            }
            """
            
            status_box.info(f"⚡ Procesando lógica con {modelo_elegido}...")
            model = genai.GenerativeModel(modelo_elegido)
            response = model.generate_content([prompt, archivo_gemini])
            
            bar.progress(80)
            
            # E. RESULTADOS
            status_box.info("🏗️ Construyendo reporte ejecutivo...")
            datos = limpiar_y_reparar_json(response.text)
            
            bar.progress(100)
            status_box.success("✅ Análisis Completado.")
            
            # DASHBOARD
            with st.container():
                c1, c2 = st.columns(2)
                with c1:
                    st.error(f"🚨 **Multas:**\n\n{datos.get('multas', '-')}")
                with c2:
                    st.info(f"📦 **Logística:**\n\n{datos.get('cenabast', '-')}")
            
            # F. EXCEL CORTEX
            df = pd.DataFrame([datos])
            
            # Ordenar
            cols_deseadas = ['id_licitacion', 'fechas', 'productos', 'multas', 'garantia_seriedad', 'garantia_cumplimiento', 'cenabast', 'presupuesto']
            cols_finales = [c for c in cols_deseadas if c in df.columns] + [c for c in df.columns if c not in cols_deseadas]
            df = df[cols_finales]

            buffer = io.BytesIO()
            
            with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                df.to_excel(writer, sheet_name='Reporte_Cortex', index=False)
                
                workbook = writer.book
                worksheet = writer.sheets['Reporte_Cortex']
                
                # Estilos Cortex
                fmt_header = workbook.add_format({'bold': True, 'bg_color': '#2E5CB8', 'font_color': 'white', 'border': 1, 'align': 'center', 'valign': 'vcenter'})
                fmt_risk = workbook.add_format({'bg_color': '#FFC7CE', 'text_wrap': True, 'border': 1, 'valign': 'top'})
                fmt_info = workbook.add_format({'bg_color': '#D9E1F2', 'text_wrap': True, 'border': 1, 'valign': 'top'})
                fmt_normal = workbook.add_format({'text_wrap': True, 'border': 1, 'valign': 'top'})
                
                worksheet.set_row(0, 30)
                
                for col_num, value in enumerate(df.columns.values):
                    worksheet.write(0, col_num, str(value).upper(), fmt_header)
                    col_name = str(value).lower()
                    
                    if 'multas' in col_name or 'garantia' in col_name:
                        worksheet.set_column(col_num, col_num, 35, fmt_risk)
                    elif 'productos' in col_name or 'cenabast' in col_name:
                        worksheet.set_column(col_num, col_num, 30, fmt_info)
                    else:
                        worksheet.set_column(col_num, col_num, 22, fmt_normal)

            st.divider()
            filename = f"Cortex_Reporte_{datos.get('id_licitacion', 'General')}.xlsx"
            st.download_button(
                label="📥 DESCARGAR REPORTE CORTEX",
                data=buffer,
                file_name=filename,
                mime="application/vnd.ms-excel"
            )
            
            os.remove(tmp_path)

        except Exception as e:
            st.error(f"❌ Error: {e}")
