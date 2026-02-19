import streamlit as st
import pandas as pd
import google.generativeai as genai
import traceback

# ==========================================
# 1. CONFIGURACIÓN DE PÁGINA Y ESTÉTICA
# ==========================================
st.set_page_config(page_title="Cortex Analytics: Suite Inteligente", page_icon="🤖", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #0e1117; color: #e0e0e0; }
    .stSidebar { background-color: #161b22; border-right: 1px solid #30363d; }
    h1 { color: #00d4ff; font-family: 'Inter', sans-serif; font-weight: 800; }
    .stChatMessage { border-radius: 15px; border: 1px solid #30363d; margin-bottom: 10px; }
    div[data-testid="stMetricValue"] { color: #00d4ff; }
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# 2. INICIALIZACIÓN DE IA Y ESTADOS
# ==========================================
if "GEMINI_API_KEY" not in st.secrets:
    st.error("❌ Error Crítico: No se encontró 'GEMINI_API_KEY' en tus secretos.")
    st.info("💡 Asegúrate de tener el archivo .streamlit/secrets.toml con tu clave.")
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
    if "fecha lectura" in cols_str or "precio sin oferta" in cols_str:
        return "Convenio Marco"
    elif "licitación" in cols_str or "codigoexterno" in cols_str or "adjudicado" in cols_str:
        return "Licitaciones"
    elif "orden de compra" in cols_str or "comprador" in cols_str:
        return "Compras Ágiles"
    else:
        return "Análisis General"

# ==========================================
# 4. INTERFAZ: SIDEBAR Y CARGA DE DATOS
# ==========================================
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/4712/4712139.png", width=80)
    st.title("Cortex Core")
    st.markdown("Sube tu reporte descargado del portal (Mercado Público / Convenios).")
    uploaded_file = st.file_uploader("Cargar Archivo Excel/CSV", type=['xlsx', 'csv'])
    
    st.markdown("---")
    if st.button("🧹 Limpiar Historial de Chat"):
        st.session_state.messages = []
        st.rerun()

# ==========================================
# 5. NÚCLEO DE PROCESAMIENTO Y DASHBOARDS
# ==========================================
if uploaded_file:
    # --- Lectura Segura ---
    try:
        if uploaded_file.name.endswith('csv'):
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)
    except Exception as e:
        st.error(f"Error al leer el archivo: {e}")
        st.stop()

    # --- Detección del Contexto ---
    tipo_reporte = detectar_tipo_reporte(df.columns.tolist())
    
    st.title(f"🤖 Cortex Analytics: Módulo {tipo_reporte}")
    st.success(f"✅ Archivo analizado exitosamente. **{len(df):,} registros procesados.**")
    st.markdown("---")
    
    # --- DASHBOARDS DINÁMICOS ---
    if tipo_reporte == "Convenio Marco":
        df['Fecha_Datetime'] = pd.to_datetime(df['Fecha Lectura'], format='mixed', dayfirst=True, errors='coerce')
        st.subheader("⚡ Radar de Convenio Marco en Tiempo Real")
        col1, col2, col3 = st.columns(3)
        col1.metric("📦 Productos Únicos (IDs)", df.get('ID Producto', pd.Series()).nunique())
        col2.metric("🏢 Competidores", df.get('Empresa', pd.Series()).nunique())
        
        if not df['Fecha_Datetime'].isna().all() and 'Precio Oferta' in df.columns:
            ultima_fecha = df['Fecha_Datetime'].max()
            df_reciente = df[df['Fecha_Datetime'] == ultima_fecha]
            top_5 = df_reciente.nsmallest(5, 'Precio Oferta')[['ID Producto', 'Nombre Producto', 'Región', 'Precio Oferta', 'Empresa']]
            st.markdown(f"#### 🏆 Top 5 Mejores Precios Ofertados (Última Lectura: {ultima_fecha.strftime('%d/%m/%Y')})")
            st.dataframe(top_5.style.format({"Precio Oferta": "${:,.0f}"}), use_container_width=True, hide_index=True)

    elif tipo_reporte == "Licitaciones":
        # Cálculos Base de Licitaciones
        df['Fecha_Datetime'] = pd.to_datetime(df.get('Fecha Adjudicación', pd.Series()), format='mixed', dayfirst=True, errors='coerce')
        df['Cantidad Adjudicada'] = pd.to_numeric(df.get('Cantidad Adjudicada', pd.Series()), errors='coerce').fillna(0)
        df['Monto Unitario'] = pd.to_numeric(df.get('Monto Unitario', pd.Series()), errors='coerce').fillna(0)
        df['Monto_Total_Estimado'] = df['Cantidad Adjudicada'] * df['Monto Unitario']

        st.subheader("📊 Panel Estratégico de Licitaciones Históricas")
        col1, col2, col3 = st.columns(3)
        col1.metric("📝 Licitaciones Únicas", df.get('CodigoExterno', pd.Series()).nunique())
        
        volumen_total = df[df.get('Moneda') == 'CLP']['Monto_Total_Estimado'].sum() if 'Moneda' in df.columns else df['Monto_Total_Estimado'].sum()
        col2.metric("💰 Volumen Total Adjudicado", f"${volumen_total:,.0f} CLP")
        
        top_comprador = df['Nombre Organismo'].mode()[0] if 'Nombre Organismo' in df.columns and not df['Nombre Organismo'].empty else "N/A"
        col3.metric("🏢 Mayor Comprador", top_comprador)

        st.markdown("---")
        
        # --- SECCIÓN UNICORNIOS (OCÉANOS AZULES) ---
        st.subheader("🎯 Radar de Oportunidades: Océanos Azules")
        st.info("💡 **Inteligencia de Mercado:** Cortex ha detectado licitaciones donde la competencia es mínima o nula. Oportunidades clave para altos márgenes.")
        
        if 'CodigoExterno' in df.columns and 'Nombre Proveedor' in df.columns:
            competencia = df.groupby('CodigoExterno')['Nombre Proveedor'].nunique().reset_index()
            competencia.columns = ['CodigoExterno', 'Num_Competidores']
            
            df_unicos = df.drop_duplicates(subset=['CodigoExterno']).merge(competencia, on='CodigoExterno')
            
            unicornios_df = df_unicos[df_unicos['Num_Competidores'] == 1]
            baja_comp_df = df_unicos[df_unicos['Num_Competidores'] == 2]
            
            col_u1, col_u2 = st.columns(2)
            col_u1.metric("🦄 Licitaciones Unicornio (1 solo Proveedor)", len(unicornios_df))
            col_u2.metric("🛡️ Baja Competencia (Solo 2 Proveedores)", len(baja_comp_df))
            
            if not unicornios_df.empty:
                st.markdown("#### 🔍 Detalle de Licitaciones Unicornio")
                col_ubicacion = 'Región' if 'Región' in df.columns else 'Nombre Organismo'
                columnas_mostrar = ['CodigoExterno', col_ubicacion, 'Nombre Producto', 'Nombre Proveedor', 'Monto_Total_Estimado']
                columnas_mostrar = [c for c in columnas_mostrar if c in unicornios_df.columns]
                
                tabla_mostrar = unicornios_df[columnas_mostrar].sort_values(by='Monto_Total_Estimado', ascending=False)
                st.dataframe(tabla_mostrar.style.format({"Monto_Total_Estimado": "${:,.0f}"}), use_container_width=True, hide_index=True)
            else:
                st.success("No se detectaron Licitaciones Unicornio en este reporte.")
            
    else: 
        st.subheader(f"🛒 Panel de Visualización: {tipo_reporte}")
        st.dataframe(df.head(5), use_container_width=True)

    st.markdown("---")

    # ==========================================
    # 6. MOTOR RAG: AGENTE IA (CHAT COMERCIAL)
    # ==========================================
    st.subheader(f"💬 Analista Inteligente ({tipo_reporte})")
    
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if prompt := st.chat_input("Ej: Genera un informe comercial de FARMALATINA LTDA..."):
        
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Cortex procesando estrategia y datos..."):
                
                # --- EL NUEVO CEREBRO COMERCIAL DE CORTEX ---
                system_instruction = f"""
                Eres Cortex, el Director Comercial e Inteligencia de Negocios de SmartOffer.
                Dataset actual: '{tipo_reporte}'. Columnas: {df.columns.tolist()}.

                REGLAS CRÍTICAS DE PROGRAMACIÓN:
                1. Devuelve SOLO código Python válido (sin formato markdown ```python ni nada extra). 
                2. SIEMPRE asigna el resultado final a la variable 'resultado'.
                3. Si el usuario pide un DATO, GRÁFICO o TABLA: 'resultado' debe ser un DataFrame o Serie de Pandas.
                4. Si el usuario pide un "INFORME", "RESUMEN" o "ANÁLISIS": Escribe código Pandas para calcular KPIs, y luego construye un string en formato Markdown con un resumen ejecutivo para gerencia. Asigna ese string final a 'resultado'.
                5. Para Licitaciones, usa SIEMPRE 'Monto_Total_Estimado' para volumen de dinero.
                6. Maneja nulos con fillna(0) o dropna() antes de sumar o calcular.
                """
                
                try:
                    response = model.generate_content([system_instruction, prompt])
                    clean_code = response.text.replace("```python", "").replace("```", "").strip()
                    
                    scope = {"df": df.copy(), "pd": pd}
                    exec(clean_code, scope)
                    
                    if "resultado" not in scope:
                        raise ValueError("El agente IA no generó la variable 'resultado'.")
                        
                    resultado = scope["resultado"]

                    # --- RENDERIZADO INTELIGENTE (Texto vs Gráficos) ---
                    st.markdown("**Análisis de Cortex:**")
                    
                    if isinstance(resultado, str):
                        # Si es un Informe Ejecutivo (Texto Markdown)
                        st.markdown(resultado)
                        
                    elif isinstance(resultado, (pd.Series, pd.DataFrame)):
                        # Si es un cálculo de datos puros, mostrar tabla y posible gráfico
                        st.write(resultado)
                        prompt_lower = prompt.lower()
                        
                        if any(word in prompt_lower for word in ["tendencia", "evolución", "tiempo", "histórico", "fecha", "grafico", "gráfico"]):
                            try:
                                st.line_chart(resultado)
                            except:
                                st.bar_chart(resultado)
                        elif any(word in prompt_lower for word in ["top", "market share", "comparativa", "quien", "participacion", "ranking"]):
                            st.bar_chart(resultado)
                    else:
                        st.write(resultado)
                            
                    st.session_state.messages.append({"role": "assistant", "content": "Análisis estratégico completado."})
                
                except Exception as e:
                    st.error("⚠️ Hubo un error procesando tu solicitud estratégica. Intenta ser un poco más específico con los nombres.")
                    # print(f"Error AI: {e}\nTraza: {traceback.format_exc()}") # Oculto en prod

else:
    st.info("👋 ¡Hola! Soy Cortex Analytics de SmartOffer. Sube un archivo de Mercado Público o Convenios Marco en el menú lateral para iniciar el escáner comercial.")
