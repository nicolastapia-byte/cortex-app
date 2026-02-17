import streamlit as st
import google.generativeai as genai
import pandas as pd
import io

# --- 1. CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(
    page_title="Sentinela - Analítica Comercial",
    page_icon="📊",
    layout="wide"
)

# --- CSS PRO ---
st.markdown("""
    <style>
    .stButton>button {
        background-color: #2E5CB8;
        color: white;
        border-radius: 8px;
        padding: 0.6rem 1.2rem;
        border: none;
        font-weight: 600;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        transition: all 0.3s ease;
    }
    .stButton>button:hover {
        background-color: #1F4085;
        transform: translateY(-2px);
    }
    div[data-testid="stMetricValue"] {
        font-size: 26px;
        color: #2E5CB8;
        font-weight: bold;
    }
    .chat-box {
        background-color: #f8f9fa;
        padding: 25px;
        border-radius: 12px;
        border-left: 6px solid #2E5CB8;
        margin-top: 20px;
        color: #333;
        box-shadow: 0 2px 10px rgba(0,0,0,0.05);
        font-size: 16px;
        line-height: 1.6;
    }
    </style>
    """, unsafe_allow_html=True)

# --- SIDEBAR ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/4712/4712035.png", width=80)
    st.title("Cortex Analytics")
    st.markdown("**Módulo de Compras Ágiles**")
    st.markdown("---")
    st.info("Sube tu reporte de OC o histórico.")
    
    # API KEY
    if "GOOGLE_API_KEY" in st.secrets:
        genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
    else:
        st.error("⚠️ Falta API Key en Secrets.")
        st.stop()

# --- TÍTULO ---
st.title("📊 Sentinela: Inteligencia de Negocios")
st.markdown("Bienvenido al módulo estratégico. Carga tus datos para aplicar la **Lógica de Mercado Público (11 Años de Experiencia)**.")

# --- CARGA DATOS ---
uploaded_file = st.file_uploader("📂 Subir Planilla (Excel/CSV)", type=["xlsx", "csv"])

if uploaded_file:
    try:
        if uploaded_file.name.endswith('.csv'):
            try:
                df = pd.read_csv(uploaded_file, encoding='utf-8')
            except:
                df = pd.read_csv(uploaded_file, encoding='latin-1')
        else:
            df = pd.read_excel(uploaded_file)
        
        # --- DASHBOARD ---
        st.divider()
        st.subheader("📈 Estado General")
        col1, col2, col3, col4 = st.columns(4)
        
        col1.metric("Registros", f"{len(df)}")
        col2.metric("Columnas", f"{len(df.columns)}")
        
        # Detección inteligente de columnas
        col_monto = next((c for c in df.columns if "monto" in c.lower() or "total" in c.lower()), None)
        col_adq = next((c for c in df.columns if "tipo" in c.lower() and "adqui" in c.lower()), "No detectada")
        
        if col_monto:
            if df[col_monto].dtype == object:
                 try: promedio = df[col_monto].astype(str).str.replace(r'[$.]', '', regex=True).astype(float).mean()
                 except: promedio = 0
            else: promedio = df[col_monto].mean()
            col3.metric("Monto Promedio", f"${promedio:,.0f}")
        else:
            col3.metric("Monto Promedio", "-")
            
        col4.metric("Tipo Adquisición", "Detectado" if col_adq != "No detectada" else "Manual")

        with st.expander("🔍 Ver Tabla de Datos"):
            st.dataframe(df.head(50), use_container_width=True)

        # --- MOTOR DE INTELIGENCIA ---
        st.divider()
        st.subheader("🤖 Consultor Estratégico (Cortex)")
        
        col_chat, col_img = st.columns([3, 1])
        
        with col_chat:
            pregunta = st.text_input("Consulta estratégica:", placeholder="Ej: ¿Qué hospital compra más rápido? / ¿Precio corte competencia?")
            
            if st.button("⚡ ANALIZAR ESTRATEGIA") and pregunta:
                with st.spinner("Cortex analizando escenarios A, B y C..."):
                    try:
                        # --- SELECTOR DE MODELO INTELIGENTE (FIX 404) ---
                        # 1. Obtenemos la lista de modelos que TU cuenta permite
                        modelos_disponibles = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
                        
                        # 2. Buscamos el mejor candidato disponible (Prioridad: Flash -> Pro -> Cualquiera)
                        modelo_nombre = next((m for m in modelos_disponibles if 'flash' in m), None)
                        if not modelo_nombre:
                            modelo_nombre = next((m for m in modelos_disponibles if 'pro' in m), None)
                        if not modelo_nombre:
                            modelo_nombre = modelos_disponibles[0] # El que haya
                        
                        # 3. Informamos qué modelo se está usando (para depuración)
                        st.caption(f"🧠 Motor activo: `{modelo_nombre}`")
                        
                        # Instancia el modelo con el nombre correcto encontrado
                        model = genai.GenerativeModel(modelo_nombre)
                        # ------------------------------------------------------------

                        datos_contexto = df.head(80).to_string()
                        
                        prompt = f"""
                        ERES CORTEX ANALYTICS, UN EXPERTO GERENTE COMERCIAL CON 11 AÑOS DE EXPERIENCIA EN MERCADO PÚBLICO CHILE.
                        
                        ESTRATEGIA DE ANÁLISIS:
                        1. IDENTIFICA EL ESCENARIO (Columna '{col_adq}' o Montos):
                           ➡️ ESCENARIO 1: COMPRA ÁGIL (Velocidad)
                           - FOCO: Precio unitario exacto de corte y Comprador frecuente.
                           - CONSEJO: Velocidad y Stock.
                           ➡️ ESCENARIO 2: LICITACIÓN PÚBLICA (Estrategia)
                           - FOCO: Precio promedio de mercado, Volumen real y Riesgo (Competidor dominante).

                        --- DATOS (MUESTRA) ---
                        {datos_contexto}
                        -----------------------
                        
                        PREGUNTA: "{pregunta}"
                        
                        RESPUESTA (Directa y con Markdown):
                        """
                        
                        response = model.generate_content(prompt)
                        st.markdown(f'<div class="chat-box">{response.text}</div>', unsafe_allow_html=True)
                        
                    except Exception as e:
                        st.error(f"Error detallado: {e}")
        
        with col_img:
            st.markdown("###")
            st.image("https://cdn-icons-png.flaticon.com/512/6009/6009864.png", width=150)

    except Exception as e:
        st.error(f"❌ Error al procesar archivo. Asegúrate de que 'openpyxl' esté en requirements.txt. Detalle: {e}")
