import streamlit as st
import pandas as pd
import google.generativeai as genai
import traceback
import random

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
# 3. MOTOR DE RUTEO Y PREGUNTAS DINÁMICAS
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

def generar_preguntas_sugeridas(columnas):
    preguntas = []
    cols_str = " ".join(columnas).lower()
    
    if "proveedor" in cols_str or "empresa" in cols_str:
        preguntas.append("Genera un informe comercial de la competencia (Market Share).")
        preguntas.append("¿Cuáles son los 3 proveedores que más volumen mueven?")
    if "organismo" in cols_str or "comprador" in cols_str or "región" in cols_str:
        preguntas.append("Genera un ranking de los mayores compradores o regiones.")
    if "producto" in cols_str or "descripcion" in cols_str:
        preguntas.append("Dime el detalle del producto más demandado o vendido.")
    if "precio" in cols_str or "monto" in cols_str:
        preguntas.append("Haz un análisis de la tendencia de precios o montos adjudicados.")
        
    if not preguntas:
        preguntas = ["Muéstrame un resumen estadístico de estos datos."]
        
    return random.sample(preguntas, min(len(preguntas), 4))

# ==========================================
# 4. INTERFAZ: SIDEBAR Y CARGA DE DATOS
# ==========================================
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/4712/4712139.png", width=80)
    st.title("Cortex Core")
    st.markdown("Sube tu reporte descargado del portal.")
    uploaded_file = st.file_uploader("Cargar Archivo Excel/CSV", type=['xlsx', 'csv'])
    
    st.markdown("---")
    if st.button("🧹 Limpiar Historial de Chat"):
        st.session_state.messages = []
        st.rerun()

# ==========================================
# 5. NÚCLEO DE PROCESAMIENTO Y DASHBOARDS ("OJO DE DIOS")
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
    st.success(f"✅ Archivo analizado exitosamente. **{len(df):,} registros procesados.**")
    st.markdown("---")
    
    # --- A. PREPARACIÓN DE DATOS BASE ---
    if tipo_reporte == "Licitaciones" or tipo_reporte == "Compras Ágiles":
        # Asegurar columnas calculadas para volumen de dinero si aplican
        if 'Cantidad Adjudicada' in df.columns and 'Monto Unitario' in df.columns:
            df['Cantidad Adjudicada'] = pd.to_numeric(df['Cantidad Adjudicada'], errors='coerce').fillna(0)
            df['Monto Unitario'] = pd.to_numeric(df['Monto Unitario'], errors='coerce').fillna(0)
            df['Monto_Total_Estimado'] = df['Cantidad Adjudicada'] * df['Monto Unitario']

    # --- B. DASHBOARD UNIVERSAL DE OCÉANOS AZULES (UNICORNIOS) ---
    st.subheader("🎯 Radar de Oportunidades: Océanos Azules")
    st.info("💡 **Inteligencia de Mercado:** Cortex escanea el archivo buscando negocios donde la competencia es mínima o nula (Monopolios).")
    
    # "Ojo de Dios": Buscar dinámicamente qué columnas usar para agrupar
    col_id = next((c for c in df.columns if c.lower() in ['codigoexterno', 'id licitacion', 'orden de compra', 'id producto']), None)
    col_prov = next((c for c in df.columns if c.lower() in ['nombre proveedor', 'proveedor', 'empresa', 'rut proveedor']), None)
    
    if col_id and col_prov:
        # Calcular competencia por ID
        competencia = df.groupby(col_id)[col_prov].nunique().reset_index()
        competencia.columns = [col_id, 'Num_Competidores']
        
        # Unir a la tabla base (tomando 1 fila representativa por ID)
        df_unicos = df.drop_duplicates(subset=[col_id]).merge(competencia, on=col_id)
        
        unicornios_df = df_unicos[df_unicos['Num_Competidores'] == 1]
        baja_comp_df = df_unicos[df_unicos['Num_Competidores'] == 2]
        
        col_u1, col_u2 = st.columns(2)
        col_u1.metric("🦄 Negocios Unicornio (1 solo Proveedor)", len(unicornios_df))
        col_u2.metric("🛡️ Baja Competencia (Solo 2 Proveedores)", len(baja_comp_df))
        
        if not unicornios_df.empty:
            st.markdown("#### 🔍 Detalle de Negocios Unicornio")
            
            # Buscar inteligentemente qué columnas mostrar en la tabla de unicornios
            col_monto = 'Monto_Total_Estimado' if 'Monto_Total_Estimado' in df.columns else next((c for c in df.columns if 'precio' in c.lower() or 'monto' in c.lower()), None)
            col_prod = next((c for c in df.columns if 'producto' in c.lower() or 'descripcion' in c.lower()), None)
            col_org = next((c for c in df.columns if 'organismo' in c.lower() or 'comprador' in c.lower() or 'región' in c.lower()), None)
            
            cols_to_show = [c for c in [col_id, col_org, col_prod, col_prov, col_monto] if c is not None]
            tabla_mostrar = unicornios_df[cols_to_show]
            
            if col_monto: # Ordenar por dinero si existe
                tabla_mostrar = tabla_mostrar.sort_values(by=col_monto, ascending=False)
                st.dataframe(tabla_mostrar.style.format({col_monto: "${:,.0f}"}), use_container_width=True, hide_index=True)
            else:
                st.dataframe(tabla_mostrar, use_container_width=True, hide_index=True)
    else:
        st.warning("⚠️ El archivo no contiene columnas claras de 'ID/Código' y 'Proveedor/Empresa' para calcular los monopolios.")

    st.markdown("---")

    # ==========================================
    # 6. MOTOR RAG: AGENTE IA (CONCIENCIA DE ESQUEMA)
    # ==========================================
    st.subheader(f"💬 Analista Estratégico Cortex")
    
    # Mostrar preguntas inteligentes basadas en sus datos reales
    preguntas_sugeridas = generar_preguntas_sugeridas(df.columns.tolist())
    with st.expander("💡 Preguntas sugeridas basadas en tus columnas (Haz clic)"):
        for p in preguntas_sugeridas:
            st.markdown(f"- *{p}*")

    # Mostrar historial de chat
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if prompt := st.chat_input("Escribe tu consulta comercial estratégica aquí..."):
        
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Cortex mapeando esquema y procesando estrategia..."):
                
                # --- EL CEREBRO BLINDADO ---
                columnas_disponibles = df.columns.tolist()
                
                system_instruction = f"""
                Eres Cortex, Director Comercial de SmartOffer.
                Dataset actual: '{tipo_reporte}'. 
                
                ATENCIÓN: Estas son las ÚNICAS columnas que existen en el DataFrame 'df':
                {columnas_disponibles}

                REGLAS CRÍTICAS DE PROGRAMACIÓN:
                1. SOLO usa las columnas de la lista de arriba. NUNCA inventes nombres de columnas.
                2. Si el usuario te pide un cálculo pero falta la columna necesaria, no uses código Pandas. Asigna a 'resultado' un string que diga que te falta esa columna en el reporte.
                3. Si tienes los datos: Devuelve SOLO código Python válido. Sin formato markdown (sin ```python).
                4. SIEMPRE asigna el resultado a la variable 'resultado'.
                5. Si piden "INFORME", "RESUMEN" o "ANÁLISIS": Extrae los datos con Pandas y construye un string en formato Markdown con el reporte ejecutivo. Asigna ese string a 'resultado'.
                6. Maneja valores nulos antes de sumar (fillna(0)).
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
                            if any(word in prompt_lower for word in ["tendencia", "evolución", "tiempo", "histórico"]):
                                st.line_chart(resultado)
                            elif any(word in prompt_lower for word in ["top", "market", "comparativa", "quien", "participacion", "ranking"]):
                                st.bar_chart(resultado)
                        except Exception:
                            pass 
                    else:
                        st.write(resultado)
                            
                    st.session_state.messages.append({"role": "assistant", "content": "Análisis estratégico completado."})
                
                except Exception as e:
                    st.error("⚠️ Hubo un error procesando esta consulta. Verifica que estés usando los nombres de las columnas que existen en tu archivo.")

else:
    st.info("👋 ¡Hola! Soy Cortex Analytics. Sube tu archivo Excel/CSV para activar el radar de oportunidades comerciales.")
