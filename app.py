import streamlit as st
from supabase import create_client
import google.generativeai as genai
import json

# -----------------------------------------------------------------------------
# CREDENCIALES Y CONFIGURACIÓN DE PÁGINA
# -----------------------------------------------------------------------------
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]

# Inicializar clientes
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
genai.configure(api_key=GEMINI_API_KEY)

st.set_page_config(
    page_title="Clatri Private Engine",
    page_icon="💳",
    layout="wide",
    initial_sidebar_state="expanded"
)

# -----------------------------------------------------------------------------
# ESTILOS CSS PERSONALIZADOS (Diseño Fintech Moderno)
# -----------------------------------------------------------------------------
st.markdown("""
<style>
    .block-container {
        padding-top: 1.5rem;
        padding-bottom: 2rem;
        max-width: 1200px;
    }
    
    [data-testid="stMetric"] {
        background-color: #161b22;
        border: 1px solid #30363d;
        border-radius: 12px;
        padding: 16px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    }
    
    .account-card {
        background-color: #161b22;
        border: 1px solid #30363d;
        border-radius: 12px;
        padding: 16px;
        text-align: center;
        transition: transform 0.2s ease, border-color 0.2s ease;
    }
    .account-card:hover {
        border-color: #58a6ff;
        transform: translateY(-2px);
    }
    
    .badge-gasto {
        background-color: rgba(248, 81, 73, 0.15);
        color: #f85149;
        border: 1px solid rgba(248, 81, 73, 0.4);
        padding: 2px 8px;
        border-radius: 6px;
        font-size: 0.75rem;
        font-weight: 600;
    }
    .badge-ingreso {
        background-color: rgba(46, 160, 67, 0.15);
        color: #3fb950;
        border: 1px solid rgba(46, 160, 67, 0.4);
        padding: 2px 8px;
        border-radius: 6px;
        font-size: 0.75rem;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)

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
        "coopercom": "https://logo.clearbit.com/google.com"
    }
    nombre_lower = nombre_entidad.lower()
    for clave, url in dominios_conocidos.items():
        if clave in nombre_lower:
            return url
    return f"https://ui-avatars.com/api/?name={nombre_entidad}&background=1f6feb&color=fff&bold=true"

def procesar_mensaje_ia(mensaje_usuario):
    try:
        modelos_disponibles = [
            m.name for m in genai.list_models() 
            if 'generateContent' in m.supported_generation_methods
        ]
    except Exception as e:
        raise RuntimeError(f"Error al consultar la lista de modelos de Google: {e}")

    if not modelos_disponibles:
        raise RuntimeError("Tu API Key no tiene modelos activos asignados.")

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

    ultimo_error = None
    for nombre_modelo in modelos_ordenados:
        try:
            model = genai.GenerativeModel(nombre_modelo)
            response = model.generate_content(prompt)
            
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

    raise RuntimeError(f"Error procesando el modelo. Detalle: {ultimo_error}")

# -----------------------------------------------------------------------------
# SIDEBAR
# -----------------------------------------------------------------------------
with st.sidebar:
    st.image("[https://ui-avatars.com/api/?name=Clatri+Engine&background=238636&color=fff&size=128](https://ui-avatars.com/api/?name=Clatri+Engine&background=238636&color=fff&size=128)", width=60)
    st.title("Clatri Engine")
    st.caption("Motor financiero privado impulsado por IA")
    
    st.divider()
    st.markdown("### 💡 Ejemplos de Comandos")
    st.info("""
    * *"Deposite 200.000 en Nequi"*
    * *"Gaste 45.000 en Éxito con DaviPlata"*
    * *"Pago de nómina 1.500.000 en Caja Social"*
    """)
    
    st.divider()
    st.caption("🟢 Estado del sistema: **Operativo**")

# -----------------------------------------------------------------------------
# CONSULTA DE DATOS BASE
# -----------------------------------------------------------------------------
res_cuentas = supabase.table("cuentas").select("*").execute()
cuentas = res_cuentas.data or []

res_trans = supabase.table("transacciones").select("*, cuentas(nombre)").order("fecha", desc=True).limit(10).execute()
transacciones = res_trans.data or []

patrimonio_total = sum(c.get("saldo", 0) for c in cuentas)
total_ingresos = sum(t.get("monto", 0) for t in transacciones if t.get("tipo") == "ingreso")
total_gastos = sum(t.get("monto", 0) for t in transacciones if t.get("tipo") == "gasto")

# -----------------------------------------------------------------------------
# ENCABEZADO Y KPIS PRINCIPALES
# -----------------------------------------------------------------------------
st.title("💳 Dashboard Financiero")
st.caption("Gestiona tu patrimonio e ingresos en tiempo real mediante comandos de voz o texto.")

col1, col2, col3 = st.columns(3)
with col1:
    st.metric(label="Patrimonio Total", value=f"${patrimonio_total:,.0f} COP")
with col2:
    st.metric(label="Ingresos Registrados", value=f"${total_ingresos:,.0f} COP", delta="Ingresos", delta_color="normal")
with col3:
    st.metric(label="Gastos Registrados", value=f"${total_gastos:,.0f} COP", delta="-Gastos", delta_color="inverse")

st.divider()

# -----------------------------------------------------------------------------
# SECCIÓN CUENTAS (GRID)
# -----------------------------------------------------------------------------
st.subheader("📂 Cuentas y Saldos")

if cuentas:
    num_cols = min(len(cuentas), 4)
    cols_cuentas = st.columns(num_cols)
    for idx, c in enumerate(cuentas):
        with cols_cuentas[idx % num_cols]:
            logo = c.get("logo_url") or obtener_logo(c["nombre"])
            st.markdown(f"""
            <div class="account-card">
                <img src="{logo}" width="40" height="40" style="border-radius: 50%; margin-bottom: 8px;" />
                <div style="font-weight: 600; font-size: 1.1rem; color: #c9d1d9;">{c['nombre']}</div>
                <div style="font-size: 1.3rem; font-weight: 700; color: #58a6ff; margin-top: 4px;">
                    ${c['saldo']:,.0f} <span style="font-size: 0.8rem; color: #8b949e;">COP</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
else:
    st.info("No tienes cuentas registradas aún. Escribe un mensaje abajo para agregar la primera.")

st.divider()

# -----------------------------------------------------------------------------
# SECCIÓN ÚLTIMAS TRANSACCIONES
# -----------------------------------------------------------------------------
st.subheader("🧾 Historial Reciente")

if transacciones:
    for t in transacciones:
        with st.container(border=True):
            col_img, col_det, col_cat, col_monto = st.columns([0.6, 3, 2, 2])
            
            logo_comercio = t.get("logo_comercio") or obtener_logo(t.get("comercio", "General"))
            
            with col_img:
                st.image(logo_comercio, width=40)
                
            with col_det:
                st.markdown(f"**{t.get('comercio', 'Movimiento')}**")
                cuenta_nombre = t.get("cuentas", {}).get("nombre") if isinstance(t.get("cuentas"), dict) else "Cuenta"
                st.caption(f"{t.get('descripcion', '')} • *{cuenta_nombre}*")
                
            with col_cat:
                badge_class = "badge-ingreso" if t.get('tipo') == 'ingreso' else "badge-gasto"
                tipo_texto = "INGRESO" if t.get('tipo') == 'ingreso' else "GASTO"
                st.markdown(f'<span class="{badge_class}">{tipo_texto}</span> <span style="color: #8b949e; font-size: 0.8rem; margin-left: 6px;">{t.get("categoria", "General")}</span>', unsafe_allow_html=True)
                
            with col_monto:
                color = "#3fb950" if t.get('tipo') == 'ingreso' else "#f85149"
                signo = "+" if t.get('tipo') == 'ingreso' else "-"
                st.markdown(f"<div style='text-align: right; font-weight: 700; font-size: 1.1rem; color: {color};'>{signo}${t.get('monto', 0):,.0f} COP</div>", unsafe_allow_html=True)
else:
    st.caption("No hay transacciones registradas.")

st.divider()

# -----------------------------------------------------------------------------
# CHAT INTERACTIVO
# -----------------------------------------------------------------------------
prompt_usuario = st.chat_input("Escribe tu movimiento (Ej: Gaste 30.000 en gasolina con DaviPlata)...")
if prompt_usuario:
    with st.spinner("Procesando transacción con IA..."):
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
            st.error(f"⚠️ Error al procesar: {err}")
