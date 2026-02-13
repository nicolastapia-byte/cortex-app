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
    page_title="Cortex AI - Auditoría Pública",
    page_icon="🤖",
    layout="centered"
)

# --- CSS PREMIUM: ANIMACIONES REACTIVAS ---
st.markdown("""
    <style>
    /* Botón Principal Estilizado */
    .stButton>button {
        width: 100%;
        background-color: #2E5CB8;
        color: white;
        font-weight: 700;
        border-radius: 8px;
        padding: 0.8rem;
        font-size: 18px;
        border: none;
        box-shadow: 0 4px 6px rgba(0,0,0,0.2);
        transition: all 0.3s ease;
    }
    .stButton>button:hover {
        background-color: #1F4085;
        transform: translateY(-2px);
        box-shadow: 0 6px 12px rgba(0,0,0,0.3);
    }
    
    /* --- ESTADOS DEL AGENTE CORTEX (B&W) --- */
    
    /* CLASE BASE PARA EL CONTENEDOR DEL ROBOT */
    .robot-container {
        font-size: 110px;
        text-align: center;
        margin-bottom: 20px;
        /* Filtro B&W para seriedad corporativa */
        filter: grayscale(100%);
        transition: all 0.5s ease;
    }

    /* ESTADO 1: ZEN (Flotando suave en reposo) */
    .robot-zen {
        animation: float-zen 4s ease-in-out infinite;
        opacity: 0.9;
    }
    
    /* ESTADO 2: PENSANDO (Vibrando y procesando) */
    .robot-thinking {
        animation: processing-pulse 0.4s infinite alternate;
        filter: grayscale(100%) contrast(1.3); /* Más contraste al pensar */
    }

    /* ESTADO 3: ÉXITO (Salto de victoria) */
    .robot-success {
        font-size: 120px; /* Un poco más grande al celebrar */
        animation: victory-bounce 1s cubic-bezier(0.36, 0.07, 0.19, 0.97) both;
    }

    /* --- DEFINICIÓN DE LAS ANIMACIONES --- */
    @keyframes float-zen {
        0%, 100% { transform: translateY(0px); }
        50% { transform: translateY(-12px); }
    }
    
    /* Animación de "cerebro trabajando" (vibración + escala) */
    @keyframes processing-pulse {
        0% { transform: scale(1) rotate(0deg); opacity: 0.8; }
        100% { transform: scale(1.08) rotate(2deg); opacity: 1; }
    }

    /* Animación de salto de victoria */
    @keyframes victory-bounce {
        0%, 20%, 50%, 80%, 100% {transform: translateY(0);}
        40% {transform: translateY(-35px);}
        60% {transform: translateY(-20px);}
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. SIDEBAR CON AGENTE REACTIVO ---
with st.sidebar:
    # --- AQUÍ OCURRE LA MAGIA ---
    # Creamos un marcador de posición (placeholder) vacío.
    # Esto nos permite cambiar lo que hay dentro dinámicamente.
    robot_spot = st.empty()
    
    # Estado Inicial: Renderizamos al Robot Zen
    robot_spot.markdown('<div class="robot-container robot-zen">🤖</div>', unsafe_allow_html=True)
    # ---------------------------
    
    st.title("Cortex AI")
    st.markdown("**Agente de Auditoría Pública**")
    st.markdown("---")
    # Indicadores de estado más elegantes
    st.markdown("🟢 **Sistema:** Operativo")
    st.markdown("ℹ️ **Versión:** Platinum V24.0")

# --- 3. ENCABEZADO PRINCIPAL ---
st.title("🧠 Cortex: Análisis de Bases Públicas")
st.markdown("Soy **Cortex**, tu agente de IA experto en detectar **Riesgos, Multas y Glosas** en licitaciones del Estado.")

# --- 4. INPUT DE ARCHIVO ---
uploaded_file = st.file_uploader("📂 Cargar Bases Administrativas (PDF):", type=["pdf"])

# --- 5. FUNCIONES DE LIMPIEZA (Robustas) ---
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

# --- 6. LÓGICA CORE ---
if uploaded_file is not None:
    
    if st.button("⚡ EJECUTAR AUDITORÍA DE RIESGOS"):
        
        # 🔥 CAMBIO DE ESTADO 1: MODO PENSANDO 🔥
        # Reemplazamos el robot Zen por el robot Pensando (vibrando)
        robot_spot.markdown('<div class="robot-container robot-thinking">🤖</div>', unsafe_allow_html=True)
        
        status_box = st.empty()
        bar = st.progress(0)
        
        try:
            # A. CONEXIÓN
            status_box.info("🔐 Cortex: Estableciendo enlace seguro...")
            if "GOOGLE_API_KEY" in st.secrets:
                genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
            else:
                st.error("❌ Falta API Key.")
                st.stop()
            
            # B. MODELO
            try:
                modelos = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
                # Prioridad a modelos rápidos (Flash) para que el robot piense rápido
                modelo_elegido = next((m for m in modelos if 'flash' in m and '1.5' in m), None) or modelos[0]
            except:
                st.error("❌ Error de conexión AI.")
                st.stop()
            
            bar.progress(20)
            
            # C. LECTURA
            status_box.info("👁️ Cortex: Escaneando y procesando PDF...")
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
                tmp_file.write(uploaded_file.getvalue())
                tmp_path = tmp_file.name

            archivo_gemini = genai.upload_file(tmp_path)
            bar.progress(40)
            
            # D. PROMPT (CEREBRO EXPERTO)
            prompt = """
            ACTÚA COMO UN AUDITOR EXPERTO EN COMPRAS PÚBLICAS Y LICITACIONES.
            Tu objetivo es proteger al oferente detectando RIESGOS, MULTAS y ERRORES FORMALES.
            
            PROTOCOLOS DE REVISIÓN (ESTÁNDAR EXPERTO):
            1. PLAZOS Y FECHAS: No extraigas solo fechas. Busca los "PLAZOS" (ej: "30 días corridos desde la adjudicación").
            2. VIGENCIA DE LA OFERTA: Identifica la vigencia exigida. Si la oferta tiene MENOR vigencia a la solicitada, márcalo como CAUSAL DE RECHAZO.
            3. GLOSA DE GARANTÍA: Extrae el TEXTO LITERAL (Glosa) que exigen las bases para la boleta de garantía. Si hay una glosa específica, debes copiarla tal cual.
            4. INADMISIBILIDAD: Relaciona errores en la Glosa, Vigencia insuficiente o falta de documentos como causales críticas.

            Extrae en JSON ESTRICTO (sin saltos de línea en valores):
            {
                "id_licitacion": "ID Propuesta",
                "fechas": "Plazos claves (Días hábiles/corridos, Apertura)",
                "productos": "Resumen Productos/Servicios",
                "cenabast": "Mención a Intermediación/Faltante (SI/NO)",
                "presupuesto": "Monto Total Estimado",
                "garantia_seriedad": "Monto, VIGENCIA y GLOSA LITERAL REQUERIDA",
                "garantia_cumplimiento": "Monto, VIGENCIA y GLOSA LITERAL REQUERIDA",
                "duracion_contrato": "Vigencia del contrato",
                "reajuste": "Cláusula de Reajuste (IPC/Otro)",
                "suscripcion_contrato": "Plazo para firma",
                "plazo_entrega": "Plazos de entrega y Multas por atraso",
                "vencimiento_canje": "Política de Canje/Vencimiento",
                "multas": "Resumen de Multas y Sanciones",
                "inadmisibilidad": "CAUSALES DE RECHAZO (Vigencia, Glosa, Formatos)"
            }
            """
            
            status_box.info(f"⚡ Cortex: Auditando cumplimiento normativo (Motor {modelo_elegido.split('/')[-1]})...")
            model = genai.GenerativeModel(modelo_elegido)
            response = model.generate_content([prompt, archivo_gemini])
            
            bar.progress(85)
            
            # E. REPORTE
            status_box.info("📝 Cortex: Generando reporte ejecutivo...")
            datos = limpiar_y_reparar_json(response.text)
            
            bar.progress(100)
            status_box.success("✅ ¡Auditoría Finalizada con Éxito!")
            
            # 🎉 CAMBIO DE ESTADO 2: MODO ÉXITO 🎉
            # Cambiamos al robot por el emoji "Cool" y aplica el salto de victoria
            robot_spot.markdown('<div class="robot-container robot-success">😎</div>', unsafe_allow_html=True)
            
            # DASHBOARD
            with st.container():
                c1, c2 = st.columns(2)
                with c1:
                    st.error(f"🚫 **Riesgos de Rechazo:**\n\n{datos.get('inadmisibilidad', '-')}")
                with c2:
                    st.warning(f"⚠️ **Garantías y Glosas:**\n\n{datos.get('garantia_seriedad', '-')}")
            
            # F. EXCEL
            df = pd.DataFrame([datos])
            cols_deseadas = ['id_licitacion', 'inadmisibilidad', 'fechas', 'garantia_seriedad', 'garantia_cumplimiento', 'multas', 'cenabast', 'productos']
            cols_finales = [c for c in cols_deseadas if c in df.columns] + [c for c in df.columns if c not in cols_deseadas]
            df = df[cols_finales]

            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                df.to_excel(writer, sheet_name='Auditoria_Cortex', index=False)
                workbook = writer.book
                worksheet = writer.sheets['Auditoria_Cortex']
                
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
            filename = f"Reporte_Cortex_{datos.get('id_licitacion', 'Licitacion')}.xlsx"
            
            st.download_button(
                label="📥 DESCARGAR REPORTE CORTEX",
                data=buffer,
                file_name=filename,
                mime="application/vnd.ms-excel"
            )
            os.remove(tmp_path)
            
            # 🔄 RESET AUTOMÁTICO
            # Esperamos 4 segundos para disfrutar el éxito y volvemos al estado Zen
            time.sleep(4)
            robot_spot.markdown('<div class="robot-container robot-zen">🤖</div>', unsafe_allow_html=True)

        except Exception as e:
            st.error(f"❌ Error del Sistema: {e}")
            # Si algo falla, el robot se marea
            robot_spot.markdown('<div class="robot-container robot-zen">😵</div>', unsafe_allow_html=True)
