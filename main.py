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
                    st.info("Revisa tu email.")
                except: st.error("Error")
    else:
        st.write(f"Usuario: **{st.session_state.user.email}**")
        if st.button("Cerrar Sesión"):
            supabase.auth.sign_out()
            st.session_state.user = None
            st.rerun()

# --- FUNCIONES POP-UP ---
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
    tab_gastos, tab_categorias, tab_prevision, tab_informes, tab_anual = st.tabs([
        "💸 Movimientos", "⚙️ Categorías", "🔮 Previsión", "📊 Mensual", "📅 Anual"
    ])

    # Carga de datos
    res_cats = supabase.table("user_categories").select("*").execute()
    current_cats = sorted(res_cats.data, key=lambda x: x['name'].lower()) if res_cats.data else []

    inputs_all = supabase.table("user_imputs").select("quantity, type, category_id, date, user_categories(name)").execute().data
    df_all = pd.DataFrame(inputs_all) if inputs_all else pd.DataFrame()
    if not df_all.empty:
        df_all['date'] = pd.to_datetime(df_all['date'])

    # --- PESTAÑA: PREVISIÓN ---
    with tab_prevision:
        st.subheader("🔮 Previsión Mensual Teórica")
        
        cat_gastos = [c for c in current_cats if c.get('type') == 'Gasto']
        total_previsto = sum(c['budget'] for c in cat_gastos)
        
        ingresos_medios = 0
        if not df_all.empty:
            df_ing = df_all[df_all['type'] == 'Ingreso']
            if not df_ing.empty:
                # Media de ingresos de los meses que tienen datos
                ingresos_medios = df_ing.groupby(df_ing['date'].dt.to_period('M'))['quantity'].sum().mean()

        c1, c2, c3 = st.columns(3)
        c1.metric("Gasto Presupuestado", f"{total_previsto:.2f}€")
        c2.metric("Media Ingresos Reales", f"{ingresos_medios:.2f}€")
        balance = ingresos_medios - total_previsto
        c3.metric("Ahorro Potencial", f"{balance:.2f}€")

        st.divider()
        
        if cat_gastos:
            col_graph, col_table = st.columns([1, 1])
            
            df_prev = pd.DataFrame(cat_gastos)
            
            with col_graph:
                st.write("**Distribución del Gasto Previsto**")
                fig = px.pie(df_prev, values='budget', names='name', hole=0.4)
                st.plotly_chart(fig, use_container_width=True)
            
            with col_table:
                st.write("**Detalle de Presupuestos**")
                # Formateamos la tabla para que se vea limpia
                df_table = df_prev[['name', 'budget']].copy()
                df_table.columns = ['Categoría', 'Presupuesto']
                df_table['Presupuesto'] = df_table['Presupuesto'].map('{:.2f}€'.format)
                st.dataframe(df_table, hide_index=True, use_container_width=True)
        else:
            st.warning("Añade categorías de gasto con presupuesto para ver la previsión.")

    # --- PESTAÑA: CATEGORÍAS ---
    with tab_categorias:
        st.subheader("Gestión de Categorías")
        if st.button("➕ Añadir Categoría"):
            crear_categoria_dialog(current_cats)
        
        st.divider()
        col_ing, col_gas = st.columns(2)
        with col_ing:
            st.markdown("### 📈 Ingresos")
            for c in [cat for cat in current_cats if cat.get('type') == "Ingreso"]:
                with st.container(border=True):
                    st.write(f"**{c['name']}**")
                    c1, c2 = st.columns(2)
                    if c1.button("📝", key=f"ed_i_{c['id']}"): st.session_state[f"edit_{c['id']}"] = True
                    if c2.button("🗑️", key=f"del_i_{c['id']}"):
                        supabase.table("user_categories").delete().eq("id", c['id']).execute()
                        st.rerun()
                    if st.session_state.get(f"edit_{c['id']}", False):
                        with st.form(f"f_ed_{c['id']}"):
                            n_type = st.selectbox("Tipo", ["Gasto", "Ingreso"], index=1)
                            if st.form_submit_button("Actualizar"):
                                supabase.table("user_categories").update({"type": n_type, "budget": 0}).eq("id", c['id']).execute()
                                st.session_state[f"edit_{c['id']}"] = False
                                st.rerun()

        with col_gas:
            st.markdown("### 📉 Gastos")
            for c in [cat for cat in current_cats if cat.get('type') == "Gasto"]:
                with st.container(border=True):
                    st.write(f"**{c['name']}**")
                    st.caption(f"Presupuesto: {c['budget']:.2f}€")
                    c1, c2 = st.columns(2)
                    if c1.button("📝", key=f"ed_g_{c['id']}"): st.session_state[f"edit_{c['id']}"] = True
                    if c2.button("🗑️", key=f"del_g_{c['id']}"):
                        supabase.table("user_categories").delete().eq("id", c['id']).execute()
                        st.rerun()
                    if st.session_state.get(f"edit_{c['id']}", False):
                        with st.form(f"f_ed_g_{c['id']}"):
                            n_type = st.selectbox("Tipo", ["Gasto", "Ingreso"], index=0)
                            n_budget = st.number_input("Presupuesto", value=float(c['budget']))
                            if st.form_submit_button("Actualizar"):
                                supabase.table("user_categories").update({"type": n_type, "budget": n_budget}).eq("id", c['id']).execute()
                                st.session_state[f"edit_{c['id']}"] = False
                                st.rerun()

    # --- PESTAÑA: MOVIMIENTOS ---
    with tab_gastos:
        st.subheader("Nuevo Registro")
        col_q, col_t = st.columns(2)
        qty = col_q.number_input("Cantidad (€)", min_value=0.0, step=0.01)
        t_type = col_t.selectbox("Tipo", ["Gasto", "Ingreso"])
        fecha_mov = st.date_input("Fecha", datetime.now())
        
        filtered_cats = [c for c in current_cats if c.get('type') == t_type]
        if filtered_cats:
            cat_list = [c['name'] for c in filtered_cats]
            sel_cat_name = st.selectbox("Categoría", options=["Selecciona..."] + cat_list)
            if st.button("Guardar Registro") and sel_cat_name != "Selecciona...":
                c_id = next(c['id'] for c in filtered_cats if c['name'] == sel_cat_name)
                supabase.table("user_imputs").insert({"user_id": st.session_state.user.id, "quantity": qty, "type": t_type, "category_id": c_id, "date": str(fecha_mov)}).execute()
                st.success("¡Registrado!")
                st.rerun()
        else: st.warning(f"Crea primero una categoría de {t_type}.")

        st.divider()
        res_i = supabase.table("user_imputs").select("*, user_categories(name)").order("date", desc=True).limit(10).execute()
        if res_i.data:
            for i in res_i.data:
                c1, c2, c3, c4 = st.columns([2, 1, 1, 1])
                c1.write(f"**{i['date']}** | {i['user_categories']['name'] if i['user_categories'] else 'S/C'}")
                c2.write(f"{i['quantity']:.2f}€")
                c3.write("📉" if i['type'] == "Gasto" else "📈")
                if c4.button("🗑️", key=f"del_i_row_{i['id']}"):
                    supabase.table("user_imputs").delete().eq("id", i['id']).execute()
                    st.rerun()

    # --- PESTAÑAS INFORMES (MISMA LÓGICA ANTERIOR) ---
    with tab_informes:
        st.subheader("Resumen Mensual")
        col_m, col_a = st.columns(2)
        meses = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
        sel_mes = col_m.selectbox("Mes", meses, index=datetime.now().month-1)
        sel_año_m = col_a.selectbox("Año ", range(datetime.now().year-2, datetime.now().year+1), index=2)
        if not df_all.empty:
            df_m = df_all[(df_all['date'].dt.month == meses.index(sel_mes)+1) & (df_all['date'].dt.year == sel_año_m)]
            if not df_m.empty:
                ing_m = df_m[df_m['type'] == 'Ingreso']['quantity'].sum()
                gas_m = df_m[df_m['type'] == 'Gasto']['quantity'].sum()
                c1, c2, c3 = st.columns(3)
                c1.metric("Ingresos", f"{ing_m:.2f}€")
                c2.metric("Gastos", f"{gas_m:.2f}€")
                c3.metric("Ahorro", f"{(ing_m - gas_m):.2f}€")
                
                df_g_m = df_m[df_m['type'] == 'Gasto']
                if not df_g_m.empty:
                    df_g_m['cat_name'] = df_g_m['user_categories'].apply(lambda x: x['name'] if x else 'S/C')
                    st.plotly_chart(px.pie(df_g_m, values='quantity', names='cat_name', hole=0.4), use_container_width=True)
                    
                    st.divider()
                    gastos_cat_m = df_g_m.groupby('category_id')['quantity'].sum().reset_index()
                    cat_gastos_list = [c for c in current_cats if c.get('type') == 'Gasto']
                    if cat_gastos_list:
                        rep_m = pd.merge(pd.DataFrame(cat_gastos_list), gastos_cat_m, left_on='id', right_on='category_id', how='left').fillna(0)
                        for _, r in rep_m.iterrows():
                            porc = r['quantity'] / r['budget'] if r['budget'] > 0 else 0
                            status = "🟢" if porc < 0.8 else "🟡" if porc <= 1.0 else "🔴"
                            st.write(f"{status} **{r['name']}**")
                            st.progress(min(porc, 1.0))
                            st.write(f"{r['quantity']:.2f}€ de {r['budget']:.2f}€")
                            st.divider()

    with tab_anual:
        st.subheader("Resumen Anual")
        sel_año_a = st.selectbox("Año Seleccionado", range(datetime.now().year-2, datetime.now().year+1), index=2)
        if not df_all.empty:
            df_a = df_all[df_all['date'].dt.year == sel_año_a]
            if not df_a.empty:
                ing_a = df_a[df_a['type'] == 'Ingreso']['quantity'].sum()
                gas_a = df_a[df_a['type'] == 'Gasto']['quantity'].sum()
                c1, c2, c3 = st.columns(3)
                c1.metric("Ingresos", f"{ing_a:.2f}€")
                c2.metric("Gastos", f"{gas_a:.2f}€")
                c3.metric("Balance", f"{(ing_a - gas_a):.2f}€")
else:
    st.info("Inicia sesión para continuar.")
