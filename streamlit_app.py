import streamlit as st
import google.generativeai as genai
import random # NUEVO: Necesario para elegir llaves al azar

# Configuración visual
st.set_page_config(page_title="Tutor de Fisiología", page_icon="🧬")
st.title("🧬 Tutor de Aprendizaje Guiado")

# Mensaje de bienvenida
st.info("Bienvenido al espacio de aprendizaje sobre Fisiología - Dr. Mariano Blake")

# --- NUEVO: SISTEMA DE ROTACIÓN DE LLAVES ---
# Ahora buscamos una LISTA de llaves en lugar de una sola.
if "GOOGLE_API_KEYS" not in st.secrets:
    st.error("Error: No se encontraron las llaves de seguridad (GOOGLE_API_KEYS).")
    st.stop()

# Guardamos la lista de llaves en una variable
api_keys = st.secrets["GOOGLE_API_KEYS"]

# Configuración técnica del modelo
generation_config = {
  "temperature": 0.5,
  "top_p": 0.95,
  "top_k": 64,
  "max_output_tokens": 8192,
}

# --- SYSTEM PROMPT (Intacto) ---
SYSTEM_PROMPT = """
# PERSONA Y ROL
Eres el "Tutor de Fisiología". Tu objetivo es el dominio total del alumno mediante Diálogo Socrático.

# REGLAS CRÍTICAS
1. NO AVANCES de bloque si hay dudas o errores.
2. REFUERZO: Si falla, explica en máx 4 líneas y pregunta de nuevo con otro enfoque.
3. FOCO: Prohibido hablar de temas ajenos. Redirige con: "Mantengamos el foco en...".
4. PERSONALIZACIÓN: Usa siempre el nombre del alumno y tono amable.

# RUTA (BLOQUES)
B1: Presentación (Pide el nombre)
B2: Transporte de O2 (disuelto y unido a Hemoglobina (Hb), Curva de disociación de la Hb, desplazamiento de la curva)
B3: Transporte de CO2 (disuelto, compuestos carbamínicos y bicarbonato); Formación de Bicarbonato en el eritrocito y el efecto Hamburger; Efecto Haldane
B4: Interacción integradora (alteraciones del transporte, intoxicación por CO, anemia)
B5: Metacognición (Retos y dudas finales)

# MOTOR DE RAZONAMIENTO
- Evalúa comprensión real antes de cada respuesta.
- Si detectas repetición "de memoria", lanza un "por qué" o un "qué pasaría si...".
- No des respuestas directas; guía al alumno para que las descubra.
"""

# --- BÚSQUEDA DINÁMICA DEL MODELO ---
def get_latest_flash_model():
    try:
        for m in genai.list_models():
            if 'flash' in m.name.lower() and 'generateContent' in m.supported_generation_methods:
                return m.name
    except Exception:
        return 'gemini-1.5-flash'
    return 'gemini-1.5-flash'

# Inicializar historial de chat
if "messages" not in st.session_state:
    st.session_state.messages = []
    bienvenida = "¡Hola! Soy tu tutor de Fisiología. Vamos a trabajar sobre Transporte de gases en sangre. Para empezar, dime por favor tu nombre"
    st.session_state.messages.append({"role": "assistant", "content": bienvenida})

# Mostrar historial
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# --- MOTOR PRINCIPAL: Lógica de respuesta ---
if prompt := st.chat_input("Escribe aquí..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        try:
            # 1. BALANCEO DE CARGA: Elegimos una llave al azar para esta interacción
            llave_elegida = random.choice(api_keys)
            genai.configure(api_key=llave_elegida)
            
            # 2. INICIALIZACIÓN DEL MODELO
            MODEL_NAME = get_latest_flash_model()
            model = genai.GenerativeModel(
                model_name=MODEL_NAME,
                system_instruction=SYSTEM_PROMPT,
                generation_config=generation_config
            )

            # 3. VENTANA DE MEMORIA (Sliding Window)
            window_size = 6
            # Extraemos los últimos mensajes para no enviar historiales infinitos
            history_window = st.session_state.messages[-(window_size+1):-1]
            
            # Formateamos el historial recortado para la API
            formatted_history = [
                {"role": m["role"] if m["role"] != "assistant" else "model", "parts": [m["content"]]}
                for m in history_window
            ]

            # 4. ENVIAR CONSULTA
            chat_session = model.start_chat(history=formatted_history)
            response = chat_session.send_message(prompt)
            
            # 5. MOSTRAR Y GUARDAR RESPUESTA
            st.markdown(response.text)
            st.session_state.messages.append({"role": "assistant", "content": response.text})

        except Exception as e:
            # 6. MANEJO DE CUOTA "ANTI-PÁNICO"
            error_str = str(e).lower()
            if "429" in error_str or "quota" in error_str or "exhausted" in error_str:
                st.warning("⚠️ **¡Hola! Estoy procesando muchas consultas de tus compañeros.**")
                st.info("Para no saturarme y poder seguir ayudándote, por favor espera unos 30 segundos y vuelve a enviar tu mensaje. ¡Gracias por la paciencia!")
            else:
                st.error(f"Ocurrió un error en la conexión: {e}")
