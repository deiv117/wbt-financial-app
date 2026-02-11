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
    tab_gastos, tab_categorias, tab_informes, tab_anual = st.tabs(["💸 Movimientos", "⚙️ Categorías", "📊 Mensual", "📅 Anual"])

    # Carga de categorías
    res_cats = supabase.table("user_categories").select("*").execute()
    current_cats = sorted(res_cats.data, key=lambda x: x['name'].lower()) if res_cats.data else []

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
                            n_budget = st.number_input("Presupuesto", value=0.0) if n_type == "Gasto" else 0.0
                            if st.form_submit_button("Actualizar"):
                                supabase.table("user_categories").update({"type": n_type, "budget": n_budget}).eq("id", c['id']).execute()
                                st.session_state[f"edit_{c['id']}"] = False
                                st.rerun()

        with col_gas:
            st.markdown("### 📉 Gastos")
            for c in [cat for cat in current_cats if cat.get('type') == "Gasto"]:
                with st.container(border=True):
                    st.write(f"**{c['name']}**")
                    st.caption(f"Presupuesto: {c['budget']}€")
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
                c2.write(f"{i['quantity']}€")
                c3.write("📉" if i['type'] == "Gasto" else "📈")
                if c4.button("🗑️", key=f"del_i_row_{i['id']}"):
                    supabase.table("user_imputs").delete().eq("id", i['id']).execute()
                    st.rerun()

    # --- INFORMES ---
    inputs_all = supabase.table("user_imputs").select("quantity, type, category_id, date, user_categories(name)").execute().data
    df_all = pd.DataFrame(inputs_all) if inputs_all else pd.DataFrame()
    if not df_all.empty:
        df_all['date'] = pd.to_datetime(df_all['date'])

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
                c1.metric("Ingresos", f"{round(ing_m,2)}€")
                c2.metric("Gastos", f"{round(gas_m,2)}€")
                c3.metric("Ahorro", f"{round(ing_m - gas_m, 2)}€")
                
                df_g_m = df_m[df_m['type'] == 'Gasto']
                if not df_g_m.empty:
                    df_g_m['cat_name'] = df_g_m['user_categories'].apply(lambda x: x['name'] if x else 'S/C')
                    st.plotly_chart(px.pie(df_g_m, values='quantity', names='cat_name', hole=0.4), use_container_width=True)
                    
                    st.divider()
                    st.subheader("Presupuestos del Mes")
                    gastos_cat_m = df_g_m.groupby('category_id')['quantity'].sum().reset_index()
                    cat_gastos = [c for c in current_cats if c.get('type') == 'Gasto']
                    if cat_gastos:
                        rep_m = pd.merge(pd.DataFrame(cat_gastos), gastos_cat_m, left_on='id', right_on='category_id', how='left').fillna(0)
                        for _, r in rep_m.iterrows():
                            porc = r['quantity'] / r['budget'] if r['budget'] > 0 else 0
                            status = "🟢" if porc < 0.8 else "🟡" if porc <= 1.0 else "🔴"
                            st.write(f"{status} **{r['name']}**")
                            st.progress(min(porc, 1.0))
                            st.write(f"{round(r['quantity'],2)}€ de {r['budget']}€")
                            st.divider()
            else: st.info("No hay datos para este mes.")

    with tab_anual:
        st.subheader("Resumen Anual")
        sel_año_a = st.selectbox("Año", range(datetime.now().year-2, datetime.now().year+1), index=2)
        if not df_all.empty:
            df_a = df_all[df_all['date'].dt.year == sel_año_a]
            if not df_a.empty:
                ing_a = df_a[df_a['type'] == 'Ingreso']['quantity'].sum()
                gas_a = df_a[df_a['type'] == 'Gasto']['quantity'].sum()
                c1, c2, c3 = st.columns(3)
                c1.metric("Ingresos", f"{round(ing_a,2)}€")
                c2.metric("Gastos", f"{round(gas_a,2)}€")
                c3.metric("Balance", f"{round(ing_a - gas_a,2)}€")
                
                # Semáforo Anual
                st.divider()
                st.subheader("Control Anual (Meta x12)")
                df_g_a = df_a[df_a['type'] == 'Gasto']
                gastos_cat_a = df_g_a.groupby('category_id')['quantity'].sum().reset_index()
                cat_gastos = [c for c in current_cats if c.get('type') == 'Gasto']
                if cat_gastos:
                    rep_a = pd.merge(pd.DataFrame(cat_gastos), gastos_cat_a, left_on='id', right_on='category_id', how='left').fillna(0)
                    for _, r in rep_a.iterrows():
                        b_anual = r['budget'] * 12
                        porc_a = r['quantity'] / b_anual if b_anual > 0 else 0
                        status_a = "🟢" if porc_a < 0.8 else "🟡" if porc_a <= 1.0 else "🔴"
                        st.write(f"{status_a} **{r['name']}**")
                        st.progress(min(porc_a, 1.0))
                        st.write(f"{round(r['quantity'],2)}€ de {round(b_anual,2)}€")
                        st.divider()
            else: st.info("No hay datos para este año.")
else:
    st.info("Inicia sesión para continuar.")
