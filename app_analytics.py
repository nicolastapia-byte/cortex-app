import streamlit as st
import google.generativeai as genai
import pandas as pd
import altair as alt
import difflib # 🧠 CEREBRO FUZZY
import io

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="Sentinela - Analítica Comercial", page_icon="📊", layout="wide")

# --- CSS PRO (ESTILO T-9000) ---
st.markdown("""
    <style>
    .stApp { background-color: #0E1117; color: #FAFAFA; }
    h1 { color: #4A90E2; font-family: 'Helvetica Neue', sans-serif; font-weight: 700; }
    h2, h3 { font-family: 'Helvetica Neue', sans-serif; }
    div[data-testid="stMetricValue"] { font-size: 24px !important; color: #00D4FF; font-weight: bold; }
    
    /* ANIMACIÓN ROBOT */
    .robot-container { display: flex; justify-content: center; animation: float-breathe 4s infinite; padding-bottom: 20px; }
    .robot-img { width: 100px; filter: drop-shadow(0 0 15px rgba(0, 212, 255, 0.6)); }
    @keyframes float-breathe { 0%, 100% { transform: translateY(0); } 50% { transform: translateY(-10px); } }
    
    /* CHAT */
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
    if st.button("🗑️ Reiniciar Memoria"):
        st.session_state.history = []
        st.session_state.entidad_activa = None
        st.rerun()
    if "GOOGLE_API_KEY" in st.secrets:
        genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
    else:
        st.error("⚠️ Falta API Key.")
        st.stop()

# --- MEMORIA ---
if "history" not in st.session_state: st.session_state.history = []
if "entidad_activa" not in st.session_state: st.session_state.entidad_activa = None

# --- FUNCIONES DE INTELIGENCIA (V18) ---
def normalizar_agresivo(texto):
    """Elimina ruido para comparar 'Wall Ride' con 'wallride'."""
    if not isinstance(texto, str): return ""
    return texto.lower().replace(" ", "").replace(".", "").replace(",", "").replace("-", "")

def buscar_entidad_avanzada(df, col_prov, col_org, query):
    """Motor de Búsqueda Fuzzy + Normalizado."""
    stop_words = ["que", "quien", "dame", "el", "la", "detalle", "oc", "orden", "compra", "producto", "vende", "de", "lo", "los", "las", "dime", "codigo"]
    keywords = [w for w in query.split() if w.lower() not in stop_words and len(w) > 2]
    
    if not keywords: return None, None

    query_clean = normalizar_agresivo("".join(keywords))
    posibles_cols = [c for c in [col_prov, col_org] if c]
    
    # 1. BARRIDO EXACTO/NORMALIZADO
    for col in posibles_cols:
        lista_nombres = df[col].dropna().unique()
        for nombre_real in lista_nombres:
            if query_clean in normalizar_agresivo(str(nombre_real)): return nombre_real, col

    # 2. BÚSQUEDA DIFUSA (FUZZY)
    for col in posibles_cols:
        lista_nombres = [str(x) for x in df[col].dropna().unique()]
        for k in keywords:
            matches = difflib.get_close_matches(k, lista_nombres, n=1, cutoff=0.65) # Umbral de tolerancia
            if matches: return matches[0], col
                
    return None, None

# --- FUNCIONES DE DATOS ---
def detectar_columna(df, posibles, excluir=[]):
    for p in posibles:
        for col in df.columns:
            if any(exc.lower() in col.lower() for exc in excluir): continue
            if p.lower() in col.lower() and df[col].notna().sum() > 0: return col
    return None

def limpiar_monto(serie):
    if serie.dtype == object: return serie.astype(str).str.replace(r'[$.]', '', regex=True).astype(float)
    return serie

# --- GEO CONFIG (V15) ---
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
        
        # DETECCIÓN INTELIGENTE
        col_monto = detectar_columna(df, ['TotalNeto', 'TotalLinea', 'Monto Total', 'Total'])
        col_monto_uni = detectar_columna(df, ['Monto Unitario', 'Precio Unitario', 'PrecioNeto', 'Precio'])
        col_org = detectar_columna(df, ['Nombre Organismo', 'NombreOrganismo', 'NombreUnidad', 'Unidad'], excluir=['Rut'])
        col_reg = detectar_columna(df, ['RegionUnidad', 'Region'])
        col_prod = detectar_columna(df, ['Nombre Producto', 'Producto', 'NombreProducto', 'Descripcion'])
        col_prov = detectar_columna(df, ['Nombre Proveedor', 'NombreProvider', 'Proveedor', 'Vendedor', 'Empresa'], excluir=['Rut', 'Codigo'])
        col_cant = detectar_columna(df, ['Cantidad Adjudicada', 'Cantidad', 'Cant'])
        col_id = detectar_columna(df, ['CodigoExterno', 'Codigo Licitación', 'Orden de Compra', 'Codigo', 'ID', 'OC'])
        col_fecha = detectar_columna(df, ['Fecha Adjudicación', 'FechaCreacion', 'Fecha'])

        # LIMPIEZA DE MONTOS
        if col_monto: df['Monto_Clean'] = limpiar_monto(df[col_monto])
        elif col_monto_uni and col_cant: df['Monto_Clean'] = limpiar_monto(df[col_monto_uni]) * pd.to_numeric(df[col_cant], errors='coerce').fillna(1)
        elif col_monto_uni: df['Monto_Clean'] = limpiar_monto(df[col_monto_uni])
        else: df['Monto_Clean'] = 0
            
        st.divider()
        
        # --- SECCIÓN 1: KPIs ---
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("💰 Mercado Total", f"${df['Monto_Clean'].sum():,.0f}")
        k2.metric("🎫 Ticket Promedio", f"${df['Monto_Clean'].mean():,.0f}")
        k3.metric("📄 Registros", f"{len(df):,}")
        top_lider = df.groupby(col_prov)['Monto_Clean'].sum().idxmax() if col_prov else "N/A"
        k4.metric("🏆 Líder", f"{str(top_lider)[:15]}..")
        st.markdown("---")

        # --- SECCIÓN 2: GRÁFICOS NIVEL 1 (Compradores vs Competencia) ---
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
        
        # --- SECCIÓN 3: GRÁFICOS NIVEL 2 (Mapas y Productos) ---
        c3, c4 = st.columns([1, 1])
        
        with c3:
            st.subheader("📍 Distribución Geográfica (Norte a Sur)")
            if col_reg:
                # Normalización para el gráfico Lollipop
                df['Region_Norm'] = df[col_reg].apply(normalizar_region)
                d_geo = df.groupby('Region_Norm')['Monto_Clean'].sum().reset_index()
                
                # Gráfico Lollipop (El Esqueleto)
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
            else: st.info("No se detectó columna de Producto.")

        # --- SECCIÓN 4: CORTEX CHAT (CEREBRO V18 + MEMORIA) ---
        st.divider()
        st.subheader("🤖 Cortex Strategic Advisor")
        
        # Historial
        for msg in st.session_state.history:
            role = "user-msg" if msg["role"] == "user" else "bot-msg"
            icon = "👤" if msg["role"] == "user" else "🤖"
            st.markdown(f'<div class="{role}">{icon} {msg["content"]}</div>', unsafe_allow_html=True)

        q = st.text_input("Consulta:", placeholder="Ej: ¿Qué vende Wall Ride? ... luego ... ¿Dame los códigos de OC?", label_visibility="collapsed")
        
        if st.button("⚡ ANALIZAR") and q:
            st.session_state.history.append({"role": "user", "content": q})
            
            with st.spinner("Cortex procesando..."):
                try:
                    # 1. BÚSQUEDA AVANZADA (FUZZY)
                    nuevo_nombre, nueva_col = buscar_entidad_avanzada(df, col_prov, col_org, q)
                    
                    if nuevo_nombre:
                        st.session_state.entidad_activa = {"nombre": nuevo_nombre, "columna": nueva_col}
                        msg_sistema = f"✅ ENTIDAD DETECTADA: '{nuevo_nombre}'."
                    elif st.session_state.entidad_activa:
                        # Si no hay match nuevo, pero hay memoria, verificamos si la intención es cambiar
                        # Simple heurística: Si la frase es corta y parece nombre, intentamos buscar de nuevo o alertar
                        msg_sistema = f"MANTENIENDO FOCO: '{st.session_state.entidad_activa['nombre']}'."
                    else:
                        msg_sistema = "⚠️ ALERTA: No se encontró la entidad en la base de datos."
                        st.session_state.entidad_activa = None

                    # 2. EXTRACCIÓN DE DATOS
                    contexto_data = ""
                    if st.session_state.entidad_activa:
                        nombre = st.session_state.entidad_activa["nombre"]
                        col = st.session_state.entidad_activa["columna"]
                        df_f = df[df[col] == nombre].copy()
                        total = df_f['Monto_Clean'].sum()
                        
                        prods = df_f.groupby(col_prod)['Monto_Clean'].sum().sort_values(ascending=False).head(10).to_string() if col_prod else "N/A"
                        
                        # Tabla de Detalles (OCs)
                        txt_ocs = ""
                        keywords_detalle = ["oc", "orden", "codigo", "código", "detalle", "id", "fecha"]
                        if any(k in q.lower() for k in keywords_detalle) and col_id:
                            cols = [c for c in [col_fecha, col_id, col_prod, 'Monto_Clean'] if c]
                            if col_fecha: 
                                try: df_f = df_f.sort_values(col_fecha, ascending=False)
                                except: pass
                            txt_ocs = f"\n[TABLA DE DETALLE - ÚLTIMAS 10 COMPRAS]\n{df_f[cols].head(10).to_string(index=False)}"

                        contexto_data = f"ENTIDAD: {nombre}\nTOTAL: ${total:,.0f}\nTOP PRODUCTOS:\n{prods}\n{txt_ocs}"
                    else:
                        # Si falló la búsqueda, no pasamos datos para evitar alucinaciones
                        contexto_data = "NO HAY DATOS. INFORMA QUE NO SE ENCONTRÓ LA EMPRESA/ORGANISMO."

                    # 3. GENERACIÓN RESPUESTA
                    models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
                    model = genai.GenerativeModel(next((m for m in models if 'flash' in m), models[0]))
                    
                    prompt = f"""
                    ERES CORTEX.
                    ESTADO: {msg_sistema}
                    DATOS:
                    {contexto_data}
                    PREGUNTA: "{q}"
                    
                    INSTRUCCIONES:
                    1. Si el estado es ALERTA, di que no encontraste la empresa (sé honesto).
                    2. Si hay datos, responde directo y ejecutivo.
                    3. Si hay tabla de OC, preséntala limpia.
                    """
                    
                    res = model.generate_content(prompt)
                    st.session_state.history.append({"role": "assistant", "content": res.text})
                    st.rerun()

                except Exception as e:
                    st.error(f"Error: {e}")

    except Exception as e:
        st.error(f"❌ Error archivo: {e}")
