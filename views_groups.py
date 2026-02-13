# views_groups.py
import streamlit as st
import time
# IMPORTANTE: Añadimos todas las funciones necesarias de database_groups
from database_groups import (create_group, get_user_groups, delete_group, 
                             get_my_invitations, send_invitation, respond_invitation)

# Reutilizamos la importación de iconos
BOOTSTRAP_ICONS_LINK = '<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.10.5/font/bootstrap-icons.css">'

def render_header(icon_name, text):
    st.markdown(f'{BOOTSTRAP_ICONS_LINK}<h1><i class="bi bi-{icon_name}"></i> {text}</h1>', unsafe_allow_html=True)

def render_subheader(icon_name, text):
    st.markdown(f'{BOOTSTRAP_ICONS_LINK}<h3><i class="bi bi-{icon_name}"></i> {text}</h3>', unsafe_allow_html=True)

# Modal de seguridad para borrar un grupo
@st.dialog("Eliminar Grupo")
def confirmar_borrar_grupo(group_id):
    st.markdown(f'{BOOTSTRAP_ICONS_LINK}<p style="font-size:16px;"><i class="bi bi-question-circle" style="color:#636EFA;"></i> ¿Estás seguro de que quieres eliminar este grupo?</p>', unsafe_allow_html=True)
    
    st.markdown("""
        <div style="color: #842029; background-color: #f8d7da; border: 1px solid #f5c2c7; padding: 10px; border-radius: 5px; margin-bottom: 20px;">
            <i class="bi bi-exclamation-triangle-fill"></i> Se borrará el grupo para TODOS los miembros. Esta acción no se puede deshacer.
        </div>
    """, unsafe_allow_html=True)
    
    col_no, col_si = st.columns(2)
    with col_si:
        if st.button(":material/delete: Sí, Eliminar", type="primary", use_container_width=True):
            delete_group(group_id)
            st.rerun()
    with col_no:
        if st.button("Cancelar", use_container_width=True):
            st.rerun()

@st.dialog("Invitar Usuario")
def invitar_usuario_dialog(group_id, group_name):
    st.write(f"Enviar invitación para **{group_name}**")
    email_to_invite = st.text_input("Email del amigo")
    if st.button("Enviar Invitación", use_container_width=True):
        if email_to_invite:
            ok, msg = send_invitation(group_id, email_to_invite)
            if ok: 
                st.success("¡Invitación enviada!")
                time.sleep(1)
                st.rerun()
            else: st.error(msg)
        else:
            st.warning("Introduce un email válido.")

def render_groups(user_id, user_email):
    render_header("people", "Grupos Compartidos")
    st.caption("Gestiona gastos compartidos con amigos, pareja o compañeros de piso.")
    
    # Sistema de pestañas para Mis Grupos e Invitaciones
    tab_mis_grupos, tab_invitaciones = st.tabs(["📂 Mis Grupos", "✉️ Invitaciones"])

    with tab_mis_grupos:
        # --- 1. CREAR NUEVO GRUPO ---
        with st.expander("➕ Crear Nuevo Grupo", expanded=False):
            with st.form("new_group_v2", clear_on_submit=True):
                col1, col2 = st.columns([3, 1])
                g_name = col1.text_input("Nombre del grupo")
                g_emoji = col2.text_input("Emoji", value="👥")
                g_color = st.color_picker("Color de identificación", value="#636EFA")
                
                if st.form_submit_button("Crear Grupo", use_container_width=True):
                    if g_name.strip():
                        ok, msg = create_group(g_name, g_emoji, g_color, user_id)
                        if ok: 
                            st.success("Grupo creado!")
                            st.rerun()
                        else: st.error(msg)
                    else:
                        st.error("El nombre es obligatorio.")

        st.divider()

        # --- 2. LISTADO DE MIS GRUPOS ---
        render_subheader("collection", "Mis Grupos")
        my_groups = get_user_groups(user_id)
        
        if not my_groups:
            st.info("No perteneces a ningún grupo todavía. ¡Crea uno arriba para empezar!")
        else:
            cols = st.columns(3)
            for index, group in enumerate(my_groups):
                col = cols[index % 3]
                with col:
                    # Aplicamos un estilo sutil usando el color del grupo
                    with st.container(border=True):
                        st.markdown(f"### {group.get('emoji', '👥')} {group['name']}")
                        
                        es_admin = group['created_by'] == user_id
                        rol_badge = "👑 Admin" if es_admin else "👤 Miembro"
                        st.caption(f"Rol: {rol_badge}")
                        
                        # Botonera de la tarjeta
                        if st.button("Abrir Grupo ➡️", key=f"open_{group['id']}", use_container_width=True, type="primary"):
                            st.session_state.current_group_id = group['id']
                            st.session_state.current_group_name = group['name']
                            st.toast(f"Abriendo {group['name']}...")

                        c_inv, c_del = st.columns([1, 1])
                        with c_inv:
                            if st.button("Invitar 👤", key=f"inv_btn_{group['id']}", use_container_width=True):
                                invitar_usuario_dialog(group['id'], group['name'])
                        with c_del:
                            if es_admin:
                                if st.button(":material/delete:", key=f"del_btn_{group['id']}", type="secondary", use_container_width=True):
                                    confirmar_borrar_grupo(group['id'])

    with tab_invitaciones:
        render_subheader("envelope", "Invitaciones Pendientes")
        invites = get_my_invitations(user_email)
        
        if not invites:
            st.write("No tienes invitaciones pendientes.")
        else:
            for inv in invites:
                # El JOIN de Supabase trae los datos del grupo dentro de una sub-llave
                g_info = inv.get('groups', {})
                with st.container(border=True):
                    st.markdown(f"**{g_info.get('emoji', '👥')} {g_info.get('name', 'Grupo')}**")
                    st.write(f"Te han invitado a este grupo.")
                    
                    ca, cr = st.columns(2)
                    if ca.button("Aceptar ✅", key=f"acc_{inv['id']}", use_container_width=True):
                        if respond_invitation(inv['id'], inv['group_id'], user_id, True):
                            st.success("¡Bienvenido al grupo!")
                            st.rerun()
                    if cr.button("Rechazar ❌", key=f"rej_{inv['id']}", use_container_width=True):
                        if respond_invitation(inv['id'], inv['group_id'], user_id, False):
                            st.info("Invitación rechazada.")
                            st.rerun()
