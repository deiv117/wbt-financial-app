# views_groups.py
import streamlit as st
import time
from streamlit_option_menu import option_menu
# IMPORTANTE: Añadimos TODAS las funciones necesarias de database_groups sin abreviar
from database_groups import (
    create_group, get_user_groups, delete_group, 
    get_my_invitations, send_invitation, respond_invitation,
    get_group_members, get_group_info, remove_group_member, update_group_setting
)

# Reutilizamos la importación de iconos para los encabezados principales
BOOTSTRAP_ICONS_LINK = '<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.10.5/font/bootstrap-icons.css">'

def render_header(icon_name, text):
    st.markdown(f'{BOOTSTRAP_ICONS_LINK}<h1><i class="bi bi-{icon_name}"></i> {text}</h1>', unsafe_allow_html=True)

def render_subheader(icon_name, text):
    st.markdown(f'{BOOTSTRAP_ICONS_LINK}<h3><i class="bi bi-{icon_name}"></i> {text}</h3>', unsafe_allow_html=True)

# --- CALLBACKS DE NAVEGACIÓN ---
def abrir_grupo_callback(g_id, g_name):
    """Guarda los datos del grupo antes de que la página recargue"""
    st.session_state.current_group_id = g_id
    st.session_state.current_group_name = g_name

def cerrar_grupo_callback():
    """Limpia los datos para volver al menú principal"""
    st.session_state.current_group_id = None
    st.session_state.current_group_name = None

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


# --- VISTA INTERIOR DEL GRUPO ---
def render_single_group(group_id, group_name, user_id):
    """Esta es la pantalla interior cuando entras a un grupo"""
    
    st.button(":material/arrow_back: Volver a mis grupos", on_click=cerrar_grupo_callback)

    # Obtenemos la info del grupo para saber quién es el admin y los ajustes
    group_info = get_group_info(group_id)
    if not group_info:
        st.error("Error al cargar la información del grupo.")
        return

    es_admin = group_info['created_by'] == user_id
    allow_leaving = group_info.get('allow_leaving', True)

    render_header("collection", f"{group_name}")
    if es_admin:
        st.caption("👑 Eres el administrador de este grupo")
    st.divider()

    # Añadimos la pestaña de Ajustes
    selected_tab = option_menu(
        menu_title=None,
        options=["Resumen", "Gastos", "Miembros", "Ajustes"],
        icons=["graph-up", "receipt", "people", "gear"],
        orientation="horizontal",
        default_index=0,
        styles={
            "container": {"padding": "0!important", "background-color": "transparent"},
            "icon": {"color": "orange", "font-size": "18px"}, 
            "nav-link": {"font-size": "16px", "text-align": "center", "margin": "0px", "--hover-color": "#eee"},
            "nav-link-selected": {"background-color": "#636EFA"},
        }
    )

    if selected_tab == "Resumen":
        st.write("Aquí pondremos la calculadora de deudas (Quién le debe a quién).")

    elif selected_tab == "Gastos":
        st.write("Aquí pondremos la lista de tickets y un botón para añadir un gasto.")

    elif selected_tab == "Miembros":
        render_subheader("people", "Miembros del Grupo")
        miembros = get_group_members(group_id)
        
        if miembros:
            for m in miembros:
                prof = m.get('profiles') or {} # Protegemos por si falla el JOIN
                name = prof.get('name', 'Usuario Pendiente')
                color = prof.get('profile_color', '#636EFA')
                is_current_user = m['user_id'] == user_id
                
                with st.container(border=True):
                    c1, c2, c3 = st.columns([1, 3, 1])
                    with c1:
                        st.markdown(f"""
                            <div style="width: 40px; height: 40px; background-color: {color}; 
                                        border-radius: 50%; display: flex; align-items: center; 
                                        justify-content: center; color: white; font-weight: bold;">
                                {name[0].upper() if name else '?'}
                            </div>
                        """, unsafe_allow_html=True)
                    with c2:
                        st.markdown(f"**{name}** {prof.get('lastname', '')}")
                        if is_current_user:
                            st.caption("(Tú)")
                    with c3:
                        # Si eres admin y no eres tú mismo, puedes expulsar
                        if es_admin and not is_current_user:
                            if st.button(":material/person_remove:", key=f"kick_{m['user_id']}", help="Eliminar del grupo"):
                                if remove_group_member(group_id, m['user_id']):
                                    st.toast("Usuario eliminado")
                                    st.rerun()

    elif selected_tab == "Ajustes":
        render_subheader("gear", "Configuración del Grupo")
        
        with st.container(border=True):
            if es_admin:
                st.write("**Permisos de los miembros**")
                nuevo_allow = st.toggle("Permitir a los miembros abandonar el grupo por su cuenta", value=allow_leaving)
                
                if nuevo_allow != allow_leaving:
                    update_group_setting(group_id, "allow_leaving", nuevo_allow)
                    st.toast("Ajuste guardado")
                    time.sleep(0.5)
                    st.rerun()
            else:
                st.write("**Opciones de Miembro**")
                if allow_leaving:
                    st.info("Puedes abandonar este grupo en cualquier momento. El histórico de tus gastos se mantendrá.")
                    if st.button(":material/logout: Abandonar Grupo", type="primary"):
                        if remove_group_member(group_id, user_id):
                            cerrar_grupo_callback() # Limpiamos la sesión
                            st.rerun() # Recargamos para ir al menú principal
                else:
                    st.warning("🔒 El administrador ha bloqueado la opción de abandonar el grupo voluntariamente.")


# --- FUNCIÓN PRINCIPAL ENRUTADORA ---
def render_groups(user_id, user_email):
    
    # 1. SEMÁFORO: Si hay un grupo seleccionado, mostramos SU pantalla y detenemos la ejecución
    current_group_id = st.session_state.get('current_group_id')
    current_group_name = st.session_state.get('current_group_name', 'Grupo')

    if current_group_id:
        render_single_group(current_group_id, current_group_name, user_id)
        return

    # 2. SI NO HAY GRUPO: Mostramos la vista general (Lista e Invitaciones)
    render_header("people", "Grupos Compartidos")
    st.caption("Gestiona gastos compartidos con amigos, pareja o compañeros de piso.")
    
    # Menú horizontal principal
    main_tab = option_menu(
        menu_title=None,
        options=["Mis Grupos", "Invitaciones"],
        icons=["folder-fill", "envelope-paper"],
        orientation="horizontal",
        default_index=0,
        styles={
            "container": {"padding": "0!important", "background-color": "transparent"},
            "icon": {"color": "orange", "font-size": "18px"}, 
            "nav-link": {"font-size": "16px", "text-align": "center", "margin": "0px", "--hover-color": "#eee"},
            "nav-link-selected": {"background-color": "#636EFA"},
        }
    )

    if main_tab == "Mis Grupos":
        # --- CREAR NUEVO GRUPO ---
        with st.expander(":material/add_circle: Crear Nuevo Grupo", expanded=False):
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

        # --- LISTADO DE MIS GRUPOS ---
        render_subheader("collection", "Mis Grupos")
        my_groups = get_user_groups(user_id)
        
        if not my_groups:
            st.info("No perteneces a ningún grupo todavía. ¡Crea uno arriba para empezar!")
        else:
            cols = st.columns(3)
            for index, group in enumerate(my_groups):
                col = cols[index % 3]
                with col:
                    with st.container(border=True):
                        st.markdown(f"### {group.get('emoji', '👥')} {group['name']}")
                        
                        es_admin = group['created_by'] == user_id
                        rol_badge = "👑 Admin" if es_admin else "👤 Miembro"
                        st.caption(f"Rol: {rol_badge}")
                        
                        # Botón Abrir con Material Design
                        st.button(
                            ":material/arrow_forward: Abrir Grupo", 
                            key=f"open_{group['id']}", 
                            use_container_width=True, 
                            type="primary",
                            on_click=abrir_grupo_callback,
                            args=(group['id'], group['name'])
                        )

                        c_inv, c_del = st.columns([1, 1])
                        with c_inv:
                            if st.button(":material/person_add: Invitar", key=f"inv_btn_{group['id']}", use_container_width=True):
                                invitar_usuario_dialog(group['id'], group['name'])
                        with c_del:
                            if es_admin:
                                if st.button(":material/delete:", key=f"del_btn_{group['id']}", type="secondary", use_container_width=True):
                                    confirmar_borrar_grupo(group['id'])

    elif main_tab == "Invitaciones":
        render_subheader("envelope", "Invitaciones Pendientes")
        invites = get_my_invitations(user_email)
        
        if not invites:
            st.write("No tienes invitaciones pendientes.")
        else:
            for inv in invites:
                g_info = inv.get('groups', {})
                with st.container(border=True):
                    st.markdown(f"**{g_info.get('emoji', '👥')} {g_info.get('name', 'Grupo')}**")
                    st.write(f"Te han invitado a este grupo.")
                    
                    ca, cr = st.columns(2)
                    if ca.button(":material/check: Aceptar", key=f"acc_{inv['id']}", use_container_width=True):
                        if respond_invitation(inv['id'], inv['group_id'], user_id, True):
                            st.success("¡Bienvenido al grupo!")
                            st.rerun()
                    if cr.button(":material/close: Rechazar", key=f"rej_{inv['id']}", use_container_width=True):
                        if respond_invitation(inv['id'], inv['group_id'], user_id, False):
                            st.info("Invitación rechazada.")
                            st.rerun()
