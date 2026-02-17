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
    st.info("Sube tu reporte 'Detalle OC' o histórico de Mercado Público.")
    
    # API KEY
    if "GOOGLE_API_KEY" in st.secrets:
        genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
    else:
        st.error("⚠️ Falta API Key en Secrets.")
        st.stop()

# --- TÍTULO ---
st.title("📊 Sentinela: Inteligencia de Negocios")
st.markdown("Bienvenido al módulo estratégico. Carga tus datos para identificar **Oportunidades de Venta y Patrones de Compra**.")

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
        
        # --- DASHBOARD DE KPI ---
        st.divider()
        st.subheader("📈 Estado General")
        col1, col2, col3, col4 = st.columns(4)
        
        col1.metric("Registros", f"{len(df):,}")
        
        # Detección inteligente de columnas para KPI
        col_monto = next((c for c in df.columns if c in ['TotalNeto', 'TotalLinea', 'Monto']), None)
        col_organismo = next((c for c in df.columns if c in ['NombreUnidad', 'NombreOrganismo', 'Organismo']), None)
        col_region = next((c for c in df.columns if c in ['RegionUnidad', 'Region']), None)
        col_producto = next((c for c in df.columns if c in ['Producto', 'NombreProducto']), None)

        if col_monto:
             total_venta = df[col_monto].sum()
             col2.metric("Monto Total Analizado", f"${total_venta:,.0f}")
        else:
             col2.metric("Monto Total", "No detectado")
             
        if col_organismo:
            top_org = df[col_organismo].value_counts().idxmax()
            col3.metric("Mayor Comprador", f"{top_org[:20]}...")
        else:
             col3.metric("Mayor Comprador", "-")

        if col_region:
            top_reg = df[col_region].value_counts().idxmax()
            col4.metric("Región Dominante", f"{top_reg}")
        else:
             col4.metric("Región", "-")

        with st.expander("🔍 Ver Tabla de Datos"):
            st.dataframe(df.head(50), use_container_width=True)

        # --- MOTOR DE INTELIGENCIA (CHAT) ---
        st.divider()
        st.subheader("🤖 Consultor Estratégico (Cortex)")
        
        col_chat, col_img = st.columns([3, 1])
        
        with col_chat:
            pregunta = st.text_input("Consulta estratégica:", placeholder="Ej: ¿Cuáles son los 5 productos más vendidos? / ¿Qué región compra más?")
            
            if st.button("⚡ ANALIZAR ESTRATEGIA") and pregunta:
                with st.spinner("Cortex está calculando estadísticas globales y analizando..."):
                    try:
                        # --- 1. INTELECTO MATEMÁTICO (Pre-Cálculo de Verdades) ---
                        # Calculamos los datos DUROS antes de pasarlos a la IA para que no alucine.
                        stats_txt = ""
                        
                        if col_producto and 'Cantidad' in df.columns and 'PrecioNeto' in df.columns:
                            # Top 5 Productos
                            top_prods = df.groupby(col_producto).agg({'Cantidad':'sum', 'PrecioNeto':'mean'}).sort_values('Cantidad', ascending=False).head(5)
                            stats_txt += f"\n[TOP 5 PRODUCTOS MÁS COMPRADOS]\n{top_prods.to_string()}\n"

                        if col_region and col_monto:
                            # Top Región
                            top_reg = df.groupby(col_region)[col_monto].sum().sort_values(ascending=False).head(3)
                            stats_txt += f"\n[TOP 3 REGIONES POR MONTO COMPRADO]\n{top_reg.to_string()}\n"

                        if col_organismo and col_monto:
                            # Top Organismo
                            top_org = df.groupby(col_organismo)[col_monto].sum().sort_values(ascending=False).head(3)
                            stats_txt += f"\n[TOP 3 ORGANISMOS COMPRADORES]\n{top_org.to_string()}\n"
                        
                        # --- 2. SELECTOR DE MODELO (Anti-Error 404) ---
                        modelos_disponibles = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
                        modelo_nombre = next((m for m in modelos_disponibles if 'flash' in m), modelos_disponibles[0])
                        model = genai.GenerativeModel(modelo_nombre)
                        
                        # --- 3. PROMPT MAESTRO (11 AÑOS DE EXPERIENCIA) ---
                        prompt = f"""
                        ERES CORTEX ANALYTICS, UN EXPERTO GERENTE COMERCIAL DE MERCADO PÚBLICO CHILE.
                        
                        Tienes acceso a dos fuentes de información:
                        1. ESTADÍSTICAS GLOBALES CALCULADAS (Datos duros de toda la base):
                        {stats_txt}
                        
                        2. MUESTRA DE DATOS DETALLADOS (Primeras 50 filas):
                        {df.head(50).to_string()}
                        
                        PREGUNTA DEL USUARIO: "{pregunta}"
                        
                        INSTRUCCIONES PARA RESPONDER:
                        - Si te preguntan por "Top", "Más vendido" o "Quién compra más", USA LAS ESTADÍSTICAS GLOBALES primero.
                        - Si te preguntan por "Precios", indica el 'PrecioNeto' promedio.
                        - Si te preguntan por "Región", cruza el dato de la Región que más compra con los productos que prefiere.
                        - FORMATO: Sé directo. Usa viñetas. Habla como un estratega ("Nicolás, los datos muestran...").
                        
                        COLUMNAS CLAVE EN TU ANÁLISIS:
                        - Organismo = '{col_organismo}'
                        - Región = '{col_region}'
                        - Producto = '{col_producto}'
                        - Precio = 'PrecioNeto'
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
