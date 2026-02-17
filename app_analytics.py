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
    Busca columnas priorizando el orden de 'posibles'.
    'excluir': lista de palabras que SI están en la columna, la descartamos (ej: 'Rut' cuando buscamos Nombres).
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
    if 'rios' in n or 'ríos' in n: return "Los Ríos"
    if 'lagos' in n: return "Los Lagos"
    if 'aysen' in n or 'aysén' in n: return "Aysén"
    if 'magallanes' in n: return "Magallanes"
    return "Otras"

# --- APP ---
st.title("📊 Tablero de Comando Comercial")
uploaded_file = st.file_uploader("📂 Cargar Datos (Excel/CSV)", type=["xlsx", "csv"])

if uploaded_file:
    try:
        # 1. Carga
        if uploaded_file.name.endswith('.csv'):
            try: df = pd.read_csv(uploaded_file, encoding='utf-8')
            except: df = pd.read_csv(uploaded_file, encoding='latin-1')
        else:
            df = pd.read_excel(uploaded_file)
        
        # 2. Detección Inteligente de Columnas
        # Monto Total
        col_monto = detectar_columna(df, ['TotalNeto', 'TotalLinea', 'Monto Total', 'Total'])
        # Monto Unitario (Nuevo para archivo Precios)
        col_monto_uni = detectar_columna(df, ['Monto Unitario', 'Precio Unitario', 'PrecioNeto', 'Precio'])
        
        # Organismo
        col_org = detectar_columna(df, ['Nombre Organismo', 'NombreOrganismo', 'NombreUnidad', 'Unidad', 'Comprador'], excluir=['Rut'])
        
        # Region
        col_reg = detectar_columna(df, ['RegionUnidad', 'Region', 'RegionComprador'])
        
        # Producto
        col_prod = detectar_columna(df, ['Nombre Producto', 'Producto', 'NombreProducto', 'Descripcion'])
        
        # Proveedor (AQUÍ ESTABA EL ERROR: Excluimos 'Rut' para que no se confunda)
        col_prov = detectar_columna(df, ['Nombre Proveedor', 'NombreProvider', 'Proveedor', 'Vendedor', 'Empresa'], excluir=['Rut', 'Codigo', 'ID'])
        
        # Cantidad
        col_cant = detectar_columna(df, ['Cantidad Adjudicada', 'Cantidad', 'Cant'])

        # 3. Lógica de Negocio: Cálculo de Monto Real
        # Si no hay columna "Total", la creamos (Precio * Cantidad)
        if col_monto:
            df['Monto_Clean'] = limpiar_monto(df[col_monto])
        elif col_monto_uni and col_cant:
            # Caso archivo Precios/Cotizaciones
            df['Monto_Clean'] = limpiar_monto(df[col_monto_uni]) * pd.to_numeric(df[col_cant], errors='coerce').fillna(1)
        elif col_monto_uni:
            df['Monto_Clean'] = limpiar_monto(df[col_monto_uni]) # Mejor que nada
        else:
            df['Monto_Clean'] = 0
            
        # Para análisis de precios unitarios
        if col_monto_uni:
             df['Precio_Clean'] = limpiar_monto(df[col_monto_uni])
        else:
             df['Precio_Clean'] = 0

        st.divider()
        
        # --- DASHBOARD ---
        
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
            else: st.info("No se detectó Organismo.")
        
        with c2:
            st.subheader("🏢 Top Competencia")
            if col_prov:
                d_prov = df.groupby(col_prov)['Monto_Clean'].sum().reset_index().sort_values('Monto_Clean', ascending=False).head(10)
                ch_prov = alt.Chart(d_prov).mark_bar(cornerRadius=5).encode(
                    x=alt.X('Monto_Clean', title='Monto ($)'), y=alt.Y(col_prov, sort='-x', title=''), color=alt.value('#4ECDC4'), tooltip=[col_prov, 'Monto_Clean']
                ).properties(height=300)
                st.altair_chart(ch_prov, use_container_width=True)
            else: st.info("No se detectó Proveedor (Nombre).")

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
            else: st.info("No se detectó Región.")

        with c4:
            st.subheader("📦 Top Productos")
            if col_prod:
                d_prod = df.groupby(col_prod)['Monto_Clean'].sum().reset_index().sort_values('Monto_Clean', ascending=False).head(15)
                ch_prod = alt.Chart(d_prod).mark_bar(cornerRadius=5).encode(
                    x=alt.X('Monto_Clean', title='Monto ($)'), y=alt.Y(col_prod, sort='-x', title=''), color=alt.value('#4A90E2'), tooltip=[col_prod, 'Monto_Clean']
                ).properties(height=500)
                st.altair_chart(ch_prod, use_container_width=True)

        # --- IA OMNISCIENTE ---
        st.divider()
        st.subheader("🤖 Cortex Strategic Advisor")
        
        q = st.text_input("Consulta:", placeholder="Ej: ¿Qué proveedor gana más en Biobío? / Precio promedio del top producto", label_visibility="collapsed")
        if st.button("⚡ ANALIZAR") and q:
            with st.spinner("Analizando mercado..."):
                try:
                    # Contexto
                    txt_prod = df.groupby(col_prod)['Monto_Clean'].sum().sort_values(ascending=False).head(10).to_string() if col_prod else ""
                    
                    # Precios Unitarios (Solo si detectamos la columna de precio)
                    txt_precios = "No disponible."
                    if col_prod and col_monto_uni:
                        # Usamos 'Precio_Clean' que limpiamos antes
                        stats = df.groupby(col_prod)['Precio_Clean'].agg(['min', 'max', 'mean'])
                        top_names = df.groupby(col_prod)['Monto_Clean'].sum().sort_values(ascending=False).head(10).index
                        txt_precios = stats.loc[top_names].to_string()

                    # Cruce Regional
                    txt_cruce = ""
                    if 'Region_Norm' in df.columns and col_prod:
                        try:
                            aux = df.groupby(['Region_Norm', col_prod])['Monto_Clean'].sum().reset_index().sort_values(['Region_Norm', 'Monto_Clean'], ascending=[True, False])
                            txt_cruce = aux.groupby('Region_Norm').head(2).to_string(index=False)
                        except: pass

                    # Modelo
                    models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
                    model = genai.GenerativeModel(next((m for m in models if 'flash' in m), models[0]))
                    
                    prompt = f"""
                    ERES CORTEX, EXPERTO EN LICITACIONES.
                    [TOP PRODUCTOS (POR MONTO TOTAL)] {txt_prod}
                    [PRECIOS UNITARIOS REALES (MIN/MAX)] {txt_precios}
                    [TOP PRODUCTOS POR REGIÓN] {txt_cruce}
                    PREGUNTA: "{q}"
                    """
                    res = model.generate_content(prompt)
                    st.markdown(f'<div class="chat-box">{res.text}</div>', unsafe_allow_html=True)
                except Exception as e:
                    st.error(f"Error IA: {e}")

    except Exception as e:
        st.error(f"❌ Error archivo: {e}")
