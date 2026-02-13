import streamlit as st
import pandas as pd
from database import init_db, login_user, register_user, recover_password, get_user_profile, get_transactions, get_categories
from styles import get_custom_css

# Importaciones desde la nueva estructura de carpetas
from views.dashboard import render_main_dashboard
from views.transactions import render_dashboard
from views.categories import render_categories
from views.profile import render_profile
from views.import_data import render_import

# 1. Configuración de página
st.set_page_config(page_title="Mi Finanzas", page_icon="💰", layout="wide")

# 2. Inicializar base de datos
init_db()

# 3. Cargar CSS Global desde styles.py
st.markdown(get_custom_css(), unsafe_allow_html=True)

# CSS Adicional para el Login (ajustes finos)
st.markdown("""
    <style>
    .stTextInput input {
        background-color: rgba(255, 255, 255, 0.05) !important;
        color: inherit !important;
        border: 1px solid rgba(128, 128, 128, 0.2) !important;
    }
    </style>
""", unsafe_allow_html=True)

# 4. Gestión de Sesión
if 'user' not in st.session_state:
    st.session_state.user = None

def main():
    if st.session_state.user:
        # --- APP PRINCIPAL (USUARIO AUTENTICADO) ---
        user_profile = st.session_state.user
        user_id = user_profile['id']
        
        # Cargar datos comunes necesarios para todas las vistas
        df_all = get_transactions(user_id)
        current_cats = get_categories(user_id)
        
        # --- BARRA LATERAL (SIDEBAR) ---
        with st.sidebar:
            # Recuperamos datos para el avatar
            avatar_url = user_profile.get('avatar_url')
            p_color = user_profile.get('profile_color', '#636EFA')
            name = user_profile.get('name', 'Usuario')
            
            # HTML para el Avatar Circular Centrado
            if avatar_url:
                avatar_html = f'<img src="{avatar_url}" style="width: 120px; height: 120px; border-radius: 50%; object-fit: cover; border: 4px solid {p_color}; margin-bottom: 15px; display: block; margin-left: auto; margin-right: auto;">'
            else:
                initial = name[0].upper() if name else 'U'
                avatar_html = f'<div style="width: 120px; height: 120px; background-color: {p_color}; border-radius: 50%; display: flex; align-items: center; justify-content: center; color: white; font-size: 50px; font-weight: bold; margin-bottom: 15px; margin-left: auto; margin-right: auto;">{initial}</div>'
            
            # Renderizar Cabecera de Usuario
            st.markdown(f"""
                <div style="text-align: center; padding-top: 20px; padding-bottom: 10px;">
                    {avatar_html}
                    <h2 style="margin: 0; font-size: 24px;">Hola, {name}</h2>
                </div>
            """, unsafe_allow_html=True)
            
            st.divider()
            
            # Selector de Navegación
            page = st.radio(
                "Navegación", 
                ["🏠 Resumen", "💸 Movimientos", "📂 Categorías", "📥 Importar", "⚙️ Perfil"], 
                label_visibility="collapsed"
            )
            
            st.divider()
            
            # Botón de Cerrar Sesión
            if st.button("Cerrar Sesión", use_container_width=True):
                st.session_state.user = None
                st.rerun()

        # --- ENRUTAMIENTO DE PÁGINAS ---
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
        # --- PANTALLA DE ACCESO (LOGIN / REGISTRO) ---
        c1, c2, c3 = st.columns([1, 2, 1])
        with c2:
            st.title("💰 Mi Finanzas App")
            st.markdown("---")
            
            tab_login, tab_register = st.tabs(["Iniciar Sesión", "Registrarse"])
            
            # Formulario de Login
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
                
                # Olvido de contraseña
                with st.expander("¿Olvidaste tu contraseña?", expanded=False):
                    rec_email = st.text_input("Tu Email de registro", key="rec_email")
                    if st.button("Enviar correo de recuperación"):
                        if rec_email:
                            success, msg = recover_password(rec_email)
                            if success: st.success(msg)
                            else: st.error(msg)

            # Formulario de Registro
            with tab_register:
                with st.form("register_form"):
                    reg_name = st.text_input("Nombre")
                    reg_email = st.text_input("Email")
                    reg_pass = st.text_input("Contraseña", type="password")
                    reg_pass_conf = st.text_input("Confirmar Contraseña", type="password")
                    
                    if st.form_submit_button("Crear Cuenta", use_container_width=True):
                        if reg_pass != reg_pass_conf:
                            st.error("Las contraseñas no coinciden.")
                        else:
                            success, msg = register_user(reg_email, reg_pass, reg_name, "")
                            if success: st.success("¡Cuenta creada! Ya puedes iniciar sesión.")
                            else: st.error(f"Error: {msg}")

if __name__ == "__main__":
    main()
