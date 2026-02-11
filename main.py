import streamlit as st
from supabase import create_client, Client
import pandas as pd
from datetime import datetime
import plotly.express as px
import plotly.graph_objects as go

# 1. CONEXIÓN SEGURA CON SUPABASE
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

st.set_page_config(page_title="Mis Gastos", page_icon="💰", layout="centered")
st.title("💰 Mi App de Gastos")

# --- CONTROL DE SESIÓN ---
if 'user' not in st.session_state:
    st.session_state.user = None

with st.sidebar:
    st.header("Acceso")
    if not st.session_state.user:
        email = st.text_input("Correo electrónico")
        password = st.text_input("Contraseña", type="password")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Entrar"):
                try:
                    res = supabase.auth.sign_in_with_password({"email": email, "password": password})
                    st.session_state.user = res.user
                    st.rerun()
                except: st.error("Error de acceso")
        with col2:
            if st.button("Registrarse"):
                try:
                    supabase.auth.sign_up({"email": email, "password": password})
                    st.info("Revisa tu email.")
                except: st.error("Error")
    else:
        st.write(f"Usuario: **{st.session_state.user.email}**")
        if st.button("Cerrar Sesión"):
            supabase.auth.sign_out()
            st.session_state.user = None
            st.rerun()

# --- FUNCIONES POP-UP (DIALOGS) ---
@st.dialog("➕ Crear Nueva Categoría")
def crear_categoria_dialog(current_cats):
    name = st.text_input("Nombre de categoría")
    c_type = st.selectbox("Tipo", ["Gasto", "Ingreso"])
    budget = 0.0
    if c_type == "Gasto":
        budget = st.number_input("Presupuesto Mensual (€)", min_value=0.0, step=10.0)
    
    if st.button("Guardar"):
        exists = any(c['name'].upper() == name.upper() and c.get('type') == c_type for c in current_cats)
        if exists:
            st.error("Ya existe esta categoría.")
        elif name:
            supabase.table("user_categories").insert({
                "user_id": st.session_state.user.id, 
                "name": name, "type": c_type, "budget": budget
            }).execute()
            st.rerun()

# --- CONTENIDO PRINCIPAL ---
if st.session_state.user:
    # AÑADIDA LA PESTAÑA DE PREVISIÓN
    tab_gastos, tab_categorias, tab_prevision, tab_informes, tab_anual = st.tabs([
        "💸 Movimientos", "⚙️ Categorías", "🔮 Previsión", "📊 Mensual", "📅 Anual"
    ])

    # Carga de categorías
    res_cats = supabase.table("user_categories").select("*").execute()
    current_cats = sorted(res_cats.data, key=lambda x: x['name'].lower()) if res_cats.data else []

    # Carga de movimientos para cálculos
    inputs_all = supabase.table("user_imputs").select("quantity, type, category_id, date, user_categories(name)").execute().data
    df_all = pd.DataFrame(inputs_all) if inputs_all else pd.DataFrame()
    if not df_all.empty:
        df_all['date'] = pd.to_datetime(df_all['date'])

    # --- PESTAÑA: PREVISIÓN (NUEVA) ---
    with tab_prevision:
        st.subheader("🔮 Previsión de Gastos Mensuales")
        st.info("Este es tu escenario teórico basado en tus presupuestos.")

        cat_gastos = [c for c in current_cats if c.get('type') == 'Gasto']
        total_presupuestado = sum(c['budget'] for c in cat_gastos)
        
        # Calcular ingresos medios (últimos 3 meses) para la previsión
        ingresos_medios = 0
        if not df_all.empty:
            df_ing = df_all[df_all['type'] == 'Ingreso']
            if not df_ing.empty:
                ingresos_medios = df_ing.groupby(df_ing['date'].dt.to_period('M'))['quantity'].sum().mean()

        c1, c2, c3 = st.columns(3)
        c1.metric("Gasto Comprometido", f"{round(total_presupuestado, 2)}€", help="Suma de todos tus presupuestos mensuales")
        c2.metric("Ingreso Estimado", f"{round(ingresos_medios, 2)}€", help="Media de tus ingresos mensuales reales")
        balance_prev = ingresos_medios - total_presupuestado
        c3.metric("Capacidad de Ahorro", f"{round(balance_prev, 2)}€", delta=f"{round(balance_prev,2)}€", delta_color="normal")

        st.divider()
        st.markdown("### 📋 Desglose de Previsión por Categoría")
        
        if cat_gastos:
            prev_data = []
            for c in cat_gastos:
                # Gasto real del mes actual para comparar
                real_mes_actual = 0
                if not df_all.empty:
                    mes_act = datetime.now().month
                    año_act = datetime.now().year
                    real_mes_actual = df_all[(df_all['category_id'] == c['id']) & 
                                            (df_all['date'].dt.month == mes_act) & 
                                            (df_all['date'].dt.year == año_act)]['quantity'].sum()
                
                prev_data.append({
                    "Categoría": c['name'],
                    "Presupuesto": c['budget'],
                    "Real (Este mes)": real_mes_actual
                })
            
            df_prev = pd.DataFrame(prev_data)
            
            # Gráfico comparativo
            fig_prev = go.Figure(data=[
                go.Bar(
