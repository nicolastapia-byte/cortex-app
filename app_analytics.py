import streamlit as st
import pandas as pd
import google.generativeai as genai
import traceback

# ==========================================
# 1. CONFIGURACIÓN DE PÁGINA Y ESTÉTICA
# ==========================================
st.set_page_config(page_title="Cortex Analytics: Suite Comercial", page_icon="🤖", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #0e1117; color: #e0e0e0; }
    .stSidebar { background-color: #161b22; border-right: 1px solid #30363d; }
    h1 { color: #00d4ff; font-family: 'Inter', sans-serif; font-weight: 800; }
    .stChatMessage { border-radius: 15px; border: 1px solid #30363d; margin-bottom: 10px; }
    div[data-testid="stMetricValue"] { color: #00d4ff; }
    .prompt-box { background-color: #21262d; padding: 10px; border-radius: 8px; margin-bottom: 5px; border-left: 3px solid #00d4ff; font-size: 0.9em;}
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# 2. INICIALIZACIÓN DE IA Y ESTADOS
# ==========================================
if "GEMINI_API_KEY" not in st.secrets:
    st.error("❌ Error Crítico: No se encontró 'GEMINI_API_KEY' en tus secretos.")
    st.stop()

try:
    api_key = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-1.5-flash')
except Exception as e:
    st.error(f"❌ Error conectando con Gemini: {str(e)}")
    st.stop()

if "messages" not in st.session_state:
    st.session_state.messages = []

# ==========================================
# 3. MOTOR DE RUTEO INTELIGENTE
# ==========================================
def detectar_tipo_reporte(columnas):
    cols_str = " ".join(columnas).lower()
    if "estado compra ágil" in cols_str or "estado compra agil" in cols_str:
        return "Compras Ágiles"
    elif "estado licitación" in cols_str or "estado licitacion" in cols_str:
        return "Licitaciones"
    elif "fecha lectura" in cols_str or "precio sin oferta" in cols_str:
        return "Convenio Marco"
    else:
        return "Análisis General"

# ==========================================
# 4. INTERFAZ: SIDEBAR Y CARGA DE DATOS
# ==========================================
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/4712/4712139.png", width=80)
    st.title("Cortex Core")
    st.markdown("Sube tu reporte de Mercado Público / Convenios.")
    uploaded_file = st.file_uploader("Cargar Archivo Excel/CSV", type=['xlsx', 'csv'])
    
    st.markdown("---")
    if st.button("🧹 Limpiar Historial de Chat"):
        st.session_state.messages = []
        st.rerun()

# ==========================================
# 5. NÚCLEO DE PROCESAMIENTO Y DASHBOARDS
# ==========================================
if uploaded_file:
    try:
        if uploaded_file.name.endswith('csv'):
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)
    except Exception as e:
        st.error(f"Error al leer el archivo: {e}")
        st.stop()

    tipo_reporte = detectar_tipo_reporte(df.columns.tolist())
    
    st.title(f"🤖 Cortex Analytics: Módulo {tipo_reporte}")
    st.success(f"✅ Archivo analizado. **{len(df):,} registros procesados.**")
    
    # --- PREPARACIÓN DE DATOS BASE ---
    if tipo_reporte in ["Licitaciones", "Compras Ágiles"]:
        if 'Cantidad Adjudicada' in df.columns and 'Monto Unitario' in df.columns:
            df['Cantidad Adjudicada'] = pd.to_numeric(df['Cantidad Adjudicada'], errors='coerce').fillna(0)
            df['Monto Unitario'] = pd.to_numeric(df['Monto Unitario'], errors='coerce').fillna(0)
            df['Monto_Total_Estimado'] = df['Cantidad Adjudicada'] * df['Monto Unitario']
        if 'Fecha Adjudicación' in df.columns:
            df['Fecha_Datetime'] = pd.to_datetime(df['Fecha Adjudicación'], format='mixed', dayfirst=True, errors='coerce')

    elif tipo_reporte == "Convenio Marco":
        if 'Fecha Lectura' in df.columns:
            df['Fecha_Datetime'] = pd.to_datetime(df['Fecha Lectura'], format='mixed', dayfirst=True, errors='coerce')

    # --- RADAR DE UNICORNIOS (MONOPOLIOS) "OJO DE DIOS" ---
    st.subheader("🎯 Radar de Oportunidades: Océanos Azules")
    
    col_id = next((c for c in df.columns if c.lower() in ['codigoexterno', 'id licitacion', 'orden de compra', 'id producto']), None)
    col_prov = next((c for c in df.columns if c.lower() in ['nombre proveedor', 'proveedor', 'empresa', 'rut proveedor']), None)
    
    if col_id and col_prov:
        competencia = df.groupby(col_id)[col_prov].nunique().reset_index()
        competencia.columns = [col_id, 'Num_Competidores']
        df_unicos = df.drop_duplicates(subset=[col_id]).merge(competencia, on=col_id)
        
        unicornios_df = df_unicos[df_unicos['Num_Competidores'] == 1]
        baja_comp_df = df_unicos[df_unicos['Num_Competidores'] == 2]
        
        col_u1, col_u2 = st.columns(2)
        etiqueta_negocio = "Órdenes" if tipo_reporte == "Compras Ágiles" else "Licitaciones"
        col_u1.metric(f"🦄 {etiqueta_negocio} Unicornio (1 solo Proveedor)", len(unicornios_df))
        col_u2.metric("🛡️ Baja Competencia (Solo 2 Proveedores)", len(baja_comp_df))
        
        if not unicornios_df.empty:
            st.markdown(f"#### 🔍 Detalle de {etiqueta_negocio} Unicornio")
            col_monto = 'Monto_Total_Estimado' if 'Monto_Total_Estimado' in df.columns else next((c for c in df.columns if 'precio' in c.lower() or 'monto' in c.lower()), None)
            col_prod = next((c for c in df.columns if 'producto' in c.lower() or 'descripcion' in c.lower()), None)
            col_org = next((c for c in df.columns if 'organismo' in c.lower() or 'comprador' in c.lower() or 'región' in c.lower()), None)
            
            cols_to_show = [c for c in [col_id, col_org, col_prod, col_prov, col_monto] if c is not None]
            tabla_mostrar = unicornios_df[cols_to_show]
            
            if col_monto:
                tabla_mostrar = tabla_mostrar.sort_values(by=col_monto, ascending=False)
                st.dataframe(tabla_mostrar.style.format({col_monto: "${:,.0f}"}), use_container_width=True, hide_index=True)
            else:
                st.dataframe(tabla_mostrar, use_container_width=True, hide_index=True)
    else:
        st.warning("⚠️ Faltan columnas de ID o Proveedor para calcular los monopolios.")

    st.markdown("---")

    # ==========================================
    # 6. MOTOR RAG (CHAT PRE-ENTRENADO)
    # ==========================================
    st.subheader(f"💬 Consultor Estratégico Cortex")
    
    with st.expander("📖 Catálogo de Prompts Comerciales (Copia y pega la pregunta que necesites)"):
        col_a, col_b = st.columns(2)
        with col_a:
            st.markdown("**📊 Análisis de Competencia**")
            st.markdown('<div class="prompt-box">Genera un informe comercial de Market Share por proveedor.</div>', unsafe_allow_html=True)
            st.markdown('<div class="prompt-box">¿Cuáles son los 5 proveedores que más dinero mueven?</div>', unsafe_allow_html=True)
            st.markdown('<div class="prompt-box">Muestra el ranking de las empresas con más adjudicaciones.</div>', unsafe_allow_html=True)
            st.markdown('<div class="prompt-box">Compara el precio máximo y mínimo ofertado por cada empresa.</div>', unsafe_allow_html=True)
            st.markdown('<div class="prompt-box">¿Qué competidor tiene el precio promedio más bajo ofertado?</div>', unsafe_allow_html=True)
            
            st.markdown("**🛒 Compradores y Clientes**")
            st.markdown('<div class="prompt-box">Genera un ranking de los 5 mayores compradores u organismos.</div>', unsafe_allow_html=True)
            st.markdown('<div class="prompt-box">¿Qué regiones o instituciones concentran el mayor gasto?</div>', unsafe_allow_html=True)
            st.markdown('<div class="prompt-box">Dime el detalle de compras del organismo que más gasta.</div>', unsafe_allow_html=True)
            st.markdown('<div class="prompt-box">¿Cuántas compras/licitaciones únicas hay por cada comprador?</div>', unsafe_allow_html=True)
            st.markdown('<div class="prompt-box">Muestra la tabla de compradores ordenados por monto total.</div>', unsafe_allow_html=True)

        with col_b:
            st.markdown("**📦 Productos y Precios**")
            st.markdown('<div class="prompt-box">¿Cuál es el producto que genera más volumen de dinero?</div>', unsafe_allow_html=True)
            st.markdown('<div class="prompt-box">Haz un análisis de la tendencia de precios en el tiempo.</div>', unsafe_allow_html=True)
            st.markdown('<div class="prompt-box">Genera un reporte detallado del producto más demandado.</div>', unsafe_allow_html=True)
            st.markdown('<div class="prompt-box">¿Cuál es el precio promedio, máximo y mínimo por producto?</div>', unsafe_allow_html=True)
            st.markdown('<div class="prompt-box">Muestra los 5 productos con mayor cantidad adjudicada.</div>', unsafe_allow_html=True)
            
            st.markdown("**🎯 Estrategia y Oportunidades**")
            st.markdown('<div class="prompt-box">¿Cuáles son los negocios más rentables (Top 5 por mayor monto)?</div>', unsafe_allow_html=True)
            st.markdown('<div class="prompt-box">Resume los montos totales adjudicados agrupados por fecha.</div>', unsafe_allow_html=True)
            st.markdown('<div class="prompt-box">¿Cuál es el ticket promedio (monto) por negocio?</div>', unsafe_allow_html=True)
            st.markdown('<div class="prompt-box">Crea un resumen estadístico general de todos los datos.</div>', unsafe_allow_html=True)
            st.markdown('<div class="prompt-box">Genera un informe detallando las oportunidades de negocio en este archivo.</div>', unsafe_allow_html=True)

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if prompt := st.chat_input("Pega aquí uno de los Prompts Comerciales..."):
        
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner(f"Cortex aplicando modelo '{tipo_reporte}'..."):
                
                columnas_disponibles = df.columns.tolist()
                
                # ========================================================
                # 🧠 ENTRENAMIENTO ESPECÍFICO POR TIPO DE REPORTE (LA MAGIA)
                # ========================================================
                entrenamiento_especifico = ""
                
                if tipo_reporte == "Licitaciones":
                    entrenamiento_especifico = """
                    ESTÁS ANALIZANDO: LICITACIONES PÚBLICAS.
                    - La empresa competidora está en 'Nombre Proveedor'.
                    - El comprador está en 'Nombre Organismo'.
                    - Para VOLUMEN DE DINERO o MARKET SHARE: Usa SIEMPRE la columna calculada 'Monto_Total_Estimado'.
                    - Para detalle de PRODUCTOS: DEBES incluir en tus tablas ambas columnas: 'Nombre Producto' y 'Descripcion Producto' para que el usuario sepa exactamente qué se vendió.
                    - Las fechas están en 'Fecha_Datetime'.
                    """
                elif tipo_reporte == "Compras Ágiles":
                    entrenamiento_especifico = """
                    ESTÁS ANALIZANDO: COMPRAS ÁGILES (Micromercado).
                    - La empresa competidora está en 'Nombre Proveedor'.
                    - El comprador está en 'Nombre Organismo'.
                    - Para VOLUMEN DE DINERO o MARKET SHARE: Usa SIEMPRE la columna calculada 'Monto_Total_Estimado'.
                    - Para detalle de PRODUCTOS: DEBES incluir en tus tablas ambas columnas: 'Nombre Producto' y 'Descripcion Producto' para ver la especificación técnica.
                    - Las fechas están en 'Fecha_Datetime'.
                    """
                elif tipo_reporte == "Convenio Marco":
                    entrenamiento_especifico = """
                    ESTÁS ANALIZANDO: CONVENIO MARCO (Catálogo).
                    - La empresa competidora está en 'Empresa'.
                    - La zona geográfica es 'Región'.
                    - Para PRECIOS y MARKET SHARE: Aquí no hay Monto_Total_Estimado. Usa 'Precio Oferta'.
                    - Para detalle de PRODUCTOS: Usa 'Nombre Producto' y 'Formato' (No existe Descripcion Producto).
                    - Las fechas están en 'Fecha_Datetime'.
                    """
                else:
                    entrenamiento_especifico = "Usa las columnas disponibles para deducir la mejor respuesta."

                system_instruction = f"""
                Eres Cortex, Director Comercial de SmartOffer.
                Columnas exactas en 'df': {columnas_disponibles}
                
                {entrenamiento_especifico}

                REGLAS CRÍTICAS DE PROGRAMACIÓN:
                1. SOLO usa las columnas de la lista. Nunca asumas nombres.
                2. Devuelve SOLO código Python puro. SIN markdown (sin ```python).
                3. SIEMPRE asigna el resultado a la variable 'resultado'.
                4. Si el usuario pide un "Informe" o "Resumen", haz los cálculos con pandas, y guarda en 'resultado' un string con el formato Markdown. Si pide tabla/gráfico, guarda en 'resultado' un DataFrame.
                5. Maneja los valores nulos (fillna) antes de sumar o calcular medias.
                """
                
                try:
                    response = model.generate_content([system_instruction, prompt])
                    clean_code = response.text.replace("```python", "").replace("```", "").strip()
                    
                    scope = {"df": df.copy(), "pd": pd}
                    exec(clean_code, scope)
                    
                    if "resultado" not in scope:
                        raise ValueError("No se generó la variable 'resultado'.")
                        
                    resultado = scope["resultado"]

                    st.markdown("**Análisis de Cortex:**")
                    
                    if isinstance(resultado, str):
                        st.markdown(resultado) 
                    elif isinstance(resultado, (pd.Series, pd.DataFrame)):
                        st.write(resultado) 
                        
                        prompt_lower = prompt.lower()
                        try: 
                            if any(word in prompt_lower for word in ["tendencia", "evolución", "fecha", "tiempo"]):
                                st.line_chart(resultado)
                            elif any(word in prompt_lower for word in ["top", "market share", "ranking", "compradores", "proveedores"]):
                                st.bar_chart(resultado)
                        except Exception:
                            pass 
                    else:
                        st.write(resultado)
                            
                    st.session_state.messages.append({"role": "assistant", "content": "Análisis estratégico completado."})
                
                except Exception as e:
                    st.error("⚠️ Cortex no pudo procesar esta consulta. Esto suele ocurrir si el prompt pide analizar una columna que no está presente en tu archivo actual.")
                    # print(f"Traza: {traceback.format_exc()}") # Puedes descomentar para debugear

else:
    st.info("👋 Sube tu archivo Excel/CSV para activar el motor de inteligencia de negocios.")
