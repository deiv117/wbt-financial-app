import streamlit as st
import pandas as pd
import random
import time
from streamlit_option_menu import option_menu 

# FÍJATE AQUÍ: He añadido 'supabase' a las importaciones para poder leer el código mágico
from database import init_db, login_user, register_user, recover_password, get_user_profile, get_transactions, get_categories, supabase
from styles import get_custom_css

# Importaciones unificadas
from views import render_dashboard, render_categories, render_profile, render_import, render_main_dashboard

# 1. Configuración de página
st.set_page_config(page_title="Mi Finanzas", page_icon="💰", layout="wide")
init_db()
st.markdown(get_custom_css(), unsafe_allow_html=True)

# CSS Extra para ocultar el padding superior excesivo de Streamlit y ajustar el menú
st.markdown("""
    <style>
        .st-emotion-cache-16txtl3 {padding-top: 1rem;} /* Ajuste padding sidebar */
        .block-container {padding-top: 2rem;} /* Ajuste padding main */
    </style>
""", unsafe_allow_html=True)

# --- INICIALIZACIÓN DE VARIABLES DE SESIÓN ---
if 'user' not in st.session_state:
    st.session_state.user = None

if 'captcha_n1' not in st.session_state:
    st.session_state.captcha_n1 = random.randint(1, 10)
if 'captcha_n2' not in st.session_state:
    st.session_state.captcha_n2 = random.randint(1, 10)

def reset_captcha():
    st.session_state.captcha_n1 = random.randint(1, 10)
    st.session_state.captcha_n2 = random.randint(1, 10)

def main():
    # --- LA MAGIA: INTERCEPTAR ENLACES DEL CORREO ---
    if "code" in st.query_params:
        code = st.query_params.get("code")
        try:
            # Si venimos de un enlace del correo, canjeamos el código por una sesión activa
            res = supabase.auth.exchange_code_for_session({"auth_code": code})
            if res and res.user:
                st.session_state.user = get_user_profile(res.user.id)
                st.session_state.just_verified = True # Activamos el pop-up de bienvenida
                st.query_params.clear() # Limpiamos la URL para que no moleste
                st.rerun()
        except Exception as e:
            st.error("❌ El enlace de verificación ha caducado o es inválido. Por favor, solicita uno nuevo.")
            st.query_params.clear()

    # --- FLUJO DE USUARIO LOGUEADO ---
    if st.session_state.user:
        user_profile = st.session_state.user
        user_id = user_profile['id']
        df_all = get_transactions(user_id)
        current_cats = get_categories(user_id)
        
        # POP-UP DE VERIFICACIÓN / CAMBIO DE CONTRASEÑA
        if st.session_state.get("just_verified"):
            @st.dialog("🎉 ¡Verificación Exitosa!")
            def welcome_dialog():
                st.success("Hemos comprobado tu identidad y ya has iniciado sesión automáticamente.")
                st.info("🔐 **¿Venías a recuperar tu contraseña?**\nComo ya estás dentro, dirígete al menú **Perfil > Seguridad** para establecer tu nueva contraseña de forma segura.")
                if st.button("¡Entendido!", use_container_width=True):
                    st.session_state.just_verified = False
                    st.rerun()
            
            welcome_dialog()
        
        # --- BARRA LATERAL ---
        with st.sidebar:
            avatar_url = user_profile.get('avatar_url')
            p_color = user_profile.get('profile_color', '#636EFA')
            name = user_profile.get('name', 'Usuario')
            
            if avatar_url:
                avatar_html = f'<img src="{avatar_url}" style="width: 60px; height: 60px; border-radius: 50%; object-fit: cover; border: 2px solid {p_color};">'
            else:
                initial = name[0].upper() if name else 'U'
                avatar_html = f'<div style="width: 60px; height: 60px; background-color: {p_color}; border-radius: 50%; display: flex; align-items: center; justify-content: center; color: white; font-size: 24px; font-weight: bold;">{initial}</div>'
            
            st.markdown(f"""
                <div style="display: flex; align-items: center; gap: 15px; margin-bottom: 20px; padding: 10px; background-color: rgba(255,255,255,0.05); border-radius: 10px;">
                    {avatar_html}
                    <div style="font-weight: bold; font-size: 16px;">{name}</div>
                </div>
            """, unsafe_allow_html=True)

            selected = option_menu(
                menu_title=None,
                options=["Resumen", "Movimientos", "Categorías", "Importar", "Perfil"],
                icons=["house", "wallet2", "list-task", "cloud-upload", "person-gear"],
                default_index=0,
                styles={
                    "container": {"padding": "0!important", "background-color": "transparent"},
                    "icon": {"color": "orange", "font-size": "18px"}, 
                    "nav-link": {"font-size": "16px", "text-align": "left", "margin": "0px", "--hover-color": "#eee"},
                    "nav-link-selected": {"background-color": "#636EFA"},
                }
            )
            
            st.divider()
            if st.button("Cerrar Sesión", use_container_width=True):
                supabase.auth.sign_out() # Cerramos sesión real en Supabase por seguridad
                st.session_state.user = None
                st.rerun()

        # --- ENRUTAMIENTO ---
        if selected == "Resumen": render_main_dashboard(df_all, user_profile)
        elif selected == "Movimientos": render_dashboard(df_all, current_cats, user_id)
        elif selected == "Categorías": render_categories(current_cats)
        elif selected == "Importar": render_import(current_cats, user_id)
        elif selected == "Perfil": render_profile(user_id, user_profile)

    # --- FLUJO DE USUARIO NO LOGUEADO ---
    else:
        c1, c2, c3 = st.columns([1, 2, 1])
        with c2:
            st.title("💰 Mi Finanzas App")
            st.markdown("---")
            tab_login, tab_register = st.tabs(["Iniciar Sesión", "Registrarse"])
            
            with tab_login:
                with st.form("login_form"):
                    email = st.text_input("Email")
                    password = st.text_input("Contraseña", type="password")
                    if st.form_submit_button("Entrar", use_container_width=True):
                        auth_user = login_user(email, password)
                        if auth_user:
                            st.session_state.user = get_user_profile(auth_user.id)
                            st.rerun()
                        else: st.error("Credenciales incorrectas o cuenta sin confirmar.")
                
                with st.expander("¿Olvidaste tu contraseña?"):
                    st.write("Te enviaremos un enlace mágico para entrar y cambiarla.")
                    rec_email = st.text_input("Tu Email", key="rec")
                    if st.button("Recuperar Contraseña"):
                        ok, msg = recover_password(rec_email)
                        if ok: st.success("✅ " + msg)
                        else: st.error(msg)

            with tab_register:
                with st.form("register_form"):
                    reg_name, reg_email = st.text_input("Nombre"), st.text_input("Email")
                    p1, p2 = st.text_input("Contraseña", type="password"), st.text_input("Confirmar", type="password")
                    
                    st.divider()
                    st.markdown("**🛡️ Verificación de Seguridad**")
                    n1, n2 = st.session_state.captcha_n1, st.session_state.captcha_n2
                    correct_answer = n1 + n2
                    
                    captcha_user_answer = st.number_input(f"¿Cuánto es {n1} + {n2}? (Anti-bots)", min_value=0, max_value=100, step=1)
                    
                    if st.form_submit_button("Crear Cuenta", use_container_width=True):
                        if p1 != p2: 
                            st.error("Las contraseñas no coinciden")
                        elif captcha_user_answer != correct_answer:
                            st.error("❌ Verificación de seguridad fallida. La suma es incorrecta.")
                            reset_captcha()
                            time.sleep(1)
                            st.rerun()
                        else:
                            ok, msg = register_user(reg_email, p1, reg_name, "")
                            if ok: 
                                # Mensaje actualizado para recordar lo del correo
                                st.success("✅ **¡Cuenta creada!** Por favor, revisa tu correo electrónico y haz clic en el enlace para confirmar tu cuenta.")
                                reset_captcha()
                            else: 
                                st.error(f"Error: {msg}")
                                reset_captcha()

if __name__ == "__main__":
    main()
