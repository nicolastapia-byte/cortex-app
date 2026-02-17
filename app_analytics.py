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
    st.info("Sube tu histórico (OC, Licitaciones o Cotizaciones).")
    if "GOOGLE_API_KEY" in st.secrets:
        genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
    else:
        st.error("⚠️ Falta API Key.")
        st.stop()

# --- FUNCIONES ROBUSTAS ---
def detectar_columna(df, posibles, excluir=[]):
    """
    Busca columnas priorizando el orden de 'posibles' y evitando 'excluir'.
    """
    for p in posibles:
        for col in df.columns:
            # 1. Chequeo de Exclusión (Anti-Rut)
            if any(exc.lower() in col.lower() for exc in excluir):
                continue
            
            # 2. Chequeo de Coincidencia
            if p.lower() in col.lower() and df[col].notna().sum() > 0:
                return col
    return None

def limpiar_monto(serie):
    if serie.dtype == object:
        return serie.astype(str).str.replace(r'[$.]', '', regex=True).astype(float)
    return serie

# --- GEO CONFIG ---
ORDEN_CHILE = ["Arica y Parinacota", "Tarapacá", "Antofagasta", "Atacama", "Coquimbo", "Valparaíso", "Metropolitana", "O'Higgins", "Maule", "Ñuble", "Biobío", "Araucanía", "Los Ríos", "Los Lagos", "Aysén", "Magallanes", "Sin Región"]

def normalizar_region(nombre):
    if not isinstance(nombre, str): return "Sin Región"
    n = nombre.lower()
    if 'arica' in n: return "Arica y Parinacota"
    if 'tarapa' in n: return "Tarapacá"
    if 'antofa' in n: return "Antofagasta"
    if 'atacama' in n: return "Atacama"
    if 'coquimbo' in n: return "Coquimbo"
    if 'valpara' in n: return "Valparaíso"
    if 'metrop' in n or 'santiago' in n: return "Metropolitana"
    if 'higgins' in n: return "O'Higgins"
    if 'maule' in n: return "Maule"
    if 'uble' in n: return "Ñuble"
    if 'biob' in n: return "Biobío"
    if 'araucan' in n: return "Araucanía"
    if 'rios' in n: return "Los Ríos"
    if 'lagos' in n: return "Los Lagos"
    if 'aysen' in n: return "Aysén"
    if 'magallanes' in n: return "Magallanes"
    return "Otras"

# --- BÚSQUEDA INTELIGENTE DE ENTIDADES ---
def buscar_entidades(df, columna, query):
    """
    Busca entidades en una columna usando coincidencia flexible (espacios, mayúsculas).
    Retorna una lista de nombres encontrados.
    """
    if not columna: return []
    
    # 1. Limpieza de Query
    stop_words = ["que", "quien", "como", "donde", "el", "la", "los", "las", "un", "una", "por", "para", "con", "del", "al", "esta", "comprando", "vende", "detalle", "dime", "sobre"]
    keywords = [w for w in query.lower().split() if w not in stop_words and len(w) > 2]
    
    encontrados = []
    
    # 2. Búsqueda por Keyword
    for k in keywords:
        # Búsqueda normal (contiene la palabra)
        mask_normal = df[columna].astype(str).str.lower().str.contains(k, regex=False)
        
        # Búsqueda comprimida (para 'skatemarket' vs 'skate market')
        mask_compress = df[columna].astype(str).str.lower().str.replace(" ", "").str.contains(k, regex=False)
        
        match = df[mask_normal | mask_compress][columna].unique()
        encontrados.extend(match)
        
    return list(set(encontrados)) # Eliminar duplicados

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
        col_monto = detectar_columna(df, ['TotalNeto', 'TotalLinea', 'Monto Total', 'Total'])
        col_monto_uni = detectar_columna(df, ['Monto Unitario', 'Precio Unitario', 'PrecioNeto', 'Precio'])
        col_org = detectar_columna(df, ['Nombre Organismo', 'NombreOrganismo', 'NombreUnidad', 'Unidad', 'Comprador'], excluir=['Rut'])
        col_reg = detectar_columna(df, ['RegionUnidad', 'Region', 'RegionComprador'])
        col_prod = detectar_columna(df, ['Nombre Producto', 'Producto', 'NombreProducto', 'Descripcion'])
        # AQUI AGREGAMOS MAS SINÓNIMOS PARA ASEGURARNOS
        col_prov = detectar_columna(df, ['Nombre Proveedor', 'NombreProvider', 'Proveedor', 'Razon Social', 'Vendedor', 'Empresa'], excluir=['Rut', 'Codigo'])
        col_cant = detectar_columna(df, ['Cantidad Adjudicada', 'Cantidad', 'Cant'])

        # Lógica de Montos
        if col_monto:
            df['Monto_Clean'] = limpiar_monto(df[col_monto])
        elif col_monto_uni and col_cant:
            df['Monto_Clean'] = limpiar_monto(df[col_monto_uni]) * pd.to_numeric(df[col_cant], errors='coerce').fillna(1)
        elif col_monto_uni:
            df['Monto_Clean'] = limpiar_monto(df[col_monto_uni])
        else:
            df['Monto_Clean'] = 0
            
        if col_monto_uni: df['Precio_Clean'] = limpiar_monto(df[col_monto_uni])
        else: df['Precio_Clean'] = 0

        st.divider()
        
        # KPI 1
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("💰 Mercado Total", f"${df['Monto_Clean'].sum():,.0f}")
        k2.metric("🎫 Ticket Promedio", f"${df['Monto_Clean'].mean():,.0f}")
        k3.metric("📄 Registros", f"{len(df):,}")
        
        top_lider = "N/A"
        if col_prov: top_lider = df.groupby(col_prov)['Monto_Clean'].sum().idxmax()
        elif col_org: top_lider = df[col_org].value_counts().idxmax()
        k4.metric("🏆 Líder", f"{str(top_lider)[:15]}..")

        st.markdown("---")

        # GRÁFICOS
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
        
        c3, c4 = st.columns([1, 1])
        with c3:
            st.subheader("📍 Distribución Geográfica")
            if col_reg:
                df['Region_Norm'] = df[col_reg].apply(normalizar_region)
                d_geo = df.groupby('Region_Norm')['Monto_Clean'].sum().reset_index()
                
                base = alt.Chart(d_geo).encode(y=alt.Y('Region_Norm', sort=ORDEN_CHILE, title=None), x=alt.X('Monto_Clean', title='Monto ($)'), tooltip=['Region_Norm', 'Monto_Clean'])
                rule = base.mark_rule(color="#525252", opacity=0.6)
                circle = base.mark_circle(size=200, opacity=1).encode(color=alt.Color('Monto_Clean', scale=alt.Scale(scheme='turbo'), legend=None), size=alt.Size('Monto_Clean', legend=None, scale=alt.Scale(range=[100, 1000])))
                text = base.mark_text(align='left', dx=10, color="#FAFAFA").encode(text=alt.Text('Monto_Clean', format='$.2s'))
                
                st.altair_chart((rule + circle + text).properties(height=500), use_container_width=True)

        with c4:
            st.subheader("📦 Top Productos")
            if col_prod:
                d_prod = df.groupby(col_prod)['Monto_Clean'].sum().reset_index().sort_values('Monto_Clean', ascending=False).head(15)
                ch_prod = alt.Chart(d_prod).mark_bar(cornerRadius=5).encode(
                    x=alt.X('Monto_Clean', title='Monto ($)'), y=alt.Y(col_prod, sort='-x', title=''), color=alt.value('#4A90E2'), tooltip=[col_prod, 'Monto_Clean']
                ).properties(height=500)
                st.altair_chart(ch_prod, use_container_width=True)

        # --- IA OMNISCIENTE V3 (DETECTIVE DE ENTIDADES) ---
        st.divider()
        st.subheader("🤖 Cortex Strategic Advisor")
        
        q = st.text_input("Consulta:", placeholder="Ej: ¿Qué productos vende Skatemarket? / ¿Qué compra el Hospital X?", label_visibility="collapsed")
        if st.button("⚡ INVESTIGAR") and q:
            with st.spinner("Ejecutando búsqueda profunda..."):
                try:
                    # 1. BÚSQUEDA DE ENTIDAD ESPECÍFICA
                    txt_especifico = "No se detectó una entidad específica."
                    entidades_match = []
                    
                    # Buscamos en Proveedores y Organismos usando la función inteligente
                    if col_prov:
                        entidades_match.extend(buscar_entidades(df, col_prov, q))
                    if col_org:
                        entidades_match.extend(buscar_entidades(df, col_org, q))
                    
                    if entidades_match:
                        # Filtramos el DF por las entidades encontradas
                        filtro = df[df[col_prov].isin(entidades_match) | df[col_org].isin(entidades_match)] if col_prov and col_org else pd.DataFrame()
                        
                        # Si no funcionó el filtro combinado, probamos individual
                        if filtro.empty and col_prov: filtro = df[df[col_prov].isin(entidades_match)]
                        
                        total_entidad = filtro['Monto_Clean'].sum()
                        
                        # Detalle de productos de esa entidad
                        prods_entidad = "Sin detalle."
                        if col_prod:
                            prods_entidad = filtro.groupby(col_prod)['Monto_Clean'].sum().sort_values(ascending=False).head(10).to_string()

                        txt_especifico = f"""
                        ✅ SE ENCONTRARON LAS SIGUIENTES ENTIDADES: {entidades_match}
                        - Total Transado (Grupo): ${total_entidad:,.0f}
                        - TOP PRODUCTOS ESPECÍFICOS:
                        {prods_entidad}
                        """
                    
                    # 2. Contexto General
                    txt_prod = df.groupby(col_prod)['Monto_Clean'].sum().sort_values(ascending=False).head(10).to_string() if col_prod else ""
                    
                    models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
                    model = genai.GenerativeModel(next((m for m in models if 'flash' in m), models[0]))
                    
                    prompt = f"""
                    ERES CORTEX, EXPERTO EN DATOS.
                    
                    [BÚSQUEDA ESPECÍFICA]
                    {txt_especifico}
                    
                    [CONTEXTO GENERAL]
                    Top Productos Globales: {txt_prod}
                    
                    PREGUNTA: "{q}"
                    
                    INSTRUCCIONES:
                    1. Si hay datos en [BÚSQUEDA ESPECÍFICA], ÚSALOS. Es la prioridad.
                    2. Responde: "He analizado a [Nombre] y encontré que vende..."
                    3. Si no hay búsqueda específica, usa el contexto general.
                    """
                    res = model.generate_content(prompt)
                    st.markdown(f'<div class="chat-box">{res.text}</div>', unsafe_allow_html=True)
                except Exception as e:
                    st.error(f"Error IA: {e}")

    except Exception as e:
        st.error(f"❌ Error archivo: {e}")
