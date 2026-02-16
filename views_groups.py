# views_groups.py
import streamlit as st
import time
import plotly.graph_objects as go
from streamlit_option_menu import option_menu
from database_groups import (
    create_group, get_user_groups, delete_group, 
    get_my_invitations, send_invitation, respond_invitation,
    get_group_members, get_group_info, get_group_expenses, remove_group_member, 
    update_group_setting, update_group_details,
    request_leave_group, resolve_leave_request
)

BOOTSTRAP_ICONS_LINK = '<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.10.5/font/bootstrap-icons.css">'

def render_header(icon_name, text):
    st.markdown(f'{BOOTSTRAP_ICONS_LINK}<h1><i class="bi bi-{icon_name}"></i> {text}</h1>', unsafe_allow_html=True)

def render_subheader(icon_name, text):
    st.markdown(f'{BOOTSTRAP_ICONS_LINK}<h3><i class="bi bi-{icon_name}"></i> {text}</h3>', unsafe_allow_html=True)

# --- CALLBACKS DE NAVEGACIÓN ---
def abrir_grupo_callback(g_id, g_name):
    st.session_state.current_group_id = g_id
    st.session_state.current_group_name = g_name

def cerrar_grupo_callback():
    st.session_state.current_group_id = None
    st.session_state.current_group_name = None

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
            if st.session_state.get('current_group_id') == group_id:
                cerrar_grupo_callback()
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
@st.dialog("💸 Confirmar Pago Recibido")
def saldar_deuda_dialog(group_id, creditor_id, debtor_id, debtor_name, amount):
    st.warning(f"¿Confirmas que **{debtor_name}** te ha pagado **{amount:.2f}€** fuera de la aplicación?")
    st.info("💡 Al confirmar, se le pondrá un 🔒 candado a los tickets compartidos y tu gasto personal se reducirá automáticamente para cuadrar tus cuentas.")
    
    if st.button("Sí, he recibido el dinero", type="primary", use_container_width=True):
        from database_groups import settle_debt_between_users
        import time
        ok, msg = settle_debt_between_users(group_id, creditor_id, debtor_id)
        if ok:
            st.toast(f"✅ {msg}")
            time.sleep(1.5)
            st.rerun()
        else:
            st.error(msg)

def render_single_group(group_id, group_name, user_id):
    st.button(":material/arrow_back: Volver a mis grupos", on_click=cerrar_grupo_callback)

    group_info = get_group_info(group_id)
    if not group_info:
        st.error("Error al cargar la información del grupo.")
        return

    admin_id = group_info['created_by']
    es_admin = admin_id == user_id
    allow_leaving = bool(group_info.get('allow_leaving', True))

    emoji = group_info.get('emoji', '👥')
    nombre = group_info.get('name', group_name)
    render_header("collection", f"{emoji} {nombre}")
    
    if es_admin:
        st.caption("👑 Eres el administrador de este grupo")
    st.divider()

    # 1. Obtenemos los miembros ANTES de dibujar el menú para saber si hay notificaciones
    miembros = get_group_members(group_id)
    pendientes = [m for m in miembros if m.get('leave_status') == 'pending']
    
    # 2. Lógica de la bolita roja
    label_ajustes = "Ajustes 🔴" if (es_admin and pendientes) else "Ajustes"

    selected_tab = option_menu(
        menu_title=None,
        options=["Resumen", "Gastos", "Miembros", label_ajustes],
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
        render_subheader("analytics", "Resumen y Liquidación")
        from database_groups import get_pending_balances, calculate_settlements, get_group_expenses
        
        balances = get_pending_balances(group_id)
        gastos_totales = get_group_expenses(group_id)
        
        nombres = {m['user_id']: (m.get('profiles') or [{}])[0].get('name', 'Usuario') for m in miembros if isinstance(m.get('profiles'), list)}
        
        if not gastos_totales:
            st.info("Añade gastos para ver las estadísticas del grupo.")
        else:
            # --- 1. GRÁFICOS Y MÉTRICAS ---
            total_gastado = sum(g['total_amount'] for g in gastos_totales)
            gastado_por_persona = {}
            for g in gastos_totales:
                pid = g['paid_by']
                gastado_por_persona[nombres.get(pid, 'Desconocido')] = gastado_por_persona.get(nombres.get(pid, 'Desconocido'), 0) + g['total_amount']

            c_met, c_graf = st.columns([1, 2], vertical_alignment="center")
            c_met.metric("Gasto Total del Grupo", f"{total_gastado:,.2f}€")
            
            fig = go.Figure(data=[go.Pie(labels=list(gastado_por_persona.keys()), values=list(gastado_por_persona.values()), hole=.4)])
            fig.update_layout(height=250, margin=dict(t=0, b=0, l=0, r=0), showlegend=True)
            c_graf.plotly_chart(fig, use_container_width=True)
            
            st.divider()
            
            # --- 2. LIQUIDACIÓN DE DEUDAS ---
            st.write("### 💸 Liquidación Pendiente")
            pagos = calculate_settlements(balances)
            
            if not pagos:
                st.success("✨ ¡Todo el mundo está al día! No hay deudas pendientes en este grupo.")
            else:
                for p in pagos:
                    de_nombre = nombres.get(p['from'], "Alguien")
                    a_nombre = nombres.get(p['to'], "Alguien")
                    
                    with st.container(border=True):
                        c1, c2 = st.columns([3, 1], vertical_alignment="center")
                        c1.markdown(f"👉 **{de_nombre}** debe pagar **{p['amount']:.2f}€** a **{a_nombre}**")
                        
                        # Solo el acreedor (el que recibe el dinero) puede darle al botón de cobrar
                        with c2:
                            if user_id == p['to']:
                                if st.button("Cobrar ✅", key=f"cobrar_{p['from']}_{p['to']}", type="primary", use_container_width=True):
                                    saldar_deuda_dialog(group_id, p['to'], p['from'], de_nombre, p['amount'])
                            elif user_id == p['from']:
                                st.caption("Esperando confirmación...")

    elif selected_tab == "Gastos":
        render_subheader("receipt", "Historial de Gastos")
        from database_groups import get_group_expenses, delete_group_expense, get_locked_movements
        from components import editar_movimiento_dialog
        
        gastos = get_group_expenses(group_id)
        locked_movs = get_locked_movements() # Lista negra de tickets con candado
        
        if not gastos:
            st.info("Aún no hay gastos registrados en este grupo.")
        else:
            for g in gastos:
                is_locked = g['movement_id'] in locked_movs
                
                with st.container(border=True):
                    col1, col2, col3, col_btns = st.columns([2.5, 1.2, 1.2, 1], vertical_alignment="center")
                    
                    with col1:
                        candado_str = "🔒 " if is_locked else ""
                        st.markdown(f"**{candado_str}{g['description']}**")
                        pagador = g.get('profiles', {}).get('name', 'Alguien')
                        st.caption(f"Pagado por: {pagador} | 📅 {g['date']}")
                    with col2:
                        st.markdown(f"### {g['total_amount']:.2f}€")
                    with col3:
                        mi_parte = next((s['amount_owed'] for s in g.get('group_expense_splits', []) if s['user_id'] == user_id), 0)
                        st.markdown(f"**Tu cuota: {mi_parte:.2f}€**")
                        
                    with col_btns:
                        if es_admin or g['paid_by'] == user_id:
                            btn_edit, btn_del = st.columns(2)
                            with btn_edit:
                                from database import get_categories
                                cats_para_editar = get_categories(user_id)
                                mov_compatible = {
                                    "id": g['movement_id'], "user_id": g['paid_by'], "quantity": g['total_amount'], "type": "Gasto",
                                    "category_id": g.get('category_id'), "date": g['date'], "notes": g['description'], "group_id": g['group_id']
                                }
                                # MAGIA DEL CANDADO
                                if st.button(":material/edit:", key=f"ed_g_{g['id']}", disabled=is_locked, help="No se puede editar si hay pagos saldados"):
                                    editar_movimiento_dialog(mov_compatible, cats_para_editar)
                            with btn_del:
                                if st.button(":material/delete:", key=f"dl_g_{g['id']}", type="primary"):
                                    from database_groups import delete_group_expense
                                    if delete_group_expense(g['id'], g.get('movement_id')): 
                                        st.rerun()

    elif selected_tab == "Miembros":
        col_tit, col_btn = st.columns([3, 1])
        with col_tit:
            render_subheader("people", "Miembros del Grupo")
        with col_btn:
            if st.button(":material/person_add: Invitar", use_container_width=True):
                invitar_usuario_dialog(group_id, nombre)
        
        if miembros:
            cols = st.columns(3)
            
            for index, m in enumerate(miembros):
                col = cols[index % 3] 
                
                prof = m.get('profiles')
                if isinstance(prof, list) and len(prof) > 0: prof = prof[0]
                if not prof: prof = {}
                
                name_raw = prof.get('name', 'Usuario')
                lastname_raw = prof.get('lastname', '')
                full_name = " ".join(f"{name_raw} {lastname_raw}".split()) 
                
                color = prof.get('profile_color', '#636EFA')
                avatar = prof.get('avatar_url')
                
                is_current_user = m['user_id'] == user_id
                is_member_admin = m['user_id'] == admin_id
                rol_badge = "👑 Admin" if is_member_admin else "👤 Miembro"
                
                with col:
                    with st.container(border=True, height=180):
                        c1, c2 = st.columns([1.2, 2], vertical_alignment="center")
                        with c1:
                            if avatar:
                                st.image(avatar, width=90)
                            else:
                                st.markdown(f"""
                                    <div style="width: 90px; height: 90px; background-color: {color}; 
                                                border-radius: 50%; display: flex; align-items: center; 
                                                justify-content: center; color: white; font-weight: bold; font-size: 36px;">
                                        {full_name[0].upper() if full_name else '?'}
                                    </div>
                                """, unsafe_allow_html=True)
                        with c2:
                            estado_extra = " ⏳ *(Saliendo)*" if m.get('leave_status') == 'pending' else ""
                            st.markdown(f"### {full_name}{estado_extra}")
                            st.caption(f"{rol_badge} {'**(Tú)**' if is_current_user else ''}")
                        
                        if es_admin and not is_current_user:
                            st.write("") 
                            if st.button(":material/person_remove: Expulsar", key=f"kick_{m['user_id']}", use_container_width=True):
                                if remove_group_member(group_id, m['user_id']):
                                    st.toast("Usuario eliminado")
                                    st.rerun()
        else:
            st.warning("No se ha podido cargar la lista de miembros.")

    elif selected_tab == label_ajustes:
        render_subheader("gear", "Configuración del Grupo")
        with st.container(border=True):
            if es_admin:
                st.write("**Ajustes Generales**")
                with st.form("edit_group_form"):
                    col1, col2 = st.columns([3, 1])
                    new_name = col1.text_input("Nombre del grupo", value=nombre)
                    new_emoji = col2.text_input("Emoji", value=emoji)
                    new_color = st.color_picker("Color", value=group_info.get('color', '#636EFA'))
                    
                    st.divider()
                    st.write("**Permisos de los miembros**")
                    nuevo_allow = st.toggle("Permitir a los miembros abandonar el grupo por su cuenta", value=allow_leaving)
                    
                    if st.form_submit_button("Guardar Cambios", use_container_width=True):
                        if new_name.strip():
                            ok, msg = update_group_details(group_id, new_name, new_emoji, new_color)
                            update_group_setting(group_id, "allow_leaving", bool(nuevo_allow))
                            if ok:
                                st.session_state.current_group_name = new_name
                                st.success("Ajustes guardados")
                                time.sleep(0.5)
                                st.rerun()
                            else:
                                st.error(msg)
                        else:
                            st.error("El nombre no puede estar vacío")

                st.divider()

                st.write("**Zona Peligrosa**")
                if st.button(":material/delete: Eliminar Grupo Definitivamente", type="primary"):
                    confirmar_borrar_grupo(group_id)

                if pendientes:
                    st.divider()
                    st.error("**⚠️ Solicitudes pendientes para abandonar el grupo**")
                    for p in pendientes:
                        p_prof = p.get('profiles', {})
                        if isinstance(p_prof, list) and len(p_prof) > 0: p_prof = p_prof[0]
                        
                        p_name_raw = p_prof.get('name', 'Un usuario')
                        p_last_raw = p_prof.get('lastname', '')
                        p_full_name = " ".join(f"{p_name_raw} {p_last_raw}".split()) 
                        
                        with st.container(border=True):
                            st.write(f"**{p_full_name}** ha solicitado salir.")
                            c_yes, c_no = st.columns(2)
                            if c_yes.button("Aprobar salida", key=f"app_{p['user_id']}", type="primary", use_container_width=True):
                                resolve_leave_request(group_id, p['user_id'], True)
                                st.rerun()
                            if c_no.button("Rechazar", key=f"rej_{p['user_id']}", use_container_width=True):
                                resolve_leave_request(group_id, p['user_id'], False)
                                st.rerun()

            else:
                st.write("**Opciones de Miembro**")
                if allow_leaving:
                    st.info("Puedes abandonar este grupo en cualquier momento. El histórico de tus gastos se mantendrá.")
                    if st.button(":material/logout: Abandonar Grupo", type="primary"):
                        if remove_group_member(group_id, user_id):
                            cerrar_grupo_callback() 
                            st.rerun() 
                else:
                    mi_estado = next((m.get('leave_status') for m in miembros if m['user_id'] == user_id), 'none')
                    if mi_estado == 'pending':
                        st.info("⏳ Has solicitado abandonar el grupo. Esperando aprobación.")
                    else:
                        st.warning("🔒 El administrador ha bloqueado la opción de abandonar voluntariamente.")
                        if st.button("Solicitar abandonar el grupo", type="primary"):
                            request_leave_group(group_id, user_id)
                            st.rerun()


# --- FUNCIÓN PRINCIPAL ENRUTADORA ---
def render_groups(user_id, user_email):
    current_group_id = st.session_state.get('current_group_id')
    current_group_name = st.session_state.get('current_group_name', 'Grupo')

    if current_group_id:
        render_single_group(current_group_id, current_group_name, user_id)
        return

    render_header("people", "Grupos Compartidos")
    st.caption("Gestiona gastos compartidos con amigos, pareja o compañeros de piso.")
    
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
                            abrir_grupo_callback(inv['group_id'], g_info.get('name', 'Grupo'))
                            st.rerun()
                    if cr.button(":material/close: Rechazar", key=f"rej_{inv['id']}", use_container_width=True):
                        if respond_invitation(inv['id'], inv['group_id'], user_id, False):
                            st.info("Invitación rechazada.")
                            st.rerun()
