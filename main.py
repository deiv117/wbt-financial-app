import streamlit as st
from supabase import create_client, Client

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
    email = st.text_input("Correo electrónico")
    password = st.text_input("Contraseña", type="password")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Entrar"):
            try:
                res = supabase.auth.sign_in_with_password({"email": email, "password": password})
                st.session_state.user = res.user
                st.success("¡Bienvenido!")
                st.rerun()
            except Exception as e:
                st.error(f"Error: {e}")
                
    with col2:
        if st.button("Registrarse"):
            try:
                # Nota: El registro crea el usuario en la tabla auth.users de Supabase
                res = supabase.auth.sign_up({"email": email, "password": password})
                st.info("¡Revisa tu email o intenta loguearte si quitaste la confirmación!")
            except Exception as e:
                st.error(f"Error: {e}")

# --- SI EL USUARIO ESTÁ LOGUEADO ---
if st.session_state.user:
    st.write(f"Sesión iniciada como: **{st.session_state.user.email}**")
    
    if st.button("Cerrar Sesión"):
        supabase.auth.sign_out()
        st.session_state.user = None
        st.rerun()

    st.divider()

    # --- SECCIÓN: AÑADIR GASTO/INGRESO ---
    st.subheader("Añadir nuevo registro")
    
    quantity = st.number_input("Cantidad (€)", min_value=0.0, step=0.01)
    type_choice = st.selectbox("Tipo", ["Gasto", "Ingreso"])
    
    # 2. Intentar cargar las categorías del usuario de la tabla 'user_categories'
    try:
        categories_data = supabase.table("user_categories").select("id, name").execute()
        categories = categories_data.data
    except:
        categories = []

    if categories:
        # Creamos un diccionario para mostrar el nombre pero guardar el ID
        cat_options = {c['name']: c['id'] for c in categories}
        selected_cat_name = st.selectbox("Categoría", options=list(cat_options.keys()))
        selected_cat_id = cat_options[selected_cat_name]
    else:
        st.info("Aún no tienes categorías creadas.")
        selected_cat_id = None

    if st.button("Guardar Registro"):
        if selected_cat_id or not categories: # Permitir guardar aunque no haya categorías por ahora
            new_input = {
                "user_id": st.session_state.user.id,
                "quantity": quantity,
                "type": type_choice,
                "category_id": selected_cat_id
                # El campo 'date' se suele llenar solo si en Supabase pusiste 'now()'
            }
            try:
                supabase.table("user_imputs").insert(new_input).execute()
                st.success(f"¡{type_choice} de {quantity}€ guardado correctamente!")
            except Exception as e:
                st.error(f"Error al guardar: {e}")
        else:
            st.warning("Por favor, selecciona una categoría.")

else:
    st.warning("Por favor, inicia sesión para gestionar tus finanzas.")
