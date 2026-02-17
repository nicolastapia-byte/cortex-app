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

# --- FUNCIONES AUXILIARES ---
def detectar_columna_con_datos(df, posibles_nombres):
    """Busca la primera columna que exista Y que tenga datos reales (no solo vacíos)."""
    for col in df.columns:
        if col in posibles_nombres:
            # Verifica si tiene al menos un dato no nulo
            if df[col].notna().sum() > 0:
                return col
    return None

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
        
        # --- DASHBOARD DE KPI (CON PROTECCIÓN DE ERRORES) ---
        st.divider()
        st.subheader("📈 Estado General")
        col1, col2, col3, col4 = st.columns(4)
        
        col1.metric("Registros", f"{len(df):,}")
        
        # Detección inteligente de columnas CON VALIDACIÓN DE DATOS
        col_monto = detectar_columna_con_datos(df, ['TotalNeto', 'TotalLinea', 'Monto', 'Total'])
        # Aquí priorizamos NombreUnidad porque NombreOrganismo suele venir vacío en CSVs de OC
        col_organismo = detectar_columna_con_datos(df, ['NombreUnidad', 'NombreOrganismo', 'Organismo', 'Comprador']) 
        col_region = detectar_columna_con_datos(df, ['RegionUnidad', 'Region', 'RegionComprador'])
        col_producto = detectar_columna_con_datos(df, ['Producto', 'NombreProducto', 'Descripcion'])

        # 1. KPI MONTO
        if col_monto:
             try:
                # Limpieza si viene con signos $
                if df[col_monto].dtype == object:
                    total_venta = df[col_monto].astype(str).str.replace(r'[$.]', '', regex=True).astype(float).sum()
                else:
                    total_venta = df[col_monto].sum()
                col2.metric("Monto Total Analizado", f"${total_venta:,.0f}")
             except:
                col2.metric("Monto Total", "Error calc.")
        else:
             col2.metric("Monto Total", "No detectado")
             
        # 2. KPI COMPRADOR (AQUÍ FALLABA ANTES)
        if col_organismo:
            try:
                conteo = df[col_organismo].value_counts()
                if not conteo.empty:
                    top_org = conteo.idxmax()
                    col3.metric("Mayor Comprador", f"{str(top_org)[:20]}...")
                else:
                    col3.metric("Mayor Comprador", "Sin datos válidos")
            except:
                col3.metric("Mayor Comprador", "-")
        else:
             col3.metric("Mayor Comprador", "-")

        # 3. KPI REGIÓN
        if col_region:
            try:
                conteo_reg = df[col_region].value_counts()
                if not conteo_reg.empty:
                    top_reg = conteo_reg.idxmax()
                    col4.metric("Región Dominante", f"{str(top_reg)}")
                else:
                    col4.metric("Región", "-")
            except:
                col4.metric("Región", "-")
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
                        stats_txt = ""
                        
                        # Top Productos (Validando que existan columnas y datos)
                        if col_producto and 'Cantidad' in df.columns and col_monto:
                             # Intentamos usar PrecioNeto si existe, si no, inferimos del Monto Total
                             col_precio = 'PrecioNeto' if 'PrecioNeto' in df.columns else col_monto
                             
                             try:
                                top_prods = df.groupby(col_producto).agg({'Cantidad':'sum', col_precio:'mean'}).sort_values('Cantidad', ascending=False).head(5)
                                stats_txt += f"\n[TOP 5 PRODUCTOS MÁS COMPRADOS]\n{top_prods.to_string()}\n"
                             except:
                                pass # Si falla el groupby, seguimos sin ese dato

                        # Top Región por Monto
                        if col_region and col_monto:
                            try:
                                top_reg_monto = df.groupby(col_region)[col_monto].sum().sort_values(ascending=False).head(3)
                                stats_txt += f"\n[TOP 3 REGIONES POR MONTO COMPRADO]\n{top_reg_monto.to_string()}\n"
                            except: pass

                        # Top Organismo por Monto
                        if col_organismo and col_monto:
                            try:
                                top_org_monto = df.groupby(col_organismo)[col_monto].sum().sort_values(ascending=False).head(3)
                                stats_txt += f"\n[TOP 3 ORGANISMOS COMPRADORES]\n{top_org_monto.to_string()}\n"
                            except: pass
                        
                        # --- 2. SELECTOR DE MODELO (Anti-Error 404) ---
                        modelos_disponibles = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
                        # Prioridad: Flash -> Pro -> Cualquiera
                        modelo_nombre = next((m for m in modelos_disponibles if 'flash' in m), None)
                        if not modelo_nombre:
                            modelo_nombre = next((m for m in modelos_disponibles if 'pro' in m), modelos_disponibles[0])
                        
                        model = genai.GenerativeModel(modelo_nombre)
                        
                        # --- 3. PROMPT MAESTRO (11 AÑOS DE EXPERIENCIA) ---
                        prompt = f"""
                        ERES CORTEX ANALYTICS, UN EXPERTO GERENTE COMERCIAL DE MERCADO PÚBLICO CHILE.
                        
                        Tienes acceso a dos fuentes de información:
                        1. ESTADÍSTICAS GLOBALES CALCULADAS (Datos duros):
                        {stats_txt}
                        
                        2. MUESTRA DE DATOS DETALLADOS (Primeras 50 filas):
                        {df.head(50).to_string()}
                        
                        PREGUNTA DEL USUARIO: "{pregunta}"
                        
                        INSTRUCCIONES:
                        - Usa las ESTADÍSTICAS GLOBALES para responder sobre "Top", "Más vendido" o "Totales".
                        - Si preguntan por precios, usa el promedio calculado.
                        - Si preguntan por Región, cruza el dato de la Región con los productos.
                        - Sé directo y estratégico.
                        """
                        
                        response = model.generate_content(prompt)
                        st.markdown(f'<div class="chat-box">{response.text}</div>', unsafe_allow_html=True)
                        
                    except Exception as e:
                        st.error(f"Error detallado durante el análisis: {e}")
        
        with col_img:
            st.markdown("###")
            st.image("https://cdn-icons-png.flaticon.com/512/6009/6009864.png", width=150)

    except Exception as e:
        st.error(f"❌ Error al procesar archivo. Asegúrate de 'openpyxl' en requirements.txt. Detalle: {e}")
