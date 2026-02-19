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
    page_title="Cortex AI - Acceso Seguro",
    page_icon="🔒",
    layout="centered"
)

# --- CSS QUANTUM (Animaciones Premium) ---
st.markdown("""
    <style>
    .stButton>button {
        width: 100%;
        background: linear-gradient(45deg, #1e3c72, #2a5298);
        color: white;
        font-weight: 700;
        border-radius: 10px;
        padding: 0.8rem;
        font-size: 18px;
        border: none;
        box-shadow: 0 4px 15px rgba(0,0,0,0.3);
        transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
    }
    .stButton>button:hover {
        transform: translateY(-3px) scale(1.02);
        box-shadow: 0 8px 25px rgba(42, 82, 152, 0.6);
    }
    /* Estilos Login */
    .login-container {
        padding: 2rem;
        border-radius: 10px;
        background-color: #f0f2f6;
        text-align: center;
        margin-top: 50px;
    }
    
    /* Animaciones Robot */
    .robot-container {
        font-size: 120px;
        text-align: center;
        margin-bottom: 25px;
        filter: grayscale(100%) drop-shadow(0 10px 10px rgba(0,0,0,0.5));
        transition: all 0.5s ease;
        perspective: 1000px;
    }
    .robot-zen { animation: float-breathe 4s ease-in-out infinite; }
    .robot-thinking {
        font-size: 125px;
        filter: grayscale(100%) contrast(1.5) drop-shadow(0 0 15px rgba(255,255,255,0.8));
        animation: glitch-skew 0.3s cubic-bezier(0.25, 0.46, 0.45, 0.94) infinite both;
    }
    .robot-success {
        font-size: 130px;
        filter: grayscale(100%);
        animation: backflip-victory 1.2s cubic-bezier(0.68, -0.55, 0.265, 1.55) forwards;
    }
    @keyframes float-breathe {
        0%, 100% { transform: translateY(0); filter: grayscale(100%) drop-shadow(0 10px 5px rgba(0,0,0,0.3)); }
        50% { transform: translateY(-15px); filter: grayscale(100%) drop-shadow(0 25px 15px rgba(0,0,0,0.1)); }
    }
    @keyframes glitch-skew {
        0% { transform: translate(0); }
        20% { transform: translate(-3px, 3px) skewX(5deg); }
        40% { transform: translate(-3px, -3px) skewX(-5deg); }
        60% { transform: translate(3px, 3px) skewX(5deg); }
        80% { transform: translate(3px, -3px) skewX(-5deg); }
        100% { transform: translate(0); }
    }
    @keyframes backflip-victory {
        0% { transform: scale(1) rotateY(0deg); }
        50% { transform: scale(0.5) rotateY(180deg); }
        100% { transform: scale(1.1) rotateY(360deg); }
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. SISTEMA DE LOGIN DE SEGURIDAD ---
def check_password():
    """Retorna True si el usuario ingresó la clave correcta."""
    
    # Si no hay clave configurada en secrets, dejamos pasar (Modo Desarrollo)
    if "PASSWORD_ACCESO" not in st.secrets:
        st.warning("⚠️ ADVERTENCIA DE SEGURIDAD: No se ha configurado 'PASSWORD_ACCESO' en Secrets.")
        return True

    if "password_correct" not in st.session_state:
        st.session_state.password_correct = False

    if st.session_state.password_correct:
        return True

    # Pantalla de Login
    st.markdown("<h1 style='text-align: center;'>🔒 Acceso Restringido</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center;'>Sistema Cortex AI - Solo Personal Autorizado</p>", unsafe_allow_html=True)
    
    password_input = st.text_input("Ingrese Credencial de Acceso:", type="password")
    
    if st.button("🔐 INICIAR SESIÓN"):
        if password_input == st.secrets["PASSWORD_ACCESO"]:
            st.session_state.password_correct = True
            st.rerun()
        else:
            st.error("❌ Credencial Incorrecta. Acceso Denegado.")
    
    return False

if not check_password():
    st.stop()  # Detiene la ejecución si no hay login

# --- 3. APLICACIÓN CORTEX (Solo carga si pasó el login) ---

# --- SIDEBAR ---
with st.sidebar:
    robot_spot = st.empty()
    robot_spot.markdown('<div class="robot-container robot-zen">🤖</div>', unsafe_allow_html=True)
    st.title("Cortex AI")
    st.markdown("**Enterprise Edition**")
    st.markdown("---")
    st.success("🟢 **Acceso:** Seguro (SSL)")
    st.info("🧬 **Versión:** Secure V30.0")
    
    if st.button("🚪 CERRAR SESIÓN"):
        st.session_state.password_correct = False
        st.rerun()

# --- ENCABEZADO ---
st.title("🧠 Cortex: Auditoría Matriz 24")
st.markdown("Soy **Cortex**, agente para analizar bases de manera dedicada.")

# --- INPUT ---
uploaded_file = st.file_uploader("📂 Cargar Bases (PDF):", type=["pdf"])

# --- FUNCIONES ---
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
        except: return {}

# --- LÓGICA ---
if uploaded_file is not None:
    
    if st.button("⚡ GENERAR MATRIZ 24 COLUMNAS"):
        
        # ANIMACIÓN THINKING
        robot_spot.markdown('<div class="robot-container robot-thinking">⚡</div>', unsafe_allow_html=True)
        status_box = st.empty()
        bar = st.progress(0)
        
        archivo_gemini = None 
        
        try:
            # A. CONEXIÓN DIRECTA (AQUÍ ESTÁ LA CORRECCIÓN)
            status_box.info("🔐 Cortex: Conectando motor AI...")
            if "GOOGLE_API_KEY" in st.secrets:
                genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
            else:
                st.error("❌ Falta API Key.")
                st.stop()
            
            # Asignamos el modelo de forma directa y segura
            modelo_elegido = 'gemini-2.5-flash'
            
            bar.progress(20)
            
            # C. LECTURA Y SUBIDA
            status_box.info("👁️ Cortex: Procesando documento seguro...")
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
                tmp_file.write(uploaded_file.getvalue())
                tmp_path = tmp_file.name
            
            archivo_gemini = genai.upload_file(tmp_path)
            bar.progress(40)
            
            # D. PROMPT (24 PUNTOS)
            prompt = """
            ACTÚA COMO UN AUDITOR EXPERTO EN LICITACIONES PÚBLICAS.
            Tu tarea es extraer INFORMACIÓN EXACTA para llenar una matriz de 24 columnas.
            Si un dato no aparece, responde explícitamente "NO INDICA".
            
            Genera un JSON con las siguientes claves (c01 a c24):
            1. "c01": ID Licitación.
            2. "c02": Fecha preguntas y cierre.
            3. "c03": Plazos licitación.
            4. "c04": Productos ofertados (Principios activos).
            5. "c05": Presupuesto institución.
            6. "c06": Boletas Garantía (Monto/Glosa).
            7. "c07": Duración contrato.
            8. "c08": Vigencia mínima propuesta.
            9. "c09": Reajuste (SI/NO).
            10. "c10": Suscripción contrato (SI/NO).
            11. "c11": Anexos admisibilidad.
            12. "c12": Pauta evaluativa.
            13. "c13": Requisitos administrativos.
            14. "c14": Requisitos técnicos.
            15. "c15": Requisitos económicos.
            16. "c16": Plazo entrega (inc. emergencia).
            17. "c17": Monto mínimo.
            18. "c18": Faltante Cenabast (SI/NO).
            19. "c19": Glosa Textual Garantía.
            20. "c20": Vencimiento mínimo ofertar.
            21. "c21": Canje y condiciones.
            22. "c22": Causales inadmisibilidad.
            23. "c23": Formato experiencia (SI/NO).
            24. "c24": Multas asociadas.
            """
            
            status_box.info(f"⚡ Cortex: Auditando cumplimiento normativo...")
            model = genai.GenerativeModel(modelo_elegido)
            response = model.generate_content([prompt, archivo_gemini])
            
            bar.progress(85)
            
            # E. PROCESAMIENTO
            status_box.info("📝 Cortex: Estructurando reporte blindado...")
            datos_raw = limpiar_y_reparar_json(response.text)
            
            # MAPA DE 24 COLUMNAS
            mapa_columnas = {
                "c01": "1. ID", "c02": "2. Fecha preguntas, fechas de cierre", "c03": "3. Plazos de la licitación",
                "c04": "4. Productos ofertados", "c05": "5. Presupuesto institución", "c06": "6. Boleta de garantía",
                "c07": "7. Duración de la licitación", "c08": "8. Vigencia mínima de la propuesta", "c09": "9. Si tiene reajuste la licitación",
                "c10": "10. Hay suscripción de contrato", "c11": "11. Anexos de admisibilidad", "c12": "12. Pauta evaluativa",
                "c13": "13. Requisitos administrativos", "c14": "14. Requisitos técnicos", "c15": "15. Requisitos económicos",
                "c16": "16. Plazo de entrega (inc. emergencia)", "c17": "17. Monto mínimo", "c18": "18. Si es faltante Cenabast",
                "c19": "19. Detección de glosa a ofertar", "c20": "20. Vencimiento mínimo a ofertar", "c21": "21. Canje y sus condiciones",
                "c22": "22. Causales de inadmisibilidad", "c23": "23. Solicita formato de experiencia", "c24": "24. Multas asociadas"
            }
            
            datos_finales = {}
            for clave_json, titulo_excel in mapa_columnas.items():
                datos_finales[titulo_excel] = datos_raw.get(clave_json, "No detectado")
            
            bar.progress(100)
            status_box.success("✅ Matriz Generada.")
            
            # ANIMACIÓN VICTORIA
            robot_spot.markdown('<div class="robot-container robot-success">😎</div>', unsafe_allow_html=True)
            
            # DASHBOARD
            with st.container():
                c1, c2 = st.columns(2)
                with c1:
                    st.error(f"🚫 **Inadmisibilidad:**\n\n{datos_finales['22. Causales de inadmisibilidad']}")
                with c2:
                    st.warning(f"⚠️ **Garantías:**\n\n{datos_finales['19. Detección de glosa a ofertar']}")
            
            # F. EXCEL
            df = pd.DataFrame([datos_finales])
            columnas_ordenadas = list(mapa_columnas.values())
            df = df[columnas_ordenadas]

            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                df.to_excel(writer, sheet_name='Matriz_Cortex', index=False)
                workbook = writer.book
                worksheet = writer.sheets['Matriz_Cortex']
                fmt_header = workbook.add_format({'bold': True, 'bg_color': '#1e3c72', 'font_color': 'white', 'border': 1, 'align': 'center', 'valign': 'vcenter', 'text_wrap': True})
                fmt_body = workbook.add_format({'text_wrap': True, 'border': 1, 'valign': 'top'})
                worksheet.set_row(0, 50)
                for col_num, value in enumerate(df.columns.values):
                    worksheet.write(0, col_num, str(value), fmt_header)
                    width = 40 if "inadmisibilidad" in str(value).lower() else 25
                    worksheet.set_column(col_num, col_num, width, fmt_body)

            st.divider()
            filename = f"Reporte_Cortex_24P_{datos_finales.get('1. ID', 'General')}.xlsx"
            st.download_button(
                label="📥 DESCARGAR REPORTE",
                data=buffer,
                file_name=filename,
                mime="application/vnd.ms-excel"
            )
            
            # === AUTO-LIMPIEZA ===
            if archivo_gemini:
                archivo_gemini.delete()
            os.remove(tmp_path)
            
            time.sleep(4)
            robot_spot.markdown('<div class="robot-container robot-zen">🤖</div>', unsafe_allow_html=True)

        except Exception as e:
            st.error(f"❌ Error en el proceso: {e}")
            robot_spot.markdown('<div class="robot-container robot-zen">😵</div>', unsafe_allow_html=True)
