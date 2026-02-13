# views_groups.py
import streamlit as st
from database_groups import create_group, get_user_groups, delete_group

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

def render_groups(user_id, user_email):
    render_header("people", "Grupos Compartidos")
    
    # Sistema de pestañas para Invitaciones y Mis Grupos
    tab_mis_grupos, tab_invitaciones = st.tabs(["📂 Mis Grupos", "✉️ Invitaciones"])

    with tab_mis_grupos:
        # --- CREAR GRUPO ---
        with st.expander("➕ Crear Nuevo Grupo"):
            with st.form("new_group_v2"):
                col1, col2 = st.columns([3, 1])
                g_name = col1.text_input("Nombre del grupo")
                g_emoji = col2.text_input("Emoji", value="👥")
                g_color = st.color_picker("Color de identificación", value="#636EFA")
                
                if st.form_submit_button("Crear Grupo", use_container_width=True):
                    ok, msg = create_group(g_name, g_emoji, g_color, user_id)
                    if ok: st.rerun()
                    else: st.error(msg)

        # --- LISTADO DE GRUPOS ---
        my_groups = get_user_groups(user_id) # Esta función debe traer ahora emoji y color
        if not my_groups:
            st.info("No tienes grupos.")
        else:
            for g in my_groups:
                # Usamos el color del grupo para el borde o un pequeño indicador
                with st.container(border=True):
                    c1, c2, c3 = st.columns([0.5, 3, 2])
                    c1.markdown(f"### {g.get('emoji', '👥')}")
                    c2.markdown(f"**{g['name']}**")
                    
                    with c3:
                        # Botón para invitar (solo si eres admin, por ejemplo)
                        if st.button("Invitar 👤", key=f"inv_{g['id']}"):
                            invitar_usuario_dialog(g['id'], g['name'])
                        
                        if st.button("Abrir ➡️", key=f"open_{g['id']}", type="primary"):
                            st.session_state.current_group_id = g['id']
                            st.toast(f"Entrando en {g['name']}")

    with tab_invitaciones:
        invites = get_my_invitations(user_email)
        if not invites:
            st.write("No tienes invitaciones pendientes.")
        for inv in invites:
            with st.container(border=True):
                st.write(f"Has sido invitado al grupo: **{inv['groups']['emoji']} {inv['groups']['name']}**")
                ca, cr = st.columns(2)
                if ca.button("Aceptar ✅", key=f"acc_{inv['id']}"):
                    respond_invitation(inv['id'], inv['group_id'], user_id, True)
                    st.rerun()
                if cr.button("Rechazar ❌", key=f"rej_{inv['id']}"):
                    respond_invitation(inv['id'], inv['group_id'], user_id, False)
                    st.rerun()

@st.dialog("Invitar Usuario")
def invitar_usuario_dialog(group_id, group_name):
    st.write(f"Enviar invitación para **{group_name}**")
    email_to_invite = st.text_input("Email del amigo")
    if st.button("Enviar Invitación"):
        ok, msg = send_invitation(group_id, email_to_invite)
        if ok: 
            st.success("¡Invitación enviada!")
            time.sleep(1)
            st.rerun()
        else: st.error(msg)

    # --- 2. MIS GRUPOS (TARJETAS) ---
    render_subheader("collection", "Mis Grupos")
    
    my_groups = get_user_groups(user_id)
    
    if not my_groups:
        st.info("No perteneces a ningún grupo todavía. ¡Crea uno arriba para empezar!")
    else:
        # Mostramos los grupos en una cuadrícula (grid de 3 columnas)
        cols = st.columns(3)
        for index, group in enumerate(my_groups):
            col = cols[index % 3]
            with col:
                with st.container(border=True):
                    st.markdown(f"#### {group['name']}")
                    
                    # Identificamos si el usuario es el Administrador (el que lo creó)
                    es_admin = group['created_by'] == user_id
                    rol_badge = "👑 Admin" if es_admin else "👤 Miembro"
                    st.caption(f"Rol: {rol_badge}")
                    
                    st.write("") # Espaciador
                    
                    # Botonera
                    c1, c2 = st.columns([3, 1])
                    with c1:
                        if st.button("Abrir Grupo ➡️", key=f"open_{group['id']}", use_container_width=True):
                            # Más adelante usaremos esto para navegar dentro del grupo
                            st.session_state.current_group_id = group['id']
                            st.session_state.current_group_name = group['name']
                            st.toast(f"Abriendo {group['name']}... (Próximamente)")
                    with c2:
                        if es_admin:
                            if st.button(":material/delete:", key=f"del_{group['id']}", type="primary", use_container_width=True):
                                confirmar_borrar_grupo(group['id'])
