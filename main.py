import streamlit as st
from supabase import create_client, Client
import pandas as pd
from datetime import datetime
import plotly.express as px

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
                    st.info("Revisa tu email o intenta entrar.")
                except: st.error("Error al registrar")
    else:
        st.write(f"Conectado como: **{st.session_state.user.email}**")
        if st.button("Cerrar Sesión"):
            supabase.auth.sign_out()
            st.session_state.user = None
            st.rerun()

# --- CONTENIDO PRINCIPAL ---
if st.session_state.user:
    tab_gastos, tab_categorias, tab_informes = st.tabs(["💸 Movimientos", "⚙️ Categorías", "📊 Resumen Mensual"])

    # --- CARGA Y ORDENACIÓN DE CATEGORÍAS ---
    res_cats = supabase.table("user_categories").select("*").execute()
    # Ordenamos las categorías alfabéticamente por el campo 'name'
    current_cats = sorted(res_cats.data, key=lambda x: x['name'].lower()) if res_cats.data else []

    # --- PESTAÑA: GESTIONAR CATEGORÍAS ---
    with tab_categorias:
        st.subheader("Tus Categorías")
        cat_names_upper = [c['name'].upper() for c in current_cats]
        
        with st.expander("➕ Crear Nueva Categoría"):
            with st.form("form_cat"):
                name = st.text_input("Nombre de categoría")
                budget = st.number_input("Presupuesto Mensual (€)", min_value=0.0, step=10.0)
                if st.form_submit_button("Guardar"):
                    if name.upper() in cat_names_upper:
                        st.error("Esta categoría ya existe.")
                    elif name:
                        supabase.table("user_categories").insert({
                            "user_id": st.session_state.user.id, 
                            "name": name, 
                            "budget": budget
                        }).execute()
                        st.rerun()

        st.divider()
        for c in current_cats:
            col1, col2, col3 = st.columns([2, 1, 1])
            col1.write(f"**{c['name']}**")
            col2.write(f"{c['budget']}€")
            if col3.button("Eliminar", key=f"del_cat_{c['id']}"):
                supabase.table("user_categories").delete().eq("id", c['id']).execute()
                st.rerun()

    # --- PESTAÑA: REGISTRAR MOVIMIENTOS ---
    with tab_gastos:
        st.subheader("Nuevo Registro")
        col_q, col_t = st.columns(2)
        qty = col_q.number_input("Cantidad (€)", min_value=0.0, step=0.01)
        t_type = col_t.selectbox("Tipo", ["Gasto", "Ingreso"])
        fecha_mov = st.date_input("Fecha", datetime.now())
        
        # LÓGICA DE SELECTOR VACÍO Y BUSCADOR
        if current_cats:
            # Creamos la lista de nombres para el selector
            cat_list = [c['name'] for c in current_cats]
            # Añadimos la opción vacía al principio
            display_options = ["Selecciona una categoría..."] + cat_list
            
            # El componente selectbox permite escribir para buscar automáticamente
            sel_cat_name = st.selectbox("Categoría", options=display_options, index=0)
            
            if st.button("Guardar Registro"):
                if sel_cat_name == "Selecciona una categoría...":
                    st.warning("Por favor, selecciona una categoría válida.")
                else:
                    # Buscamos el ID de la categoría seleccionada
                    cat_id = next(c['id'] for c in current_cats if c['name'] == sel_cat_name)
                    
                    supabase.table("user_imputs").insert({
                        "user_id": st.session_state.user.id, 
                        "quantity": qty, 
                        "type": t_type, 
                        "category_id": cat_id,
                        "date": str(fecha_mov)
                    }).execute()
                    st.success("¡Anotado!")
                    st.rerun()
        else:
            st.warning("Crea una categoría primero en la pestaña correspondiente.")
        
        st.divider()
        st.subheader("Últimos Registros")
        res_inputs = supabase.table("user_imputs").select("*, user_categories(name)").order("date", desc=True).limit(15).execute()
        if res_inputs.data:
            for i in res_inputs.data:
                c1, c2, c3, c4 = st.columns([2, 1, 1, 1])
                nombre_cat = i['user_categories']['name'] if i['user_categories'] else "S/C"
                c1.write(f"**{i['date']}** | {nombre_cat}")
                c2.write(f"{i['quantity']}€")
                c3.write("📉" if i['type'] == "Gasto" else "📈")
                if c4.button("🗑️", key=f"del_inp_{i['id']}"):
                    supabase.table("user_imputs").delete().eq("id", i['id']).execute()
                    st.rerun()

    # --- PESTAÑA: INFORMES MENSUALES ---
    with tab_informes:
        st.subheader("Análisis Mensual")
        col_m, col_a = st.columns(2)
        meses = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
        sel_mes_nombre = col_m.selectbox("Mes", meses, index=datetime.now().month-1)
        sel_año = col_a.selectbox("Año", range(datetime.now().year-2, datetime.now().year+1), index=2)

        inputs_data = supabase.table("user_imputs").select("quantity, type, category_id, date, user_categories(name)").execute().data
        
        if current_cats and inputs_data:
            df_inputs = pd.DataFrame(inputs_data)
            df_inputs['date'] = pd.to_datetime(df_inputs['date'])
            sel_mes_num = meses.index(sel_mes_nombre) + 1
            df_filtrado = df_inputs[(df_inputs['date'].dt.month == sel_mes_num) & (df_inputs['date'].dt.year == sel_año)]
            
            if not df_filtrado.empty:
                ingresos = df_filtrado[df_filtrado['type'] == 'Ingreso']['quantity'].sum()
                gastos = df_filtrado[df_filtrado['type'] == 'Gasto']['quantity'].sum()
                
                c1, c2, c3 = st.columns(3)
                c1.metric("Ingresos", f"{ingresos}€")
                c2.metric("Gastos", f"{gastos}€")
                c3.metric("Ahorro", f"{ingresos - gastos}€")

                df_gastos_pie = df_filtrado[df_filtrado['type'] == 'Gasto']
                if not df_gastos_pie.empty:
                    df_gastos_pie['cat_name'] = df_gastos_pie['user_categories'].apply(lambda x: x['name'] if x else 'S/C')
                    fig = px.pie(df_gastos_pie, values='quantity', names='cat_name', title='Gasto por Categoría', hole=0.4)
                    st.plotly_chart(fig, use_container_width=True)

                st.divider()
                st.subheader("Presupuestos")
                # Aquí también usamos 'current_cats' que ya está ordenada alfabéticamente
                gastos_por_cat = df_gastos_pie.groupby('category_id')['quantity'].sum().reset_index()
                df_cats = pd.DataFrame(current_cats)
                rep = pd.merge(df_cats, gastos_por_cat, left_on='id', right_on='category_id', how='left').fillna(0)
                
                for _, r in rep.iterrows():
                    if r['budget'] > 0 or r['quantity'] > 0:
                        porcentaje = r['quantity'] / r['budget'] if r['budget'] > 0 else 0
                        if porcentaje < 0.8: status = "🟢"
                        elif porcentaje <= 1.0: status = "🟡"
                        else: status = "🔴"
                        
                        st.write(f"{status} **{r['name']}**")
                        st.progress(min(porcentaje, 1.0))
                        
                        texto = f"{r['quantity']}€ de {r['budget']}€"
                        if porcentaje > 1.0:
                            st.write(f":red[{texto} - ¡Exceso de {round(r['quantity'] - r['budget'], 2)}€!]")
                        else:
                            st.write(texto)
                        st.divider()
            else:
                st.info("No hay datos para el mes seleccionado.")
        else:
            st.info("Registra categorías y movimientos para ver el análisis.")

else:
    st.info("👋 ¡Hola! Inicia sesión para gestionar tus finanzas personales.")
