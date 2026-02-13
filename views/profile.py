import streamlit as st
import time
from database import upsert_profile, upload_avatar, change_password

def render_profile(user_id, p_data):
    st.title("⚙️ Mi Perfil")
    
    with st.container(border=True):
        st.subheader("👤 Datos Personales")
        c_ava, c_form = st.columns([1, 2])
        with c_ava:
            current_avatar = st.session_state.user.get('avatar_url')
            if current_avatar: st.image(current_avatar, width=150)
            else: st.markdown(f'<div style="width:150px;height:150px;background:{p_data.get("profile_color","#636EFA")};border-radius:50%;display:flex;align-items:center;justify-content:center;color:white;font-size:50px;">{p_data.get("name","U")[0].upper()}</div>', unsafe_allow_html=True)
            uploaded_file = st.file_uploader("Cambiar foto (Máx 5MB)", type=['png', 'jpg', 'jpeg'])
        
        with c_form:
            with st.form("perfil_form"):
                n_name, n_last = st.text_input("Nombre", value=p_data.get('name','')), st.text_input("Apellido", value=p_data.get('lastname',''))
                n_color = st.color_picker("Color de Perfil", value=p_data.get('profile_color','#636EFA'))
                n_social = st.toggle("Modo Social", value=p_data.get('social_active', False))
                if st.form_submit_button("Guardar Datos Personales"):
                    avatar_url = upload_avatar(uploaded_file, user_id) if uploaded_file else p_data.get('avatar_url')
                    new_data = {**p_data, "name": n_name, "lastname": n_last, "profile_color": n_color, "social_active": n_social, "avatar_url": avatar_url}
                    if upsert_profile(new_data):
                        st.session_state.user.update(new_data)
                        st.rerun()

    with st.container(border=True):
        st.subheader("💰 Configuración Financiera")
        with st.form("finance_form"):
            n_balance = st.number_input("Saldo Inicial (€)", value=float(p_data.get('initial_balance', 0.0)))
            n_salary = st.number_input("Nómina Base (€)", value=float(p_data.get('base_salary', 0.0)))
            n_pagas = st.slider("Pagas al año", 12, 16, int(p_data.get('payments_per_year', 12)))
            if st.form_submit_button("💾 Guardar"):
                new_fin = {**p_data, "initial_balance": n_balance, "base_salary": n_salary, "payments_per_year": n_pagas}
                if upsert_profile(new_fin):
                    st.session_state.user.update(new_fin)
                    st.rerun()
