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
    page_title="Cortex AI - Sentinela",
    page_icon="🧠",
    layout="centered"
)

st.markdown("""
    <style>
    .stButton>button {
        width: 100%;
        background-color: #2E5CB8; /* Azul Tech Cortex */
        color: white;
        font-weight: 600;
        border-radius: 6px;
        padding: 0.7rem;
        font-size: 16px;
        border: none;
    }
    .stProgress > div > div > div > div {
        background-color: #2E5CB8;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. SIDEBAR (MARCA CORTEX) ---
with st.sidebar:
    # Logo de Cerebro Digital (Cortex)
    st.image("https://cdn-icons-png.flaticon.com/512/12395/12395369.png", width=80)
    st.title("Cortex AI")
    st.markdown("**Powered by Sentinela**")
    st.success("✅ Sistema Operativo")
    st.info("ℹ️ Versión: Global V13.0")

# --- 3. ENCABEZADO ---
st.title("🧠 Cortex: Auditoría de Licitaciones")
st.markdown("Plataforma de inteligencia artificial para detección de **Riesgos, Multas y Garantías** en bases públicas.")

# --- 4. INPUT ---
uploaded_file = st.file_uploader("📂 Cargue las Bases Administrativas (PDF):", type=["pdf"])

# --- 5. LIMPIEZA Y REPARACIÓN ---
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
        try:
            return ast.literal_eval(json_str)
        except:
            return {"multas": "Error de lectura - Revise PDF", "id_licitacion": "Error"}

# --- 6. LÓGICA PRINCIPAL ---
if uploaded_file is not None:
    
    if st.button("⚡ INICIAR AUDITORÍA CORTEX"):
        
        status_box = st.empty()
        bar = st.progress(0)
        
        try:
            # A. CONEXIÓN
            if "GOOGLE_API_KEY" in st.secrets:
                genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
            else:
                st.error("❌ Falta API Key.")
                st.stop()
            
            # B. MODELO
            status_box.info("📡 Conectando red neuronal...")
            modelos = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
            modelo_elegido = next((m for m in modelos if 'flash' in m and '1.5' in m), modelos[0] if modelos else None)
            
            if not modelo_elegido:
                st.error("❌ Sin modelos disponibles.")
                st.stop()
            
            bar.progress(20)
            
            # C. SUBIR PDF
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
                tmp_file.write(uploaded_file.getvalue())
                tmp_path = tmp_file.name

            archivo_gemini = genai.upload_file(tmp_path)
            bar.progress(40)
            
            # D. PROMPT UNIVERSAL (PARA CUALQUIER CLIENTE)
            prompt = """
            ACTÚA COMO UN EXPERTO GERENTE DE LICITACIONES.
            Analiza el PDF adjunto y extrae los datos críticos en formato JSON.
            IMPORTANTE: NO uses saltos de línea (Enter) dentro de los valores del texto.

            DATOS A EXTRAER:
            {
                "id_licitacion": "ID Propuesta",
                "fechas": "Apertura y Cierre",
                "productos": "Resumen de Productos/Servicios",
                "cenabast": "Menciona Faltante/Intermediación (SI/NO)",
                "presupuesto": "Monto Total Estimado",
                "garantia_seriedad": "Monto y Vigencia",
                "garantia_cumplimiento": "Monto y Vigencia",
                "duracion_contrato": "Vigencia",
                "reajuste": "IPC (SI/NO)",
                "suscripcion_contrato": "Requiere Firma (SI/NO)",
                "plazo_entrega": "Plazos y Urgencias",
                "vencimiento_canje": "Política de Canje/Devolución",
                "multas": "Resumen de Multas",
                "inadmisibilidad": "Causales Rechazo"
            }
            """
            
            status_box.info(f"🧠 Procesando con motor Cortex ({modelo_elegido})...")
            model = genai.GenerativeModel(modelo_elegido)
            response = model.generate_content([prompt, archivo_gemini])
            
            bar.progress(80)
            
            # E. PROCESAR RESULTADOS
            status_box.info("🔧 Estructurando reporte...")
            datos = limpiar_y_reparar_json(response.text)
            
            bar.progress(100)
            status_box.success("✅ Auditoría Finalizada.")
            
            # Vista previa
            c1, c2 = st.columns(2)
            c1.error(f"🚨 **Multas:**\n{datos.get('multas', '-')}")
            c2.info(f"📦 **Logística:**\n{datos.get('cenabast', '-')}")
            
            # F. GENERAR EXCEL CORTEX
            df = pd.DataFrame([datos])
            
            # Orden
            cols_deseadas = ['id_licitacion', 'fechas', 'productos', 'multas', 'garantia_seriedad', 'cenabast']
            cols_finales = [c for c in cols_deseadas if c in df.columns] + [c for c in df.columns if c not in cols_deseadas]
            df = df[cols_finales]

            buffer = io.BytesIO()
            
            with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                df.to_excel(writer, sheet_name='Reporte_Cortex', index=False)
                
                workbook = writer.book
                worksheet = writer.sheets['Reporte_Cortex']
                
                # Estilos Cortex (Azul Tech)
                fmt_header = workbook.add_format({'bold': True, 'bg_color': '#2E5CB8', 'font_color': 'white', 'border': 1})
                fmt_risk = workbook.add_format({'bg_color': '#FFC7CE', 'text_wrap': True, 'border': 1})
                fmt_normal = workbook.add_format({'text_wrap': True, 'border': 1})
                
                for col_num, value in enumerate(df.columns.values):
                    worksheet.write(0, col_num, str(value).upper(), fmt_header)
                    if 'multas' in str(value).lower() or 'garantia' in str(value).lower():
                        worksheet.set_column(col_num, col_num, 35, fmt_risk)
                    else:
                        worksheet.set_column(col_num, col_num, 25, fmt_normal)

            # G. DESCARGA
            st.download_button(
                label="📥 DESCARGAR REPORTE CORTEX",
                data=buffer,
                file_name=f"Cortex_Reporte_{datos.get('id_licitacion', 'General')}.xlsx",
                mime="application/vnd.ms-excel"
            )
            
            os.remove(tmp_path)

        except Exception as e:
            st.error(f"❌ Error: {e}")
