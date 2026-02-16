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
    add_shared_expense
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

@st.dialog("Añadir Miembro Invitado")
def add_guest_dialog(group_id):
    st.write("Añade a un amigo que no use la app.")
    nombre_invitado = st.text_input("Nombre del amigo")
    if st.button("Crear Miembro Invitado", type="primary", use_container_width=True):
        if nombre_invitado:
            ok, msg = add_external_member(group_id, nombre_invitado)
            if ok:
                st.success(msg)
                time.sleep(1)
                st.rerun()

@st.dialog("✅ Confirmar Recepción de Pago")
def saldar_deuda_dialog(group_id, creditor_id, debtor_id, debtor_name, amount):
    st.warning(f"¿Confirmas que has recibido **{amount:.2f}€** de **{debtor_name}**?")
    if st.button("Sí, confirmar cobro", type="primary", use_container_width=True):
        from database_groups import settle_debt_between_users
        ok, msg = settle_debt_between_users(group_id, creditor_id, debtor_id)
        if ok:
            st.toast(f"✅ {msg}")
            time.sleep(1)
            st.rerun()

@st.dialog("💸 Registrar Pago de Deuda")
def avisar_pago_dialog(group_id, debtor_id, creditor_id, creditor_name, amount):
    st.write(f"Vas a avisar a **{creditor_name}** de que le has pagado **{amount:.2f}€**.")
    from database import get_categories, save_input
    from datetime import datetime
    cats = get_categories(debtor_id)
    gasto_cats = [c for c in cats if c.get('type') == 'Gasto']
    nombres_cats = [f"{c.get('emoji', '📁')} {c['name']}" for c in gasto_cats]
    sel_cat = st.selectbox("Categoría personal", nombres_cats)
    if st.button("Confirmar Pago y Avisar", type="primary", use_container_width=True):
        cat_obj = next((c for c in gasto_cats if f"{c.get('emoji', '📁')} {c['name']}" == sel_cat), None)
        if cat_obj:
            save_input({"user_id": debtor_id, "quantity": amount, "type": "Gasto", "category_id": cat_obj['id'], "date": str(datetime.now().date()), "notes": f"Pago deuda grupo a {creditor_name}"})
            if request_settlement(group_id, debtor_id, creditor_id):
                st.toast("✅ Aviso enviado.")
                time.sleep(1)
                st.rerun()

def render_single_group(group_id, group_name, user_id):
    st.button(":material/arrow_back: Volver a mis grupos", on_click=cerrar_grupo_callback)
    group_info = get_group_info(group_id)
    if not group_info: return

    admin_id = group_info['created_by']
    es_admin = admin_id == user_id
    render_header("collection", f"{group_info.get('emoji', '👥')} {group_info.get('name', group_name)}")
    
    miembros = get_group_members(group_id)
    notif_cobro = check_pending_confirmations(user_id)
    label_resumen = "Resumen 🔴" if group_id in notif_cobro else "Resumen"

    selected_tab = option_menu(None, [label_resumen, "Gastos", "Miembros", "Ajustes"], 
        icons=["graph-up", "receipt", "people", "gear"], orientation="horizontal",
        styles={"nav-link-selected": {"background-color": (st.session_state.user.get('profile_color') or '#636EFA')}})

    # LÓGICA DE NOMBRES SEGURA
    nombres = {}
    es_externo_dict = {}
    for m in miembros:
        m_id = f"ext_{m['id']}" if m.get('is_external') else m['user_id']
        es_externo_dict[m_id] = m.get('is_external', False)
        
        if m.get('is_external'):
            nombres[m_id] = m.get('external_name', 'Invitado')
        else:
            prof = m.get('profiles', {})
            # Si profiles es una lista, cogemos el primero. Si es dicc, directo.
            if isinstance(prof, list) and len(prof) > 0:
                nombres[m_id] = prof[0].get('name', 'Usuario')
            elif isinstance(prof, dict):
                nombres[m_id] = prof.get('name', 'Usuario')
            else:
                nombres[m_id] = 'Usuario'

    if selected_tab == label_resumen:
        render_subheader("analytics", "Resumen")
        from database_groups import get_pending_balances, calculate_settlements, get_group_expenses
        balances = get_pending_balances(group_id)
        peticiones = get_settlement_requests(group_id)
        
        pagos = calculate_settlements(balances)
        if not pagos:
            st.success("✨ ¡Todo al día!")
        else:
            for p in pagos:
                de_id, a_id = p['from'], p['to']
                de_nom, a_nom = nombres.get(de_id, "Alguien"), nombres.get(a_id, "Alguien")
                solicitado = (de_id, a_id) in peticiones
                de_ext, a_ext = es_externo_dict.get(de_id, False), es_externo_dict.get(a_id, False)

                with st.container(border=True):
                    c1, c2 = st.columns([2.5, 1.5], vertical_alignment="center")
                    c1.write(f"👉 {'👻 ' if de_ext else ''}**{de_nom}** debe **{p['amount']:.2f}€** a {'👻 ' if a_ext else ''}**{a_nom}**")
                    with c2:
                        if de_ext and es_admin:
                            if st.button("Saldar manual ✅", key=f"s_{de_id}_{a_id}", use_container_width=True):
                                from database_groups import settle_external_debt_admin
                                if settle_external_debt_admin(group_id, de_nom, a_id)[0]: st.rerun()
                        elif a_ext:
                            if de_id == user_id:
                                if solicitado: st.caption("⏳ Validando Admin")
                                elif st.button("💸 Ya pagué", key=f"p_ext_{a_id}", use_container_width=True):
                                    avisar_pago_dialog(group_id, de_id, a_id, a_nom, p['amount'])
                            elif es_admin and solicitado:
                                if st.button("Confirmar ✅", key=f"adm_c_{de_id}", type="primary", use_container_width=True):
                                    from database_groups import settle_debt_to_external
                                    if settle_debt_to_external(group_id, de_id, a_nom)[0]: st.rerun()
                            else: st.caption("⏳ Procesando" if solicitado else "Pendiente")
                        else:
                            if de_id == user_id:
                                if solicitado: st.caption("⏳ Pendiente")
                                elif st.button("💸 Ya pagué", key=f"pr_{a_id}", use_container_width=True):
                                    avisar_pago_dialog(group_id, de_id, a_id, a_nom, p['amount'])
                            elif a_id == user_id and solicitado:
                                if st.button("✅ Recibido", key=f"rec_{de_id}", type="primary", use_container_width=True):
                                    saldar_deuda_dialog(group_id, a_id, de_id, de_nom, p['amount'])
                            else: st.caption("⏳ En aviso" if solicitado else "Pendiente")

    elif selected_tab == "Gastos":
        render_subheader("receipt", "Gastos")
        with st.expander("➕ Añadir Gasto", expanded=False):
             with st.form("add_exp", clear_on_submit=True):
                 desc = st.text_input("Descripción")
                 amt = st.number_input("Cantidad (€)", min_value=0.01)
                 
                 op_pag = {nombres[f"ext_{m['id']}" if m.get('is_external') else m['user_id']]: (f"ext_{m['id']}" if m.get('is_external') else m['user_id']) for m in miembros}
                 final_pagador = op_pag[st.selectbox("¿Quién pagó?", op_pag.keys())] if es_admin else user_id
                 
                 st.write("¿Quién participa?")
                 p_cols = st.columns(3)
                 p_ids = []
                 for idx, m in enumerate(miembros):
                     m_id = f"ext_{m['id']}" if m.get('is_external') else m['user_id']
                     with p_cols[idx % 3]:
                         if st.checkbox(nombres[m_id], value=True, key=f"chk_{m_id}"): p_ids.append(m_id)
                             
                 if st.form_submit_button("Guardar"):
                     if desc and amt > 0 and p_ids:
                         from database_groups import add_shared_expense
                         mov = {"user_id": user_id, "quantity": amt, "type": "Gasto", "date": time.strftime("%Y-%m-%d"), "notes": desc, "paid_by_custom": final_paid_by}
                         if add_shared_expense(group_id, mov, p_ids)[0]: st.rerun()

        from database_groups import get_group_expenses
        for g in get_group_expenses(group_id):
            with st.container(border=True):
                st.write(f"**{g['description']}** - {g['total_amount']:.2f}€")

    elif selected_tab == "Miembros":
        c1, c2 = st.columns([2, 1])
        c1.subheader("Miembros")
        if es_admin:
            if c2.button("👻+ Invitado", use_container_width=True): add_guest_dialog(group_id)
        
        m_cols = st.columns(3)
        for idx, m in enumerate(miembros):
            m_id = f"ext_{m['id']}" if m.get('is_external') else m['user_id']
            with m_cols[idx % 3]:
                with st.container(border=True):
                    st.write(f"**{'👻 ' if es_externo_dict[m_id] else ''}{nombres[m_id]}**")
                    if es_admin and m_id != user_id:
                        if st.button("Expulsar", key=f"k_{m_id}", use_container_width=True):
                            from database_groups import remove_group_member
                            if remove_group_member(group_id, m_id, es_externo_dict[m_id]): st.rerun()

    elif selected_tab == "Ajustes":
        if es_admin:
            if st.button("Eliminar Grupo", type="primary", use_container_width=True):
                from database_groups import delete_group
                delete_group(group_id)
                cerrar_grupo_callback()
                st.rerun()

def render_groups(user_id, user_email):
    gid = st.session_state.get('current_group_id')
    if gid:
        render_single_group(gid, st.session_state.get('current_group_name'), user_id)
    else:
        render_header("people", "Grupos")
        tab = option_menu(None, ["Mis Grupos", "Invitaciones"], icons=["folder", "envelope"], orientation="horizontal")
        if tab == "Mis Grupos":
            with st.expander("➕ Nuevo Grupo"):
                with st.form("new_g"):
                    nom = st.text_input("Nombre")
                    if st.form_submit_button("Crear"):
                        if nom:
                            from database_groups import create_group
                            if create_group(nom, "👥", "#636EFA", user_id)[0]: st.rerun()
            
            for g in get_user_groups(user_id):
                with st.container(border=True):
                    st.write(f"### {g.get('emoji', '👥')} {g['name']}")
                    st.button("Abrir", key=f"o_{g['id']}", on_click=abrir_grupo_callback, args=(g['id'], g['name']), type="primary")

        elif tab == "Invitaciones":
            invs = get_my_invitations(user_email)
            for i in invs:
                with st.container(border=True):
                    st.write(f"Invitación a **{i.get('groups', {}).get('name')}**")
                    if st.button("Aceptar", key=f"a_{i['id']}"):
                        if respond_invitation(i['id'], i['group_id'], user_id, True): st.rerun()
