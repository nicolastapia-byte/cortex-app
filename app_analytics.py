import streamlit as st
import google.generativeai as genai
import pandas as pd
import altair as alt
import io

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="Sentinela - Analítica Comercial", page_icon="📊", layout="wide")

# --- CSS PRO ---
st.markdown("""
    <style>
    .stApp { background-color: #0E1117; color: #FAFAFA; }
    h1 { color: #4A90E2; font-family: 'Helvetica Neue', sans-serif; font-weight: 700; }
    div[data-testid="stMetricValue"] { font-size: 24px !important; color: #00D4FF; font-weight: bold; }
    .robot-container { display: flex; justify-content: center; animation: float-breathe 4s infinite; padding-bottom: 20px; }
    .robot-img { width: 100px; filter: drop-shadow(0 0 15px rgba(0, 212, 255, 0.6)); }
    @keyframes float-breathe { 0%, 100% { transform: translateY(0); } 50% { transform: translateY(-10px); } }
    .chat-box { background-color: #1E2329; padding: 20px; border-radius: 10px; border-left: 5px solid #00D4FF; margin-top: 15px; color: #E0E0E0; }
    .user-msg { text-align: right; color: #A0A0A0; font-style: italic; margin-bottom: 5px; }
    .bot-msg { text-align: left; color: #E0E0E0; margin-bottom: 15px; border-bottom: 1px solid #333; padding-bottom: 10px; }
    .stButton>button { background: linear-gradient(90deg, #2E5CB8 0%, #4A00E0 100%); color: white; border-radius: 8px; border: none; padding: 0.6rem 1.5rem; font-weight: 600; }
    </style>
    """, unsafe_allow_html=True)

# --- SIDEBAR ---
with st.sidebar:
    st.markdown("""<div class="robot-container"><img src="https://cdn-icons-png.flaticon.com/512/4712/4712035.png" class="robot-img"></div>""", unsafe_allow_html=True)
    st.title("Cortex Analytics")
    st.info("Sube tu histórico (OC, Licitaciones o Cotizaciones).")
    
    # CONEXIÓN SEGURA
    if "GOOGLE_API_KEY" in st.secrets:
        try:
            genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
            st.success("✅ Sistema Conectado")
        except Exception as e:
            st.error(f"Error de Llave: {e}")
    else:
        st.error("⚠️ Falta API Key en secrets.toml")
        st.stop()

    if st.button("🗑️ Reiniciar Memoria"):
        st.session_state.history = []
        st.session_state.entidad_activa = None
        st.rerun()

# --- MEMORIA ---
if "history" not in st.session_state: st.session_state.history = []
if "entidad_activa" not in st.session_state: st.session_state.entidad_activa = None

# --- MOTOR DE BÚSQUEDA NUCLEAR (V26) ---
def normalizar_nuclear(texto):
    """Destruye cualquier formato: minusculas, sin espacios, sin simbolos."""
    if not isinstance(texto, str): return ""
    return texto.lower().replace(" ", "").replace(".", "").replace(",", "").replace("-", "").replace("_", "").replace("/", "")

def buscar_nuclear(df, col_prov, col_org, query):
    """
    Busca por coincidencia de ADN (slug in slug).
    Si falla en columnas clave, busca en TODO el DataFrame.
    """
    log = [] # Para depuración
    stop_words = ["que", "quien", "dame", "el", "la", "detalle", "oc", "orden", "compra", "producto", "vende", "de", "lo", "los", "las", "dime", "codigo", "precio", "cuanto", "valor", "es", "son", "sobre", "del", "al", "en", "para", "por", "sus"]
    
    # 1. Limpiar Query
    keywords = [w for w in query.split() if w.lower() not in stop_words and len(w) > 1]
    if not keywords: 
        return None, None, ["Query vacía después de limpiar."]
    
    # "Wall Ride" -> "wallride"
    query_slug = normalizar_nuclear("".join(keywords))
    log.append(f"Slug de búsqueda: '{query_slug}'")

    # 2. Definir dónde buscar (Prioridad: Proveedor -> Organismo -> Todo lo demás)
    cols_prioridad = [c for c in [col_prov, col_org] if c]
    cols_extra = [c for c in df.select_dtypes(include=['object']).columns if c not in cols_prioridad]
    
    todas_cols = cols_prioridad + cols_extra
    
    # 3. Ejecutar Barrido Nuclear
    for col in todas_cols:
        # Optimización: Solo buscar en valores únicos para no iterar millones de filas
        valores_unicos = df[col].dropna().unique()
        
        for val in valores_unicos:
            val_str = str(val)
            val_slug = normalizar_nuclear(val_str)
            
            # MAGIA: ¿Está 'wallride' dentro de 'comercialwallridesupplyltda'?
            if query_slug in val_slug:
                log.append(f"✅ MATCH ENCONTRADO en columna '{col}': '{val}'")
                return val, col, log
                
    log.append("❌ Fin del barrido nuclear. No se encontraron coincidencias.")
    return None, None, log

# --- FUNCIONES BASE ---
def detectar_columna(df, posibles, excluir=[]):
    for p in posibles:
        for col in df.columns:
            if any(exc.lower() in col.lower() for exc in excluir): continue
            if p.lower() in col.lower() and df[col].notna().sum() > 0: return col
    return None

def limpiar_monto(serie):
    if serie.dtype == object: return serie.astype(str).str.replace(r'[$.]', '', regex=True).astype(float)
    return serie

# Geo
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

# --- APP PRINCIPAL ---
st.title("📊 Tablero de Comando Comercial")
uploaded_file = st.file_uploader("📂 Cargar Datos (Excel/CSV)", type=["xlsx", "csv"])

if uploaded_file:
    try:
        # CARGA
        if uploaded_file.name.endswith('.csv'):
            try: df = pd.read_csv(uploaded_file, encoding='utf-8')
            except: df = pd.read_csv(uploaded_file, encoding='latin-1')
        else: df = pd.read_excel(uploaded_file)
        
        # DETECCIÓN
        col_monto = detectar_columna(df, ['TotalNeto', 'TotalLinea', 'Monto Total', 'Total'])
        col_monto_uni = detectar_columna(df, ['Monto Unitario', 'Precio Unitario', 'PrecioNeto', 'Precio'])
        col_org = detectar_columna(df, ['Nombre Organismo', 'NombreOrganismo', 'NombreUnidad', 'Unidad'], excluir=['Rut'])
        col_reg = detectar_columna(df, ['RegionUnidad', 'Region'])
        col_prod = detectar_columna(df, ['Nombre Producto', 'Producto', 'NombreProducto', 'Descripcion'])
        col_prov = detectar_columna(df, ['Nombre Proveedor', 'NombreProvider', 'Proveedor', 'Vendedor', 'Empresa'], excluir=['Rut', 'Codigo'])
        col_cant = detectar_columna(df, ['Cantidad Adjudicada', 'Cantidad', 'Cant'])
        col_id = detectar_columna(df, ['CodigoExterno', 'Codigo Licitación', 'Orden de Compra', 'Codigo', 'ID', 'OC'])
        col_fecha = detectar_columna(df, ['Fecha Adjudicación', 'FechaCreacion', 'Fecha'])

        # MONTOS
        if col_monto: df['Monto_Clean'] = limpiar_monto(df[col_monto])
        elif col_monto_uni and col_cant: df['Monto_Clean'] = limpiar_monto(df[col_monto_uni]) * pd.to_numeric(df[col_cant], errors='coerce').fillna(1)
        elif col_monto_uni: df['Monto_Clean'] = limpiar_monto(df[col_monto_uni])
        else: df['Monto_Clean'] = 0
            
        if col_monto_uni: df['Precio_Clean'] = limpiar_monto(df[col_monto_uni])
        else: df['Precio_Clean'] = 0
            
        st.divider()
        
        # KPI
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("💰 Mercado Total", f"${df['Monto_Clean'].sum():,.0f}")
        k2.metric("🎫 Ticket Promedio", f"${df['Monto_Clean'].mean():,.0f}")
        k3.metric("📄 Registros", f"{len(df):,}")
        top_lider = df.groupby(col_prov)['Monto_Clean'].sum().idxmax() if col_prov else "N/A"
        k4.metric("🏆 Líder", f"{str(top_lider)[:15]}..")
        st.markdown("---")

        # GRÁFICOS
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("🏛️ Top Compradores")
            if col_org:
                d = df.groupby(col_org)['Monto_Clean'].sum().reset_index().sort_values('Monto_Clean', ascending=False).head(10)
                st.altair_chart(alt.Chart(d).mark_bar(cornerRadius=5).encode(
                    x=alt.X('Monto_Clean', title='Monto ($)'), y=alt.Y(col_org, sort='-x', title=''), color=alt.value('#FF6B6B'), tooltip=[col_org, 'Monto_Clean']
                ).properties(height=300), use_container_width=True)
        with c2:
            st.subheader("🏢 Top Competencia")
            if col_prov:
                d = df.groupby(col_prov)['Monto_Clean'].sum().reset_index().sort_values('Monto_Clean', ascending=False).head(10)
                st.altair_chart(alt.Chart(d).mark_bar(cornerRadius=5).encode(
                    x=alt.X('Monto_Clean', title='Monto ($)'), y=alt.Y(col_prov, sort='-x', title=''), color=alt.value('#4ECDC4'), tooltip=[col_prov, 'Monto_Clean']
                ).properties(height=300), use_container_width=True)

        st.markdown("---")
        
        # GEO Y PRODUCTOS
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
            else: st.info("No se detectó columna de Región.")

        with c4:
            st.subheader("📦 Top 15 Productos")
            if col_prod:
                d_prod = df.groupby(col_prod)['Monto_Clean'].sum().reset_index().sort_values('Monto_Clean', ascending=False).head(15)
                st.altair_chart(alt.Chart(d_prod).mark_bar(cornerRadius=5).encode(
                    x=alt.X('Monto_Clean', title='Monto ($)'), y=alt.Y(col_prod, sort='-x', title=''), color=alt.value('#4A90E2'), tooltip=[col_prod, 'Monto_Clean']
                ).properties(height=500), use_container_width=True)

        # --- CHAT V26 (CON BARRIDO NUCLEAR) ---
        st.divider()
        st.subheader("🤖 Cortex Strategic Advisor")
        
        for msg in st.session_state.history:
            role = "user-msg" if msg["role"] == "user" else "bot-msg"
            icon = "👤" if msg["role"] == "user" else "🤖"
            st.markdown(f'<div class="{role}">{icon} {msg["content"]}</div>', unsafe_allow_html=True)

        q = st.text_input("Consulta:", placeholder="Ej: ¿Qué vende Wall Ride? ... ¿Precio mínimo?", label_visibility="collapsed")
        
        if st.button("⚡ ANALIZAR") and q:
            st.session_state.history.append({"role": "user", "content": q})
            
            with st.spinner("Ejecutando Barrido Nuclear..."):
                try:
                    # 1. BÚSQUEDA NUCLEAR
                    nuevo_nombre, nueva_col, log_busqueda = buscar_nuclear(df, col_prov, col_org, q)
                    
                    # LOG VISIBLE (DEBUG PARA QUE VEAS QUE FUNCIONA)
                    with st.expander("🕵️‍♂️ Ver Log de Búsqueda (Debug)"):
                        st.write(log_busqueda)
                        if nuevo_nombre: st.success(f"¡Encontrado! -> {nuevo_nombre}")
                        else: st.error("No encontrado en barrido nuclear.")

                    if nuevo_nombre:
                        st.session_state.entidad_activa = {"nombre": nuevo_nombre, "columna": nueva_col}
                        msg_sistema = f"✅ ENTIDAD DETECTADA: '{nuevo_nombre}'."
                    elif st.session_state.entidad_activa:
                        msg_sistema = f"MANTENIENDO FOCO: '{st.session_state.entidad_activa['nombre']}'."
                    else:
                        msg_sistema = "⚠️ ALERTA: La entidad no existe en el archivo cargado."
                        st.session_state.entidad_activa = None

                    # 2. DATOS
                    contexto_data = ""
                    if st.session_state.entidad_activa:
                        nombre = st.session_state.entidad_activa["nombre"]
                        col = st.session_state.entidad_activa["columna"]
                        df_f = df[df[col] == nombre].copy()
                        total = df_f['Monto_Clean'].sum()
                        
                        prods = df_f.groupby(col_prod)['Monto_Clean'].sum().sort_values(ascending=False).head(10).to_string() if col_prod else "N/A"
                        
                        # PRECIOS
                        txt_precios_unitarios = "No disponible."
                        if col_monto_uni:
                            stats = df_f.groupby(col_prod)['Precio_Clean'].agg(['min', 'max', 'mean'])
                            top_names = df_f.groupby(col_prod)['Monto_Clean'].sum().sort_values(ascending=False).head(10).index
                            txt_precios_unitarios = stats.loc[top_names].to_string()

                        # DETALLE OC
                        txt_ocs = ""
                        keywords_detalle = ["oc", "orden", "codigo", "código", "detalle", "id", "fecha"]
                        if any(k in q.lower() for k in keywords_detalle) and col_id:
                            cols = [c for c in [col_fecha, col_id, col_prod, 'Monto_Clean'] if c]
                            if col_fecha: df_f = df_f.sort_values(col_fecha, ascending=False)
                            txt_ocs = f"\n[TABLA DETALLE OC (RAW)]\n{df_f[cols].head(10).to_string(index=False)}"

                        contexto_data = f"ENTIDAD: {nombre}\nTOTAL: ${total:,.0f}\n[PRECIOS UNITARIOS MIN/MAX]\n{txt_precios_unitarios}\n[PRODUCTOS]\n{prods}\n{txt_ocs}"
                    else:
                        contexto_data = "NO HAY DATOS. LA ENTIDAD NO EXISTE EN LA BASE."

                    # 3. LLM
                    models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
                    model = genai.GenerativeModel(next((m for m in models if 'flash' in m), models[0]))
                    
                    prompt = f"""
                    ERES CORTEX.
                    ESTADO: {msg_sistema}
                    DATOS:
                    {contexto_data}
                    PREGUNTA: "{q}"
                    INSTRUCCIONES:
                    1. Si el estado es ALERTA, di que no encontraste la empresa.
                    2. Si preguntan precios, usa la tabla [PRECIOS UNITARIOS].
                    3. Si hay tabla OC, GENERA UNA TABLA MARKDOWN bonita.
                    """
                    
                    res = model.generate_content(prompt)
                    st.session_state.history.append({"role": "assistant", "content": res.text})
                    st.rerun()

                except Exception as e:
                    if "429" in str(e):
                         st.error("🚦 ¡Sobrecarga! Actualiza la API Key.")
                    else:
                        st.error(f"Error: {e}")

    except Exception as e:
        st.error(f"❌ Error archivo: {e}")
