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
try:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    model = genai.GenerativeModel('gemini-1.5-flash')
except Exception as e:
    st.error("❌ Error Crítico: No se encontró GEMINI_API_KEY en st.secrets.")
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
# 4. INTERFAZ: SIDEBAR Y CARGA
# ==========================================
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/4712/4712139.png", width=80)
    st.title("Cortex Core")
    st.markdown("Sube tu reporte descargado del portal (Mercado Público / Convenios).")
    uploaded_file = st.file_uploader("Cargar Archivo", type=['xlsx', 'csv'])
    
    if st.button("Limpiar Historial de Chat"):
        st.session_state.messages = []
        st.rerun()

# ==========================================
# 5. NÚCLEO DE PROCESAMIENTO
# ==========================================
if uploaded_file:
    # --- A. Lectura Segura ---
    try:
        if uploaded_file.name.endswith('csv'):
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)
    except Exception as e:
        st.error(f"Error leyendo el archivo: {e}")
        st.stop()

    # --- B. Detección y Contexto ---
    tipo_reporte = detectar_tipo_reporte(df.columns.tolist())
    
    st.title(f"🤖 Cortex Analytics: Módulo {tipo_reporte}")
    st.success(f"✅ Archivo analizado exitosamente. **{len(df):,} registros detectados.**")
    st.markdown("---")
    
    # --- C. DASHBOARDS DINÁMICOS ---
    if tipo_reporte == "Convenio Marco":
        # Conversión de fecha robusta (maneja múltiples formatos)
        df['Fecha_Datetime'] = pd.to_datetime(df['Fecha Lectura'], format='mixed', dayfirst=True, errors='coerce')
        
        st.subheader("⚡ Radar de Convenio Marco")
        col1, col2, col3 = st.columns(3)
        col1.metric("📦 IDs Monitorizados", df.get('ID Producto', pd.Series()).nunique())
        col2.metric("🏢 Competidores", df.get('Empresa', pd.Series()).nunique())
        
        if not df['Fecha_Datetime'].isna().all():
            ultima_fecha = df['Fecha_Datetime'].max()
            df_reciente = df[df['Fecha_Datetime'] == ultima_fecha]
            
            if 'Precio Oferta' in df.columns:
                top_5 = df_reciente.nsmallest(5, 'Precio Oferta')[['ID Producto', 'Nombre Producto', 'Región', 'Precio Oferta', 'Empresa']]
                st.markdown("#### 🏆 Top 5: Oportunidades de Compra Inmediata")
                st.dataframe(top_5.style.format({"Precio Oferta": "${:,.0f}"}), use_container_width=True, hide_index=True)

    elif tipo_reporte == "Licitaciones":
        st.subheader("📊 Panel de Estado de Licitaciones")
        col1, col2 = st.columns(2)
        col1.metric("📝 Total Postulaciones", len(df))
        if 'Estado' in df.columns:
            ganadas = len(df[df['Estado'].astype(str).str.lower().str.contains('ganada|adjudicada', na=False)])
            col2.metric("✅ Licitaciones Ganadas", ganadas)
            
    else: 
        st.subheader(f"🛒 Panel de {tipo_reporte}")
        st.dataframe(df.head(5), use_container_width=True)

    st.markdown("---")

    # ==========================================
    # 6. AGENTE IA: CHAT Y EJECUCIÓN PANDAS
    # ==========================================
    st.subheader(f"💬 Analista Inteligente ({tipo_reporte})")
    
    # Mostrar historial
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Input del usuario
    if prompt := st.chat_input("Ej: Muéstrame un gráfico con los productos más vendidos..."):
        # Guardar y mostrar pregunta
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Cortex procesando tu solicitud..."):
                # PROMPT BLINDADO
                system_instruction = f"""
                Eres Cortex, un analista de BI Senior de SmartOffer.
                Dataset actual: '{tipo_reporte}'.
                Columnas exactas del DataFrame 'df': {df.columns.tolist()}.
                
                REGLAS CRÍTICAS DE PROGRAMACIÓN:
                1. Devuelve ÚNICA Y EXCLUSIVAMENTE código Python válido. Cero texto, cero explicaciones, cero markdown de bloques (sin ```python).
                2. SIEMPRE debes asignar el resultado final a una variable llamada exactamente 'resultado'.
                3. 'resultado' DEBE ser un DataFrame, una Serie, un número o un string.
                4. Si te piden un gráfico, tendencia o evolución, haz un 'groupby' o 'pivot_table' y asigna ESE DataFrame a 'resultado'. La app graficará 'resultado' automáticamente.
                5. Maneja los nulos si vas a sumar o promediar (ej: dropna()).
                """
                
                try:
                    # 1. Llamar a Gemini
                    response = model.generate_content([system_instruction, prompt])
                    clean_code = response.text.replace("```python", "").replace("```", "").strip()
                    
                    # 2. Ejecutar Código en Entorno Aislado
                    scope = {"df": df.copy(), "pd": pd}
                    exec(clean_code, scope)
                    
                    # 3. Extraer el resultado
                    if "resultado" not in scope:
                        raise ValueError("El agente IA no generó la variable 'resultado'.")
                        
                    resultado = scope["resultado"]

                    # 4. Visualización Inteligente
                    st.markdown("**Respuesta:**")
                    st.write(resultado)
                    
                    if isinstance(resultado, (pd.Series, pd.DataFrame)):
                        # Autodetectar si es apto para línea o barras
                        prompt_lower = prompt.lower()
                        if any(word in prompt_lower for word in ["tendencia", "evolución", "tiempo", "histórico", "fecha"]):
                            st.line_chart(resultado)
                        else:
                            st.bar_chart(resultado)
                            
                    # 5. Guardar en memoria
                    st.session_state.messages.append({"role": "assistant", "content": "Análisis completado y visualizado."})
                
                except Exception as e:
                    error_msg = f"⚠️ Lo siento, no pude procesar esa consulta. Verifica los nombres de las columnas o intenta ser más específico."
                    st.error(error_msg)
                    # Debug en consola para el desarrollador
                    print(f"Error: {e}\nCódigo generado:\n{clean_code}\nTraceback: {traceback.format_exc()}")

else:
    # Pantalla de Bienvenida cuando no hay archivo
    st.info("👋 ¡Hola! Soy Cortex. Sube un archivo de Mercado Público en el menú lateral para empezar a descubrir oportunidades de negocio.")
