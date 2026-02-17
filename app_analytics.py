import streamlit as st
import google.generativeai as genai
import pandas as pd
import io

# --- 1. CONFIGURACIÓN DE PÁGINA (ESTILO SENTINELA) ---
st.set_page_config(
    page_title="Sentinela - Analítica Comercial",
    page_icon="📊",
    layout="wide"
)

# --- CSS PRO (Estilo Corporativo Limpio) ---
st.markdown("""
    <style>
    /* Botón Principal */
    .stButton>button {
        background-color: #2E5CB8; /* Azul Sentinela */
        color: white;
        border-radius: 8px;
        padding: 0.6rem 1.2rem;
        border: none;
        font-weight: 600;
    }
    .stButton>button:hover {
        background-color: #1F4085;
    }
    
    /* Contenedores de Métricas */
    div[data-testid="stMetricValue"] {
        font-size: 24px;
        color: #2E5CB8;
    }
    
    /* Chat Box */
    .chat-box {
        background-color: #f8f9fa;
        padding: 20px;
        border-radius: 10px;
        border-left: 5px solid #2E5CB8;
        margin-top: 20px;
        color: #333;
    }
    </style>
    """, unsafe_allow_html=True)

# --- SIDEBAR: CONFIGURACIÓN ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/4712/4712035.png", width=80) # Icono genérico de Analytics
    st.title("Cortex Analytics")
    st.markdown("**Módulo de Compras Ágiles**")
    st.markdown("---")
    st.info("Sube tu reporte semanal de licitaciones (Excel) para detectar oportunidades.")
    
    # Manejo de API KEY (Usa la misma de Secrets)
    if "GOOGLE_API_KEY" in st.secrets:
        genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
    else:
        st.error("⚠️ Falta API Key en Secrets.")

# --- TÍTULO PRINCIPAL ---
st.title("📊 Sentinela: Inteligencia de Negocios")
st.markdown("Bienvenido al módulo de análisis. Carga tus datos históricos para interrogar a **Cortex**.")

# --- CARGA DE DATOS ---
uploaded_file = st.file_uploader("📂 Subir Planilla Semanal (Excel/CSV)", type=["xlsx", "csv"])

if uploaded_file:
    try:
        # Detectar formato
        if uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)
        
        # --- DASHBOARD RÁPIDO (KPIs) ---
        st.divider()
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Registros Analizados", f"{len(df)}")
        col2.metric("Columnas Detectadas", f"{len(df.columns)}")
        # Intentamos adivinar columnas numéricas para sumar (ej: Montos)
        numeric_cols = df.select_dtypes(include=['float64', 'int64']).columns
        if len(numeric_cols) > 0:
            col3.metric("Promedio General", f"{df[numeric_cols[0]].mean():.2f}")
        
        # Vista Previa
        with st.expander("🔍 Ver Tabla de Datos Completa"):
            st.dataframe(df, use_container_width=True)

        # --- MOTOR DE INTELIGENCIA (CHAT) ---
        st.divider()
        st.subheader("🤖 Pregúntale a tus Datos")
        
        col_chat, col_img = st.columns([3, 1])
        
        with col_chat:
            pregunta = st.text_input("Ej: ¿Cuál fue el producto más caro? / ¿Qué licitaciones perdimos esta semana?", placeholder="Escribe tu consulta aquí...")
            
            if st.button("⚡ ANALIZAR DATOS") and pregunta:
                with st.spinner("Cortex está cruzando información..."):
                    try:
                        # Convertimos los datos a texto para que Gemini los lea
                        # Limitamos a las primeras 100 filas para velocidad en demo (ajustable)
                        datos_contexto = df.head(100).to_string()
                        
                        prompt = f"""
                        ERES CORTEX ANALYTICS, UN EXPERTO EN INTELIGENCIA DE NEGOCIOS Y COMPRAS PÚBLICAS.
                        
                        Tu misión es responder preguntas estratégicas basadas en los siguientes datos de licitaciones:
                        
                        --- DATOS (Muestra) ---
                        {datos_contexto}
                        -----------------------
                        
                        PREGUNTA DEL USUARIO: "{pregunta}"
                        
                        INSTRUCCIONES:
                        1. Responde de forma ejecutiva y directa.
                        2. Cita cifras exactas de la tabla.
                        3. Si detectas una tendencia (subida/bajada de precios), avísalo.
                        4. Usa formato Markdown (Negritas, Listas) para que se vea profesional.
                        """
                        
                        # Usamos Flash para respuesta rápida
                        model = genai.GenerativeModel('gemini-1.5-flash')
                        response = model.generate_content(prompt)
                        
                        st.markdown(f'<div class="chat-box">{response.text}</div>', unsafe_allow_html=True)
                        
                    except Exception as e:
                        st.error(f"Error en el análisis: {e}")
        
        with col_img:
            # Un detalle visual: Robot Analista
            st.markdown("###")
            st.markdown("###")
            st.image("https://cdn-icons-png.flaticon.com/512/6009/6009864.png", width=150, caption="Cortex Analytics")

    except Exception as e:
        st.error(f"❌ Error al leer el archivo: {e}")

else:
    # Estado inicial (Vacio)
    st.info("👆 Carga un archivo arriba para activar el Dashboard.")
    
    # Ejemplo de lo que puede hacer
    st.markdown("""
    ### 💡 ¿Qué puedes preguntar?
    * *"¿Cuál es la diferencia de precio entre mi oferta y la competencia?"*
    * *"¿Cuáles son los 5 productos con mayor rotación?"*
    * *"Dame un resumen de las licitaciones ganadas vs perdidas."*
    """)
