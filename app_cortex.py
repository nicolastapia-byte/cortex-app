import streamlit as st
import google.generativeai as genai
import pandas as pd
import json
import re
import io
import tempfile
import os

# --- 1. CONFIGURACIÓN VISUAL (EL MARCO DEL CUADRO) ---
st.set_page_config(page_title="Cortex AI - Gador", page_icon="🎨", layout="centered")

st.markdown("""
    <style>
    .stButton>button {
        width: 100%;
        background-color: #004481; /* Azul Gador */
        color: white;
        font-weight: bold;
        border-radius: 8px;
        padding: 0.6rem;
        font-size: 16px;
    }
    .stProgress > div > div > div > div {
        background-color: #004481;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. SIDEBAR ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/3063/3063822.png", width=70)
    st.title("Gador Farma")
    st.success("✅ Sistema Blindado")
    st.info("ℹ️ Versión: Mona Lisa V9.0")
    st.caption("Excel con Formato Condicional")

# --- 3. ENCABEZADO ---
st.title("🎨 Cortex AI: Auditoría Maestra")
st.markdown("Generando reporte estratégico con detección de **Multas, Garantías y Faltantes**.")

# --- 4. INPUT ---
uploaded_file = st.file_uploader("📂 Sube las Bases (PDF) para pintar el reporte:", type=["pdf"])

# --- 5. FUNCIONES ---
def limpiar_json(texto):
    texto = re.sub(r'```json', '', texto)
    texto = re.sub(r'```', '', texto)
    inicio = texto.find('{')
    fin = texto.rfind('}') + 1
    if inicio != -1 and fin != 0:
        return texto[inicio:fin]
    return "{}"

# --- 6. LÓGICA PRINCIPAL ---
if uploaded_file is not None:
    
    if st.button("⚡ GENERAR REPORTE EXCEL AHORA"):
        
        status = st.empty()
        bar = st.progress(0)
        
        try:
            # A. CONEXIÓN SEGURA
            if "GOOGLE_API_KEY" in st.secrets:
                api_key = st.secrets["GOOGLE_API_KEY"]
            else:
                st.error("❌ Falta la API Key en Secrets.")
                st.stop()
                
            genai.configure(api_key=api_key)
            
            # --- B. ESCÁNER DE MODELOS (ANTIBALAS) ---
            status.text("🔍 Calibrando pinceles (Buscando modelo IA)...")
            modelos_disponibles = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
            
            # Prioridad: Flash -> Pro -> Cualquiera
            modelo_elegido = None
            for m in modelos_disponibles:
                if 'flash' in m and '1.5' in m:
                    modelo_elegido = m
                    break
            if not modelo_elegido:
                modelo_elegido = modelos_disponibles[0] if modelos_disponibles else None
            
            if not modelo_elegido:
                st.error("❌ Error: No hay modelos disponibles en tu cuenta.")
                st.stop()
                
            # ------------------------------------------

            # C. PROCESAMIENTO
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
                tmp_file.write(uploaded_file.getvalue())
                tmp_path = tmp_file.name

            archivo_gemini = genai.upload_file(tmp_path)
            bar.progress(30)
            
            # D. PROMPT "MONA LISA" (DETALLE MÁXIMO)
            prompt = """
            ACTÚA COMO GERENTE DE GADOR. Analiza el PDF y extrae en JSON estricto:
            {
                "id_licitacion": "ID Propuesta",
                "fechas": "Fecha Cierre",
                "productos": "Principios Activos / Glosas",
                "cenabast": "SI/NO (Faltante o Intermediación)",
                "presupuesto": "Monto Estimado",
                "garantia_seriedad": "Monto y Vigencia (Seriedad)",
                "garantia_cumplimiento": "Monto y Vigencia (Cumplimiento)",
                "duracion_contrato": "Meses de contrato",
                "reajuste": "SI/NO (IPC)",
                "suscripcion_contrato": "SI/NO",
                "plazo_entrega": "Plazos y Urgencias",
                "vencimiento_canje": "Vencimiento mínimo y Canje",
                "multas": "DETALLE COMPLETO de Multas",
                "inadmisibilidad": "Causales de rechazo"
            }
            """
            
            status.text(f"🎨 Pintando reporte con {modelo_elegido}...")
            model = genai.GenerativeModel(modelo_elegido)
            response = model.generate_content([prompt, archivo_gemini])
            
            bar.progress(80)
            status.text("🖌️ Aplicando colores y formatos al Excel...")
            
            # E. RESULTADOS Y EXCEL DE LUJO
            json_str = limpiar_json(response.text)
            datos = json.loads(json_str)
            
            st.success("✅ ¡Obra Maestra Terminada!")
            
            # Vista Rápida
            c1, c2 = st.columns(2)
            c1.error(f"🚨 **Multas:**\n{datos.get('multas')}")
            c2.info(f"📦 **Cenabast:**\n{datos.get('cenabast')}")
            
            # --- F. GENERACIÓN DEL EXCEL "SOBRA" ---
            df = pd.DataFrame([datos])
            
            # Reordenar columnas para que lo importante salga primero
            cols_orden = ['id_licitacion', 'fechas', 'productos', 'multas', 'garantia_seriedad', 'cenabast', 'presupuesto']
            # Agregar el resto de columnas que falten
            cols_existentes = [c for c in cols_orden if c in df.columns] + [c for c in df.columns if c not in cols_orden]
            df = df[cols_existentes]

            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                df.to_excel(writer, sheet_name='Reporte_Gador', index=False)
                workbook = writer.book
                worksheet = writer.sheets['Reporte_Gador']
                
                # --- PALETA DE COLORES ---
                fmt_header = workbook.add_format({'bold': True, 'bg_color': '#004481', 'font_color': 'white', 'border': 1, 'align': 'center', 'valign': 'vcenter'})
                fmt_wrap = workbook.add_format({'text_wrap': True, 'valign': 'top', 'border': 1})
                
                # Rojo Alerta (Multas y Garantías)
                fmt_risk = workbook.add_format({'bg_color': '#FFC7CE', 'font_color': '#9C0006', 'text_wrap': True, 'valign': 'top', 'border': 1})
                # Azul Info (Cenabast)
                fmt_info = workbook.add_format({'bg_color': '#D9E1F2', 'text_wrap': True, 'valign': 'top', 'border': 1})
                
                # Aplicar formatos
                for col_num, value in enumerate(df.columns.values):
                    # Escribir encabezado bonito
                    worksheet.write(0, col_num, value.upper().replace('_', ' '), fmt_header)
                    
                    # Decidir color de la columna
                    if 'multas' in value or 'garantia' in value or 'inadmisibilidad' in value:
                        worksheet.set_column(col_num, col_num, 35, fmt_risk) # Ancho 35 y Rojo
                    elif 'productos' in value or 'cenabast' in value:
                        worksheet.set_column(col_num, col_num, 40, fmt_info) # Ancho 40 y Azul
                    else:
                        worksheet.set_column(col_num, col_num, 20, fmt_wrap) # Normal

            # BOTÓN DE DESCARGA
            st.download_button(
                label="📥 DESCARGAR OBRA MAESTRA (EXCEL)",
                data=buffer,
                file_name=f"Reporte_Gador_{datos.get('id_licitacion', 'Final')}.xlsx",
                mime="application/vnd.ms-excel"
            )
            
            bar.progress(100)
            os.remove(tmp_path)

        except Exception as e:
            st.error(f"❌ Pincel roto: {e}")
