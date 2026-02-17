import streamlit as st
import google.generativeai as genai
import pandas as pd
import altair as alt
import pydeck as pdk # Librería de Mapas 3D
import io

# --- 1. CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(
    page_title="Sentinela - Analítica Comercial",
    page_icon="📊",
    layout="wide"
)

# --- CSS PRO (ANIMACIÓN + ESTILO DARK) ---
st.markdown("""
    <style>
    .stApp { background-color: #0E1117; color: #FAFAFA; }
    h1, h2, h3 { font-family: 'Helvetica Neue', sans-serif; font-weight: 700; }
    h1 { color: #4A90E2; }
    
    div[data-testid="stMetricValue"] {
        font-size: 24px !important;
        color: #00D4FF;
        font-weight: bold;
    }
    
    /* ANIMACIÓN ROBOT */
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

    .stButton>button {
        background: linear-gradient(90deg, #2E5CB8 0%, #4A00E0 100%);
        color: white;
        border-radius: 8px;
        border: none;
        padding: 0.6rem 1.5rem;
        font-weight: 600;
    }
    
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
    st.markdown("""<div class="robot-container"><img src="https://cdn-icons-png.flaticon.com/512/4712/4712035.png" class="robot-img"></div>""", unsafe_allow_html=True)
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
    for col in df.columns:
        for p in posibles:
            if p.lower() in col.lower() and df[col].notna().sum() > 0:
                return col
    return None

def limpiar_monto(serie):
    if serie.dtype == object:
        return serie.astype(str).str.replace(r'[$.]', '', regex=True).astype(float)
    return serie

# --- MAPEO GEOESPACIAL CHILE (HARDCODED PARA RAPIDEZ) ---
COORDENADAS_CHILE = {
    'arica': {'lat': -18.4746, 'lon': -70.2979},
    'tarapaca': {'lat': -20.2133, 'lon': -70.1503},
    'antofagasta': {'lat': -23.6524, 'lon': -70.3954},
    'atacama': {'lat': -27.3668, 'lon': -70.3323},
    'coquimbo': {'lat': -29.9533, 'lon': -71.3395},
    'valpara': {'lat': -33.0456, 'lon': -71.6199}, # Valparaiso
    'metropo': {'lat': -33.4372, 'lon': -70.6506}, # Santiago
    'higgins': {'lat': -34.5873, 'lon': -70.9902}, # O'Higgins
    'maule': {'lat': -35.4267, 'lon': -71.6554},
    'uble': {'lat': -36.6063, 'lon': -72.1023}, # Ñuble
    'biob': {'lat': -36.8270, 'lon': -73.0503}, # Biobio
    'araucan': {'lat': -38.7397, 'lon': -72.6019},
    'rios': {'lat': -39.8142, 'lon': -73.2459}, # Los Rios
    'lagos': {'lat': -41.4693, 'lon': -72.9424},
    'aysen': {'lat': -45.5752, 'lon': -72.0662},
    'magallane': {'lat': -53.1626, 'lon': -70.9081},
}

def obtener_lat_lon(nombre_region):
    """Busca coordenadas aproximadas según el nombre de la región."""
    if not isinstance(nombre_region, str): return None, None
    norm = nombre_region.lower()
    for key, val in COORDENADAS_CHILE.items():
        if key in norm:
            return val['lat'], val['lon']
    return None, None

# --- TÍTULO ---
st.title("📊 Tablero de Comando Comercial")

# --- CARGA DE DATOS ---
uploaded_file = st.file_uploader("📂 Cargar Datos (Excel/CSV)", type=["xlsx", "csv"])

if uploaded_file:
    try:
        if uploaded_file.name.endswith('.csv'):
            try: df = pd.read_csv(uploaded_file, encoding='utf-8')
            except: df = pd.read_csv(uploaded_file, encoding='latin-1')
        else:
            df = pd.read_excel(uploaded_file)
        
        col_monto = detectar_columna(df, ['TotalNeto', 'TotalLinea', 'Monto', 'Total'])
        col_org = detectar_columna(df, ['NombreOrganismo', 'Organismo', 'NombreUnidad', 'Unidad', 'Comprador']) 
        col_reg = detectar_columna(df, ['RegionUnidad', 'Region', 'RegionComprador'])
        col_prod = detectar_columna(df, ['Producto', 'NombreProducto', 'Descripcion'])
        col_prov = detectar_columna(df, ['NombreProvider', 'Proveedor', 'Vendedor', 'Empresa']) 
        col_cant = detectar_columna(df, ['Cantidad', 'Cant'])

        if col_monto:
            df['Monto_Clean'] = limpiar_monto(df[col_monto])
        else:
            df['Monto_Clean'] = 0

        # --- DASHBOARD ---
        st.divider()
        
        # 1. KPIs
        kpi1, kpi2, kpi3, kpi4 = st.columns(4)
        kpi1.metric("💰 Mercado Total", f"${df['Monto_Clean'].sum():,.0f}")
        kpi2.metric("🎫 Ticket Promedio", f"${df['Monto_Clean'].mean():,.0f}")
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

        # 2. GRÁFICOS TOP 10 (PODER)
        st.subheader("🏛️ ¿Quién Compra? vs 🏢 ¿Quién Vende? (TOP 10)")
        row1_col1, row1_col2 = st.columns(2)

        with row1_col1:
            if col_org and col_monto:
                data_org = df.groupby(col_org)['Monto_Clean'].sum().reset_index().sort_values('Monto_Clean', ascending=False).head(10)
                chart_org = alt.Chart(data_org).mark_bar(cornerRadius=5).encode(
                    x=alt.X('Monto_Clean', title='Monto ($)'),
                    y=alt.Y(col_org, sort='-x', title='Organismo'),
                    color=alt.value('#FF6B6B'),
                    tooltip=[col_org, alt.Tooltip('Monto_Clean', format=',.0f')]
                ).properties(height=400)
                st.altair_chart(chart_org, use_container_width=True)

        with row1_col2:
            if col_prov and col_monto:
                data_prov = df.groupby(col_prov)['Monto_Clean'].sum().reset_index().sort_values('Monto_Clean', ascending=False).head(10)
                chart_prov = alt.Chart(data_prov).mark_bar(cornerRadius=5).encode(
                    x=alt.X('Monto_Clean', title='Monto ($)'),
                    y=alt.Y(col_prov, sort='-x', title='Proveedor'),
                    color=alt.value('#4ECDC4'),
                    tooltip=[col_prov, alt.Tooltip('Monto_Clean', format=',.0f')]
                ).properties(height=400)
                st.altair_chart(chart_prov, use_container_width=True)

        # 3. MAPA Y PRODUCTOS
        st.markdown("---")
        st.subheader("🌍 Territorio y Productos")
        row2_col1, row2_col2 = st.columns([1, 1])

        # MAPA DE CALOR CHILE (PyDeck)
        with row2_col1:
            st.markdown("##### 📍 Concentración de Compras (Mapa)")
            if col_reg and col_monto:
                # Preparar datos geo
                df_map = df.groupby(col_reg)['Monto_Clean'].sum().reset_index()
                df_map['lat'], df_map['lon'] = zip(*df_map[col_reg].apply(obtener_lat_lon))
                df_map = df_map.dropna(subset=['lat', 'lon']) # Borrar lo que no se pudo geolocalizar
                
                # Normalizar radio para el mapa (para que no cubra todo)
                max_val = df_map['Monto_Clean'].max()
                df_map['radius'] = (df_map['Monto_Clean'] / max_val) * 80000 + 10000 # Escala visual

                if not df_map.empty:
                    layer = pdk.Layer(
                        "ScatterplotLayer",
                        df_map,
                        get_position='[lon, lat]',
                        get_color='[200, 30, 0, 160]', # Rojo Intenso Semi-transparente
                        get_radius='radius',
                        pickable=True,
                    )
                    view_state = pdk.ViewState(latitude=-35.6751, longitude=-71.5430, zoom=3, pitch=0)
                    st.pydeck_chart(pdk.Deck(layers=[layer], initial_view_state=view_state, tooltip={"text": "{Region}: ${Monto_Clean}"}))
                else:
                    st.info("No se pudieron geolocalizar las regiones automáticamente.")
            else:
                st.info("Faltan datos de Región.")

        # TOP 10 PRODUCTOS
        with row2_col2:
            st.markdown("##### 📦 Top 10 Productos")
            if col_prod and col_monto:
                data_prod = df.groupby(col_prod)['Monto_Clean'].sum().reset_index().sort_values('Monto_Clean', ascending=False).head(10)
                chart_prod = alt.Chart(data_prod).mark_bar(cornerRadius=5).encode(
                    x=alt.X('Monto_Clean', title='Monto ($)'),
                    y=alt.Y(col_prod, sort='-x', title='Producto'),
                    color=alt.value('#4A90E2'),
                    tooltip=[col_prod, alt.Tooltip('Monto_Clean', format=',.0f')]
                ).properties(height=400)
                st.altair_chart(chart_prod, use_container_width=True)

        # --- IA OMNISCIENTE ---
        st.divider()
        st.subheader("🤖 Cortex Strategic Advisor")
        
        col_input, col_go = st.columns([4, 1])
        with col_input:
            pregunta = st.text_input("Consulta al Agente:", placeholder="Ej: ¿Qué se compra más en la región del mapa con más rojo?", label_visibility="collapsed")
        with col_go:
            btn_analizar = st.button("⚡ INVESTIGAR")

        if btn_analizar and pregunta:
            with st.spinner("Analizando Geo-Datos..."):
                try:
                    # PREPARAR CONTEXTO PARA IA
                    txt_prod = df.groupby(col_prod)['Monto_Clean'].sum().sort_values(ascending=False).head(5).to_string() if col_prod else ""
                    txt_prov = df.groupby(col_prov)['Monto_Clean'].sum().sort_values(ascending=False).head(5).to_string() if col_prov else ""
                    
                    # CRUCE REGION-PRODUCTO (Vital para la pregunta de Valparaíso)
                    txt_cruce = ""
                    if col_reg and col_prod:
                        try:
                            aux = df.groupby([col_reg, col_prod])['Monto_Clean'].sum().reset_index()
                            aux = aux.sort_values([col_reg, 'Monto_Clean'], ascending=[True, False])
                            txt_cruce = aux.groupby(col_reg).head(3).to_string(index=False)
                        except: pass

                    models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
                    model_name = next((m for m in models if 'flash' in m), models[0])
                    model = genai.GenerativeModel(model_name)

                    prompt = f"""
                    ERES CORTEX, ESTRATEGA DE MERCADO PÚBLICO.
                    [DATOS]
                    Top Productos: {txt_prod}
                    Top Proveedores: {txt_prov}
                    CRUCE REGION-PRODUCTO (LO QUE MÁS SE VENDE POR ZONA):
                    {txt_cruce}
                    
                    PREGUNTA: "{pregunta}"
                    """
                    response = model.generate_content(prompt)
                    st.markdown(f'<div class="chat-box">{response.text}</div>', unsafe_allow_html=True)
                except Exception as e:
                    st.error(f"Error IA: {e}")

    except Exception as e:
        st.error(f"❌ Error procesando el archivo: {e}")
