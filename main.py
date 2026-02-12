import streamlit as st
import pandas as pd
from database import supabase, get_categories, get_all_inputs, get_profile
from views import render_dashboard, render_categories, render_profile, render_import
from styles import get_custom_css

st.set_page_config(page_title="Mis Gastos", page_icon="💰", layout="wide")
st.markdown(get_custom_css(), unsafe_allow_html=True)

# --- CONTROL DE SESIÓN ---
if 'user' not in st.session_state:
    try:
        res_session = supabase.auth.get_session()
        st.session_state.user = res_session.user if res_session and res_session.user else None
    except: st.session_state.user = None

if 'menu_actual' not in st.session_state:
    st.session_state.menu_actual = "📊 Panel"

# --- LOGIN ---
if not st.session_state.user:
    # 1. INYECTAMOS EL FONDO Y EL ESTILO DE LA TARJETA (Solo afecta a esta vista)
    st.markdown("""
        <style>
        /* Fondo de pantalla */
        .stApp {
            background-image: url("https://images.unsplash.com/photo-1554224155-6726b3ff858f?q=80&w=2022&auto=format&fit=crop");
            background-size: cover;
            background-position: center;
            background-attachment: fixed;
        }
        
        /* ESTILO MÁGICO: Transformar la COLUMNA CENTRAL en la tarjeta de login */
        /* Seleccionamos la segunda columna (nth-of-type(2)) y le damos estilo a su contenedor interno */
        div[data-testid="column"]:nth-of-type(2) > div {
            background-color: rgba(255, 255, 255, 0.95); /* Blanco casi sólido */
            backdrop-filter: blur(10px);
            padding: 40px;
            border-radius: 20px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.3);
            border: 1px solid rgba(255, 255, 255, 0.5);
        }

        /* Ocultar header y footer para limpieza visual */
        header {visibility: hidden;}
        footer {visibility: hidden;}
        
        /* Ajustar título dentro de la tarjeta */
        h1 {
            text-align: center;
            font-size: 2.5rem !important;
            margin-bottom: 1rem !important;
            color: #1f1f1f !important;
        }
        </style>
    """, unsafe_allow_html=True)

    # 2. ESTRUCTURA (Sin divs html manuales, usamos las columnas nativas)
    _, col_login, _ = st.columns([1, 1.5, 1]) # La columna del medio (1.5) recibirá el estilo CSS de arriba
    
    with col_login:
        st.write("###") # Un poco de espacio arriba
        st.title("💰 Finanzas App")
        
        email = st.text_input("Email", key="login_email")
        password = st.text_input("Contraseña", type="password", key="login_pass")
        
        st.write("#") # Espaciador
        
        if st.button("Entrar", use_container_width=True):
            try:
                res = supabase.auth.sign_in_with_password({"email": email, "password": password})
                if res.user:
                    st.session_state.user = res.user
                    st.rerun()
            except: 
                st.error("Credenciales incorrectas.")

else:
    # --- APP PRINCIPAL ---
    # Limpiamos el fondo para que no interfiera con el panel
    st.markdown("<style>.stApp { background-image: none !important; }</style>", unsafe_allow_html=True)
    
    # Sidebar
    p_data = get_profile(st.session_state.user.id)
    with st.sidebar:
        nombre, apellido = p_data.get('name', ''), p_data.get('lastname', '')
        iniciales = ((nombre[0] if nombre else "") + (apellido[0] if apellido else "")).upper() or st.session_state.user.email[0].upper()
        
        st.markdown('<div class="sidebar-user-container">', unsafe_allow_html=True)
        if p_data.get('avatar_url'): 
            st.markdown(f'<img src="{p_data["avatar_url"]}" class="avatar-circle">', unsafe_allow_html=True)
        else: 
            st.markdown(f'<div class="avatar-circle" style="background-color: {p_data.get("profile_color","#636EFA")};">{iniciales}</div>', unsafe_allow_html=True)
        
        st.markdown(f"**{nombre} {apellido}**")
        if st.button("Cerrar Sesión"):
            supabase.auth.sign_out(); st.session_state.user = None; st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
        st.divider()
        if st.button("📊 Panel de Control"): st.session_state.menu_actual = "📊 Panel"; st.rerun()
        if st.button("📂 Configurar Categorías"): st.session_state.menu_actual = "📂 Categorías"; st.rerun()
        if st.button("⚙️ Perfil"): st.session_state.menu_actual = "⚙️ Perfil"; st.rerun()
        if st.button("📥 Importar"): st.session_state.menu_actual = "📥 Importar"; st.rerun()

    # Carga de datos
    current_cats = get_categories()
    raw_data = get_all_inputs()
    df_all = pd.DataFrame(raw_data) if raw_data else pd.DataFrame()
    if not df_all.empty:
        df_all['date'] = pd.to_datetime(df_all['date'])
        df_all['cat_display'] = df_all['user_categories'].apply(lambda x: f"{x.get('emoji', '📁')} {x.get('name', 'S/C')}" if x else "📁 S/C")
        df_all['notes'] = df_all['notes'].fillna('')

    # Router
    if st.session_state.menu_actual == "📂 Categorías": render_categories(current_cats)
    elif st.session_state.menu_actual == "⚙️ Perfil": render_profile(st.session_state.user.id, p_data)
    elif st.session_state.menu_actual == "📥 Importar": render_import(current_cats, st.session_state.user.id)
    else: render_dashboard(df_all, current_cats, st.session_state.user.id)
