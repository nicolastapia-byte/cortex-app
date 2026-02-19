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

def generar_preguntas_sugeridas(tipo_reporte, columnas):
    preguntas = []
    cols_str = " ".join(columnas).lower()
    
    # Inteligencia de sugerencias basada estrictamente en lo que existe
    if "proveedor" in cols_str or "empresa" in cols_str:
        preguntas.append("Genera un informe comercial de la competencia (Market Share).")
        preguntas.append("¿Cuáles son los 3 proveedores que más dinero mueven?")
    
    if "organismo" in cols_str or "comprador" in cols_str:
        preguntas.append("¿Cuáles son las instituciones o compradores más frecuentes?")
        preguntas.append("Genera un ranking de los 5 mayores compradores.")
        
    if "producto" in cols_str or "descripcion" in cols_str:
        preguntas.append("Dime el detalle de postulaciones y precios del producto más vendido.")
        preguntas.append("¿Cuál es el producto o ID que genera más volumen de dinero?")
        
    if "precio" in cols_str or "monto" in cols_str:
        preguntas.append("Haz un análisis de la tendencia de precios.")
        preguntas.append("¿Cuál es el precio promedio, máximo y mínimo ofertado?")
        
    if not preguntas:
        preguntas = ["Muéstrame un resumen estadístico de estos datos.", "¿Cuántos registros únicos hay por cada categoría?"]
        
    return random.sample(preguntas, min(len(preguntas), 4)) # Sugerir hasta 4

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
    st.success(f"✅ Archivo analizado exitosamente. **{len(df):,} registros procesados.**")
    st.markdown("---")
    
    # --- PREPARACIÓN DE DATOS (Segura) ---
    if tipo_reporte == "Convenio Marco":
        df['Fecha_Datetime'] = pd.to_datetime(df.get('Fecha Lectura', pd.Series()), format='mixed', dayfirst=True, errors='coerce')
        st.subheader("⚡ Radar de Convenio Marco")
        # (Oculto en esta vista simplificada de dashboard para dar espacio al chat, puedes restaurar los KPIs si lo deseas)
        st.dataframe(df.head(3), use_container_width=True)

    elif tipo_reporte == "Licitaciones":
        df['Fecha_Datetime'] = pd.to_datetime(df.get('Fecha Adjudicación', pd.Series()), format='mixed', dayfirst=True, errors='coerce')
        df['Cantidad Adjudicada'] = pd.to_numeric(df.get('Cantidad Adjudicada', pd.Series()), errors='coerce').fillna(0)
        df['Monto Unitario'] = pd.to_numeric(df.get('Monto Unitario', pd.Series()), errors='coerce').fillna(0)
        if 'Monto_Total_Estimado' not in df.columns:
            df['Monto_Total_Estimado'] = df['Cantidad Adjudicada'] * df['Monto Unitario']
        
        st.subheader("📊 Panel Estratégico de Licitaciones")
        st.dataframe(df.head(3), use_container_width=True)
    else: 
        st.subheader(f"🛒 Panel de Visualización")
        st.dataframe(df.head(3), use_container_width=True)

    st.markdown("---")

    # ==========================================
    # 6. MOTOR RAG: AGENTE IA (CONCIENCIA DE ESQUEMA)
    # ==========================================
    st.subheader(f"💬 Analista Estratégico Cortex")
    
    # 💡 UI: Mostrar preguntas inteligentes basadas en sus datos reales
    preguntas_sugeridas = generar_preguntas_sugeridas(tipo_reporte, df.columns.tolist())
    with st.expander("💡 Preguntas sugeridas basadas en tus columnas (Haz clic)"):
        for p in preguntas_sugeridas:
            st.markdown(f"- *{p}*")

    # Mostrar historial
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if prompt := st.chat_input("Escribe tu consulta estratégica aquí..."):
        
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Cortex mapeando esquema y procesando estrategia..."):
                
                # --- EL CEREBRO BLINDADO (CONCIENCIA DE COLUMNAS) ---
                columnas_disponibles = df.columns.tolist()
                
                system_instruction = f"""
                Eres Cortex, Director Comercial de SmartOffer.
                Dataset actual: '{tipo_reporte}'. 
                
                ATENCIÓN: Estas son las ÚNICAS columnas que existen en tu DataFrame 'df':
                {columnas_disponibles}

                REGLAS CRÍTICAS DE PROGRAMACIÓN (SI VIOLAS ESTO, EL SISTEMA EXPLOTA):
                1. SOLO usa las columnas de la lista de arriba. NUNCA inventes nombres de columnas. NUNCA asumas que existe 'Proveedor' si solo dice 'Nombre Proveedor'.
                2. Si el usuario te pide un cálculo (ej. Market Share) pero te falta la columna necesaria (ej. no hay nada sobre proveedor), NO escribas código Pandas. Simplemente asigna a la variable 'resultado' un string que diga: "No puedo calcular esto porque en tu archivo falta una columna que indique [lo que falte]."
                3. Si tienes los datos: Devuelve SOLO código Python válido (sin markdown ```python). 
                4. SIEMPRE asigna el resultado final a la variable 'resultado'.
                5. Si piden un "INFORME", "RESUMEN" o "ANÁLISIS COMERCIAL": Escribe código Pandas para extraer los datos reales de 'df', y usa esos datos para construir un string en formato Markdown. Asigna ese string a 'resultado'.
                6. Maneja los valores nulos (fillna o dropna) antes de agrupar o sumar.
                """
                
                try:
                    response = model.generate_content([system_instruction, prompt])
                    clean_code = response.text.replace("```python", "").replace("```", "").strip()
                    
                    # Ejecución protegida
                    scope = {"df": df.copy(), "pd": pd}
                    exec(clean_code, scope)
                    
                    if "resultado" not in scope:
                        raise ValueError("El agente no generó la variable 'resultado'.")
                        
                    resultado = scope["resultado"]

                    # Renderizado Dinámico
                    st.markdown("**Análisis de Cortex:**")
                    
                    if isinstance(resultado, str):
                        st.markdown(resultado) # Imprime informes de texto o mensajes de error amigables
                    elif isinstance(resultado, (pd.Series, pd.DataFrame)):
                        st.write(resultado) # Muestra tablas
                        
                        # Lógica de gráficos segura
                        prompt_lower = prompt.lower()
                        try: # Intentar graficar, si falla por tipos de datos, no romper la app
                            if any(word in prompt_lower for word in ["tendencia", "evolución", "tiempo", "histórico"]):
                                st.line_chart(resultado)
                            elif any(word in prompt_lower for word in ["top", "market", "comparativa", "quien", "participacion", "ranking"]):
                                st.bar_chart(resultado)
                        except Exception as chart_error:
                            pass # Si no se puede graficar, la tabla ya se mostró arriba
                    else:
                        st.write(resultado)
                            
                    st.session_state.messages.append({"role": "assistant", "content": "Análisis estratégico completado."})
                
                except Exception as e:
                    st.error(f"⚠️ Hubo un error procesando esta consulta. Verifica que estés mencionando las columnas correctamente.")
                    # Solo en desarrollo, quita esto para la demo final:
                    st.toast(f"Error Técnico AI: Trató de usar columnas inválidas o falló la sintaxis.") 

else:
    st.info("👋 ¡Hola! Soy Cortex Analytics. Sube tu archivo Excel/CSV para que analice tus columnas y activemos el modo estratégico.")
