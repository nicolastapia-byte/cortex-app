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

# --- CSS PRO (Estilo Corporativo Limpio & Chat) ---
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
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        transition: all 0.3s ease;
    }
    .stButton>button:hover {
        background-color: #1F4085;
        transform: translateY(-2px);
    }
    
    /* Contenedores de Métricas */
    div[data-testid="stMetricValue"] {
        font-size: 26px;
        color: #2E5CB8;
        font-weight: bold;
    }
    
    /* Chat Box Estilizado */
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
    
    /* Headers */
    h1, h2, h3 {
        color: #1e3c72;
    }
    </style>
    """, unsafe_allow_html=True)

# --- SIDEBAR: CONFIGURACIÓN ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/4712/4712035.png", width=80) # Icono Analytics
    st.title("Cortex Analytics")
    st.markdown("**Módulo de Compras Ágiles**")
    st.markdown("---")
    st.info("Sube tu reporte de 'Búsqueda de OC' o histórico de licitaciones.")
    
    # Manejo de API KEY (Usa la misma de Secrets)
    if "GOOGLE_API_KEY" in st.secrets:
        genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
    else:
        st.error("⚠️ Falta API Key en Secrets.")
        st.stop()

# --- TÍTULO PRINCIPAL ---
st.title("📊 Sentinela: Inteligencia de Negocios")
st.markdown("Bienvenido al módulo estratégico. Carga tus datos para aplicar la **Lógica de Mercado Público (11 Años de Experiencia)**.")

# --- CARGA DE DATOS ---
uploaded_file = st.file_uploader("📂 Subir Planilla (Excel/CSV)", type=["xlsx", "csv"])

if uploaded_file:
    try:
        # Detectar formato y cargar
        if uploaded_file.name.endswith('.csv'):
            try:
                df = pd.read_csv(uploaded_file, encoding='utf-8')
            except:
                df = pd.read_csv(uploaded_file, encoding='latin-1') # Fallback común en Chile
        else:
            df = pd.read_excel(uploaded_file)
        
        # --- DASHBOARD RÁPIDO (KPIs) ---
        st.divider()
        st.subheader("📈 Estado General")
        col1, col2, col3, col4 = st.columns(4)
        
        col1.metric("Registros", f"{len(df)}")
        col2.metric("Columnas", f"{len(df.columns)}")
        
        # Intentamos detectar columnas clave automágicamente
        col_monto = next((c for c in df.columns if "monto" in c.lower() or "total" in c.lower()), None)
        col_adq = next((c for c in df.columns if "tipo" in c.lower() and "adqui" in c.lower()), "No detectada")
        
        if col_monto:
             # Limpieza básica de montos si vienen como texto
            if df[col_monto].dtype == object:
                 try:
                     promedio = df[col_monto].astype(str).str.replace(r'[$.]', '', regex=True).astype(float).mean()
                 except:
                     promedio = 0
            else:
                promedio = df[col_monto].mean()
            col3.metric("Monto Promedio", f"${promedio:,.0f}")
        else:
            col3.metric("Monto Promedio", "-")
            
        col4.metric("Tipo Adquisición", "Detectado" if col_adq != "No detectada" else "Manual")

        # Vista Previa
        with st.expander("🔍 Ver Tabla de Datos (Primeras filas)"):
            st.dataframe(df.head(50), use_container_width=True)

        # --- MOTOR DE INTELIGENCIA (CHAT ESTRATÉGICO) ---
        st.divider()
        st.subheader("🤖 Consultor Estratégico (Cortex)")
        
        col_chat, col_img = st.columns([3, 1])
        
        with col_chat:
            pregunta = st.text_input("Tu consulta estratégica:", placeholder="Ej: ¿Qué hospital está comprando más rápido? / ¿A qué precio ganó la competencia ayer?")
            
            if st.button("⚡ ANALIZAR ESTRATEGIA") and pregunta:
                with st.spinner("Cortex está aplicando las reglas de negocio (A, B, C)..."):
                    try:
                        # Convertimos los datos a texto para que Gemini los lea
                        # Limitamos a las primeras 80 filas más relevantes (o las ultimas si es temporal)
                        # Para demo usamos head, en prod idealmente filtrar por fecha.
                        datos_contexto = df.head(80).to_string()
                        
                        # --- EL CEREBRO DE LOS 11 AÑOS (PROMPT) ---
                        prompt = f"""
                        ERES CORTEX ANALYTICS, UN EXPERTO GERENTE COMERCIAL CON 11 AÑOS DE EXPERIENCIA EN MERCADO PÚBLICO CHILE.
                        Tu misión es analizar estos datos y dar consejos tácticos para ganar, no respuestas genéricas.

                        ESTRATEGIA DE ANÁLISIS (SIGUE ESTOS PASOS):
                        
                        1. IDENTIFICA EL ESCENARIO (Mira la columna '{col_adq}' o los Montos):
                        
                           ➡️ ESCENARIO 1: COMPRA ÁGIL (Menor cuantía / Velocidad)
                           - ACTITUD: Francotirador (Guerrilla).
                           - TU ANÁLISIS DEBE ENFOCARSE EN:
                             A) PRECIO GANADOR: ¿Cuál fue el precio unitario exacto de corte? (Para bajarle $1 peso si es necesario).
                             B) COMPRADOR FRECUENTE: ¿Quién está emitiendo muchas OC pequeñas? (Para ofrecerle stock inmediato).
                           - CONSEJO: "Nicolás, aquí la clave es velocidad. El precio de corte es $X."

                           ➡️ ESCENARIO 2: LICITACIÓN PÚBLICA (Gran Compra / Estrategia)
                           - ACTITUD: Ajedrecista (Guerra).
                           - TU ANÁLISIS DEBE ENFOCARSE EN:
                             A) PRECIO PROMEDIO: No busques el mínimo ridículo, busca el promedio de mercado sostenible.
                             B) VOLUMEN: ¿Quién compra cantidad real? (Monto total alto).
                             C) RIESGO/ESTRATEGIA: 
                                * ¿Siempre gana el mismo competidor ('Nombre Proveedor')? -> Advierte "Barrera de entrada alta".
                                * ¿Es un comprador difícil? -> Sugiere revisar garantías.
                                * ¿Precios depredadores? -> Advierte "Posible dumping o liquidación".

                        --- DATOS (MUESTRA) ---
                        {datos_contexto}
                        -----------------------
                        
                        PREGUNTA DEL USUARIO: "{pregunta}"
                        
                        RESPUESTA:
                        - Sé directo, usa lenguaje de negocios ("Margen", "Rotación", "Adjudicado").
                        - Usa Markdown (Negritas, Listas) para estructurar la respuesta.
                        - TERMINA CON UNA "ACCIÓN SUGERIDA" basada en tu experiencia.
                        """
                        
                        # Usamos Flash para respuesta rápida
                        model = genai.GenerativeModel('gemini-1.5-flash')
                        response = model.generate_content(prompt)
                        
                        st.markdown(f'<div class="chat-box">{response.text}</div>', unsafe_allow_html=True)
                        
                    except Exception as e:
                        st.error(f"Error en el análisis: {e}")
        
        with col_img:
            st.markdown("###")
            st.image("https://cdn-icons-png.flaticon.com/512/6009/6009864.png", width=150, caption="Modo Estratega")

    except Exception as e:
        st.error(f"❌ Error al leer el archivo: {e}")

else:
    # Estado inicial (Vacio)
    st.info("👆 Carga tu reporte de OC o Licitaciones para activar el cerebro estratégico.")
    
    st.markdown("""
    ### 💡 Estrategias Disponibles:
    * **Modo Ágil:** Detectar precios de corte y compradores impulsivos.
    * **Modo Licitación:** Analizar competencia histórica y volúmenes grandes.
    """)
