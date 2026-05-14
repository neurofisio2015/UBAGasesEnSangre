import streamlit as st
import google.generativeai as genai
import random

# Configuración visual
st.set_page_config(page_title="Tutor de Fisiología", page_icon="🧬")
st.title("🧬 Tutor de Aprendizaje Guiado")

# Mensaje de bienvenida
st.info("Bienvenido al espacio de aprendizaje del Dr. Mariano Blake")

# Acceso seguro a las llaves (Balanceo de carga)
if "GOOGLE_API_KEYS" not in st.secrets:
    st.error("Error: Configura GOOGLE_API_KEYS en los Secrets.")
    st.stop()

api_keys = st.secrets["GOOGLE_API_KEYS"]

# --- SYSTEM PROMPT SIMPLIFICADO (Versión Liviana) ---
SYSTEM_PROMPT = """
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

# --- MOTOR PARA FORZAR 1.5 FLASH ---
def get_stabilized_model():
    try:
        # Prioridad absoluta a Gemini 1.5 Flash para evitar colapsos 
        for m in genai.list_models():
            if 'gemini-1.5-flash' in m.name.lower() and 'generateContent' in m.supported_generation_methods:
                return m.name
        return 'gemini-1.5-flash'
    except Exception:
        return 'gemini-1.5-flash'

# Inicializar historial
if "messages" not in st.session_state:
    st.session_state.messages = []
    bienvenida = "¡Hola! Soy tu tutor de Fisiología. Trabajaremos sobre Transporte de gases en la sangre. ¿Cómo te llamas?"
    st.session_state.messages.append({"role": "assistant", "content": bienvenida})

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# --- LÓGICA DE RESPUESTA ---
if prompt := st.chat_input("Escribe aquí..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        try:
            # Rotación de llaves para balancear carga
            genai.configure(api_key=random.choice(api_keys))
            
            model = genai.GenerativeModel(
                model_name=get_stabilized_model(),
                system_instruction=SYSTEM_PROMPT
            )

            # Ventana de memoria ultra-reducida (4 mensajes) para ahorrar tokens 
            history_window = st.session_state.messages[-5:-1]
            formatted_history = [
                {"role": m["role"] if m["role"] != "assistant" else "model", "parts": [m["content"]]}
                for m in history_window
            ]

            chat_session = model.start_chat(history=formatted_history)
            response = chat_session.send_message(prompt)
            
            st.markdown(response.text)
            st.session_state.messages.append({"role": "assistant", "content": response.text})

        except Exception as e:
            if "429" in str(e) or "quota" in str(e).lower():
                st.warning("⚠️ **Alta demanda.** Por favor, espera 20 segundos y reintenta.")
            else:
                st.error(f"Error: {e}")
