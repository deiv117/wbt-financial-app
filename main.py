import streamlit as st
from supabase import create_client, Client
import pandas as pd # Usaremos esto para manejar los datos más fácil

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
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Entrar"):
                try:
                    res = supabase.auth.sign_in_with_password({"email": email, "password": password})
                    st.session_state.user = res.user
                    st.rerun()
                except: st.error("Error")
        with col2:
            if st.button("Registrarse"):
                try:
                    supabase.auth.sign_up({"email": email, "password": password})
                    st.info("Revisa tu email")
                except: st.error("Error")
    else:
        st.write(f"Usuario: {st.session_state.user.email}")
        if st.button("Cerrar Sesión"):
            supabase.auth.sign_out()
            st.session_state.user = None
            st.rerun()

# --- CONTENIDO PARA USUARIOS LOGUEADOS ---
if st.session_state.user:
    tab_gastos, tab_categorias, tab_informes = st.tabs(["💸 Movimientos", "⚙️ Categorías", "📊 Resumen Mensual"])

    # --- PESTAÑA: GESTIONAR CATEGORÍAS (Igual que antes) ---
    with tab_categorias:
        st.subheader("Tus Categorías")
        with st.form("nueva_categoria"):
            new_cat_name = st.text_input("Nombre (ej. Ocio)")
            new_cat_budget = st.number_input("Presupuesto Mensual (€)", min_value=0.0, step=10.0)
            if st.form_submit_button("Crear"):
                supabase.table("user_categories").insert({"user_id": st.session_state.user.id, "name": new_cat_name, "budget": new_cat_budget}).execute()
                st.rerun()

    # --- PESTAÑA: REGISTRAR GASTOS (Igual que antes) ---
    with tab_gastos:
        st.subheader("Añadir Movimiento")
        qty = st.number_input("Cantidad (€)", min_value=0.0, step=0.01)
        t_type = st.selectbox("Tipo", ["Gasto", "Ingreso"])
        res_c = supabase.table("user_categories").select("id, name").execute()
        options = {c['name']: c['id'] for c in res_c.data}
        if options:
            sel_cat = st.selectbox("Categoría", options.keys())
            if st.button("Guardar"):
                supabase.table("user_imputs").insert({"user_id": st.session_state.user.id, "quantity": qty, "type": t_type, "category_id": options[sel_cat]}).execute()
                st.success("¡Guardado!")
        else:
            st.warning("Crea una categoría primero.")

    # --- PESTAÑA: INFORMES (¡La Novedad!) ---
    with tab_informes:
        st.subheader("Estado de tus presupuestos")
        
        # 1. Obtener categorías y gastos
        cats = supabase.table("user_categories").select("id, name, budget").execute().data
        inputs = supabase.table("user_imputs").select("quantity, type, category_id").execute().data
        
        if cats and inputs:
            df_cats = pd.DataFrame(cats)
            df_inputs = pd.DataFrame(inputs)
            
            # 2. Calcular gasto total por categoría
            gastos_solo = df_inputs[df_inputs['type'] == 'Gasto']
            suma_gastos = gastos_solo.groupby('category_id')['quantity'].sum().reset_index()
            
            # 3. Unir datos para comparar
            reporte = pd.merge(df_cats, suma_gastos, left_on='id', right_on='category_id', how='left').fillna(0)
            
            # 4. Mostrar alertas
            for _, row in reporte.iterrows():
                progreso = row['quantity'] / row['budget'] if row['budget'] > 0 else 0
                col_a, col_b = st.columns([3, 1])
                
                with col_a:
                    st.write(f"**{row['name']}**")
                    # Barra de progreso visual
                    color = "green" if row['quantity'] <= row['budget'] else "red"
                    st.progress(min(progreso, 1.0))
                
                with col_b:
                    st.write(f"{row['quantity']}€ / {row['budget']}€")
                    if row['quantity'] > row['budget']:
                        st.caption("⚠️ ¡Límite superado!")
        else:
            st.info("Aún no hay suficientes datos para generar un informe.")

else:
    st.info("Inicia sesión para ver tus finanzas.")
