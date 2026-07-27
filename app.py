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
    # 1. Consultar modelos habilitados en tiempo real
    try:
        modelos_disponibles = [
            m.name for m in genai.list_models() 
            if 'generateContent' in m.supported_generation_methods
        ]
    except Exception as e:
        raise RuntimeError(f"Error al consultar lista de modelos de Google: {e}")

    if not modelos_disponibles:
        raise RuntimeError("Tu API Key no tiene modelos activos asignados.")

    # 2. Ordenar modelos (priorizando los rápidos tipo 'flash')
    modelos_ordenados = sorted(modelos_disponibles, key=lambda x: 0 if 'flash' in x.lower() else 1)

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

    # 3. Probar cada modelo disponible hasta que uno genere la respuesta con éxito
    ultimo_error = None
    for nombre_modelo in modelos_ordenados:
        try:
            model = genai.GenerativeModel(nombre_modelo)
            response = model.generate_content(prompt)
            
            # Limpiar etiquetas markdown de la respuesta
            raw_text = response.text.strip()
            if raw_text.startswith("```"):
                lines = raw_text.splitlines()
                if lines[0].startswith("```"):
                    lines = lines[1:]
                if lines and lines[-1].startswith("```"):
                    lines = lines[:-1]
                raw_text = "\n".join(lines).strip()

            return json.loads(raw_text)
        except Exception as err:
            ultimo_error = err
            continue

    raise RuntimeError(f"Ningún modelo de tu cuenta pudo procesar la solicitud. Detalle: {ultimo_error}")

# -----------------------------------------------------------------------------
# INTERFAZ DE USUARIO
# -----------------------------------------------------------------------------
st.title("💳 Clatri Private Engine")

# 1. SECCIÓN CUENTAS
st.subheader("📂 Cuentas")
res_cuentas = supabase.table("cuentas").select("*").execute()
cuentas = res_cuentas.data

if cuentas:
    cols = st.columns(len(cuentas))
    for idx, c in enumerate(cuentas):
        with cols[idx]:
            st.image(c.get("logo_url") or "[https://via.placeholder.com/40](https://via.placeholder.com/40)", width=40)
            st.metric(label=c["nombre"], value=f"${c['saldo']:,.0f} COP")
else:
    st.info("Escribe en el chat para agregar tu primera cuenta.")

st.divider()

# 2. SECCIÓN TRANSACCIONES
st.subheader("🧾 Últimas Transacciones")
res_trans = supabase.table("transacciones").select("*, cuentas(nombre)").order("fecha", desc=True).limit(5).execute()
for t in res_trans.data:
    with st.container(border=True):
        col_img, col_det, col_monto = st.columns([1, 3, 2])
        with col_img:
            st.image(t.get("logo_comercio") or "[https://via.placeholder.com/40](https://via.placeholder.com/40)", width=40)
        with col_det:
            st.markdown(f"**{t['comercio']}**")
            st.caption(f"{t['descripcion']} • {t['categoria']}")
        with col_monto:
            color = "green" if t['tipo'] == 'ingreso' else "red"
            signo = "+" if t['tipo'] == 'ingreso' else "-"
            st.markdown(f":{color}[**{signo}${t['monto']:,.0f} COP**]")

st.divider()

# 3. CHAT INTERACTIVO
prompt_usuario = st.chat_input("Escribe aquí tu movimiento...")
if prompt_usuario:
    with st.spinner("Procesando comando con IA..."):
        try:
            data_ia = procesar_mensaje_ia(prompt_usuario)
            banco_nombre = data_ia.get("banco")
            monto = float(data_ia.get("monto", 0))
            accion = data_ia.get("accion")
            
            res_banco = supabase.table("cuentas").select("*").eq("nombre", banco_nombre).execute()
            
            if not res_banco.data:
                logo_b = obtener_logo(banco_nombre)
                nuevo_saldo = monto if accion != "registrar_gasto" else 0
                cuenta_res = supabase.table("cuentas").insert({
                    "nombre": banco_nombre, "saldo": nuevo_saldo, "logo_url": logo_b
                }).execute()
                cuenta_id = cuenta_res.data[0]["id"]
            else:
                cuenta_db = res_banco.data[0]
                cuenta_id = cuenta_db["id"]
                nuevo_saldo = float(cuenta_db["saldo"]) - monto if accion == "registrar_gasto" else float(cuenta_db["saldo"]) + monto
                supabase.table("cuentas").update({"saldo": nuevo_saldo}).eq("id", cuenta_id).execute()

            if accion in ["registrar_gasto", "registrar_ingreso"]:
                logo_c = obtener_logo(data_ia.get("comercio", banco_nombre))
                supabase.table("transacciones").insert({
                    "cuenta_id": cuenta_id,
                    "comercio": data_ia.get("comercio", banco_nombre),
                    "descripcion": data_ia.get("descripcion", prompt_usuario),
                    "monto": monto,
                    "tipo": "gasto" if accion == "registrar_gasto" else "ingreso",
                    "categoria": data_ia.get("categoria", "General"),
                    "logo_comercio": logo_c
                }).execute()

            st.rerun()
        except Exception as err:
            st.error(f"⚠️ Respuesta de la IA: {err}")
