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
    tab_gastos, tab_categorias, tab_informes, tab_anual = st.tabs(["💸 Movimientos", "⚙️ Categorías", "📊 Resumen Mensual", "📅 Resumen Anual"])

    # --- CARGA Y ORDENACIÓN DE CATEGORÍAS ---
    # Nota: Asegúrate de que tu tabla 'user_categories' tenga una columna llamada 'type'
    res_cats = supabase.table("user_categories").select("*").execute()
    current_cats = sorted(res_cats.data, key=lambda x: x['name'].lower()) if res_cats.data else []

    # --- PESTAÑA: GESTIONAR CATEGORÍAS ---
    with tab_categorias:
        st.subheader("Gestionar Categorías")
        
        with st.expander("➕ Crear Nueva Categoría"):
            with st.form("form_cat"):
                name = st.text_input("Nombre de categoría")
                c_type = st.selectbox("Tipo de categoría", ["Gasto", "Ingreso"])
                budget = st.number_input("Presupuesto Mensual (€) - Solo para gastos", min_value=0.0, step=10.0)
                
                if st.form_submit_button("Guardar"):
                    # Validar duplicados por nombre Y tipo
                    exists = any(c['name'].upper() == name.upper() and c.get('type') == c_type for c in current_cats)
                    if exists:
                        st.error(f"La categoría de {c_type} '{name}' ya existe.")
                    elif name:
                        supabase.table("user_categories").insert({
                            "user_id": st.session_state.user.id, 
                            "name": name, 
                            "type": c_type,
                            "budget": budget if c_type == "Gasto" else 0
                        }).execute()
                        st.rerun()

        st.divider()
        col_ing, col_gas = st.columns(2)
        with col_ing:
            st.markdown("### 📈 Ingresos")
            for c in [cat for cat in current_cats if cat.get('type') == "Ingreso"]:
                c1, c2 = st.columns([3, 1])
                c1.write(f"{c['name']}")
                if c2.button("🗑️", key=f"del_cat_{c['id']}"):
                    supabase.table("user_categories").delete().eq("id", c['id']).execute()
                    st.rerun()

        with col_gas:
            st.markdown("### 📉 Gastos")
            for c in [cat for cat in current_cats if cat.get('type') == "Gasto"]:
                c1, c2 = st.columns([3, 1])
                c1.write(f"{c['name']} ({c['budget']}€)")
                if c2.button("🗑️", key=f"del_cat_{c['id']}"):
                    supabase.table("user_categories").delete().eq("id", c['id']).execute()
                    st.rerun()

    # --- PESTAÑA: REGISTRAR MOVIMIENTOS ---
    with tab_gastos:
        st.subheader("Nuevo Registro")
        col_q, col_t = st.columns(2)
        qty = col_q.number_input("Cantidad (€)", min_value=0.0, step=0.01)
        t_type = col_t.selectbox("¿Qué vas a registrar?", ["Gasto", "Ingreso"])
        fecha_mov = st.date_input("Fecha", datetime.now())
        
        # FILTRO DINÁMICO DE CATEGORÍAS
        filtered_cats = [c for c in current_cats if c.get('type') == t_type]
        
        if filtered_cats:
            cat_list = [c['name'] for c in filtered_cats]
            display_options = [f"Selecciona categoría de {t_type}..."] + cat_list
            sel_cat_name = st.selectbox("Categoría", options=display_options, index=0)
            
            if st.button("Guardar Registro"):
                if sel_cat_name.startswith("Selecciona"):
                    st.warning("Selecciona una categoría.")
                else:
                    cat_id = next(c['id'] for c in filtered_cats if c['name'] == sel_cat_name)
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
            st.warning(f"No tienes categorías de tipo '{t_type}' creadas.")
        
        st.divider()
        st.subheader("Historial")
        res_inputs = supabase.table("user_imputs").select("*, user_categories(name)").order("date", desc=True).limit(10).execute()
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

    # --- CARGA GENERAL DE INPUTS PARA INFORMES ---
    inputs_all = supabase.table("user_imputs").select("quantity, type, category_id, date, user_categories(name)").execute().data
    df_all = pd.DataFrame(inputs_all) if inputs_all else pd.DataFrame()
    if not df_all.empty:
        df_all['date'] = pd.to_datetime(df_all['date'])

    # --- PESTAÑA: INFORMES MENSUALES ---
    with tab_informes:
        st.subheader("Análisis Mensual")
        col_m, col_a = st.columns(2)
        meses = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
        sel_mes_nombre = col_m.selectbox("Mes", meses, index=datetime.now().month-1)
        sel_año_m = col_a.selectbox("Año ", range(datetime.now().year-2, datetime.now().year+1), index=2)
        
        if not df_all.empty:
            sel_mes_num = meses.index(sel_mes_nombre) + 1
            df_m = df_all[(df_all['date'].dt.month == sel_mes_num) & (df_all['date'].dt.year == sel_año_m)]
            if not df_m.empty:
                ing_m = df_m[df_m['type'] == 'Ingreso']['quantity'].sum()
                gas_m = df_m[df_m['type'] == 'Gasto']['quantity'].sum()
                c1, c2, c3 = st.columns(3)
                c1.metric("Ingresos", f"{round(ing_m,2)}€")
                c2.metric("Gastos", f"{round(gas_m,2)}€")
                c3.metric("Ahorro", f"{round(ing_m - gas_m, 2)}€")
                
                df_g_m = df_m[df_m['type'] == 'Gasto']
                if not df_g_m.empty:
                    df_g_m['cat_name'] = df_g_m['user_categories'].apply(lambda x: x['name'] if x else 'S/C')
                    st.plotly_chart(px.pie(df_g_m, values='quantity', names='cat_name', title='Distribución de Gastos', hole=0.4), use_container_width=True)
                    
                    st.divider()
                    st.subheader("Presupuestos")
                    res_g_m = df_g_m.groupby('category_id')['quantity'].sum().reset_index()
                    # Filtrar solo categorías de tipo Gasto para el informe de presupuestos
                    gastos_cats = [c for c in current_cats if c.get('type') == "Gasto"]
                    if gastos_cats:
                        rep_m = pd.merge(pd.DataFrame(gastos_cats), res_g_m, left_on='id', right_on='category_id', how='left').fillna(0)
                        for _, r in rep_m.iterrows():
                            porc = r['quantity']/r['budget'] if r['budget'] > 0 else 0
                            status = "🟢" if porc < 0.8 else "🟡" if porc <= 1.0 else "🔴"
                            st.write(f"{status} **{r['name']}**")
                            st.progress(min(porc, 1.0))
                            st.write(f"{r['quantity']}€ de {r['budget']}€")
            else: st.info("Sin datos este mes.")

    # --- PESTAÑA: INFORMES ANUALES ---
    with tab_anual:
        st.subheader("Análisis Anual")
        sel_año_a = st.selectbox("Selecciona Año", range(datetime.now().year-2, datetime.now().year+1), index=2)
        
        if not df_all.empty:
            df_a = df_all[df_all['date'].dt.year == sel_año_a]
            if not df_a.empty:
                ing_a = df_a[df_a['type'] == 'Ingreso']['quantity'].sum()
                gas_a = df_a[df_a['type'] == 'Gasto']['quantity'].sum()
                
                c1, c2, c3 = st.columns(3)
                c1.metric("Ingresos Anuales", f"{round(ing_a, 2)}€")
                c2.metric("Gastos Anuales", f"{round(gas_a, 2)}€")
                c3.metric("Balance Anual", f"{round(ing_a - gas_a, 2)}€")

                # Gráfico barras
                df_a_mes = df_a.copy()
                df_a_mes['month'] = df_a_mes['date'].dt.month
                df_a_mes = df_a_mes.groupby(['month', 'type'])['quantity'].sum().reset_index()
                df_a_mes['Mes'] = df_a_mes['month'].apply(lambda x: meses[int(x)-1])
                st.plotly_chart(px.bar(df_a_mes, x='Mes', y='quantity', color='type', barmode='group', title='Histórico Mensual'), use_container_width=True)

                st.divider()
                st.subheader("Metas Anuales (Solo Gastos)")
                df_g_a = df_a[df_a['type'] == 'Gasto']
                res_g_a = df_g_a.groupby('category_id')['quantity'].sum().reset_index()
                gastos_cats = [c for c in current_cats if c.get('type') == "Gasto"]
                
                if gastos_cats:
                    rep_a = pd.merge(pd.DataFrame(gastos_cats), res_g_a, left_on='id', right_on='category_id', how='left').fillna(0)
                    for _, r in rep_a.iterrows():
                        budget_anual = r['budget'] * 12
                        porc_a = r['quantity'] / budget_anual if budget_anual > 0 else 0
                        status_a = "🟢" if porc_a < 0.8 else "🟡" if porc_a <= 1.0 else "🔴"
                        st.write(f"{status_a} **{r['name']}**")
                        st.progress(min(porc_a, 1.0))
                        st.write(f"{round(r['quantity'],2)}€ de {round(budget_anual,2)}€")
                        st.divider()
            else: st.info("Sin datos para este año.")
else:
    st.info("👋 Inicia sesión para continuar.")
