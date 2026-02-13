import streamlit as st
import pandas as pd
from database import init_db, login_user, register_user, recover_password, get_user_profile, get_transactions, get_categories
from styles import get_custom_css

# Importaciones desde la nueva carpeta views
from views.dashboard import render_main_dashboard
from views.transactions import render_dashboard
from views.categories import render_categories
from views.profile import render_profile
from views.import_data import render_import

# 1. Configuración de página
st.set_page_config(page_title="Mi Finanzas", page_icon="💰", layout="wide")

# 2. Inicializar base de datos
init_db()

# 3. Cargar CSS
st.markdown(get_custom_css(), unsafe_allow_html=True)

# 4. Gestión de Sesión
if 'user' not in st.session_state:
    st.session_state.user = None

def main():
    if st.session_state.user:
        # --- APP PRINCIPAL (USUARIO LOGUEADO) ---
        user_profile = st.session_state.user
        user_id = user_profile['id']
        
        # Cargar datos comunes para las vistas
        df_all = get_transactions(user_id)
        current_cats = get_categories(user_id)
        
        # Sidebar con el Menú
        with st.sidebar:
            # Avatar (puedes añadir aquí el código del HTML del avatar que teníamos)
            st.title(f"Hola, {user_profile.get('name', 'Usuario')}")
            
            page = st.radio("Navegación", 
                            ["🏠 Resumen", "💸 Movimientos", "📂 Categorías", "📥 Importar", "⚙️ Perfil"], 
                            label_visibility="collapsed")
            
            st.divider()
            if st.button("Cerrar Sesión", use_container_width=True):
                st.session_state.user = None
                st.rerun()

        # --- LÓGICA DE ENRUTAMIENTO ---
        if page == "🏠 Resumen":
            render_main_dashboard(df_all, user_profile)
        elif page == "💸 Movimientos":
            render_dashboard(df_all, current_cats, user_id)
        elif page == "📂 Categorías":
            render_categories(current_cats)
        elif page == "📥 Importar":
            render_import(current_cats, user_id)
        elif page == "⚙️ Perfil":
            render_profile(user_id, user_profile)

    else:
        # --- PANTALLA DE LOGIN / REGISTRO ---
        # (Aquí debes mantener el bloque de st.tabs que tenías antes para el Login)
        st.title("💰 Mi Finanzas App")
        tab_login, tab_register = st.tabs(["Iniciar Sesión", "Registrarse"])
        
        with tab_login:
            with st.form("login_form"):
                email = st.text_input("Email")
                password = st.text_input("Contraseña", type="password")
                if st.form_submit_button("Entrar", use_container_width=True):
                    auth_user = login_user(email, password)
                    if auth_user:
                        profile = get_user_profile(auth_user.id)
                        st.session_state.user = profile
                        st.rerun()
                    else:
                        st.error("Credenciales incorrectas")

        with tab_register:
            # ... tu código de registro ...
            pass

if __name__ == "__main__":
    main()
