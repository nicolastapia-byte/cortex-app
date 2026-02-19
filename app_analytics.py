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
# 2. INICIALIZACIÓN DE IA Y ESTADOS (ROBUSTO)
# ==========================================
# A. Verificación estricta de la llave en secrets
if "GEMINI_API_KEY" not in st.secrets:
    st.error("❌ Error Crítico: No se encontró 'GEMINI_API_KEY' en tus secretos.")
    st.info("💡 Asegúrate de tener una carpeta llamada '.streamlit' con un archivo 'secrets.toml' dentro, y que el archivo contenga: GEMINI_API_KEY = 'tu_clave'")
    st.stop()

# B. Conexión con Google Gemini
try:
    api_key = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-1.5-flash')
except Exception as e:
    st.error(f"❌ Error conectando con Gemini: {str(e)}")
    st.stop()

# Inicializar memoria del chat
if "messages" not in st.session_state:
    st.session_state.messages = []

# ==========================================
# 3. MOTOR DE RUTEO INTELIGENTE
# ==========================================
def detectar_tipo_reporte(columnas):
    cols_str = " ".join(columnas).lower()
    if "fecha lectura" in cols_str or "precio sin oferta" in cols_str:
        return "Convenio Marco"
    elif "licitación" in cols_str or "licitacion" in cols_str or "adjudicacion" in cols_str:
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
    # --- Lectura Segura del Archivo ---
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
    
    # --- Dashboards Dinámicos ---
    if tipo_reporte == "Convenio Marco":
        # Conversión de fecha robusta
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
        st.subheader("📊 Panel de Estado de Licitaciones")
        col1, col2 = st.columns(2)
        col1.metric("📝 Total Postulaciones", len(df))
        if 'Estado' in df.columns:
            ganadas = len(df[df['Estado'].astype(str).str.lower().str.contains('ganada|adjudicada', na=False)])
            col2.metric("✅ Licitaciones Ganadas", ganadas)
            
    else: 
        st.subheader(f"🛒 Panel de Visualización: {tipo_reporte}")
        st.dataframe(df.head(5), use_container_width=True)

    st.markdown("---")

    # ==========================================
    # 6. MOTOR RAG: AGENTE IA (CHAT CON DATOS)
    # ==========================================
    st.subheader(f"💬 Analista Inteligente ({tipo_reporte})")
    
    # Mostrar historial de la conversación
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Input de nueva pregunta
    if prompt := st.chat_input("Ej: ¿Cuál es la tendencia del Precio Oferta de GASCO en la Región I?"):
        
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Cortex procesando matriz de datos..."):
                # System Prompt estricto para generar código Pandas
                system_instruction = f"""
                Eres Cortex, Analista de Datos experto de SmartOffer.
                Dataset actual: '{tipo_reporte}'.
                Columnas exactas del DataFrame 'df': {df.columns.tolist()}.
                
                REGLAS CRÍTICAS DE PROGRAMACIÓN:
                1. Devuelve ÚNICA Y EXCLUSIVAMENTE código Python válido. Cero texto adicional, cero explicaciones, sin formato markdown (NO uses ```python).
                2. SIEMPRE debes asignar el resultado final a una variable llamada exactamente 'resultado'.
                3. 'resultado' DEBE ser un DataFrame, una Serie, un número o un string.
                4. Si el usuario pide un gráfico o evolución en el tiempo, usa groupby o pivot_table y asigna ESE DataFrame a 'resultado'.
                5. Para Convenios Marco, las fechas están en la columna 'Fecha_Datetime' en formato datetime64.
                6. Maneja los nulos antes de sumar o promediar (ej: dropna()).
                """
                
                try:
                    # Llamada a Gemini para obtener el código
                    response = model.generate_content([system_instruction, prompt])
                    clean_code = response.text.replace("```python", "").replace("```", "").strip()
                    
                    # Entorno de ejecución seguro y controlado
                    scope = {"df": df.copy(), "pd": pd}
                    exec(clean_code, scope)
                    
                    # Validar que Gemini haya creado la variable esperada
                    if "resultado" not in scope:
                        raise ValueError("El agente IA no generó la variable 'resultado'.")
                        
                    resultado = scope["resultado"]

                    # Mostrar el resultado al usuario
                    st.markdown("**Respuesta:**")
                    st.write(resultado)
                    
                    # Decisión automática de Gráficos
                    if isinstance(resultado, (pd.Series, pd.DataFrame)):
                        prompt_lower = prompt.lower()
                        if any(word in prompt_lower for word in ["tendencia", "evolución", "tiempo", "histórico", "fecha"]):
                            st.line_chart(resultado)
                        else:
                            st.bar_chart(resultado)
                            
                    st.session_state.messages.append({"role": "assistant", "content": "Análisis completado y visualizado correctamente."})
                
                except Exception as e:
                    st.error("⚠️ Hubo un error procesando esa consulta específica. Por favor, intenta usar los nombres exactos de las columnas mostradas arriba.")
                    # Impresión en consola para depuración técnica
                    print(f"Error ejecutando código AI: {e}\nCódigo generado:\n{clean_code}\nTraza: {traceback.format_exc()}")

else:
    # Estado inicial: Esperando archivo
    st.info("👋 ¡Hola! Soy Cortex Analytics de SmartOffer. Sube un archivo de Mercado Público o Convenios Marco en el menú lateral para iniciar el escáner.")
