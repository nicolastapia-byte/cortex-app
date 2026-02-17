import streamlit as st
import google.generativeai as genai
import pandas as pd
import altair as alt # Librería de gráficos pro
import io

# --- 1. CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(
    page_title="Sentinela - Analítica Comercial",
    page_icon="📊",
    layout="wide"
)

# --- CSS PRO (ESTILO CORTEX ENTERPRISE) ---
st.markdown("""
    <style>
    /* Fondo y Títulos */
    .stApp {
        background-color: #0E1117;
        color: #FAFAFA;
    }
    h1, h2, h3 {
        font-family: 'Helvetica Neue', sans-serif;
        font-weight: 700;
    }
    h1 { color: #4A90E2; } /* Azul Cortex */
    
    /* Métricas (KPI Cards) */
    div[data-testid="stMetricValue"] {
        font-size: 32px;
        color: #00D4FF; /* Cyan Neón para números */
        font-weight: bold;
    }
    div[data-testid="stMetricLabel"] {
        font-size: 16px;
        color: #B0B0B0;
    }
    
    /* Botón Principal */
    .stButton>button {
        background: linear-gradient(90deg, #2E5CB8 0%, #4A00E0 100%);
        color: white;
        border-radius: 8px;
        border: none;
        padding: 0.6rem 1.5rem;
        font-weight: 600;
        transition: transform 0.2s;
    }
    .stButton>button:hover {
        transform: scale(1.05);
    }
    
    /* Chat Box */
    .chat-box {
        background-color: #1E2329;
        padding: 20px;
        border-radius: 10px;
        border-left: 5px solid #00D4FF;
        margin-top: 15px;
        color: #E0E0E0;
    }
    </style>
    """, unsafe_allow_html=True)

# --- SIDEBAR ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/4712/4712035.png", width=80)
    st.title("Cortex Analytics")
    st.markdown("**Inteligencia de Mercado**")
    st.markdown("---")
    st.info("Sube tu histórico de Mercado Público para generar el tablero de mando.")
    
    if "GOOGLE_API_KEY" in st.secrets:
        genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
    else:
        st.error("⚠️ Falta API Key.")
        st.stop()

# --- FUNCIONES AUXILIARES ---
def detectar_columna(df, posibles):
    """Detecta columnas clave ignorando mayúsculas/minúsculas"""
    for col in df.columns:
        for p in posibles:
            if p.lower() in col.lower() and df[col].notna().sum() > 0:
                return col
    return None

def limpiar_monto(serie):
    """Limpia signos de $ y puntos para convertir a número"""
    if serie.dtype == object:
        return serie.astype(str).str.replace(r'[$.]', '', regex=True).astype(float)
    return serie

# --- TÍTULO ---
st.title("📊 Tablero de Comando Comercial")
st.markdown("Visualización estratégica de oportunidades en Mercado Público.")

# --- CARGA DE DATOS ---
uploaded_file = st.file_uploader("📂 Cargar Datos (Excel/CSV)", type=["xlsx", "csv"])

if uploaded_file:
    try:
        # 1. Cargar Data
        if uploaded_file.name.endswith('.csv'):
            try: df = pd.read_csv(uploaded_file, encoding='utf-8')
            except: df = pd.read_csv(uploaded_file, encoding='latin-1')
        else:
            df = pd.read_excel(uploaded_file)
        
        # 2. Detección Inteligente de Columnas
        col_monto = detectar_columna(df, ['TotalNeto', 'TotalLinea', 'Monto', 'Total'])
        col_org = detectar_columna(df, ['NombreUnidad', 'NombreOrganismo', 'Organismo']) 
        col_reg = detectar_columna(df, ['RegionUnidad', 'Region'])
        col_prod = detectar_columna(df, ['Producto', 'NombreProducto', 'Descripcion'])
        col_cant = detectar_columna(df, ['Cantidad', 'Cant'])

        # 3. Procesamiento de Datos (Limpieza)
        if col_monto:
            df['Monto_Clean'] = limpiar_monto(df[col_monto])
        else:
            df['Monto_Clean'] = 0

        # --- DASHBOARD VISUAL DE IMPACTO ---
        st.divider()
        
        # FILA 1: KPIs CLAVE (Números Grandes)
        kpi1, kpi2, kpi3, kpi4 = st.columns(4)
        
        # KPI 1: Total Transado
        total_monto = df['Monto_Clean'].sum()
        kpi1.metric("💰 Mercado Total", f"${total_monto:,.0f}")
        
        # KPI 2: Ticket Promedio
        avg_ticket = df['Monto_Clean'].mean()
        kpi2.metric("🎫 Ticket Promedio", f"${avg_ticket:,.0f}")
        
        # KPI 3: Total OC/Licitaciones
        kpi3.metric("📄 Total Operaciones", f"{len(df):,}")
        
        # KPI 4: Top Comprador
        if col_org:
            top_buyer = df[col_org].value_counts().idxmax()
            kpi4.metric("🏆 Comprador #1", f"{str(top_buyer)[:15]}..")
        else:
            kpi4.metric("🏆 Comprador #1", "N/A")

        st.markdown("---")

        # FILA 2: GRÁFICOS ESTRATÉGICOS (Aquí está la magia visual)
        chart_col1, chart_col2 = st.columns(2)

        with chart_col1:
            st.subheader("📦 Top 5 Productos (Por Monto)")
            if col_prod and col_monto:
                # Agrupamos datos para el gráfico
                chart_data_prod = df.groupby(col_prod)['Monto_Clean'].sum().reset_index()
                chart_data_prod = chart_data_prod.sort_values('Monto_Clean', ascending=False).head(5)
                
                # Gráfico de Barras Horizontal con Altair
                bar_chart = alt.Chart(chart_data_prod).mark_bar(cornerRadius=5).encode(
                    x=alt.X('Monto_Clean', title='Monto Total ($)'),
                    y=alt.Y(col_prod, sort='-x', title='Producto'),
                    color=alt.value('#4A90E2'), # Azul Cortex
                    tooltip=[col_prod, alt.Tooltip('Monto_Clean', format=',.0f')]
                ).properties(height=300)
                
                st.altair_chart(bar_chart, use_container_width=True)
            else:
                st.warning("Faltan datos de Producto o Monto para graficar.")

        with chart_col2:
            st.subheader("🌍 Mapa de Calor Regional")
            if col_reg and col_monto:
                # Agrupamos por región
                chart_data_reg = df.groupby(col_reg)['Monto_Clean'].sum().reset_index()
                chart_data_reg = chart_data_reg.sort_values('Monto_Clean', ascending=False).head(7)
                
                # Gráfico de Barras Vertical
                reg_chart = alt.Chart(chart_data_reg).mark_bar(cornerRadius=5).encode(
                    x=alt.X(col_reg, sort='-y', title='Región'),
                    y=alt.Y('Monto_Clean', title='Inversión ($)'),
                    color=alt.value('#00D4FF'), # Cyan Cortex
                    tooltip=[col_reg, alt.Tooltip('Monto_Clean', format=',.0f')]
                ).properties(height=300)
                
                st.altair_chart(reg_chart, use_container_width=True)
            else:
                st.warning("Faltan datos de Región para graficar.")

        # --- SECCIÓN: CONSULTOR IA ---
        st.divider()
        st.subheader("🤖 Cortex Strategic Advisor")
        st.info("¿Qué te llama la atención de los gráficos? Pregúntame detalles.")
        
        col_input, col_go = st.columns([4, 1])
        with col_input:
            pregunta = st.text_input("Pregunta al Agente:", placeholder="Ej: ¿Por qué la Región X compra tanto Producto Y?", label_visibility="collapsed")
        with col_go:
            btn_analizar = st.button("⚡ INVESTIGAR")

        if btn_analizar and pregunta:
            with st.spinner("Cruzando datos de gráficos con inteligencia histórica..."):
                try:
                    # PREPARAR CONTEXTO PARA IA
                    # Le pasamos el TOP 5 ya calculado para que no alucine
                    top_5_txt = ""
                    if col_prod:
                         top_5_txt = df.groupby(col_prod)['Monto_Clean'].sum().sort_values(ascending=False).head(5).to_string()
                    
                    # SELECTOR DE MODELO
                    models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
                    model_name = next((m for m in models if 'flash' in m), models[0])
                    model = genai.GenerativeModel(model_name)

                    prompt = f"""
                    ERES UN ANALISTA DE INTELIGENCIA DE NEGOCIOS.
                    Tienes en pantalla un Dashboard con estos datos clave:
                    
                    [KPI MACRO]
                    Total Mercado: ${total_monto:,.0f}
                    Ticket Promedio: ${avg_ticket:,.0f}
                    
                    [TOP 5 PRODUCTOS REALES]
                    {top_5_txt}
                    
                    PREGUNTA DEL USUARIO: "{pregunta}"
                    
                    INSTRUCCIONES:
                    1. Responde basándote en los datos duros.
                    2. Sé breve, directo y estratégico.
                    3. Si detectas una oportunidad (ej: un producto que se vende mucho pero a bajo precio), menciónala.
                    """
                    
                    response = model.generate_content(prompt)
                    st.markdown(f'<div class="chat-box">{response.text}</div>', unsafe_allow_html=True)

                except Exception as e:
                    st.error(f"Error en IA: {e}")

        # DATA RAW (Escondida pero accesible)
        with st.expander("🔍 Ver Datos Crudos (Tabla Completa)"):
            st.dataframe(df)

    except Exception as e:
        st.error(f"❌ Error procesando el archivo: {e}")
