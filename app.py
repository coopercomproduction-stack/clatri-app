import streamlit as st
from supabase import create_client
import google.generativeai as genai
import json

# -----------------------------------------------------------------------------
# CREDENCIALES Y CONFIGURACIÓN
# -----------------------------------------------------------------------------
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]

# Inicializar clientes
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
genai.configure(api_key=GEMINI_API_KEY)

st.set_page_config(page_title="Clatri Private Engine", page_icon="💳", layout="centered")

# -----------------------------------------------------------------------------
# FUNCIONES AUXILIARES
# -----------------------------------------------------------------------------
def obtener_logo(nombre_entidad):
    dominios_conocidos = {
        "davivienda": "https://logo.clearbit.com/davivienda.com",
        "nu": "https://logo.clearbit.com/nubank.com.co",
        "nequi": "https://logo.clearbit.com/nequi.com.co",
        "daviplata": "https://logo.clearbit.com/daviplata.com",
        "caja social": "https://logo.clearbit.com/bancocajasocial.com",
        "mi.com": "https://logo.clearbit.com/mi.com",
        "xiaomi": "https://logo.clearbit.com/mi.com"
    }
    nombre_lower = nombre_entidad.lower()
    for clave, url in dominios_conocidos.items():
        if clave in nombre_lower:
            return url
    return f"https://logo.clearbit.com/{nombre_lower.replace(' ', '')}.com"

def procesar_mensaje_ia(mensaje_usuario):
    # 1. Consultar a Google en tiempo real cuáles modelos están habilitados para tu API Key
    try:
        modelos_disponibles = [
            m.name for m in genai.list_models() 
            if 'generateContent' in m.supported_generation_methods
        ]
    except Exception as e:
        raise RuntimeError(f"Error al consultar la lista de modelos de Google: {e}")

    if not modelos_disponibles:
        raise RuntimeError("Tu API Key no tiene ningún modelo activo asignado en Google AI Studio.")

    # 2. Elegir preferiblemente un modelo 'flash' (más rápido y barato), o el primero que responda
    nombre_modelo = next((m for m in modelos_disponibles if 'flash' in m), modelos_disponibles[0])
    
    # 3. Iniciar el modelo seleccionado
    model = genai.GenerativeModel(nombre_modelo)
    
    prompt = f"""
    Eres el motor contable de una app financiera. Analiza el siguiente mensaje y devuelve ÚNICAMENTE un JSON válido.

    Mensaje: "{mensaje_usuario}"

    Formato JSON esperado:
    {{
        "accion": "crear_o_actualizar_cuenta" | "registrar_gasto" | "registrar_ingreso",
        "banco": "Nombre del Banco/Cuenta",
        "comercio": "Nombre del Comercio (o el banco si es depósito)",
        "monto": numero_entero_o_flotante,
        "categoria": "Categoría sugerida",
        "descripcion": "Breve detalle"
    }}
    """
    
    # 4. Generar y limpiar la respuesta
    response = model.generate_content(prompt)
    texto_limpio = response.text.replace("```json", "").replace("
