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
    add_external_member, settle_external_debt_admin, settle_debt_to_external,
    add_shared_expense # <-- IMPORTANTE: Asegúrate de tener estas funciones en database_groups.py
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
    from database import get_categories, save_input
    from datetime import datetime
    cats = get_categories(debtor_id)
    gasto_cats = [c for c in cats if c.get('type') == 'Gasto']
    nombres_cats = [f"{c.get('emoji', '📁')} {c['name']}" for c in gasto_cats]
    if not nombres_cats:
        st.warning("No tienes categorías de gasto.")
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

def render_single_group(group_id, group_name, user_id):
    st.button(":material/arrow_back: Volver a mis grupos", on_click=cerrar_grupo_callback)
    group_info = get_group_info(group_id)
    if not group_info:
        st.error("Error al cargar el grupo.")
        return

    admin_id = group_info['created_by']
    es_admin = admin_id == user_id
    nombre = group_info.get('name', group_name)
    render_header("collection", f"{group_info.get('emoji', '👥')} {nombre}")
    
    miembros = get_group_members(group_id)
    notificaciones_cobro = check_pending_confirmations(user_id)
    label_resumen = "Resumen 🔴" if group_id in notificaciones_cobro else "Resumen"

    selected_tab = option_menu(None, [label_resumen, "Gastos", "Miembros", "Ajustes"], 
        icons=["graph-up", "receipt", "people", "gear"], orientation="horizontal",
        styles={"nav-link-selected": {"background-color": (st.session_state.user.get('profile_color') or '#636EFA')}})

    if selected_tab == label_resumen:
        render_subheader("analytics", "Resumen y Liquidación")
        from database_groups import get_pending_balances, calculate_settlements, get_group_expenses
        balances = get_pending_balances(group_id)
        gastos_totales = get_group_expenses(group_id)
        peticiones_activas = get_settlement_requests(group_id)
        
        nombres = {}
        es_externo_dict = {}
        for m in miembros:
            m_id = f"ext_{m['id']}" if m.get('is_external') else m['user_id']
            nombres[m_id] = m.get('external_name') if m.get('is_external') else (m.get('profiles') or [{}])[0].get('name', 'Usuario')
            es_externo_dict[m_id] = m.get('is_external', False)
        
        if not gastos_totales:
            st.info("No hay gastos todavía.")
        else:
            total_gastado = sum(g['total_amount'] for g in gastos_totales)
            st.metric("Gasto Total del Grupo", f"{total_gastado:,.2f}€")
            st.divider()

            pagos = calculate_settlements(balances)
            if not pagos:
                st.success("✨ ¡Todo el mundo está al día!")
            else:
                for p in pagos:
                    de_id, a_id = p['from'], p['to']
                    de_nom, a_nom = nombres.get(de_id, "Alguien"), nombres.get(a_id, "Alguien")
                    solicitado = (de_id, a_id) in peticiones_activas
                    de_ext, a_ext = es_externo_dict.get(de_id, False), es_externo_dict.get(a_id, False)

                    with st.container(border=True):
                        c1, c2 = st.columns([2.5, 1.5], vertical_alignment="center")
                        c1.write(f"👉 {'👻 ' if de_ext else ''}**{de_nom}** debe **{p['amount']:.2f}€** a {'👻 ' if a_ext else ''}**{a_nom}**")
                        
                        with c2:
                            # 1. CASO: DEUDOR ES EXTERNO (Admin salda manual)
                            if de_ext:
                                if es_admin:
                                    if st.button("Saldar manual ✅", key=f"s_{de_id}_{a_id}", use_container_width=True):
                                        if settle_external_debt_admin(group_id, de_nom, a_id)[0]: st.rerun()
                                else: st.caption("Esperando Admin")

                            # 2. CASO: ACREEDOR ES EXTERNO (Usuario real paga a invitado)
                            elif a_ext:
                                if de_id == user_id:
                                    if solicitado: st.caption("⏳ Validando Admin")
                                    elif st.button("💸 Ya pagué", key=f"p_ext_{a_id}", use_container_width=True):
                                        avisar_pago_dialog(group_id, de_id, a_id, a_nom, p['amount'])
                                elif es_admin:
                                    if solicitado:
                                        if st.button("Confirmar ✅", key=f"ac_{de_id}", type="primary", use_container_width=True):
                                            if settle_debt_to_external(group_id, de_id, a_nom)[0]: st.rerun()
                                    else: st.caption("⏳ Esperando aviso")
                                else: st.caption("Pendiente")

                            # 3. CASO: REAL A REAL
                            else:
                                if de_id == user_id:
                                    if solicitado: st.caption("⏳ Pendiente")
                                    elif st.button("💸 Ya pagué", key=f"pr_{a_id}", use_container_width=True):
                                        avisar_pago_dialog(group_id, de_id, a_id, a_nom, p['amount'])
                                elif a_id == user_id and solicitado:
                                    if st.button("✅ Recibido", key=f"rec_{de_id}", type="primary", use_container_width=True):
                                        saldar_deuda_dialog(group_id, a_id, de_id, de_nom, p['amount'])
                                else:
                                    st.caption("⏳ Proceso" if solicitado else "Pendiente")

    elif selected_tab == "Gastos":
        render_subheader("receipt", "Gastos")
        with st.expander("➕ Añadir Gasto", expanded=False):
             with st.form("add_exp", clear_on_submit=True):
                 desc = st.text_input("Descripción", placeholder="¿En qué se ha gastado?")
                 amt = st.number_input("Cantidad (€)", min_value=0.01)
                 
                 op_pag = {}
                 for m in miembros:
                     m_id = f"ext_{m['id']}" if m.get('is_external') else m['user_id']
                     m_nom = f"👻 {m['external_name']}" if m.get('is_external') else (m.get('profiles') or [{}])[0].get('name', 'Usuario')
                     if m_id == user_id: m_nom += " (Tú)"
                     op_pag[m_nom] = m_id

                 if es_admin:
                     pagador_sel = st.selectbox("¿Quién pagó?", options=list(op_pag.keys()))
                     final_paid_by = op_pag[pagador_sel]
                 else:
                     final_paid_by = user_id
                     st.write("Pagador: **Tú**")

                 st.write("¿Quién participa?")
                 p_cols = st.columns(3)
                 p_ids = []
                 for idx, m in enumerate(miembros):
                     m_id = f"ext_{m['id']}" if m.get('is_external') else m['user_id']
                     m_nom = m.get('external_name') if m.get('is_external') else (m.get('profiles') or [{}])[0].get('name', 'Usuario')
                     with p_cols[idx % 3]:
                         if st.checkbox(m_nom, value=True, key=f"part_{m_id}"): p_ids.append(m_id)
                             
                 if st.form_submit_button("Guardar Gasto"):
                     if desc and amt > 0 and p_ids:
                         mov = {"user_id": user_id, "quantity": amt, "type": "Gasto", "date": time.strftime("%Y-%m-%d"), "notes": desc, "paid_by_custom": final_paid_by}
                         if add_shared_expense(group_id, mov, p_ids)[0]: st.rerun()

        gastos = get_group_expenses(group_id)
        from database_groups import get_locked_movements
        locked = get_locked_movements()
        for g in gastos:
            with st.container(border=True):
                c_inf, c_mon, c_btn = st.columns([2.5, 1, 1], vertical_alignment="center")
                is_l = g['movement_id'] in locked
                c_inf.write(f"{'🔒 ' if is_l else ''}**{g['description']}**")
                c_inf.caption(f"📅 {g['date']}")
                c_mon.write(f"### {g['total_amount']:.2f}€")
                if (es_admin or g['paid_by'] == user_id) and not is_l:
                    if c_btn.button(":material/delete:", key=f"del_g_{g['id']}", type="primary"):
                        from database_groups import delete_group_expense
                        if delete_group_expense(g['id'], g.get('movement_id')): st.rerun()

    elif selected_tab == "Miembros":
        col_t, col_b1, col_b2 = st.columns([2, 1, 1])
        col_t.subheader("Miembros")
        with col_b1:
            if st.button("👤+ Invitar"): invitar_usuario_dialog(group_id, nombre)
        with col_b2:
            if es_admin:
                if st.button("👻+ Externo"): add_guest_dialog(group_id)
        
        m_cols = st.columns(3)
        for idx, m in enumerate(miembros):
            with m_cols[idx % 3]:
                with st.container(border=True):
                    is_ext = m.get('is_external', False)
                    m_name = m.get('external_name', 'Invitado') if is_ext else (m.get('profiles') or [{}])[0].get('name', 'Usuario')
                    st.write(f"**{'👻 ' if is_ext else ''}{m_name}**")
                    st.caption("👑 Admin" if m.get('user_id') == admin_id else "👤 Miembro")
                    if es_admin and m.get('user_id') != user_id:
                        u_kick = m['id'] if is_ext else m['user_id']
                        if st.button("Expulsar", key=f"k_{u_kick}", use_container_width=True):
                            if remove_group_member(group_id, u_kick, is_ext): st.rerun()

    elif selected_tab == "Ajustes":
        render_subheader("gear", "Configuración")
        if es_admin:
            if st.button("Eliminar Grupo Definitivamente", type="primary", use_container_width=True):
                confirmar_borrar_grupo(group_id)
        else:
            st.info("Solo el administrador puede realizar cambios estructurales.")

# --- FUNCIÓN PRINCIPAL ENRUTADORA ---
def render_groups(user_id, user_email):
    gid = st.session_state.get('current_group_id')
    if gid:
        render_single_group(gid, st.session_state.get('current_group_name'), user_id)
    else:
        render_header("people", "Grupos Compartidos")
        main_tab = option_menu(None, ["Mis Grupos", "Invitaciones"], icons=["folder", "envelope"], orientation="horizontal")
        
        if main_tab == "Mis Grupos":
            with st.expander("➕ Crear Nuevo Grupo"):
                with st.form("new_g"):
                    n_name = st.text_input("Nombre")
                    n_emoji = st.text_input("Emoji", value="👥")
                    if st.form_submit_button("Crear"):
                        if n_name.strip():
                            if create_group(n_name, n_emoji, "#636EFA", user_id)[0]: st.rerun()
            
            my_gs = get_user_groups(user_id)
            if not my_gs: st.info("No tienes grupos.")
            else:
                gs_cols = st.columns(3)
                for idx, g in enumerate(my_gs):
                    with gs_cols[idx % 3]:
                        with st.container(border=True):
                            st.write(f"### {g.get('emoji', '👥')} {g['name']}")
                            st.button("Abrir", key=f"o_{g['id']}", use_container_width=True, type="primary", 
                                      on_click=abrir_grupo_callback, args=(g['id'], g['name']))

        elif main_tab == "Invitaciones":
            invs = get_my_invitations(user_email)
            if not invs: st.write("No hay invitaciones.")
            for i in invs:
                with st.container(border=True):
                    st.write(f"Te invitan a **{i.get('groups', {}).get('name')}**")
                    ca, cr = st.columns(2)
                    if ca.button("Aceptar", key=f"a_{i['id']}"):
                        if respond_invitation(i['id'], i['group_id'], user_id, True): st.rerun()
                    if cr.button("Rechazar", key=f"r_{i['id']}"):
                        if respond_invitation(i['id'], i['group_id'], user_id, False): st.rerun()
