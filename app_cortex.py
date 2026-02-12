import streamlit as st
import google.generativeai as genai
import pandas as pd
import json
import re
import io
import tempfile
import os

# --- 1. CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(
    page_title="Cortex AI - Gador",
    page_icon="💊",
    layout="centered"
)

# --- 2. ESTILOS VISUALES ---
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
    st.success("✅ Sistema Conectado")
    st.info("ℹ️ Versión: Enterprise V5.0 (Auto-Connect)")

# --- 4. ENCABEZADO ---
st.title("💊 Cortex AI: Auditoría de Licitaciones")
st.markdown("""
Esta herramienta audita Bases Administrativas buscando **Riesgos Críticos**:
* 🚨 **Multas y Sanciones**
* 💰 **Garantías (Seriedad/Cumplimiento)**
* 📦 **Faltantes Cenabast y Canjes**
""")

# --- 5. SUBIDA DE ARCHIVO ---
uploaded_file = st.file_uploader("📂 Sube las Bases (PDF) aquí:", type=["pdf"])

# --- 6. FUNCIONES AUXILIARES ---
def limpiar_respuesta_json(texto):
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
        
        bar = st.progress(0, text="Iniciando motores...")
        
        try:
            # A. CONEXIÓN Y DETECCIÓN DE MODELO
            if "GOOGLE_API_KEY" in st.secrets:
                api_key = st.secrets["GOOGLE_API_KEY"]
            else:
                st.error("❌ Error: No se encontró la API Key en los Secretos.")
                st.stop()
                
            genai.configure(api_key=api_key)
            
            # --- BUSCADOR INTELIGENTE DE MODELO ---
            # Esto evita el Error 404 buscando cuál funciona
            modelo_activo = "gemini-1.5-flash" # Default
            try:
                listado = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
                # Priorizar Flash -> Pro
                for m in listado:
                    if 'flash' in m and '1.5' in m:
                        modelo_activo = m
                        break
                if not modelo_activo: modelo_activo = "gemini-1.5-pro"
            except:
                pass # Si falla el listado, usamos el default
            
            # --------------------------------------

            # B. PROCESAMIENTO
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
                tmp_file.write(uploaded_file.getvalue())
                tmp_path = tmp_file.name

            bar.progress(20, text=f"🧠 Conectado a {modelo_activo}... Leyendo PDF...")
            archivo_gemini = genai.upload_file(tmp_path)
            
            prompt_gador = """
            ACTÚA COMO GERENTE DE LICITACIONES DE UN LABORATORIO FARMACÉUTICO (GADOR).
            Analiza el PDF y extrae los siguientes datos críticos.
            Si un dato no aparece, responde "NO INDICA".

            EXTRAE LA INFORMACIÓN EN FORMATO JSON ESTRICTO:
            {
                "id_licitacion": "ID o Número de la propuesta",
                "fechas": "Fecha de preguntas y Fecha de Cierre/Apertura",
                "productos": "Lista de PRINCIPIOS ACTIVOS y GLOSAS solicitadas (Solo Fármacos)",
                "cenabast": "Indica SI/NO si menciona 'Faltante Cenabast' o intermediación",
                "presupuesto": "Monto total estimado disponible",
                "garantia_seriedad": "Monto, % y vigencia de la Seriedad de la Oferta",
                "garantia_cumplimiento": "Monto, % y vigencia del Fiel Cumplimiento",
                "duracion_contrato": "Duración en meses/años",
                "reajuste": "Indica SI/NO si hay cláusula de reajuste (IPC)",
                "suscripcion_contrato": "Indica SI/NO requiere firma de contrato",
                "anexos_admisibilidad": "Lista breve de anexos administrativos obligatorios",
                "plazo_entrega": "Plazos de entrega normales y URGENCIA",
                "vencimiento_canje": "Vencimiento mínimo y política de Canje/Devolución",
                "multas": "DETALLE COMPLETO de las multas por atraso (% o UTM)",
                "inadmisibilidad": "Causales clave para quedar fuera"
            }
            """
            
            bar.progress(50, text="⚡ Analizando Riesgos (Esto toma unos segundos)...")
            model = genai.GenerativeModel(modelo_activo)
            response = model.generate_content([prompt_gador, archivo_gemini])
            
            json_limpio = limpiar_respuesta_json(response.text)
            datos = json.loads(json_limpio)
            
            bar.progress(90, text="📊 Generando Excel...")
            
            st.success("✅ ¡Auditoría Completada!")
            
            # Vista Rápida
            c1, c2, c3 = st.columns(3)
            c1.error(f"🚨 **Multas:**\n{datos.get('multas')}")
            c2.warning(f"💰 **Garantías:**\n{datos.get('garantia_seriedad')}")
            c3.info(f"📦 **Cenabast:**\n{datos.get('cenabast')}")

            # Generar Excel
            df = pd.DataFrame([datos])
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                df.to_excel(writer, sheet_name='Reporte_Gador', index=False)
                workbook = writer.book
                worksheet = writer.sheets['Reporte_Gador']
                
                # Formatos
                header_fmt = workbook.add_format({'bold': True, 'bg_color': '#004481', 'font_color': 'white', 'border': 1})
                wrap_fmt = workbook.add_format({'text_wrap': True, 'valign': 'top', 'border': 1})
                risk_fmt = workbook.add_format({'bg_color': '#FFC7CE', 'text_wrap': True, 'border': 1})
                
                for col_num, value in enumerate(df.columns.values):
                    worksheet.write(0, col_num, value, header_fmt)
                    worksheet.set_column(col_num, col_num, 25, wrap_fmt)
                
                # Colorear Multas
                idx_multas = df.columns.get_loc("multas") if "multas" in df.columns else -1
                if idx_multas != -1:
                    worksheet.set_column(idx_multas, idx_multas, 40, risk_fmt)
            
            st.download_button(
                label="📥 DESCARGAR REPORTE GADOR",
                data=buffer,
                file_name=f"Auditoria_Cortex_{datos.get('id_licitacion', 'Gador')}.xlsx",
                mime="application/vnd.ms-excel"
            )
            
            bar.progress(100)
            os.remove(tmp_path)

        except Exception as e:
            st.error(f"❌ Error Técnico: {str(e)}")
            st.warning("Prueba recargando la página (F5) o sube otro PDF.")

        except Exception as e:
            st.error(f"❌ Error: {str(e)}")

