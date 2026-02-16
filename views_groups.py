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
    request_leave_group, resolve_leave_request,
    check_pending_confirmations, get_settlement_requests, request_settlement,
    add_external_member, settle_external_debt_admin, settle_debt_to_external # <-- Asegúrate de tener esta última en database_groups
)

BOOTSTRAP_ICONS_LINK = '<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.10.5/font/bootstrap-icons.css">'

def get_dynamic_css():
    p_color = (st.session_state.user.get('profile_color') or '#636EFA') if 'user' in st.session_state and st.session_state.user else '#636EFA'
    return f"""
    <style>
    @import url("https://cdn.jsdelivr.net/npm/bootstrap-icons@1.10.5/font/bootstrap-icons.css");
    h1 .bi, h3 .bi, h5 .bi {{ vertical-align: -3px; margin-right: 10px; color: {p_color}; }}
    </style>
    """

def render_header(icon_name, text):
    st.markdown(get_dynamic_css(), unsafe_allow_html=True)
    st.markdown(f'<h1><i class="bi bi-{icon_name}"></i> {text}</h1>', unsafe_allow_html=True)

def render_subheader(icon_name, text):
    st.markdown(f'<h3><i class="bi bi-{icon_name}"></i> {text}</h3>', unsafe_allow_html=True)

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

@st.dialog("Añadir Miembro Invitado")
def add_guest_dialog(group_id):
    st.write("Añade a un amigo que no use la app. Podrás incluirlo en los gastos y gestionar sus pagos manualmente.")
    nombre_invitado = st.text_input("Nombre del amigo")
    if st.button("Crear Miembro Invitado", type="primary", use_container_width=True):
        if nombre_invitado:
            ok, msg = add_external_member(group_id, nombre_invitado)
            if ok:
                st.success(msg)
                time.sleep(1)
                st.rerun()
            else: st.error(msg)
        else:
            st.warning("Introduce un nombre.")

# --- VISTA INTERIOR DEL GRUPO ---

@st.dialog("✅ Confirmar Recepción de Pago")
def saldar_deuda_dialog(group_id, creditor_id, debtor_id, debtor_name, amount):
    st.warning(f"¿Confirmas que has recibido **{amount:.2f}€** de **{debtor_name}**?")
    st.info("💡 Al confirmar, se le pondrá un 🔒 candado a los tickets compartidos y tu gasto personal se reducirá automáticamente para cuadrar tus cuentas.")
    
    if st.button("Sí, confirmar cobro", type="primary", use_container_width=True):
        from database_groups import settle_debt_between_users
        ok, msg = settle_debt_between_users(group_id, creditor_id, debtor_id)
        if ok:
            st.toast(f"✅ {msg}")
            time.sleep(1.5)
            st.rerun()
        else:
            st.error(msg)

@st.dialog("💸 Registrar Pago de Deuda")
def avisar_pago_dialog(group_id, debtor_id, creditor_id, creditor_name, amount):
    st.write(f"Vas a avisar a **{creditor_name}** de que le has pagado **{amount:.2f}€**.")
    st.info("Para cuadrar tus cuentas personales, ¿en qué categoría quieres registrar esta salida de dinero?")
    
    from database import get_categories, save_input
    from datetime import datetime
    
    cats = get_categories(debtor_id)
    gasto_cats = [c for c in cats if c.get('type') == 'Gasto']
    nombres_cats = [f"{c.get('emoji', '📁')} {c['name']}" for c in gasto_cats]
    
    if not nombres_cats:
        st.warning("No tienes categorías de gasto. Crea una primero.")
        return
        
    sel_cat = st.selectbox("Categoría", nombres_cats)
    concepto = st.text_input("Concepto", value=f"Pago deuda grupo a {creditor_name}")
    
    if st.button("Confirmar Pago y Avisar", type="primary", use_container_width=True):
        cat_obj = next((c for c in gasto_cats if f"{c.get('emoji', '📁')} {c['name']}" == sel_cat), None)
        if cat_obj:
            save_input({
                "user_id": debtor_id, "quantity": amount, "type": "Gasto", 
                "category_id": cat_obj['id'], "date": str(datetime.now().date()), "notes": concepto
            })
            if request_settlement(group_id, debtor_id, creditor_id):
                st.toast("✅ Gasto registrado y aviso enviado.")
                time.sleep(1)
                st.rerun()
            else:
                st.error("Error al enviar el aviso al grupo.")

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

    miembros = get_group_members(group_id)
    pendientes = [m for m in miembros if m.get('leave_status') == 'pending']
    notificaciones_cobro = check_pending_confirmations(user_id)
    
    label_ajustes = "Ajustes 🔴" if (es_admin and pendientes) else "Ajustes"
    label_resumen = "Resumen 🔴" if group_id in notificaciones_cobro else "Resumen"

    p_color = (st.session_state.user.get('profile_color') or '#636EFA')
    i_color = (st.session_state.user.get('icon_color') or '#FFA500')

    selected_tab = option_menu(
        menu_title=None,
        options=[label_resumen, "Gastos", "Miembros", label_ajustes],
        icons=["graph-up", "receipt", "people", "gear"],
        orientation="horizontal",
        default_index=0,
        styles={
            "container": {"padding": "0!important", "background-color": "transparent"},
            "icon": {"color": i_color, "font-size": "18px"}, 
            "nav-link": {"font-size": "16px", "text-align": "center", "margin": "0px", "--hover-color": "#eee"},
            "nav-link-selected": {"background-color": p_color}, 
        }
    )

    # --- EXTRACCIÓN SEGURA DE NOMBRES PARA EVITAR KEYERROR ---
    nombres = {}
    es_externo_dict = {}
    for m in miembros:
        m_id = f"ext_{m['id']}" if m.get('is_external') else m['user_id']
        es_externo_dict[m_id] = m.get('is_external', False)
        
        if m.get('is_external'):
            nombres[m_id] = m.get('external_name', 'Invitado')
        else:
            prof = m.get('profiles', {})
            # Manejo robusto de la estructura de perfiles
            if isinstance(prof, list) and len(prof) > 0:
                nombres[m_id] = prof[0].get('name', 'Usuario')
            elif isinstance(prof, dict):
                nombres[m_id] = prof.get('name', 'Usuario')
            else:
                nombres[m_id] = 'Usuario'

    if selected_tab == label_resumen:
        render_subheader("analytics", "Resumen y Liquidación")
        from database_groups import get_pending_balances, calculate_settlements, get_group_expenses
        
        balances = get_pending_balances(group_id)
        gastos_totales = get_group_expenses(group_id)
        peticiones_activas = get_settlement_requests(group_id)
        
        if not gastos_totales:
            st.info("Añade gastos para ver las estadísticas del grupo.")
        else:
            total_gastado = sum(g['total_amount'] for g in gastos_totales)
            gastado_por_persona = {}
            for g in gastos_totales:
                nom = nombres.get(g['paid_by'], 'Desconocido')
                gastado_por_persona[nom] = gastado_por_persona.get(nom, 0) + g['total_amount']

            c_met, c_graf = st.columns([1, 2], vertical_alignment="center")
            c_met.metric("Gasto Total", f"{total_gastado:,.2f}€")
            fig = go.Figure(data=[go.Pie(labels=list(gastado_por_persona.keys()), values=list(gastado_por_persona.values()), hole=.4)])
            fig.update_layout(height=250, margin=dict(t=0, b=0, l=0, r=0))
            c_graf.plotly_chart(fig, use_container_width=True)
            
            st.divider()
            st.write("### 💸 Liquidación Pendiente")
            pagos = calculate_settlements(balances)
            
            if not pagos:
                st.success("✨ ¡Todo el mundo está al día!")
            else:
                for p in pagos:
                    de_id, a_id = p['from'], p['to']
                    de_nom, a_nom = nombres.get(de_id, "Alguien"), nombres.get(a_id, "Alguien")
                    pago_solicitado = (de_id, a_id) in peticiones_activas
                    de_ext, a_ext = es_externo_dict.get(de_id, False), es_externo_dict.get(a_id, False)
                    
                    with st.container(border=True):
                        c1, c2 = st.columns([2.5, 1.5], vertical_alignment="center")
                        c1.markdown(f"👉 {'👻 ' if de_ext else ''}**{de_nom}** debe **{p['amount']:.2f}€** a {'👻 ' if a_ext else ''}**{a_nom}**")
                        
                        with c2:
                            # 1. CASO: DEUDOR ES EXTERNO (Admin salda manual)
                            if de_ext:
                                if es_admin:
                                    if st.button("Saldar manual ✅", key=f"s_{de_id}_{a_id}", use_container_width=True):
                                        if settle_external_debt_admin(group_id, de_nom, a_id)[0]: st.rerun()
                                else: st.caption("Esperando al Admin")

                            # 2. CASO: ACREEDOR ES EXTERNO (Usuario real paga a invitado)
                            elif a_ext:
                                if de_id == user_id:
                                    if pago_solicitado: st.caption("⏳ Validando Admin")
                                    elif st.button("💸 Ya lo he pagado", key=f"p_ext_{a_id}", use_container_width=True):
                                        avisar_pago_dialog(group_id, de_id, a_id, a_nom, p['amount'])
                                elif es_admin:
                                    if pago_solicitado:
                                        if st.button("Confirmar Pago ✅", key=f"ac_{de_id}", type="primary", use_container_width=True):
                                            if settle_debt_to_external(group_id, de_id, a_nom)[0]: st.rerun()
                                    else: st.caption("⏳ Esperando aviso")
                                else: st.caption("Pendiente")

                            # 3. CASO: DEUDA ENTRE USUARIOS REALES
                            else:
                                if de_id == user_id:
                                    if pago_solicitado: st.caption("⏳ Confirmación pendiente")
                                    else:
                                        if st.button("💸 Ya lo he pagado", key=f"pay_{de_id}_{a_id}", use_container_width=True):
                                            avisar_pago_dialog(group_id, de_id, a_id, a_nom, p['amount'])
                                elif a_id == user_id and pago_solicitado:
                                    if st.button("✅ Confirmar cobro", key=f"conf_{de_id}_{a_id}", type="primary", use_container_width=True):
                                        saldar_deuda_dialog(group_id, a_id, de_id, de_nom, p['amount'])
                                else:
                                    st.caption("⏳ Proceso" if pago_solicitado else "Pendiente")

    elif selected_tab == "Gastos":
        render_subheader("receipt", "Historial de Gastos")
        from database_groups import get_group_expenses, delete_group_expense, get_locked_movements
        from components import editar_movimiento_dialog
        
        with st.expander("➕ Añadir Gasto", expanded=False):
             with st.form("add_expense_form", clear_on_submit=True):
                 desc = st.text_input("Descripción", placeholder="Ej: Cena en el italiano")
                 amount = st.number_input("Cantidad (€)", min_value=0.01, step=0.01)
                 
                 op_pag = {nombres[f"ext_{m['id']}" if m.get('is_external') else m['user_id']]: (f"ext_{m['id']}" if m.get('is_external') else m['user_id']) for m in miembros}
                 if es_admin:
                     final_paid_by = op_pag[st.selectbox("¿Quién ha pagado?", options=list(op_pag.keys()))]
                 else:
                     final_paid_by = user_id
                     st.write("Pagador: **Tú**")

                 st.divider()
                 st.write("¿Quién participa?")
                 p_cols = st.columns(3)
                 p_ids = []
                 for idx, m in enumerate(miembros):
                     m_id = f"ext_{m['id']}" if m.get('is_external') else m['user_id']
                     with p_cols[idx % 3]:
                         if st.checkbox(nombres[m_id], value=True, key=f"add_p_{m_id}"): p_ids.append(m_id)
                             
                 if st.form_submit_button("Guardar Gasto"):
                     if desc and amount > 0 and p_ids:
                         from database_groups import add_shared_expense
                         mov = {"user_id": user_id, "quantity": amount, "type": "Gasto", "date": time.strftime("%Y-%m-%d"), "notes": desc, "paid_by_custom": final_paid_by}
                         if add_shared_expense(group_id, mov, p_ids)[0]: st.rerun()

        gastos = get_group_expenses(group_id)
        locked_movs = get_locked_movements()
        if not gastos:
            st.info("Aún no hay gastos.")
        else:
            for g in gastos:
                is_locked = g['movement_id'] in locked_movs
                with st.container(border=True):
                    col1, col2, col3, col_btns = st.columns([2.5, 1.2, 1.2, 1], vertical_alignment="center")
                    with col1:
                        st.markdown(f"**{'🔒 ' if is_locked else ''}{g['description']}**")
                        st.caption(f"Pagado por: {nombres.get(g['paid_by'], 'Alguien')} | 📅 {g['date']}")
                    with col2: st.markdown(f"### {g['total_amount']:.2f}€")
                    with col3:
                        mi_parte = next((s['amount_owed'] for s in g.get('group_expense_splits', []) if s['user_id'] == user_id), 0)
                        st.markdown(f"**Tu cuota: {mi_parte:.2f}€**")
                    with col_btns:
                        if (es_admin or g['paid_by'] == user_id) and not is_locked:
                            if st.button(":material/delete:", key=f"dl_g_{g['id']}", type="primary"):
                                if delete_group_expense(g['id'], g.get('movement_id')): st.rerun()

    elif selected_tab == "Miembros":
        col_tit, col_btn1, col_btn2 = st.columns([2, 1, 1])
        with col_tit: render_subheader("people", "Miembros")
        with col_btn1: 
            if st.button(":material/person_add: Invitar", use_container_width=True): invitar_usuario_dialog(group_id, nombre)
        with col_btn2:
            if es_admin:
                if st.button(":material/person_add: + Externo", use_container_width=True): add_guest_dialog(group_id)
        
        if miembros:
            cols = st.columns(3)
            for index, m in enumerate(miembros):
                m_id = f"ext_{m['id']}" if m.get('is_external') else m['user_id']
                with cols[index % 3]:
                    with st.container(border=True):
                        st.markdown(f"### {'👻 ' if es_externo_dict[m_id] else ''}{nombres[m_id]}")
                        st.caption("👑 Admin" if m_id == admin_id else "👤 Miembro")
                        if es_admin and m_id != user_id:
                            if st.button("Expulsar", key=f"k_{m_id}", use_container_width=True):
                                from database_groups import remove_group_member
                                if remove_group_member(group_id, m_id, es_externo_dict[m_id]): st.rerun()

    elif selected_tab == label_ajustes:
        render_subheader("gear", "Configuración")
        if es_admin:
            if st.button(":material/delete: Eliminar Grupo", type="primary", use_container_width=True): confirmar_borrar_grupo(group_id)

def render_groups(user_id, user_email):
    current_group_id = st.session_state.get('current_group_id')
    if current_group_id:
        render_single_group(current_group_id, st.session_state.get('current_group_name', 'Grupo'), user_id)
        return

    render_header("people", "Grupos Compartidos")
    main_tab = option_menu(None, ["Mis Grupos", "Invitaciones"], icons=["folder-fill", "envelope-paper"], orientation="horizontal")

    if main_tab == "Mis Grupos":
        with st.expander(":material/add_circle: Crear Nuevo Grupo"):
            with st.form("new_group_v2", clear_on_submit=True):
                g_name = st.text_input("Nombre del grupo")
                if st.form_submit_button("Crear Grupo", use_container_width=True):
                    if g_name.strip():
                        if create_group(g_name, "👥", "#636EFA", user_id)[0]: st.rerun()
        
        my_groups = get_user_groups(user_id)
        if my_groups:
            cols = st.columns(3)
            for index, group in enumerate(my_groups):
                with cols[index % 3]:
                    with st.container(border=True):
                        st.markdown(f"### {group.get('emoji', '👥')} {group['name']}")
                        st.button("Abrir Grupo", key=f"open_{group['id']}", use_container_width=True, type="primary", on_click=abrir_grupo_callback, args=(group['id'], group['name']))

    elif main_tab == "Invitaciones":
        invites = get_my_invitations(user_email)
        if not invites: st.write("No tienes invitaciones pendientes.")
        for inv in invites:
            with st.container(border=True):
                st.write(f"Invitación para **{inv.get('groups', {}).get('name', 'Grupo')}**")
                c1, c2 = st.columns(2)
                if c1.button("Aceptar", key=f"acc_{inv['id']}", use_container_width=True):
                    if respond_invitation(inv['id'], inv['group_id'], user_id, True): st.rerun()
                if c2.button("Rechazar", key=f"rej_{inv['id']}", use_container_width=True):
                    if respond_invitation(inv['id'], inv['group_id'], user_id, False): st.rerun()
