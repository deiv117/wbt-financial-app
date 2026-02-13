import streamlit as st
import pandas as pd
from database import init_db, get_user, get_transactions, get_categories, create_user
from styles import get_custom_css
from views import render_dashboard, render_categories, render_profile, render_import

# Configuración de página (SIEMPRE LO PRIMERO)
st.set_page_config(page_title="Mi Finanzas", page_icon="💰", layout="wide")

# Inicializar DB
init_db()

# Cargar CSS Global
st.markdown(get_custom_css(), unsafe_allow_html=True)

# CSS Específico para el Login (Parche para móvil y modo oscuro)
st.markdown("""
    <style>
    /* Quitar fondo blanco en inputs para modo oscuro/móvil */
    .stTextInput input {
        background-color: rgba(255, 255, 255, 0.05) !important;
        color: inherit !important;
        border: 1px solid rgba(128, 128, 128, 0.2) !important;
    }
    /* Centrar el login verticalmente */
    .login-container {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        margin-top: 50px;
        padding: 2rem;
        border-radius: 10px;
        background-color: rgba(255, 255, 255, 0.02);
        border: 1px solid rgba(128, 128, 128, 0.1);
    }
    </style>
""", unsafe_allow_html=True)

# Gestión de Sesión
if 'user' not in st.session_state:
    st.session_state.user = None

def main():
    if st.session_state.user:
        # --- APP PRINCIPAL (SI ESTÁ LOGUEADO) ---
        user = st.session_state.user
        
        # Sidebar
        with st.sidebar:
            st.markdown(f"""
                <div class="sidebar-user-container">
                    <div class="avatar-circle" style="background-color: {user.get('profile_color', '#636EFA')}">
                        {user['name'][0].upper() if user.get('name') else 'U'}
                    </div>
                    <h3>Hola, {user.get('name', 'Usuario')}</h3>
                </div>
            """, unsafe_allow_html=True)
            
            page = st.radio("Navegación", ["📊 Dashboard", "📂 Categorías", "📥 Importar", "⚙️ Perfil"], label_visibility="collapsed")
            
            st.divider()
            if st.button("Cerrar Sesión"):
                st.session_state.user = None
                st.rerun()

        # Datos
        df_all = get_transactions(user['id'])
        current_cats = get_categories(user['id'])

        # Renderizado de Vistas
        if page == "📊 Dashboard":
            render_dashboard(df_all, current_cats, user['id'])
        elif page == "📂 Categorías":
            render_categories(current_cats)
        elif page == "📥 Importar":
            render_import(current_cats, user['id'])
        elif page == "⚙️ Perfil":
            render_profile(user['id'], user)

    else:
        # --- PANTALLA DE LOGIN / REGISTRO ---
        c1, c2, c3 = st.columns([1, 2, 1])
        with c2:
            st.title("💰 Mi Finanzas App")
            st.markdown("---")
            
            # Selector Login vs Registro
            tab_login, tab_register = st.tabs(["Iniciar Sesión", "Registrarse"])
            
            # --- LOGIN ---
            with tab_login:
                with st.form("login_form"):
                    email = st.text_input("Usuario / Email")
                    password = st.text_input("Contraseña", type="password")
                    
                    # Botón de submit del formulario (SOLUCIONA EL DOBLE CLIC)
                    submitted = st.form_submit_button("Entrar", use_container_width=True)
                    
                    if submitted:
                        user = get_user(email) # Asumimos que get_user busca por email/nombre
                        # AQUÍ FALTA TU LÓGICA DE HASH DE CONTRASEÑA REAL
                        # Por ahora es simple para que funcione
                        if user and user['password'] == password: 
                            st.session_state.user = user
                            st.rerun()
                        else:
                            st.error("Usuario o contraseña incorrectos")

            # --- REGISTRO (Base preparada) ---
            with tab_register:
                with st.form("register_form"):
                    new_user = st.text_input("Nuevo Usuario")
                    new_email = st.text_input("Email")
                    new_pass = st.text_input("Contraseña", type="password")
                    new_pass_confirm = st.text_input("Confirmar Contraseña", type="password")
                    
                    reg_submitted = st.form_submit_button("Crear Cuenta", use_container_width=True)
                    
                    if reg_submitted:
                        if new_pass != new_pass_confirm:
                            st.error("Las contraseñas no coinciden")
                        elif not new_user or not new_email:
                            st.error("Rellena todos los campos")
                        else:
                            # Aquí llamaríamos a create_user(new_user, new_pass, new_email)
                            # create_user debe existir en database.py
                            st.success("¡Cuenta creada! Ahora puedes iniciar sesión.")

if __name__ == "__main__":
    main()
