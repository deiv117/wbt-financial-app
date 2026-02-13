import streamlit as st
import pandas as pd
from database import init_db, login_user, register_user, recover_password, get_user_profile, get_transactions, get_categories
from styles import get_custom_css
from views import render_dashboard, render_categories, render_profile, render_import

# Configuración de página
st.set_page_config(page_title="Mi Finanzas", page_icon="💰", layout="wide")

# Inicializar conexión (en este caso es pasivo)
init_db()

# Cargar CSS
st.markdown(get_custom_css(), unsafe_allow_html=True)

# CSS Específico Login
st.markdown("""
    <style>
    .stTextInput input {
        background-color: rgba(255, 255, 255, 0.05) !important;
        color: inherit !important;
        border: 1px solid rgba(128, 128, 128, 0.2) !important;
    }
    </style>
""", unsafe_allow_html=True)

# Gestión de Sesión
if 'user' not in st.session_state:
    st.session_state.user = None

def main():
    if st.session_state.user:
        # --- APP PRINCIPAL ---
        # user es ahora un diccionario con los datos de 'profiles'
        user_profile = st.session_state.user
        user_id = user_profile['id'] # Esto es el UUID
        
        # Sidebar
        with st.sidebar:
            st.markdown(f"""
                <div class="sidebar-user-container">
                    <div class="avatar-circle" style="background-color: {user_profile.get('profile_color', '#636EFA')}">
                        {user_profile['name'][0].upper() if user_profile.get('name') else 'U'}
                    </div>
                    <h3>Hola, {user_profile.get('name', 'Usuario')}</h3>
                </div>
            """, unsafe_allow_html=True)
            
            page = st.radio("Navegación", ["📊 Dashboard", "📂 Categorías", "📥 Importar", "⚙️ Perfil"], label_visibility="collapsed")
            
            st.divider()
            if st.button("Cerrar Sesión"):
                st.session_state.user = None
                st.rerun()

        # Cargar datos
        df_all = get_transactions(user_id)
        current_cats = get_categories(user_id)

        # Renderizar vistas
        if page == "📊 Dashboard":
            render_dashboard(df_all, current_cats, user_id)
        elif page == "📂 Categorías":
            render_categories(current_cats)
        elif page == "📥 Importar":
            render_import(current_cats, user_id)
        elif page == "⚙️ Perfil":
            render_profile(user_id, user_profile)

    else:
        # --- PANTALLA DE LOGIN / REGISTRO ---
        c1, c2, c3 = st.columns([1, 2, 1])
        with c2:
            st.title("💰 Mi Finanzas App")
            st.markdown("---")
            
            tab_login, tab_register = st.tabs(["Iniciar Sesión", "Registrarse"])
            
            # --- LOGIN ---
            with tab_login:
                with st.form("login_form"):
                    email = st.text_input("Email")
                    password = st.text_input("Contraseña", type="password")
                    submitted = st.form_submit_button("Entrar", use_container_width=True)
                    
                    if submitted:
                        auth_user = login_user(email, password)
                        if auth_user:
                            profile = get_user_profile(auth_user.id)
                            if profile:
                                st.session_state.user = profile
                                st.rerun()
                            else:
                                st.error("Login correcto pero no se encontró perfil.")
                        else:
                            st.error("Email o contraseña incorrectos.")
                
                # --- SECCIÓN NUEVA: RECUPERAR CONTRASEÑA ---
                with st.expander("¿Olvidaste tu contraseña?", expanded=False):
                    st.caption("Introduce tu email y te enviaremos un enlace mágico.")
                    rec_email = st.text_input("Tu Email de registro", key="rec_email")
                    if st.button("Enviar correo de recuperación"):
                        if rec_email:
                            success, msg = recover_password(rec_email)
                            if success:
                                st.success(msg)
                            else:
                                st.error(msg)
                        else:
                            st.warning("Por favor, escribe tu email.")

            # --- REGISTRO ---
            with tab_register:
                with st.form("register_form"):
                    reg_name = st.text_input("Nombre")
                    reg_lastname = st.text_input("Apellido (Opcional)")
                    reg_email = st.text_input("Email")
                    reg_pass = st.text_input("Contraseña", type="password")
                    reg_pass_conf = st.text_input("Confirmar Contraseña", type="password")
                    
                    reg_submit = st.form_submit_button("Crear Cuenta", use_container_width=True)
                    
                    if reg_submit:
                        if reg_pass != reg_pass_conf:
                            st.error("Las contraseñas no coinciden.")
                        elif len(reg_pass) < 6:
                            st.error("La contraseña debe tener al menos 6 caracteres.")
                        elif not reg_name or not reg_email:
                            st.error("Nombre y Email son obligatorios.")
                        else:
                            success, msg = register_user(reg_email, reg_pass, reg_name, reg_lastname)
                            if success:
                                st.success("¡Cuenta creada! Revisa tu email para confirmar (si está activo) o inicia sesión.")
                            else:
                                st.error(f"Error al registrar: {msg}")

if __name__ == "__main__":
    main()
