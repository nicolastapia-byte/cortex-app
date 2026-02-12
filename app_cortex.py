import streamlit as st
import google.generativeai as genai
import pandas as pd
import json
import re
import io
import tempfile
import os

# --- 1. CONFIGURACIÓN VISUAL CORPORATIVA ---
st.set_page_config(
    page_title="Sentinela x Gador - Auditoría",
    page_icon="🛡️", # Ícono de escudo profesional
    layout="centered"
)

# Estilos CSS para identidad corporativa Gador (Azul Institucional)
st.markdown("""
    <style>
    .stButton>button {
        width: 100%;
        background-color: #004481; /* Azul Gador */
        color: white;
        font-weight: 600; /* Semi-bold para look ejecutivo */
        border-radius: 6px;
        padding: 0.7rem;
        font-size: 16px;
        border: none;
        transition: background-color 0.3s;
    }
    .stButton>button:hover {
        background-color: #003366; /* Azul más oscuro al pasar el mouse */
    }
    /* Personalizar la barra de progreso al color corporativo */
    .stProgress > div > div > div > div {
        background-color: #004481;
    }
    /* Ajuste de alertas */
    .stAlert {
        border-radius: 8px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. SIDEBAR (PANEL DE CONTROL) ---
with st.sidebar:
    # Usamos un ícono médico/profesional como logo
    st.image("https://cdn-icons-png.flaticon.com/512/2382/2382461.png", width=80)
    st.title("Gador Farma")
    st.markdown("**División Licitaciones**")
    st.success("✅ Sistema Blindado Activo")
    st.divider()
    st.info("ℹ️ Versión: Enterprise V10.0")
    st.caption("Powered by Sentinela AI")

# --- 3. ENCABEZADO PRINCIPAL ---
st.title("🛡️ Centro de Auditoría de Licitaciones")
st.markdown("""
Sistema de inteligencia artificial para la detección temprana de **Riesgos Financieros y Operativos** en Bases Administrativas Públicas.

**Foco del Análisis:**
* 🚨 **Matriz de Multas y Sanciones**
* 💰 **Requisitos de Garantías (Seriedad/Fiel Cumplimiento)**
* 📦 **Logística Crítica (Cenabast, Canjes, Urgencias)**
""")

st.divider()

# --- 4. INPUT DE DOCUMENTO ---
uploaded_file = st.file_uploader("📂 Cargue las Bases Administrativas (PDF) para iniciar protocolo:", type=["pdf"])

# --- 5. FUNCIONES AUXILIARES ---
def limpiar_json(texto):
    """Limpia la respuesta de la IA para obtener un JSON válido."""
    texto = re.sub(r'```json', '', texto)
    texto = re.sub(r'```', '', texto)
    inicio = texto.find('{')
    fin = texto.rfind('}') + 1
    if inicio != -1 and fin != 0:
        return texto[inicio:fin]
    return "{}"

# --- 6. LÓGICA CENTRAL DEL PROCESO ---
if uploaded_file is not None:
    
    st.write("") # Espacio visual
    if st.button("⚡ EJECUTAR ANÁLISIS DE RIESGO AHORA"):
        
        # Componentes de estado
        status_box = st.empty()
        progress_bar = st.progress(0)
        
        try:
            # --- FASE 1: INICIALIZACIÓN Y SEGURIDAD ---
            status_box.info("🔄 Iniciando protocolo de seguridad y conexión...")
            if "GOOGLE_API_KEY" in st.secrets:
                api_key = st.secrets["GOOGLE_API_KEY"]
            else:
                st.error("❌ Error Crítico: Credenciales de API no detectadas en Secrets.")
                st.stop()
                
            genai.configure(api_key=api_key)
            progress_bar.progress(10)
            
            # --- FASE 2: SELECCIÓN DE MOTOR IA (BLINDADO) ---
            status_box.info("📡 Verificando disponibilidad de motores neuronales...")
            modelos_disponibles = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
            
            # Priorización estratégica de modelos: Flash > Pro > Fallback
            modelo_elegido = None
            for m in modelos_disponibles:
                if 'flash' in m and '1.5' in m:
                    modelo_elegido = m
                    break
            if not modelo_elegido:
                 for m in modelos_disponibles:
                    if 'pro' in m and '1.5' in m:
                        modelo_elegido = m
                        break
            if not modelo_elegido:
                modelo_elegido = modelos_disponibles[0] if modelos_disponibles else None
            
            if not modelo_elegido:
                st.error("❌ Error de Servicio: No se encontraron modelos de IA disponibles en la cuenta asociada.")
                st.stop()
            
            progress_bar.progress(25)
                
            # --- FASE 3: PROCESAMIENTO DEL DOCUMENTO ---
            status_box.info("📄 Procesando documento PDF y extrayendo contenido vectorial...")
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
                tmp_file.write(uploaded_file.getvalue())
                tmp_path = tmp_file.name

            archivo_gemini = genai.upload_file(tmp_path)
            progress_bar.progress(40)
            
            # --- FASE 4: ANÁLISIS ESTRATÉGICO (PROMPT GADOR) ---
            prompt = """
            ACTÚA COMO GERENTE DE LICITACIONES DE GADOR FARMA.
            Realiza una auditoría exhaustiva del PDF y extrae los datos en un JSON ESTRICTO:
            {
                "id_licitacion": "ID Propuesta",
                "fechas": "Fechas Clave (Apertura/Cierre)",
                "productos": "Principios Activos y Glosas Requeridas",
                "cenabast": "SI/NO (Referencia a Faltante o Intermediación)",
                "presupuesto": "Presupuesto Estimado Total",
                "garantia_seriedad": "Detalle (Monto, %, Vigencia, Tipo)",
                "garantia_cumplimiento": "Detalle (Monto, %, Vigencia, Tipo)",
                "duracion_contrato": "Vigencia del Contrato",
                "reajuste": "Cláusula de Reajuste (IPC u otro)",
                "suscripcion_contrato": "Requisito de Firma (SI/NO)",
                "plazo_entrega": "Plazos Normales y Condiciones de Urgencia",
                "vencimiento_canje": "Política de Vencimiento Mínimo y Canje",
                "multas": "MATRIZ DETALLADA de Multas y Sanciones",
                "inadmisibilidad": "Causales Críticas de Rechazo"
            }
            """
            
            status_box.info(f"🧠 Ejecutando análisis de riesgos con motor {modelo_elegido}...")
            model = genai.GenerativeModel(modelo_elegido)
            response = model.generate_content([prompt, archivo_gemini])
            
            progress_bar.progress(75)
            
            # --- FASE 5: GENERACIÓN DE REPORTE EJECUTIVO ---
            status_box.info("📊 Formateando Reporte Ejecutivo y aplicando reglas de negocio...")
            
            # Limpieza y estructuración de datos
            json_str = limpiar_json(response.text)
            datos = json.loads(json_str)
            
            # Finalización del proceso visual
            progress_bar.progress(100)
            status_box.empty() # Limpiar mensajes de estado
            
            st.success("✅ Análisis Finalizado. Reporte listo para revisión.")
            
            # --- DASHBOARD DE RESULTADOS PRELIMINARES ---
            with st.container():
                c1, c2 = st.columns(2)
                with c1:
                    st.error(f"🚨 **Análisis de Multas:**\n\n{datos.get('multas', 'Sin información')}")
                with c2:
                    st.info(f"📦 **Logística y Cenabast:**\n\nCanje: {datos.get('vencimiento_canje')}\n\nCenabast: {datos.get('cenabast')}")
            
            # --- CONSTRUCCIÓN DEL EXCEL PERFECTO ---
            df = pd.DataFrame([datos])
            
            # Ordenamiento estratégico de columnas
            cols_orden = ['id_licitacion', 'fechas', 'productos', 'multas', 'garantia_seriedad', 'garantia_cumplimiento', 'cenabast', 'presupuesto']
            cols_finales = [c for c in cols_orden if c in df.columns] + [c for c in df.columns if c not in cols_orden]
            df = df[cols_finales]

            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                df.to_excel(writer, sheet_name='Auditoria_Gador', index=False)
                workbook = writer.book
                worksheet = writer.sheets['Auditoria_Gador']
                
                # --- DEFINICIÓN DE ESTILOS CORPORATIVOS ---
                # Encabezado Azul Gador
                fmt_header = workbook.add_format({'bold': True, 'bg_color': '#004481', 'font_color': 'white', 'border': 1, 'align': 'center', 'valign': 'vcenter', 'text_wrap': True})
                # Texto Normal
                fmt_normal = workbook.add_format({'text_wrap': True, 'valign': 'top', 'border': 1})
                # Alerta Roja (Riesgos)
                fmt_risk = workbook.add_format({'bg_color': '#FFC7CE', 'font_color': '#9C0006', 'text_wrap': True, 'valign': 'top', 'border': 1, 'bold': True})
                # Énfasis Azul (Productos/Logística)
                fmt_info = workbook.add_format({'bg_color': '#D9E1F2', 'text_wrap': True, 'valign': 'top', 'border': 1})
                
                # Aplicación de estilos por columna
                worksheet.set_row(0, 30) # Altura del encabezado
                
                for col_num, value in enumerate(df.columns.values):
                    # Escribir encabezado formateado
                    header_text = value.replace('_', ' ').title()
                    worksheet.write(0, col_num, header_text, fmt_header)
                    
                    # Lógica de coloreado condicional
                    col_name = value.lower()
                    if 'multas' in col_name or 'garantia' in col_name or 'inadmisibilidad' in col_name:
                        worksheet.set_column(col_num, col_num, 35, fmt_risk) # Zona de Riesgo
                    elif 'productos' in col_name or 'cenabast' in col_name or 'canje' in col_name:
                        worksheet.set_column(col_num, col_num, 40, fmt_info) # Zona Operativa
                    else:
                        worksheet.set_column(col_num, col_num, 22, fmt_normal) # Zona General

            # --- BOTÓN DE DESCARGA FINAL ---
            st.divider()
            filename_final = f"Reporte_Auditoria_{datos.get('id_licitacion', 'Gador')}.xlsx".replace('/', '-')
            
            st.download_button(
                label="📥 DESCARGAR REPORTE EJECUTIVO (EXCEL)",
                data=buffer,
                file_name=filename_final,
                mime="application/vnd.ms-excel"
            )
            
            # Limpieza de archivos temporales
            os.remove(tmp_path)

        except Exception as e:
            status_box.empty()
            progress_bar.empty()
            st.error(f"❌ Error en el Protocolo: {str(e)}")
            st.warning("Por favor, verifique el archivo PDF o intente nuevamente.")
