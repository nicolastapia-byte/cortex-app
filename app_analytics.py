import streamlit as st
import pandas as pd
import google.generativeai as genai
import traceback
import re

# ==========================================
# 1. CONFIGURACIÓN Y FUNCIONES UTILITARIAS BLINDADAS
# ==========================================
st.set_page_config(page_title="Cortex Analytics: Suite Comercial Robusta", page_icon="🛡️", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #0e1117; color: #e0e0e0; }
    .stSidebar { background-color: #161b22; border-right: 1px solid #30363d; }
    h1 { color: #00d4ff; font-family: 'Inter', sans-serif; font-weight: 800; }
    .stChatMessage { border-radius: 15px; border: 1px solid #30363d; margin-bottom: 10px; }
    div[data-testid="stMetricValue"] { color: #00d4ff; }
    .prompt-box { background-color: #21262d; padding: 8px; border-radius: 5px; margin-bottom: 5px; border-left: 3px solid #00d4ff; font-size: 0.85em; cursor: pointer;}
    .prompt-box:hover { background-color: #30363d; }
    </style>
    """, unsafe_allow_html=True)

# Función robusta para limpiar columnas numéricas (maneja $, puntos, comas)
def limpiar_numeros(serie):
    if pd.api.types.is_numeric_dtype(serie):
        return serie.fillna(0)
    # Si es texto, intentar limpiar caracteres no numéricos excepto puntos y comas decimales
    try:
        return serie.astype(str).str.replace(r'[^\d.,-]', '', regex=True).str.replace(',', '.').astype(float).fillna(0)
    except:
        return pd.to_numeric(serie, errors='coerce').fillna(0)

# Función robusta para limpiar fechas
def limpiar_fechas(serie):
    return pd.to_datetime(serie, format='mixed', dayfirst=True, errors='coerce')

# ==========================================
# 2. INICIALIZACIÓN DE IA Y ESTADOS
# ==========================================
if "GEMINI_API_KEY" not in st.secrets:
    st.error("🛡️ Seguridad: No se encontró 'GEMINI_API_KEY' en secrets.toml.")
    st.stop()

try:
    api_key = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-1.5-flash')
except Exception as e:
    st.error(f"🛡️ Error de conexión API: {str(e)}")
    st.stop()

if "messages" not in st.session_state:
    st.session_state.messages = []

# ==========================================
# 3. MOTOR DE RUTEO Y PREPARACIÓN DE DATOS
# ==========================================
def detectar_tipo_reporte(columnas):
    cols_str = " ".join(columnas).lower()
    # Detección priorizada
    if "estado compra ágil" in cols_str or "estado compra agil" in cols_str:
        return "Compras Ágiles"
    elif "estado licitación" in cols_str or "estado licitacion" in cols_str:
        return "Licitaciones"
    elif "fecha lectura" in cols_str or "precio sin oferta" in cols_str:
        return "Convenio Marco"
    else:
        return "Análisis General"

# ==========================================
# 4. INTERFAZ: CARGA
# ==========================================
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/4712/4712139.png", width=80)
    st.title("Cortex Core 🛡️")
    st.markdown("Sistema blindado para análisis de Mercado Público.")
    uploaded_file = st.file_uploader("Cargar Archivo (Excel/CSV)", type=['xlsx', 'csv'])
    
    st.markdown("---")
    if st.button("🧹 Limpiar Historial"):
        st.session_state.messages = []
        st.rerun()

# ==========================================
# 5. NÚCLEO DE PROCESAMIENTO SEGURO
# ==========================================
if uploaded_file:
    try:
        if uploaded_file.name.endswith('csv'):
            # Intentar leer CSV con diferentes codificaciones si falla la estándar
            try:
                df = pd.read_csv(uploaded_file)
            except UnicodeDecodeError:
                 df = pd.read_csv(uploaded_file, encoding='latin1')
        else:
            df = pd.read_excel(uploaded_file)
            
        # --- SANEAMIENTO INICIAL BÁSICO ---
        df.columns = df.columns.str.strip() # Eliminar espacios en nombres de columnas
        
    except Exception as e:
        st.error(f"🛡️ El archivo está corrupto o tiene un formato ilegible: {e}")
        st.stop()

    tipo_reporte = detectar_tipo_reporte(df.columns.tolist())
    st.title(f"🤖 Módulo Blindado: {tipo_reporte}")
    
    # ====================================================
    # 🛡️ CAPA DE PREPARACIÓN DE DATOS (Data Sanitation)
    # ====================================================
    with st.spinner("🛡️ Cortex saneando datos y calculando métricas base..."):
        try:
            # Variables para la "Piedra Rosetta"
            col_map = {} 
            cols_detalle_prod = []

            if tipo_reporte in ["Licitaciones", "Compras Ágiles"]:
                # 1. Limpieza Numérica Obligatoria
                if 'Cantidad Adjudicada' in df.columns:
                    df['Cantidad Adjudicada'] = limpiar_numeros(df['Cantidad Adjudicada'])
                if 'Monto Unitario' in df.columns:
                    df['Monto Unitario'] = limpiar_numeros(df['Monto Unitario'])
                
                # 2. Cálculo Seguro de Monto Total
                if 'Cantidad Adjudicada' in df.columns and 'Monto Unitario' in df.columns:
                    df['Monto_Total_Estimado'] = df['Cantidad Adjudicada'] * df['Monto Unitario']
                else:
                    # Fallback si faltan columnas clave
                    df['Monto_Total_Estimado'] = 0
                    st.warning("⚠️ Faltan columnas 'Cantidad Adjudicada' o 'Monto Unitario'. El análisis de volumen no será preciso.")

                # 3. Limpieza de Fechas
                if 'Fecha Adjudicación' in df.columns:
                    df['Fecha_Datetime'] = limpiar_fechas(df['Fecha Adjudicación'])

                # 4. Definir Mapa de Columnas (Piedra Rosetta)
                col_map = {
                    'MONTO_REAL': 'Monto_Total_Estimado',
                    'PROVEEDOR_CLAVE': 'Nombre Proveedor',
                    'COMPRADOR_CLAVE': 'Nombre Organismo',
                    'FECHA_CLAVE': 'Fecha_Datetime',
                    'ID_CLAVE': 'CodigoExterno' if 'CodigoExterno' in df.columns else 'ID Licitación'
                }
                cols_detalle_prod = ['Nombre Producto', 'Descripcion Producto']

            elif tipo_reporte == "Convenio Marco":
                 # 1. Limpieza Numérica
                if 'Precio Oferta' in df.columns:
                    df['Precio Oferta'] = limpiar_numeros(df['Precio Oferta'])
                
                # 2. Limpieza de Fechas
                if 'Fecha Lectura' in df.columns:
                     df['Fecha_Datetime'] = limpiar_fechas(df['Fecha Lectura'])

                # 3. Definir Mapa de Columnas (Piedra Rosetta)
                col_map = {
                    'MONTO_REAL': 'Precio Oferta',
                    'PROVEEDOR_CLAVE': 'Empresa',
                    'COMPRADOR_CLAVE': 'Región', # En CM usamos Región como proxy de comprador/zona
                    'FECHA_CLAVE': 'Fecha_Datetime',
                    'ID_CLAVE': 'ID Producto'
                }
                cols_detalle_prod = ['Nombre Producto', 'Formato']
            
            # Validar que las columnas del mapa realmente existan después de la limpieza
            col_map_final = {k: v for k, v in col_map.items() if v in df.columns}
            
            st.success(f"✅ Datos saneados y esquema mapeado. **{len(df):,} registros listos.**")

        except Exception as e:
             st.error(f"🛡️ Error crítico durante la preparación de datos: {e}")
             st.stop()
            
    st.markdown("---")

    # ==========================================
    # 6. MOTOR RAG: CHAT COMERCIAL ROBUSTO
    # ==========================================
    st.subheader(f"💬 Consultor Estratégico")

    # Menú de Prompts Fijo (Copia y Pega seguro)
    with st.expander("📖 Menú de Preguntas Comerciales (Copiar y Pegar)"):
        col_a, col_b = st.columns(2)
        with col_a:
            st.markdown("**📊 Competencia & Mercado**")
            st.code("Genera un informe de Market Share (cuota de mercado) por competidor.")
            st.code("Ranking de los 5 mayores competidores por volumen de dinero.")
            st.code("¿Qué competidor tiene el precio/monto promedio más bajo?")
        with col_b:
            st.markdown("**🎯 Estrategia & Oportunidades**")
            st.code("Análisis de tendencia de montos/precios en el tiempo.")
            st.code("Ranking de los mayores compradores u organismos.")
            st.code("Dime el detalle del producto que más dinero mueve.")

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if prompt := st.chat_input("Pega aquí una pregunta del menú..."):
        
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Cortex ejecutando análisis seguro..."):
                
                # --- EL CEREBRO BLINDADO CON "PIEDRA ROSETTA" ---
                # Inyectamos el mapa exacto de columnas como un diccionario Python
                system_instruction = f"""
                Eres Cortex, Director Comercial de SmartOffer.
                Tipo de Reporte: '{tipo_reporte}'.
                
                TU MAPA DE COLUMNAS SEGURO (PIEDRA ROSETTA):
                {col_map_final}
                
                Columnas adicionales de detalle de producto: {cols_detalle_prod}

                REGLAS CRÍTICAS DE PROGRAMACIÓN (ANTI-ERRORES):
                1.  **USO ESTRICTO DEL MAPA:** NO uses nombres de columnas en strings. Usa SIEMPRE las llaves del mapa.
                    * Incorrecto: `df.groupby('Nombre Proveedor')['Monto_Total_Estimado'].sum()`
                    * **CORRECTO:** `df.groupby(col_map_final['PROVEEDOR_CLAVE'])[col_map_final['MONTO_REAL']].sum()`
                2.  Devuelve SOLO código Python puro. SIN markdown (sin ```python).
                3.  SIEMPRE asigna el resultado a la variable 'resultado'.
                4.  **Manejo de Nulos:** Usa `.fillna(0)` antes de sumar y `.dropna()` antes de agrupar si es necesario.
                5.  **Informes:** Si piden "Informe", calcula los datos con pandas, y luego usa f-strings para crear un resumen ejecutivo en Markdown.
                6.  **Detalle de Productos:** Si piden detalle, asegúrate de incluir las columnas en `cols_detalle_prod`.
                """
                
                try:
                    # Llamada a la API con el prompt blindado
                    response = model.generate_content([system_instruction, prompt])
                    clean_code = response.text.replace("```python", "").replace("```", "").strip()
                    
                    # Entorno de ejecución seguro con las variables necesarias
                    scope = {"df": df.copy(), "pd": pd, "col_map_final": col_map_final, "cols_detalle_prod": cols_detalle_prod}
                    exec(clean_code, scope)
                    
                    if "resultado" not in scope:
                        raise ValueError("El código generado no produjo la variable 'resultado'.")
                        
                    resultado = scope["resultado"]

                    st.markdown("**Análisis de Cortex:**")
                    
                    if isinstance(resultado, str):
                        st.markdown(resultado) 
                    elif isinstance(resultado, (pd.Series, pd.DataFrame)):
                        st.write(resultado) 
                        prompt_lower = prompt.lower()
                        try: 
                            if any(word in prompt_lower for word in ["tendencia", "evolución", "fecha", "tiempo"]) and 'FECHA_CLAVE' in col_map_final:
                                st.line_chart(resultado)
                            elif any(word in prompt_lower for word in ["top", "market", "ranking", "compradores", "competidor"]):
                                st.bar_chart(resultado)
                        except:
                            pass 
                    else:
                        st.write(resultado)
                            
                    st.session_state.messages.append({"role": "assistant", "content": "Análisis estratégico completado."})
                
                except Exception as e:
                    # Captura de errores de ejecución de Pandas generado por IA
                    st.error(f"🛡️ No se pudo ejecutar el análisis. El código generado por la IA falló con los datos actuales.")
                    with st.expander("Ver detalles técnicos del error (para soporte)"):
                        st.code(f"Error: {e}\n\nCódigo intentado:\n{clean_code}")

else:
    st.info("👋 Sube tu archivo para iniciar el análisis blindado.")


# ==========================================
# 7. ZONA DE PRUEBAS INTERNAS (SIN API KEY)
# ==========================================
# Descomenta estas líneas para probar si el saneamiento de datos
# y el mapeo de columnas funcionan sin llamar a Google.

# if st.checkbox("🛠️ Activar Modo Pruebas Internas (Sin API)"):
#     st.warning("Modo de pruebas activado. Sube un archivo para ver si el saneamiento funciona.")
#     if uploaded_file:
#         st.write("--- INICIO DIAGNÓSTICO ---")
#         st.write(f"Tipo detectado: {tipo_reporte}")
#         st.write("Columnas originales:", df.columns.tolist())
#         try:
#             # Simulamos la preparación
#             if tipo_reporte == "Licitaciones":
#                 df['Monto_Total_Estimado'] = pd.to_numeric(df['Cantidad Adjudicada'], errors='coerce').fillna(0) * pd.to_numeric(df['Monto Unitario'], errors='coerce').fillna(0)
#                 st.success(f"Cálculo de Monto Total exitoso. Suma total: ${df['Monto_Total_Estimado'].sum():,.0f}")
#                 st.write("Mapa de columnas propuesto:", {
#                     'MONTO': 'Monto_Total_Estimado', 'PROVEEDOR': 'Nombre Proveedor'
#                 })
#             elif tipo_reporte == "Convenio Marco":
#                 df['Precio Oferta'] = pd.to_numeric(df['Precio Oferta'], errors='coerce').fillna(0)
#                 st.success(f"Limpieza de Precio Oferta exitosa. Promedio: ${df['Precio Oferta'].mean():,.0f}")
#         except Exception as e:
#             st.error(f"Falló el diagnóstico: {e}")
#         st.write("--- FIN DIAGNÓSTICO ---")
