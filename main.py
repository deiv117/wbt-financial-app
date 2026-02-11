import streamlit as st
from supabase import create_client, Client
import pandas as pd
from datetime import datetime
import plotly.express as px # Nueva librería para gráficos bonitos

# 1. Conexión segura con Supabase
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

st.set_page_config(page_title="Mis Gastos", page_icon="💰")
st.title("💰 Mi App de Gastos")

# IMPORTANTE: Asegúrate de añadir 'plotly' a tu archivo requirements.txt en GitHub

# --- CONTROL DE SESIÓN ---
if 'user' not in st.session_state:
    st.session_state.user = None

with st.sidebar:
    st.header("Acceso")
    if not st.session_state.user:
        email = st.text_input("Correo electrónico")
        password = st.text_input("Contraseña", type="password")
        if st.button("Entrar"):
            try:
                res = supabase.auth.sign_in_with_password({"email": email, "password": password})
                st.session_state.user = res.user
                st.rerun()
            except: st.error("Credenciales incorrectas")
    else:
        st.write(f"Usuario: {st.session_state.user.email}")
        if st.button("Cerrar Sesión"):
            supabase.auth.sign_out()
            st.session_state.user = None
            st.rerun()

if st.session_state.user:
    tab_gastos, tab_categorias, tab_informes = st.tabs(["💸 Movimientos", "⚙️ Categorías", "📊 Resumen Mensual"])

    res_cats = supabase.table("user_categories").select("*").execute()
    current_cats = res_cats.data if res_cats.data else []

    # --- PESTAÑA: CATEGORÍAS ---
    with tab_categorias:
        st.subheader("Gestionar Categorías")
        cat_names_upper = [c['name'].upper() for c in current_cats]
        with st.expander("➕ Crear Nueva Categoría"):
            with st.form("form_cat"):
                name = st.text_input("Nombre")
                budget = st.number_input("Presupuesto (€)", min_value=0.0)
                if st.form_submit_button("Guardar"):
                    if name.upper() in cat_names_upper: st.error("Ya existe.")
                    elif name:
                        supabase.table("user_categories").insert({"user_id": st.session_state.user.id, "name": name, "budget": budget}).execute()
                        st.rerun()
        for c in current_cats:
            col1, col2, col3 = st.columns([2, 1, 1])
            col1.write(f"**{c['name']}**")
            col2.write(f"{c['budget']}€")
            if col3.button("Eliminar", key=f"del_cat_{c['id']}"):
                supabase.table("user_categories").delete().eq("id", c['id']).execute()
                st.rerun()

    # --- PESTAÑA: MOVIMIENTOS (CON SELECTOR DE FECHA) ---
    with tab_gastos:
        st.subheader("Nuevo Movimiento")
        col_q, col_t = st.columns(2)
        qty = col_q.number_input("Cantidad (€)", min_value=0.0, step=0.01)
        t_type = col_t.selectbox("Tipo", ["Gasto", "Ingreso"])
        
        # EL NUEVO CAMPO DE FECHA:
        fecha_mov = st.date_input("Fecha del movimiento", datetime.now())
        
        options = {c['name']: c['id'] for c in current_cats}
        if options:
            sel_cat = st.selectbox("Categoría", options.keys())
            if st.button("Registrar"):
                supabase.table("user_imputs").insert({
                    "user_id": st.session_state.user.id, 
                    "quantity": qty, 
                    "type": t_type, 
                    "category_id": options[sel_cat],
                    "date": str(fecha_mov) # Guardamos la fecha elegida
                }).execute()
                st.success("¡Registrado!")
                st.rerun()
        
        st.divider()
        st.subheader("Últimos 10 registros")
        res_inputs = supabase.table("user_imputs").select("*, user_categories(name)").order("date", desc=True).limit(10).execute()
        if res_inputs.data:
            for i in res_inputs.data:
                c1, c2, c3, c4 = st.columns([2, 1, 1, 1])
                c1.write(f"{i['date']} | {i['user_categories']['name'] if i['user_categories'] else 'S/C'}")
                c2.write(f"{i['quantity']}€")
                c3.write(i['type'])
                if c4.button("🗑️", key=f"del_inp_{i['id']}"):
                    supabase.table("user_imputs").delete().eq("id", i['id']).execute()
                    st.rerun()

    # --- PESTAÑA: INFORMES (CON GRÁFICO) ---
    with tab_informes:
        st.subheader("Análisis de Gastos")
        col_m, col_a = st.columns(2)
        meses = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
        sel_mes_nombre = col_m.selectbox("Mes", meses, index=datetime.now().month-1)
        sel_año = col_a.selectbox("Año", range(datetime.now().year-2, datetime.now().year+1), index=2)

        inputs_data = supabase.table("user_imputs").select("quantity, type, category_id, date, user_categories(name)").execute().data
        
        if current_cats and inputs_data:
            df_inputs = pd.DataFrame(inputs_data)
            df_inputs['date'] = pd.to_datetime(df_inputs['date'])
            df_filtrado = df_inputs[(df_inputs['date'].dt.month == meses.index(sel_mes_nombre) + 1) & (df_inputs['date'].dt.year == sel_año)]
            
            if not df_filtrado.empty:
                ingresos = df_filtrado[df_filtrado['type'] == 'Ingreso']['quantity'].sum()
                gastos = df_filtrado[df_filtrado['type'] == 'Gasto']['quantity'].sum()
                
                c1, c2, c3 = st.columns(3)
                c1.metric("Ingresos", f"{ingresos}€")
                c2.metric("Gastos", f"{gastos}€")
                c3.metric("Ahorro", f"{ingresos - gastos}€")

                # GRÁFICO DE TARTA (Distribución del gasto)
                df_gastos = df_filtrado[df_filtrado['type'] == 'Gasto']
                if not df_gastos.empty:
                    # Extraer el nombre de la categoría para el gráfico
                    df_gastos['cat_name'] = df_gastos['user_categories'].apply(lambda x: x['name'] if x else 'S/C')
                    fig = px.pie(df_gastos, values='quantity', names='cat_name', title='Distribución por Categoría')
                    st.plotly_chart(fig, use_container_width=True)

                st.divider()
                # Barras de presupuesto
                gastos_mes = df_gastos.groupby('category_id')['quantity'].sum().reset_index()
                df_cats = pd.DataFrame(current_cats)
                rep = pd.merge(df_cats, gastos_mes, left_on='id', right_on='category_id', how='left').fillna(0)
                for _, r in rep.iterrows():
                    if r['budget'] > 0 or r['quantity'] > 0:
                        st.write(f"**{r['name']}** ({r['quantity']}€ / {r['budget']}€)")
                        st.progress(min(r['quantity']/r['budget'], 1.0) if r['budget'] > 0 else 0)
            else:
                st.info("No hay datos para este mes.")
        else:
            st.info("Crea categorías y movimientos primero.")
else:
    st.info("Inicia sesión para continuar.")
