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
    st.success("✅ Sistema Operativo")
    st.info("ℹ️ Versión: V12.0 (Stable)")

# --- 3. ENCABEZADO ---
st.title("🛡️ Centro de Auditoría de Licitaciones")
st.markdown("Auditoría automática de **Multas, Garantías y Logística**.")

# --- 4. INPUT ---
uploaded_file = st.file_uploader("📂 Cargue las Bases (PDF):", type=["pdf"])

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
            return {"multas": "Error de lectura manual", "id_licitacion": "Error"}

# --- 6. LÓGICA PRINCIPAL ---
if uploaded_file is not None:
    
    if st.button("⚡ EJECUTAR ANÁLISIS"):
        
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
            status_box.info("📡 Conectando...")
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
            
            # D. PROMPT
            prompt = """
            ACTÚA COMO GERENTE DE GADOR.
            Extrae datos en JSON SIN SALTOS DE LÍNEA en los valores:
            {
                "id_licitacion": "ID",
                "fechas": "Apertura/Cierre",
                "productos": "Principios Activos",
                "cenabast": "SI/NO",
                "presupuesto": "Monto",
                "garantia_seriedad": "Detalle",
                "garantia_cumplimiento": "Detalle",
                "duracion_contrato": "Vigencia",
                "reajuste": "SI/NO",
                "suscripcion_contrato": "SI/NO",
                "plazo_entrega": "Plazos",
                "vencimiento_canje": "Politica",
                "multas": "Detalle",
                "inadmisibilidad": "Causales"
            }
            """
            
            status_box.info(f"🧠 Analizando con {modelo_elegido}...")
            model = genai.GenerativeModel(modelo_elegido)
            response = model.generate_content([prompt, archivo_gemini])
            
            bar.progress(80)
            
            # E. PROCESAR RESULTADOS
            status_box.info("🔧 Procesando datos...")
            datos = limpiar_y_reparar_json(response.text)
            
            bar.progress(100)
            status_box.success("✅ Listo.")
            
            # Vista previa
            c1, c2 = st.columns(2)
            c1.error(f"🚨 **Multas:**\n{datos.get('multas', '-')}")
            c2.info(f"📦 **Cenabast:**\n{datos.get('cenabast', '-')}")
            
            # F. GENERAR EXCEL (Aquí estaba el error antes)
            df = pd.DataFrame([datos])
            
            # Ordenar columnas si existen
            cols_deseadas = ['id_licitacion', 'fechas', 'productos', 'multas', 'garantia_seriedad', 'cenabast']
            cols_finales = [c for c in cols_deseadas if c in df.columns] + [c for c in df.columns if c not in cols_deseadas]
            df = df[cols_finales]

            buffer = io.BytesIO()
            
            # BLOQUE CORREGIDO CON CUIDADO
            with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                # 1. Escribir datos
                df.to_excel(writer, sheet_name='Gador', index=False)
                
                # 2. Obtener objetos para formato
                workbook = writer.book
                worksheet = writer.sheets['Gador']
                
                # 3. Formatos
                fmt_header = workbook.add_format({'bold': True, 'bg_color': '#004481', 'font_color': 'white', 'border': 1})
                fmt_risk = workbook.add_format({'bg_color': '#FFC7CE', 'text_wrap': True, 'border': 1})
                fmt_normal = workbook.add_format({'text_wrap': True, 'border': 1})
                
                # 4. Aplicar formatos
                for col_num, value in enumerate(df.columns.values):
                    worksheet.write(0, col_num, str(value).upper(), fmt_header)
                    if 'multas' in str(value).lower() or 'garantia' in str(value).lower():
                        worksheet.set_column(col_num, col_num, 35, fmt_risk)
                    else:
                        worksheet.set_column(col_num, col_num, 25, fmt_normal)

            # G. DESCARGA
            st.download_button(
                label="📥 DESCARGAR EXCEL",
                data=buffer,
                file_name=f"Reporte_{datos.get('id_licitacion', 'Gador')}.xlsx",
                mime="application/vnd.ms-excel"
            )
            
            os.remove(tmp_path)

        except Exception as e:
            st.error(f"❌ Error: {e}")
