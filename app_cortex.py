import streamlit as st
import google.generativeai as genai
import pandas as pd
import json
import re
import io
import tempfile
import os

# --- 1. CONFIGURACIÓN DE PÁGINA (OBLIGATORIO PRIMERO) ---
st.set_page_config(
    page_title="Cortex AI - Gador",
    page_icon="💊",
    layout="centered"
)

# --- 2. ESTILOS VISUALES (LOOK GADOR) ---
st.markdown("""
    <style>
    .stButton>button {
        width: 100%;
        background-color: #004481; /* Azul Gador */
        color: white;
        font-weight: bold;
        border-radius: 8px;
        padding: 0.5rem;
    }
    .stAlert {
        border-radius: 8px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 3. SIDEBAR (CONFIGURACIÓN) ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/3063/3063822.png", width=60)
    st.title("⚙️ Configuración")
    st.markdown("**Sistema Sentinela x Gador**")
    
    # Campo para la API KEY (Clave de Google)
    api_key_input = st.text_input("🔑 Google API Key", type="password")
    
    st.divider()
    st.info("ℹ️ Versión: Gador V3.0 (Full Farma)")

# --- 4. ENCABEZADO PRINCIPAL ---
st.title("💊 Cortex AI: Auditoría de Licitaciones")
st.markdown("""
Esta herramienta audita Bases Administrativas buscando **Riesgos Críticos** para Gador:
* 🚨 **Multas y Sanciones**
* 💰 **Garantías (Seriedad/Cumplimiento)**
* 📦 **Faltantes Cenabast y Canjes**
""")

# --- 5. SUBIDA DE ARCHIVO ---
uploaded_file = st.file_uploader("📂 Sube las Bases (PDF) aquí:", type=["pdf"])

# --- 6. FUNCIÓN DE LIMPIEZA DE JSON ---
def limpiar_respuesta_json(texto):
    # Eliminar bloques de código markdown
    texto = re.sub(r'```json', '', texto)
    texto = re.sub(r'```', '', texto)
    # Buscar el primer { y el último }
    inicio = texto.find('{')
    fin = texto.rfind('}') + 1
    if inicio != -1 and fin != 0:
        return texto[inicio:fin]
    return "{}" # Retorno seguro si falla

# --- 7. LÓGICA DE PROCESAMIENTO ---
if uploaded_file is not None:
    
    # Verificación de API Key
    if not api_key_input:
        st.warning("⚠️ Por favor, ingresa tu API Key en el menú de la izquierda para comenzar.")
        st.stop()

    if st.button("⚡ AUDITAR DOCUMENTO AHORA"):
        
        bar = st.progress(0, text="Iniciando motores...")
        
        try:
            # A. Configurar Google Gemini
            genai.configure(api_key=api_key_input)
            
            # B. Guardar PDF temporalmente (necesario para enviarlo a Google)
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
                tmp_file.write(uploaded_file.getvalue())
                tmp_path = tmp_file.name

            bar.progress(20, text="🧠 Leyendo PDF con Visión Artificial...")
            
            # C. Subir archivo a la nube de Google
            archivo_gemini = genai.upload_file(tmp_path)
            
            # D. El Prompt "GADOR" (Los 24 Puntos Críticos)
            prompt_gador = """
            ACTÚA COMO GERENTE DE LICITACIONES DE UN LABORATORIO FARMACÉUTICO (GADOR).
            Analiza este PDF de bases de licitación y extrae los siguientes datos críticos.
            Si un dato no aparece, responde "NO INDICA".

            EXTRAE LA INFORMACIÓN EN FORMATO JSON ESTRICTO (sin texto extra):

            {
                "id_licitacion": "ID o Número de la propuesta",
                "fechas": "Fecha de preguntas y Fecha de Cierre/Apertura",
                "productos": "Lista de PRINCIPIOS ACTIVOS y GLOSAS solicitadas (Solo Fármacos)",
                "cenabast": "Indica SI/NO si menciona 'Faltante Cenabast' o intermediación",
                "presupuesto": "Monto total estimado disponible",
                "garantia_seriedad": "Monto, % y vigencia de la Seriedad de la Oferta",
                "garantia_cumplimiento": "Monto, % y vigencia del Fiel Cumplimiento",
                "duracion_contrato": "Duración en meses/años",
                "vigencia_oferta": "Tiempo mínimo de vigencia de la oferta",
                "reajuste": "Indica SI/NO si hay cláusula de reajuste (IPC)",
                "suscripcion_contrato": "Indica SI/NO requiere firma de contrato",
                "anexos_admisibilidad": "Lista breve de anexos administrativos obligatorios",
                "pauta_evaluacion": "Resumen de ponderaciones (Precio, Plazo, Técnica)",
                "requisitos_tecnicos": "Resumen breve de requisitos técnicos",
                "plazo_entrega": "Plazos de entrega normales y URGENCIA",
                "monto_minimo": "Monto mínimo de despacho (si existe)",
                "vencimiento_canje": "Vencimiento mínimo (ej: 18 meses) y política de Canje/Devolución",
                "multas": "DETALLE COMPLETO de las multas por atraso (% o UTM)",
                "inadmisibilidad": "Causales clave para quedar fuera",
                "experiencia": "Requisitos de experiencia previa"
            }
            """
            
            bar.progress(50, text="⚡ Analizando Riesgos Legales y Financieros...")
            
            # E. Generar Respuesta
            model = genai.GenerativeModel("gemini-1.5-flash")
            response = model.generate_content([prompt_gador, archivo_gemini])
            
            # F. Limpiar y Convertir a Datos
            json_limpio = limpiar_respuesta_json(response.text)
            datos = json.loads(json_limpio)
            
            bar.progress(90, text="📊 Generando Excel de Auditoría...")
            
            # G. Mostrar Resultados en Pantalla (Resumen Ejecutivo)
            st.success("✅ ¡Auditoría Completada Exitosamente!")
            
            c1, c2, c3 = st.columns(3)
            c1.error(f"🚨 **Multas:**\n{datos.get('multas', 'No detectadas')}")
            c2.warning(f"💰 **Garantías:**\nSeriedad: {datos.get('garantia_seriedad')}\nCumplimiento: {datos.get('garantia_cumplimiento')}")
            c3.info(f"📦 **Cenabast/Canje:**\nCenabast: {datos.get('cenabast')}\nCanje: {datos.get('vencimiento_canje')}")

            # H. Crear Excel para Descargar
            df = pd.DataFrame([datos])
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                df.to_excel(writer, sheet_name='Reporte_Gador', index=False)
                workbook = writer.book
                worksheet = writer.sheets['Reporte_Gador']
                
                # Formatos de Excel
                fmt_header = workbook.add_format({'bold': True, 'bg_color': '#004481', 'font_color': 'white', 'border': 1})
                fmt_wrap = workbook.add_format({'text_wrap': True, 'valign': 'top', 'border': 1})
                fmt_risk = workbook.add_format({'bg_color': '#FFC7CE', 'text_wrap': True, 'border': 1}) # Rojo Riesgo
                
                # Aplicar estilos
                for col_num, value in enumerate(df.columns.values):
                    worksheet.write(0, col_num, value, fmt_header)
                    worksheet.set_column(col_num, col_num, 25, fmt_wrap)
                
                # Resaltar Columnas de Riesgo
                col_indices = {col: i for i, col in enumerate(df.columns)}
                if 'multas' in col_indices:
                    worksheet.set_column(col_indices['multas'], col_indices['multas'], 40, fmt_risk)
                if 'garantia_cumplimiento' in col_indices:
                    worksheet.set_column(col_indices['garantia_cumplimiento'], col_indices['garantia_cumplimiento'], 35, fmt_risk)

            # I. Botón de Descarga
            st.download_button(
                label="📥 DESCARGAR REPORTE EXCEL OFICIAL",
                data=buffer,
                file_name=f"Auditoria_Cortex_{datos.get('id_licitacion', 'Gador')}.xlsx",
                mime="application/vnd.ms-excel"
            )
            
            bar.progress(100)
            
            # J. Limpieza final
            os.remove(tmp_path)

        except Exception as e:
            st.error(f"❌ Error Técnico: {str(e)}")
            st.info("Intenta recargar la página o verifica que el PDF no esté dañado.")

