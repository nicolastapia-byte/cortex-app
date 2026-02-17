import streamlit as st
import google.generativeai as genai
import pandas as pd
import altair as alt
import io

# --- 1. CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(
    page_title="Sentinela - Analítica Comercial",
    page_icon="📊",
    layout="wide"
)

# --- CSS PRO (CON ANIMACIÓN CORTEX) ---
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
    h1 { color: #4A90E2; }
    
    /* Métricas (KPI Cards) - COMPACTAS */
    div[data-testid="stMetricValue"] {
        font-size: 24px !important;
        color: #00D4FF;
        font-weight: bold;
        word-wrap: break-word;
    }
    div[data-testid="stMetricLabel"] {
        font-size: 14px;
        color: #B0B0B0;
    }
    
    /* ANIMACIÓN ROBOT (CORTEX VIVE) */
    .robot-container {
        display: flex;
        justify-content: center;
        animation: float-breathe 4s ease-in-out infinite;
        padding-bottom: 20px;
    }
    .robot-img {
        width: 100px;
        filter: drop-shadow(0 0 15px rgba(0, 212, 255, 0.6));
    }
    @keyframes float-breathe {
        0%, 100% { transform: translateY(0); filter: drop-shadow(0 0 15px rgba(0, 212, 255, 0.6)); }
        50% { transform: translateY(-10px); filter: drop-shadow(0 0 25px rgba(0, 212, 255, 0.9)); }
    }

    /* Botón Principal */
    .stButton>button {
        background: linear-gradient(90deg, #2E5CB8 0%, #4A00E0 100%);
        color: white;
        border-radius: 8px;
        border: none;
        padding: 0.6rem 1.5rem;
        font-weight: 600;
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

# --- SIDEBAR (CON ROBOT ANIMADO) ---
with st.sidebar:
    st.markdown("""
        <div class="robot-container">
            <img src="https://cdn-icons-png.flaticon.com/512/4712/4712035.png" class="robot-img">
        </div>
    """, unsafe_allow_html=True)
    
    st.title("Cortex Analytics")
    st.markdown("**Inteligencia de Mercado**")
    st.markdown("---")
    st.info("Sube tu histórico de Mercado Público.")
    
    if "GOOGLE_API_KEY" in st.secrets:
        genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
    else:
        st.error("⚠️ Falta API Key.")
        st.stop()

# --- FUNCIONES AUXILIARES ---
def detectar_columna(df, posibles):
    """Detecta columnas clave ignorando mayúsculas/minúsculas y verificando datos"""
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
        # PRIORIDAD: NombreOrganismo
        col_org = detectar_columna(df, ['NombreOrganismo', 'Organismo', 'NombreUnidad', 'Unidad', 'Comprador']) 
        col_reg = detectar_columna(df, ['RegionUnidad', 'Region', 'RegionComprador'])
        col_prod = detectar_columna(df, ['Producto', 'NombreProducto', 'Descripcion'])
        col_prov = detectar_columna(df, ['NombreProvider', 'Proveedor', 'Vendedor', 'Empresa']) 
        col_cant = detectar_columna(df, ['Cantidad', 'Cant'])

        # 3. Procesamiento de Datos (Limpieza)
        if col_monto:
            df['Monto_Clean'] = limpiar_monto(df[col_monto])
        else:
            df['Monto_Clean'] = 0

        # --- DASHBOARD VISUAL ---
        st.divider()
        
        # === FILA 1: KPIs ===
        kpi1, kpi2, kpi3, kpi4 = st.columns(4)
        
        total_monto = df['Monto_Clean'].sum()
        kpi1.metric("💰 Mercado Total", f"${total_monto:,.0f}")
        
        avg_ticket = df['Monto_Clean'].mean()
        kpi2.metric("🎫 Ticket Promedio", f"${avg_ticket:,.0f}")
        
        kpi3.metric("📄 Total Ops", f"{len(df):,}")
        
        if col_prov and col_monto:
            top_player = df.groupby(col_prov)['Monto_Clean'].sum().idxmax()
            kpi4.metric("🏆 Top Proveedor", f"{str(top_player)[:15]}..")
        elif col_org:
            top_buyer = df[col_org].value_counts().idxmax()
            kpi4.metric("🏆 Top Comprador", f"{str(top_buyer)[:15]}..")
        else:
            kpi4.metric("🏆 Líder", "N/A")

        st.markdown("---")

        # === FILA 2: GRÁFICOS ===
        st.subheader("🏛️ ¿Quién Compra? vs 🏢 ¿Quién Vende?")
        row1_col1, row1_col2 = st.columns(2)

        with row1_col1:
            if col_org and col_monto:
                chart_data_org = df.groupby(col_org)['Monto_Clean'].sum().reset_index()
                chart_data_org = chart_data_org.sort_values('Monto_Clean', ascending=False).head(5)
                
                chart_org = alt.Chart(chart_data_org).mark_bar(cornerRadius=5).encode(
                    x=alt.X('Monto_Clean', title='Monto ($)'),
                    y=alt.Y(col_org, sort='-x', title='Organismo'),
                    color=alt.value('#FF6B6B'),
                    tooltip=[col_org, alt.Tooltip('Monto_Clean', format=',.0f')]
                ).properties(title="Top 5 Compradores", height=300)
                st.altair_chart(chart_org, use_container_width=True)

        with row1_col2:
            if col_prov and col_monto:
                chart_data_prov = df.groupby(col_prov)['Monto_Clean'].sum().reset_index()
                chart_data_prov = chart_data_prov.sort_values('Monto_Clean', ascending=False).head(5)
                
                chart_prov = alt.Chart(chart_data_prov).mark_bar(cornerRadius=5).encode(
                    x=alt.X('Monto_Clean', title='Monto ($)'),
                    y=alt.Y(col_prov, sort='-x', title='Proveedor'),
                    color=alt.value('#4ECDC4'),
                    tooltip=[col_prov, alt.Tooltip('Monto_Clean', format=',.0f')]
                ).properties(title="Top 5 Proveedores", height=300)
                st.altair_chart(chart_prov, use_container_width=True)

        # === FILA 3: DETALLES ===
        st.markdown("### 📦 ¿Qué se vende? y ¿Dónde?")
        row2_col1, row2_col2 = st.columns(2)

        with row2_col1:
            if col_prod and col_monto:
                chart_data_prod = df.groupby(col_prod)['Monto_Clean'].sum().reset_index()
                chart_data_prod = chart_data_prod.sort_values('Monto_Clean', ascending=False).head(5)
                
                chart_prod = alt.Chart(chart_data_prod).mark_bar(cornerRadius=5).encode(
                    x=alt.X('Monto_Clean', title='Monto ($)'),
                    y=alt.Y(col_prod, sort='-x', title='Producto'),
                    color=alt.value('#4A90E2'),
                    tooltip=[col_prod, alt.Tooltip('Monto_Clean', format=',.0f')]
                ).properties(height=250)
                st.altair_chart(chart_prod, use_container_width=True)

        with row2_col2:
            if col_reg and col_monto:
                chart_data_reg = df.groupby(col_reg)['Monto_Clean'].sum().reset_index()
                chart_data_reg = chart_data_reg.sort_values('Monto_Clean', ascending=False).head(5)
                
                chart_reg = alt.Chart(chart_data_reg).mark_bar(cornerRadius=5).encode(
                    x=alt.X(col_reg, sort='-y', title='Región'), 
                    y=alt.Y('Monto_Clean', title='Monto ($)'),
                    color=alt.value('#A3A1FB'),
                    tooltip=[col_reg, alt.Tooltip('Monto_Clean', format=',.0f')]
                ).properties(height=250)
                st.altair_chart(chart_reg, use_container_width=True)

        # --- CONSULTOR IA (CEREBRO OMNISCIENTE) ---
        st.divider()
        st.subheader("🤖 Cortex Strategic Advisor")
        
        col_input, col_go = st.columns([4, 1])
        with col_input:
            pregunta = st.text_input("Pregunta al Agente:", placeholder="Ej: ¿Qué compran más en Valparaíso? / Estrategia contra el proveedor líder", label_visibility="collapsed")
        with col_go:
            btn_analizar = st.button("⚡ INVESTIGAR")

        if btn_analizar and pregunta:
            with st.spinner("Cortex está cruzando variables (Región vs Producto vs Precio)..."):
                try:
                    # --- PREPARACIÓN DE INTELIGENCIA (EL FIX QUE FALTABA) ---
                    # 1. Top Productos
                    txt_prod = ""
                    if col_prod:
                        txt_prod = df.groupby(col_prod)['Monto_Clean'].sum().sort_values(ascending=False).head(5).to_string()
                    
                    # 2. Top Proveedores
                    txt_prov = ""
                    if col_prov:
                        txt_prov = df.groupby(col_prov)['Monto_Clean'].sum().sort_values(ascending=False).head(5).to_string()

                    # 3. Top Regiones
                    txt_reg = ""
                    if col_reg:
                        txt_reg = df.groupby(col_reg)['Monto_Clean'].sum().sort_values(ascending=False).head(5).to_string()

                    # 4. CRUCE INTELIGENTE (LA BALA DE PLATA)
                    # Calculamos: El producto más vendido POR REGIÓN
                    txt_cruce = ""
                    if col_reg and col_prod:
                        try:
                            # Agrupamos por Region y Producto, sumamos monto
                            aux = df.groupby([col_reg, col_prod])['Monto_Clean'].sum().reset_index()
                            # Ordenamos para dejar el producto top de cada región primero
                            aux = aux.sort_values([col_reg, 'Monto_Clean'], ascending=[True, False])
                            # Nos quedamos con el Top 1 de cada región
                            top_por_region = aux.groupby(col_reg).head(3) # Top 3 productos por región
                            txt_cruce = top_por_region.to_string(index=False)
                        except:
                            txt_cruce = "No se pudo calcular el cruce."

                    # --- SELECTOR DE MODELO ---
                    models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
                    model_name = next((m for m in models if 'flash' in m), models[0])
                    model = genai.GenerativeModel(model_name)

                    # --- PROMPT MAESTRO ---
                    prompt = f"""
                    ERES CORTEX, ANALISTA ESTRATÉGICO DE MERCADO PÚBLICO (11 AÑOS EXP).
                    
                    He procesado los datos y aquí tienes los HECHOS DUROS:
                    
                    [TOP 5 PRODUCTOS GLOBALES]
                    {txt_prod}
                    
                    [TOP 5 PROVEEDORES (COMPETENCIA)]
                    {txt_prov}
                    
                    [TOP REGIONES]
                    {txt_reg}
                    
                    [CRUCE: LO QUE MÁS SE VENDE EN CADA REGIÓN] (¡IMPORTANTE!)
                    {txt_cruce}
                    
                    PREGUNTA DEL USUARIO: "{pregunta}"
                    
                    INSTRUCCIONES:
                    1. Si preguntan "Qué se compra en X Región", mira la sección [CRUCE].
                    2. Cruza los datos. Si Valparaíso aparece en el cruce, di exactamente qué producto es.
                    3. Responde con autoridad y datos exactos.
                    """
                    
                    response = model.generate_content(prompt)
                    st.markdown(f'<div class="chat-box">{response.text}</div>', unsafe_allow_html=True)

                except Exception as e:
                    st.error(f"Error IA: {e}")

    except Exception as e:
        st.error(f"❌ Error procesando el archivo: {e}")
