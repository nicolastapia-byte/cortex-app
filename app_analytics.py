import streamlit as st
import google.generativeai as genai
import pandas as pd
import altair as alt
import pydeck as pdk
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
    .stApp { background-color: #0E1117; color: #FAFAFA; }
    h1, h2, h3 { font-family: 'Helvetica Neue', sans-serif; font-weight: 700; }
    h1 { color: #4A90E2; }
    div[data-testid="stMetricValue"] { font-size: 24px !important; color: #00D4FF; font-weight: bold; }
    
    .robot-container { display: flex; justify-content: center; animation: float-breathe 4s ease-in-out infinite; padding-bottom: 20px; }
    .robot-img { width: 100px; filter: drop-shadow(0 0 15px rgba(0, 212, 255, 0.6)); }
    @keyframes float-breathe {
        0%, 100% { transform: translateY(0); filter: drop-shadow(0 0 15px rgba(0, 212, 255, 0.6)); }
        50% { transform: translateY(-10px); filter: drop-shadow(0 0 25px rgba(0, 212, 255, 0.9)); }
    }
    
    .stButton>button { background: linear-gradient(90deg, #2E5CB8 0%, #4A00E0 100%); color: white; border-radius: 8px; border: none; padding: 0.6rem 1.5rem; font-weight: 600; }
    .chat-box { background-color: #1E2329; padding: 20px; border-radius: 10px; border-left: 5px solid #00D4FF; margin-top: 15px; color: #E0E0E0; }
    </style>
    """, unsafe_allow_html=True)

# --- SIDEBAR ---
with st.sidebar:
    st.markdown("""<div class="robot-container"><img src="https://cdn-icons-png.flaticon.com/512/4712/4712035.png" class="robot-img"></div>""", unsafe_allow_html=True)
    st.title("Cortex Analytics")
    st.info("Sube tu histórico de Mercado Público.")
    if "GOOGLE_API_KEY" in st.secrets:
        genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
    else:
        st.error("⚠️ Falta API Key.")
        st.stop()

# --- FUNCIONES ---
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

# --- GEO ---
COORDENADAS_CHILE = {
    'arica': {'lat': -18.4746, 'lon': -70.2979}, 'tarapaca': {'lat': -20.2133, 'lon': -70.1503},
    'antofagasta': {'lat': -23.6524, 'lon': -70.3954}, 'atacama': {'lat': -27.3668, 'lon': -70.3323},
    'coquimbo': {'lat': -29.9533, 'lon': -71.3395}, 'valpara': {'lat': -33.0456, 'lon': -71.6199},
    'metropo': {'lat': -33.4372, 'lon': -70.6506}, 'higgins': {'lat': -34.5873, 'lon': -70.9902},
    'maule': {'lat': -35.4267, 'lon': -71.6554}, 'uble': {'lat': -36.6063, 'lon': -72.1023},
    'biob': {'lat': -36.8270, 'lon': -73.0503}, 'araucan': {'lat': -38.7397, 'lon': -72.6019},
    'rios': {'lat': -39.8142, 'lon': -73.2459}, 'lagos': {'lat': -41.4693, 'lon': -72.9424},
    'aysen': {'lat': -45.5752, 'lon': -72.0662}, 'magallane': {'lat': -53.1626, 'lon': -70.9081},
}
def obtener_lat_lon(nombre_region):
    if not isinstance(nombre_region, str): return None, None
    norm = nombre_region.lower()
    for key, val in COORDENADAS_CHILE.items():
        if key in norm: return val['lat'], val['lon']
    return None, None

# --- APP ---
st.title("📊 Tablero de Comando Comercial")
uploaded_file = st.file_uploader("📂 Cargar Datos (Excel/CSV)", type=["xlsx", "csv"])

if uploaded_file:
    try:
        if uploaded_file.name.endswith('.csv'):
            try: df = pd.read_csv(uploaded_file, encoding='utf-8')
            except: df = pd.read_csv(uploaded_file, encoding='latin-1')
        else:
            df = pd.read_excel(uploaded_file)
        
        # Detección
        col_monto = detectar_columna(df, ['TotalNeto', 'TotalLinea', 'Monto', 'Total'])
        col_org = detectar_columna(df, ['NombreOrganismo', 'Organismo', 'NombreUnidad', 'Unidad', 'Comprador']) 
        col_reg = detectar_columna(df, ['RegionUnidad', 'Region', 'RegionComprador'])
        col_prod = detectar_columna(df, ['Producto', 'NombreProducto', 'Descripcion'])
        col_prov = detectar_columna(df, ['NombreProvider', 'Proveedor', 'Vendedor', 'Empresa']) 
        
        # NUEVO: Detección explícita de PRECIO UNITARIO
        col_precio_uni = detectar_columna(df, ['PrecioNeto', 'PrecioUnitario', 'Precio', 'Unitario'])

        if col_monto: df['Monto_Clean'] = limpiar_monto(df[col_monto])
        else: df['Monto_Clean'] = 0
        
        if col_precio_uni: df['Precio_Clean'] = limpiar_monto(df[col_precio_uni])
        else: df['Precio_Clean'] = 0

        st.divider()
        
        # 1. KPIs
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("💰 Mercado Total", f"${df['Monto_Clean'].sum():,.0f}")
        k2.metric("🎫 Ticket Promedio", f"${df['Monto_Clean'].mean():,.0f}")
        k3.metric("📄 Total Ops", f"{len(df):,}")
        
        top_lider = "N/A"
        if col_prov: top_lider = df.groupby(col_prov)['Monto_Clean'].sum().idxmax()
        elif col_org: top_lider = df[col_org].value_counts().idxmax()
        k4.metric("🏆 Líder", f"{str(top_lider)[:15]}..")

        st.markdown("---")

        # 2. GRÁFICOS (POWER VIEW)
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("🏛️ Top Compradores")
            if col_org:
                d_org = df.groupby(col_org)['Monto_Clean'].sum().reset_index().sort_values('Monto_Clean', ascending=False).head(10)
                ch_org = alt.Chart(d_org).mark_bar(cornerRadius=5).encode(
                    x=alt.X('Monto_Clean', title='Monto ($)'), y=alt.Y(col_org, sort='-x', title=''), color=alt.value('#FF6B6B'), tooltip=[col_org, 'Monto_Clean']
                ).properties(height=300)
                st.altair_chart(ch_org, use_container_width=True)
        
        with c2:
            st.subheader("🏢 Top Competencia")
            if col_prov:
                d_prov = df.groupby(col_prov)['Monto_Clean'].sum().reset_index().sort_values('Monto_Clean', ascending=False).head(10)
                ch_prov = alt.Chart(d_prov).mark_bar(cornerRadius=5).encode(
                    x=alt.X('Monto_Clean', title='Monto ($)'), y=alt.Y(col_prov, sort='-x', title=''), color=alt.value('#4ECDC4'), tooltip=[col_prov, 'Monto_Clean']
                ).properties(height=300)
                st.altair_chart(ch_prov, use_container_width=True)

        st.markdown("---")
        
        # 3. MAPA Y PRODUCTOS
        c3, c4 = st.columns(2)
        with c3:
            st.subheader("📍 Mapa de Calor")
            if col_reg:
                d_map = df.groupby(col_reg)['Monto_Clean'].sum().reset_index().rename(columns={col_reg: 'Region'})
                d_map['lat'], d_map['lon'] = zip(*d_map['Region'].apply(obtener_lat_lon))
                d_map = d_map.dropna(subset=['lat'])
                d_map['radius'] = (d_map['Monto_Clean'] / d_map['Monto_Clean'].max()) * 80000 + 10000
                
                layer = pdk.Layer("ScatterplotLayer", d_map, get_position='[lon, lat]', get_color='[200, 30, 0, 160]', get_radius='radius', pickable=True)
                view = pdk.ViewState(latitude=-35.6, longitude=-71.5, zoom=3)
                st.pydeck_chart(pdk.Deck(layers=[layer], initial_view_state=view, tooltip={"text": "{Region}\n${Monto_Clean}"}))

        with c4:
            st.subheader("📦 Top Productos")
            if col_prod:
                d_prod = df.groupby(col_prod)['Monto_Clean'].sum().reset_index().sort_values('Monto_Clean', ascending=False).head(10)
                ch_prod = alt.Chart(d_prod).mark_bar(cornerRadius=5).encode(
                    x=alt.X('Monto_Clean', title='Monto ($)'), y=alt.Y(col_prod, sort='-x', title=''), color=alt.value('#4A90E2'), tooltip=[col_prod, 'Monto_Clean']
                ).properties(height=300)
                st.altair_chart(ch_prod, use_container_width=True)

        # --- IA OMNISCIENTE (CON PRECIOS UNITARIOS) ---
        st.divider()
        st.subheader("🤖 Cortex Strategic Advisor")
        
        q = st.text_input("Consulta:", placeholder="Ej: ¿Cuál es el precio mínimo y máximo de los productos más vendidos?", label_visibility="collapsed")
        if st.button("⚡ ANALIZAR") and q:
            with st.spinner("Analizando precios unitarios de mercado..."):
                try:
                    # 1. TEXTO BASE (Montos Totales)
                    txt_prod = df.groupby(col_prod)['Monto_Clean'].sum().sort_values(ascending=False).head(10).to_string() if col_prod else ""
                    txt_prov = df.groupby(col_prov)['Monto_Clean'].sum().sort_values(ascending=False).head(5).to_string() if col_prov else ""
                    
                    # 2. ANÁLISIS DE PRECIOS UNITARIOS (LA JOYA DE LA CORONA) 💎
                    txt_precios = "No se detectó columna de precio unitario."
                    if col_prod and col_precio_uni:
                        # Agrupamos por producto y pedimos Min, Max y Promedio del PRECIO UNITARIO
                        stats_precios = df.groupby(col_prod)[col_precio_uni].agg(['min', 'max', 'mean', 'count'])
                        # Filtramos solo los Top 10 productos más vendidos (por monto) para no marear a la IA
                        top_10_names = df.groupby(col_prod)['Monto_Clean'].sum().sort_values(ascending=False).head(10).index
                        stats_precios = stats_precios.loc[top_10_names]
                        txt_precios = stats_precios.to_string()

                    # 3. CRUCE REGIONAL
                    txt_cruce = ""
                    if col_reg and col_prod:
                        try:
                            aux = df.groupby([col_reg, col_prod])['Monto_Clean'].sum().reset_index().sort_values([col_reg, 'Monto_Clean'], ascending=[True, False])
                            txt_cruce = aux.groupby(col_reg).head(3).to_string(index=False)
                        except: pass

                    # LLM
                    models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
                    model = genai.GenerativeModel(next((m for m in models if 'flash' in m), models[0]))
                    
                    prompt = f"""
                    ERES CORTEX, ANALISTA DE PRECIOS Y MERCADO PÚBLICO.
                    
                    HECHOS:
                    [TOP 10 PRODUCTOS (POR MONTO TOTAL VENDIDO)]
                    {txt_prod}
                    
                    [DETALLE DE PRECIOS UNITARIOS (DEL TOP 10)] <--- IMPORTANTE
                    Columna 'min' = Precio Mínimo de mercado.
                    Columna 'max' = Precio Máximo de mercado.
                    Columna 'mean' = Precio Promedio.
                    {txt_precios}
                    
                    [CRUCE REGIONAL]
                    {txt_cruce}
                    
                    PREGUNTA: "{q}"
                    
                    INSTRUCCIONES:
                    1. Si preguntan por "Precio Mínimo/Máximo", USA LA TABLA DE [DETALLE DE PRECIOS UNITARIOS]. No inventes.
                    2. Si preguntan por "Más vendidos", usa la tabla de [TOP 10].
                    3. Diferencia siempre entre "Venta Total" (Monto) y "Precio Unitario".
                    """
                    
                    res = model.generate_content(prompt)
                    st.markdown(f'<div class="chat-box">{res.text}</div>', unsafe_allow_html=True)
                except Exception as e:
                    st.error(f"Error: {e}")

    except Exception as e:
        st.error(f"❌ Error archivo: {e}")
