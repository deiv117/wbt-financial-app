import streamlit as st
import pandas as pd
import random
import time
from streamlit_option_menu import option_menu 

# IMPORTANTE: He añadido 'change_password' y 'supabase' a las importaciones
from database import (init_db, login_user, register_user, recover_password, 
                      get_user_profile, get_transactions, get_categories, 
                      change_password, supabase)
from styles import get_custom_css

# Importaciones unificadas
from views import render_dashboard, render_categories, render_profile, render_import, render_main_dashboard
from views_groups import render_groups

# 1. Configuración de página
st.set_page_config(page_title="Mi Finanzas", page_icon="💰", layout="wide")
init_db()
st.markdown(get_custom_css(), unsafe_allow_html=True)

# CSS Extra para ocultar el padding superior excesivo de Streamlit y ocultar menús por defecto
st.markdown("""
    <style>
        /* 1. Ajuste padding general */
        .block-container {
            padding-top: 2rem !important; 
        } 
        
        /* 2. Ocultar la parte DERECHA del header (Deploy, Github, 3 puntos) */
        [data-testid="stToolbar"], 
        [data-testid="stHeaderActionElements"], 
        .stDeployButton, 
        #MainMenu {
            display: none !important;
            visibility: hidden !important;
        }
        
        /* 3. Ocultar FOOTER */
        footer {
            display: none !important;
        }

        /* 🛟 4. ESCUDO PROTECTOR SUPREMO: Botón del menú lateral SIEMPRE visible */
        [data-testid="collapsedControl"],
        [data-testid="stSidebarCollapsedControl"] {
            display: flex !important;
            visibility: visible !important;
            opacity: 1 !important;
            z-index: 999999 !important;
        }
        
        /* Asegurar que el header en sí no bloquee el botón */
        [data-testid="stHeader"] {
            background-color: transparent !important;
            z-index: 999998 !important;
        }
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
            # Canjeamos el código del correo por una sesión activa
            res = supabase.auth.exchange_code_for_session({"auth_code": code})
            if res and res.user:
                st.session_state.user = get_user_profile(res.user.id)
                # Activamos la bandera para mostrar la ventana de cambio de contraseña
                st.session_state.show_recovery_dialog = True 
                st.query_params.clear() # Limpiamos la URL
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
        
        # --- NUEVO POP-UP PARA CAMBIAR CONTRASEÑA DIRECTAMENTE ---
        if st.session_state.get("show_recovery_dialog"):
            @st.dialog("🔐 Recuperación de Contraseña")
            def recovery_dialog():
                st.success("¡Enlace verificado! Ya estás dentro de tu cuenta.")
                st.write("Si solicitaste **recuperar tu contraseña**, escribe la nueva a continuación:")
                
                # Formulario directo para cambiar la clave
                with st.form("reset_pass_form"):
                    p1 = st.text_input("Nueva Contraseña", type="password")
                    p2 = st.text_input("Confirmar Contraseña", type="password")
                    submit = st.form_submit_button("Actualizar Contraseña", type="primary", use_container_width=True)
                    
                    if submit:
                        if p1 == p2 and len(p1) >= 6:
                            ok, msg = change_password(p1)
                            if ok:
                                st.success("✅ ¡Contraseña actualizada con éxito!")
                                time.sleep(1.5)
                                st.session_state.show_recovery_dialog = False
                                st.rerun()
                            else:
                                st.error(f"Error: {msg}")
                        else:
                            st.error("Las contraseñas no coinciden o son muy cortas (mínimo 6 caracteres).")
                
                st.divider()
                st.write("¿No querías cambiar la contraseña y solo venías a confirmar tu correo?")
                if st.button("Solo venía a confirmar mi cuenta (Cerrar)", use_container_width=True):
                    st.session_state.show_recovery_dialog = False
                    st.rerun()
            
            recovery_dialog()
        
        # --- BARRA LATERAL ---
        from database_groups import get_invitations_count
                
        # Obtenemos el email (usando la lógica segura que pusimos ayer)
        session_user = st.session_state.supabase_client.auth.get_user()
        try:
            user_email = session_user.user.email
        except AttributeError:
            user_email = session_user.data.user.email if hasattr(session_user, 'data') else None
        
        # Contamos las invitaciones
        n_invites = get_invitations_count(user_email) if user_email else 0
                
        # Personalizamos la etiqueta del menú
        label_grupos = f"Grupos {'🔴' if n_invites > 0 else ''}"
       
        with st.sidebar:
            avatar_url = user_profile.get('avatar_url')
            p_color = user_profile.get('profile_color', '#636EFA')
            i_color = user_profile.get('icon_color', '#FFA500') # <-- SACAMOS EL COLOR DEL ICONO
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
                options=["Resumen", "Movimientos", "Categorías", label_grupos, "Importar", "Perfil"],
                icons=["house", "wallet2", "list-task", "people", "cloud-upload", "person-gear"],
                default_index=0,
                styles={
                    "container": {"padding": "0!important", "background-color": "transparent"},
                    "icon": {"color": i_color, "font-size": "18px"}, # <-- LO APLICAMOS AQUÍ
                    "nav-link": {"font-size": "16px", "text-align": "left", "margin": "0px", "--hover-color": "#eee"},
                    "nav-link-selected": {"background-color": p_color},
                }
            )
            
            st.divider()
            if st.button("Cerrar Sesión", use_container_width=True):
                supabase.auth.sign_out() 
                st.session_state.user = None
                st.rerun()

        # --- ENRUTAMIENTO ---
        if selected == "Resumen": render_main_dashboard(df_all, user_profile)
        elif selected == "Movimientos": render_dashboard(df_all, current_cats, user_id)
        elif selected == "Categorías": render_categories(current_cats)
        elif selected == label_grupos:  # <--- Usamos la variable, tenga bolita o no
            if user_email:
                render_groups(user_id, user_email)
            else:
                st.error("No se pudo recuperar tu email de sesión. Intenta cerrar sesión y volver a entrar.")
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
                            # 1. Buscamos el perfil
                            user_prof = get_user_profile(auth_user.id)
                            
                            # 2. Si el perfil existe, entramos
                            if user_prof:
                                st.session_state.user = user_prof
                                st.rerun()
                            # 3. Si no existe, damos el aviso para no volvernos locos
                            else:
                                st.error("⚠️ Credenciales correctas, pero tu Perfil no se generó bien en la base de datos. Por favor, crea una cuenta nueva.")
                        else: 
                            st.error("Credenciales incorrectas o cuenta sin confirmar.")
                
                with st.expander("¿Olvidaste tu contraseña?"):
                    st.write("Te enviaremos un enlace mágico para entrar y cambiarla.")
                    rec_email = st.text_input("Tu Email", key="rec")
                    if st.button("Recuperar Contraseña"):
                        ok, msg = recover_password(rec_email)
                        if ok: st.success("✅ " + msg)
                        else: st.error(msg)

            # --- NUEVO FORMULARIO DE REGISTRO CON CAMPOS OBLIGATORIOS ---
            with tab_register:
                with st.form("register_form"):
                    c_reg1, c_reg2 = st.columns(2)
                    reg_name = c_reg1.text_input("Nombre*")
                    reg_last = c_reg2.text_input("Apellido*")
                    
                    reg_email = st.text_input("Email*")
                    
                    c_pass1, c_pass2 = st.columns(2)
                    p1 = c_pass1.text_input("Contraseña*", type="password")
                    p2 = c_pass2.text_input("Confirmar Contraseña*", type="password")
                    
                    st.divider()
                    st.markdown("**🛡️ Verificación de Seguridad**")
                    n1, n2 = st.session_state.captcha_n1, st.session_state.captcha_n2
                    correct_answer = n1 + n2
                    
                    captcha_user_answer = st.number_input(f"¿Cuánto es {n1} + {n2}? (Anti-bots)", min_value=0, max_value=100, step=1)
                    
                    if st.form_submit_button("Crear Cuenta", use_container_width=True):
                        # LÓGICA DE CAMPOS OBLIGATORIOS
                        if not reg_name.strip() or not reg_last.strip() or not reg_email.strip() or not p1.strip() or not p2.strip():
                            st.error("⚠️ Todos los campos marcados con (*) son obligatorios.")
                        elif p1 != p2: 
                            st.error("⚠️ Las contraseñas no coinciden.")
                        elif len(p1) < 6:
                            st.error("⚠️ La contraseña debe tener al menos 6 caracteres.")
                        elif captcha_user_answer != correct_answer:
                            st.error("❌ Verificación de seguridad fallida. La suma es incorrecta.")
                            reset_captcha()
                            time.sleep(1)
                            st.rerun()
                        else:
                            # Pasamos el apellido (reg_last) a tu función de registro
                            ok, msg = register_user(reg_email, p1, reg_name, reg_last)
                            if ok: 
                                st.success("✅ **¡Cuenta creada!** Por favor, revisa tu correo electrónico y haz clic en el enlace para confirmar tu cuenta.")
                                reset_captcha()
                            else: 
                                st.error(f"Error: {msg}")
                                reset_captcha()

if __name__ == "__main__":
    main()
