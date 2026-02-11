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
                except Exception as e:
                    st.error("Credenciales incorrectas")
        with col2:
            if st.button("Registrarse"):
                try:
                    res = supabase.auth.sign_up({"email": email, "password": password})
                    st.info("Revisa tu email si es necesario.")
                except Exception as e:
                    st.error(f"Error: {e}")
    else:
        st.write(f"Usuario: {st.session_state.user.email}")
        if st.button("Cerrar Sesión"):
            supabase.auth.sign_out()
            st.session_state.user = None
            st.rerun()

# --- CONTENIDO PARA USUARIOS LOGUEADOS ---
if st.session_state.user:
    # Creamos dos pestañas
    tab_gastos, tab_categorias = st.tabs(["💸 Registrar Movimiento", "⚙️ Gestionar Categorías"])

    # --- PESTAÑA: GESTIONAR CATEGORÍAS ---
    with tab_categorias:
        st.subheader("Tus Categorías")
        
        # Formulario para crear categoría
        with st.form("nueva_categoria"):
            new_cat_name = st.text_input("Nombre de la categoría (ej. Comida)")
            new_cat_budget = st.number_input("Presupuesto Mensual (€)", min_value=0.0, step=10.0)
            submit_cat = st.form_submit_button("Crear Categoría")
            
            if submit_cat and new_cat_name:
                try:
                    cat_data = {
                        "user_id": st.session_state.user.id,
                        "name": new_cat_name,
                        "budget": new_cat_budget
                    }
                    supabase.table("user_categories").insert(cat_data).execute()
                    st.success(f"Categoría '{new_cat_name}' creada!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error al crear categoría: {e}")

        # Mostrar categorías existentes
        st.divider()
        try:
            res_cats = supabase.table("user_categories").select("*").execute()
            if res_cats.data:
                for c in res_cats.data:
                    st.write(f"📂 **{c['name']}** - Presupuesto: {c['budget']}€")
            else:
                st.info("No tienes categorías todavía.")
        except:
            pass

    # --- PESTAÑA: REGISTRAR GASTOS ---
    with tab_gastos:
        st.subheader("Añadir Gasto o Ingreso")
        
        quantity = st.number_input("Cantidad (€)", min_value=0.0, step=0.01)
        type_choice = st.selectbox("Tipo", ["Gasto", "Ingreso"])
        
        # Cargar categorías para el selector
        try:
            cats_for_select = supabase.table("user_categories").select("id, name").execute()
            options = {c['name']: c['id'] for c in cats_for_select.data}
        except:
            options = {}

        if options:
            selected_name = st.selectbox("Selecciona Categoría", options.keys())
            
            if st.button("Guardar Registro"):
                try:
                    new_input = {
                        "user_id": st.session_state.user.id,
                        "quantity": quantity,
                        "type": type_choice,
                        "category_id": options[selected_name]
                    }
                    supabase.table("user_imputs").insert(new_input).execute()
                    st.success("¡Registro guardado!")
                except Exception as e:
                    st.error(f"Error: {e}")
        else:
            st.warning("Primero crea una categoría en la otra pestaña.")

else:
    st.info("Inicia sesión para empezar a gestionar tus ahorros.")
