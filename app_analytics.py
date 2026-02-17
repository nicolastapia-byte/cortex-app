import streamlit as st
import google.generativeai as genai
import pandas as pd
import altair as alt
import difflib # 🧠 LIBRERÍA DE INTELIGENCIA DE TEXTO
import io

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="Sentinela - Analítica Comercial", page_icon="📊", layout="wide")

# --- CSS ---
st.markdown("""
    <style>
    .stApp { background-color: #0E1117; color: #FAFAFA; }
    h1 { color: #4A90E2; font-family: 'Helvetica Neue', sans-serif; }
    div[data-testid="stMetricValue"] { font-size: 24px !important; color: #00D4FF; font-weight: bold; }
    .robot-container { display: flex; justify-content: center; animation: float-breathe 4s infinite; padding-bottom: 20px; }
    .robot-img { width: 100px; filter: drop-shadow(0 0 15px rgba(0, 212, 255, 0.6)); }
    @keyframes float-breathe { 0%, 100% { transform: translateY(0); } 50% { transform: translateY(-10px); } }
    .chat-box { background-color: #1E2329; padding: 20px; border-radius: 10px; border-left: 5px solid #00D4FF; margin-top: 15px; color: #E0E0E0; }
    .user-msg { text-align: right; color: #A0A0A0; font-style: italic; margin-bottom: 5px; }
    .bot-msg { text-align: left; color: #E0E0E0; margin-bottom: 15px; }
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

# --- FUNCIONES DE AUDITORÍA DE TEXTO (NUEVO MOTOR) ---
def normalizar_agresivo(texto):
    """Elimina espacios, puntos y mayúsculas para comparación bruta."""
    if not isinstance(texto, str): return ""
    return texto.lower().replace(" ", "").replace(".", "").replace(",", "").replace("-", "")

def buscar_entidad_avanzada(df, col_prov, col_org, query):
    """
    Motor de Búsqueda V18:
    1. Limpieza de Query (quita palabras vacías).
    2. Búsqueda por Normalización (Wall Ride == wallride).
    3. Búsqueda Difusa (Wallrid ~= Wallride).
    """
    stop_words = ["que", "quien", "dame", "el", "la", "detalle", "oc", "orden", "compra", "producto", "vende", "de", "lo", "los", "las", "dime"]
    # Extraemos las palabras clave reales del usuario (ej: "wall", "ride")
    keywords = [w for w in query.split() if w.lower() not in stop_words and len(w) > 2]
    
    if not keywords: return None, None # Si no hay palabras clave, no buscamos

    # Unimos keywords para búsqueda normalizada (ej: "wallride")
    query_clean = normalizar_agresivo("".join(keywords))
    
    posibles_cols = []
    if col_prov: posibles_cols.append(col_prov)
    if col_org: posibles_cols.append(col_org)
    
    # 1. BARRIDO EXACTO Y NORMALIZADO
    for col in posibles_cols:
        lista_nombres = df[col].dropna().unique()
        for nombre_real in lista_nombres:
            nombre_clean = normalizar_agresivo(str(nombre_real))
            # Si "wallride" está dentro de "comercialwallridelimitada" -> MATCH
            if query_clean in nombre_clean: 
                return nombre_real, col

    # 2. BÚSQUEDA DIFUSA (FUZZY) - Por si escribió "Walride" (falta una L)
    # Usamos difflib para encontrar similitudes > 0.6
    for col in posibles_cols:
        lista_nombres = [str(x) for x in df[col].dropna().unique()]
        # Busca palabras parecidas a las keywords del usuario
        for k in keywords:
            matches = difflib.get_close_matches(k, lista_nombres, n=1, cutoff=0.7)
            if matches:
                return matches[0], col
                
    return None, None

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

# --- APP ---
st.title("📊 Tablero de Comando Comercial")
uploaded_file = st.file_uploader("📂 Cargar Datos (Excel/CSV)", type=["xlsx", "csv"])

if uploaded_file:
    try:
        if uploaded_file.name.endswith('.csv'):
            try: df = pd.read_csv(uploaded_file, encoding='utf-8')
            except: df = pd.read_csv(uploaded_file, encoding='latin-1')
        else: df = pd.read_excel(uploaded_file)
        
        # Detección
        col_monto = detectar_columna(df, ['TotalNeto', 'TotalLinea', 'Monto Total', 'Total'])
        col_monto_uni = detectar_columna(df, ['Monto Unitario', 'Precio Unitario', 'PrecioNeto', 'Precio'])
        col_org = detectar_columna(df, ['Nombre Organismo', 'NombreOrganismo', 'NombreUnidad', 'Unidad'], excluir=['Rut'])
        col_reg = detectar_columna(df, ['RegionUnidad', 'Region'])
        col_prod = detectar_columna(df, ['Nombre Producto', 'Producto', 'NombreProducto', 'Descripcion'])
        col_prov = detectar_columna(df, ['Nombre Proveedor', 'NombreProvider', 'Proveedor', 'Vendedor', 'Empresa'], excluir=['Rut', 'Codigo'])
        col_cant = detectar_columna(df, ['Cantidad Adjudicada', 'Cantidad', 'Cant'])
        col_id = detectar_columna(df, ['CodigoExterno', 'Codigo Licitación', 'Orden de Compra', 'Codigo', 'ID', 'OC'])
        col_fecha = detectar_columna(df, ['Fecha Adjudicación', 'FechaCreacion', 'Fecha'])

        # Montos
        if col_monto: df['Monto_Clean'] = limpiar_monto(df[col_monto])
        elif col_monto_uni and col_cant: df['Monto_Clean'] = limpiar_monto(df[col_monto_uni]) * pd.to_numeric(df[col_cant], errors='coerce').fillna(1)
        elif col_monto_uni: df['Monto_Clean'] = limpiar_monto(df[col_monto_uni])
        else: df['Monto_Clean'] = 0
            
        st.divider()
        
        # KPI
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("💰 Mercado Total", f"${df['Monto_Clean'].sum():,.0f}")
        k2.metric("🎫 Ticket Promedio", f"${df['Monto_Clean'].mean():,.0f}")
        k3.metric("📄 Registros", f"{len(df):,}")
        top_lider = df.groupby(col_prov)['Monto_Clean'].sum().idxmax() if col_prov else "N/A"
        k4.metric("🏆 Líder", f"{str(top_lider)[:15]}..")
        st.markdown("---")

        # GRÁFICOS SIMPLIFICADOS
        c1, c2 = st.columns(2)
        if col_org:
            d = df.groupby(col_org)['Monto_Clean'].sum().reset_index().sort_values('Monto_Clean', ascending=False).head(10)
            st.altair_chart(alt.Chart(d).mark_bar().encode(x='Monto_Clean', y=alt.Y(col_org, sort='-x'), color=alt.value('#FF6B6B')).properties(height=300), use_container_width=True)
        if col_prov:
            d = df.groupby(col_prov)['Monto_Clean'].sum().reset_index().sort_values('Monto_Clean', ascending=False).head(10)
            st.altair_chart(alt.Chart(d).mark_bar().encode(x='Monto_Clean', y=alt.Y(col_prov, sort='-x'), color=alt.value('#4ECDC4')).properties(height=300), use_container_width=True)

        # --- IA CORTEX V18 (AUDITOR) ---
        st.divider()
        st.subheader("🤖 Cortex Strategic Advisor")
        
        for msg in st.session_state.history:
            role = "user-msg" if msg["role"] == "user" else "bot-msg"
            icon = "👤" if msg["role"] == "user" else "🤖"
            st.markdown(f'<div class="{role}">{icon} {msg["content"]}</div>', unsafe_allow_html=True)

        q = st.text_input("Consulta:", placeholder="Ej: ¿Qué vende Wall Ride?", label_visibility="collapsed")
        
        if st.button("⚡ ANALIZAR") and q:
            st.session_state.history.append({"role": "user", "content": q})
            
            with st.spinner("Auditando textos y buscando coincidencias..."):
                try:
                    # 1. BÚSQUEDA AVANZADA (AUDITORÍA)
                    nuevo_nombre, nueva_col = buscar_entidad_avanzada(df, col_prov, col_org, q)
                    
                    if nuevo_nombre:
                        # ¡ENCONTRADO! Actualizamos memoria
                        st.session_state.entidad_activa = {"nombre": nuevo_nombre, "columna": nueva_col}
                        msg_sistema = f"✅ BÚSQUEDA EXITOSA: Se detectó a '{nuevo_nombre}'."
                    elif st.session_state.entidad_activa:
                        # No encontré nada nuevo, ¿seguimos hablando del mismo?
                        # Solo si la pregunta NO parece buscar a alguien nuevo
                        msg_sistema = f"MANTENIENDO FOCO: Seguimos analizando a '{st.session_state.entidad_activa['nombre']}'."
                    else:
                        # No hay nada en memoria y no se encontró nada nuevo
                        msg_sistema = "⚠️ ALERTA: No se encontró la entidad solicitada en la base de datos."
                        # IMPORTANTE: Forzamos a que no invente datos
                        st.session_state.entidad_activa = None 

                    # 2. EXTRACCIÓN DE DATOS (SEGÚN MEMORIA)
                    if st.session_state.entidad_activa:
                        nombre = st.session_state.entidad_activa["nombre"]
                        col = st.session_state.entidad_activa["columna"]
                        df_f = df[df[col] == nombre].copy()
                        
                        total = df_f['Monto_Clean'].sum()
                        
                        # Productos
                        prods = df_f.groupby(col_prod)['Monto_Clean'].sum().sort_values(ascending=False).head(10).to_string() if col_prod else "N/A"
                        
                        # Tabla de Detalles (OCs)
                        txt_ocs = ""
                        palabras_detalle = ["oc", "orden", "codigo", "código", "detalle", "id"]
                        if any(k in q.lower() for k in palabras_detalle) and col_id:
                            cols = [c for c in [col_fecha, col_id, col_prod, 'Monto_Clean'] if c]
                            if col_fecha: df_f = df_f.sort_values(col_fecha, ascending=False)
                            txt_ocs = f"\n[DETALLE DE ÚLTIMAS TRANSACCIONES]\n{df_f[cols].head(10).to_string(index=False)}"

                        contexto_data = f"""
                        ENTIDAD ENCONTRADA: {nombre}
                        MONTO TOTAL: ${total:,.0f}
                        TOP PRODUCTOS:
                        {prods}
                        {txt_ocs}
                        """
                    else:
                        # Si falló la búsqueda, pasamos contexto vacío para que NO ALUCINE
                        contexto_data = "NO SE ENCONTRÓ INFORMACIÓN DE LA ENTIDAD SOLICITADA. INFORMA AL USUARIO QUE NO ESTÁ EN EL EXCEL."

                    # 3. LLM
                    models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
                    model = genai.GenerativeModel(next((m for m in models if 'flash' in m), models[0]))
                    
                    prompt = f"""
                    ERES CORTEX ANALYTICS.
                    TU OBJETIVO: Dar información exacta basada SOLO en lo encontrado.
                    
                    ESTADO DEL SISTEMA: {msg_sistema}
                    
                    DATOS ENCONTRADOS:
                    {contexto_data}
                    
                    PREGUNTA USUARIO: "{q}"
                    
                    INSTRUCCIONES CRÍTICAS:
                    1. Si el estado es "ALERTA", DILE AL USUARIO QUE NO ENCONTRASTE A ESA EMPRESA. No le des datos de otra (como Dimerc).
                    2. Si encontraste la empresa, muestra sus productos y montos.
                    3. Si hay tabla de OC, muéstrala formateada.
                    """
                    
                    res = model.generate_content(prompt)
                    st.session_state.history.append({"role": "assistant", "content": res.text})
                    st.rerun()

                except Exception as e:
                    st.error(f"Error: {e}")

    except Exception as e:
        st.error(f"❌ Error archivo: {e}")
