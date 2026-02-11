import streamlit as st
from supabase import create_client, Client
import pandas as pd

# 1. Conexión segura con Supabase
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

st.set_page_config(page_title="Mis Gastos", page_icon="💰")
st.title("💰 Mi App de Gastos")

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
    tab_gastos, tab_categorias, tab_informes = st.tabs(["💸 Movimientos", "⚙️ Categorías", "📊 Resumen"])

    # --- PESTAÑA: CATEGORÍAS (CON BLOQUEO DE DUPLICADOS Y BORRADO) ---
    with tab_categorias:
        st.subheader("Gestionar Categorías")
        
        # Cargar categorías actuales
        res_cats = supabase.table("user_categories").select("*").execute()
        current_cats = res_cats.data if res_cats.data else []
        cat_names_upper = [c['name'].upper() for c in current_cats]

        with st.expander("➕ Crear Nueva Categoría"):
            with st.form("form_cat"):
                name = st.text_input("Nombre de la categoría")
                budget = st.number_input("Presupuesto (€)", min_value=0.0)
                if st.form_submit_button("Guardar"):
                    if name.upper() in cat_names_upper:
                        st.error(f"La categoría '{name}' ya existe.")
                    elif name:
                        supabase.table("user_categories").insert({"user_id": st.session_state.user.id, "name": name, "budget": budget}).execute()
                        st.rerun()

        st.divider()
        for c in current_cats:
            col1, col2, col3 = st.columns([2, 1, 1])
            col1.write(f"**{c['name']}**")
            col2.write(f"{c['budget']}€")
            if col3.button("Eliminar", key=f"del_cat_{c['id']}"):
                supabase.table("user_categories").delete().eq("id", c['id']).execute()
                st.rerun()

    # --- PESTAÑA: MOVIMIENTOS (CON HISTORIAL Y BORRADO) ---
    with tab_gastos:
        st.subheader("Nuevo Movimiento")
        qty = st.number_input("Cantidad (€)", min_value=0.0, step=0.01)
        t_type = st.selectbox("Tipo", ["Gasto", "Ingreso"])
        
        options = {c['name']: c['id'] for c in current_cats}
        if options:
            sel_cat = st.selectbox("Categoría", options.keys())
            if st.button("Registrar"):
                supabase.table("user_imputs").insert({
                    "user_id": st.session_state.user.id, 
                    "quantity": qty, 
                    "type": t_type, 
                    "category_id": options[sel_cat]
                }).execute()
                st.success("¡Registrado!")
                st.rerun()
        
        st.divider()
        st.subheader("Historial Reciente")
        res_inputs = supabase.table("user_imputs").select("*, user_categories(name)").order("id", desc=True).limit(10).execute()
        if res_inputs.data:
            for i in res_inputs.data:
                c1, c2, c3, c4 = st.columns([2, 1, 1, 1])
                c1.write(i['user_categories']['name'] if i['user_categories'] else "S/C")
                c2.write(f"{i['quantity']}€")
                c3.write(i['type'])
                if c4.button("🗑️", key=f"del_inp_{i['id']}"):
                    supabase.table("user_imputs").delete().eq("id", i['id']).execute()
                    st.rerun()

    # --- PESTAÑA: INFORMES ---
    with tab_informes:
        # (Se mantiene la lógica anterior de las barras de progreso)
        st.subheader("Estado de Presupuestos")
        inputs_data = supabase.table("user_imputs").select("quantity, type, category_id").execute().data
        if current_cats and inputs_data:
            df_cats = pd.DataFrame(current_cats)
            df_inputs = pd.DataFrame(inputs_data)
            gastos = df_inputs[df_inputs['type'] == 'Gasto'].groupby('category_id')['quantity'].sum().reset_index()
            rep = pd.merge(df_cats, gastos, left_on='id', right_on='category_id', how='left').fillna(0)
            for _, r in rep.iterrows():
                st.write(f"**{r['name']}** ({r['quantity']}€ de {r['budget']}€)")
                st.progress(min(r['quantity']/r['budget'], 1.0) if r['budget'] > 0 else 0)
        else:
            st.info("Sin datos suficientes.")

else:
    st.info("Inicia sesión para continuar.")
