import streamlit as st
import pandas as pd
import time
from datetime import datetime
from database import update_input
from database_groups import get_user_groups, get_group_members, update_shared_expense, get_expense_participants
from database import save_category, update_category, update_input

@st.dialog("➕ Nueva Categoría")
def crear_categoria_dialog(user_id):
    # Recuperamos ingresos para el cálculo dinámico
    p_data = st.session_state.user
    ingresos_totales = (p_data.get('base_salary', 0) or 0) + (p_data.get('other_fixed_income', 0) or 0)
    
    lista_emojis = ["📁", "💰", "🍔", "🏠", "🚗", "🛒", "🔌", "🎬", "🏥", "✈️", "👔", "🎓", "🎁", "🏋️", "🍹", "📱", "🐾", "💡", "🛠️", "🍕"]
    
    c1, c2 = st.columns([1, 2])
    emoji_sel = c1.selectbox("Emoji", lista_emojis)
    emoji_custom = c1.text_input("U otro...", value="")
    emoji_final = emoji_custom if emoji_custom else emoji_sel
    name = c2.text_input("Nombre")
    c_type = st.selectbox("Tipo", ["Gasto", "Ingreso"])
    
    # --- Lógica de Presupuesto Variable ---
    final_budget = 0.0
    b_type = "fixed"
    b_percent = 0.0

    if c_type == "Gasto":
        st.write("---")
        metodo = st.radio("Método de presupuesto", ["Cantidad Fija (€)", "Porcentaje (%)"], horizontal=True)
        
        if metodo == "Cantidad Fija (€)":
            final_budget = st.number_input("Presupuesto Mensual (€)", min_value=0.0, step=10.0)
            b_type = "fixed"
        else:
            b_percent = st.number_input("Porcentaje de ingresos (%)", min_value=0.0, max_value=100.0, step=1.0)
            # Cálculo dinámico
            final_budget = (ingresos_totales * b_percent) / 100
            st.info(f"💡 Equivale a **{final_budget:,.2f}€** mensuales.")
            b_type = "percentage"

    if st.button("Guardar"):
        if name:
            save_category({
                "user_id": user_id, 
                "name": name, 
                "type": c_type, 
                "budget": final_budget, 
                "emoji": emoji_final,
                "budget_type": b_type,
                "budget_percent": b_percent
            })
            st.rerun()

@st.dialog("✏️ Editar Categoría")
def editar_categoria_dialog(cat_data):
    p_data = st.session_state.user
    ingresos_totales = (p_data.get('base_salary', 0) or 0) + (p_data.get('other_fixed_income', 0) or 0)
    
    lista_emojis = ["📁", "💰", "🍔", "🏠", "🚗", "🛒", "🔌", "🎬", "🏥", "✈️", "👔", "🎓", "🎁", "🏋️", "🍹", "📱", "🐾", "💡", "🛠️", "🍕"]
    
    c1, c2 = st.columns([1, 2])
    try: idx = lista_emojis.index(cat_data.get('emoji', '📁'))
    except: idx = 0
    
    emoji_sel = c1.selectbox("Emoji", lista_emojis, index=idx)
    emoji_custom = c1.text_input("U otro...", value="")
    emoji_final = emoji_custom if emoji_custom else emoji_sel
    new_name = c2.text_input("Nombre", value=cat_data['name'])
    
    final_budget = 0.0
    b_type = cat_data.get('budget_type', 'fixed')
    b_percent = float(cat_data.get('budget_percent', 0.0))

    if cat_data['type'] == 'Gasto':
        st.write("---")
        idx_metodo = 0 if b_type == "fixed" else 1
        metodo = st.radio("Método de presupuesto", ["Cantidad Fija (€)", "Porcentaje (%)"], index=idx_metodo, horizontal=True)
        
        if metodo == "Cantidad Fija (€)":
            final_budget = st.number_input("Presupuesto Mensual (€)", value=float(cat_data['budget']), min_value=0.0)
            b_type = "fixed"
            b_percent = 0.0
        else:
            b_percent = st.number_input("Porcentaje (%)", value=b_percent, min_value=0.0, max_value=100.0)
            final_budget = (ingresos_totales * b_percent) / 100
            st.info(f"💡 Equivale a **{final_budget:,.2f}€** mensuales.")
            b_type = "percentage"

    if st.button("Actualizar Categoría"):
        if new_name:
            update_category(cat_data['id'], {
                "name": new_name, 
                "emoji": emoji_final, 
                "budget": final_budget,
                "budget_type": b_type,
                "budget_percent": b_percent
            })
            st.rerun()

@st.dialog("Editar Movimiento")
def editar_movimiento_dialog(mov_data, current_cats):
    # 1. Identificadores únicos
    m_id = str(mov_data.get('id', 'unknown'))
    u_id = str(mov_data.get('user_id', 'unknown'))
    c_grp = mov_data.get('group_id')
    
    # PREFIJO ÚNICO (DNI de los elementos de esta ventana)
    px = f"v_ed_{m_id}_"
    
    # 2. Cargar participantes previos si existían
    c_parts = get_expense_participants(m_id) if c_grp else []
    
    # --- LA MAGIA: Calculadora de devoluciones ---
    st.caption("Cálculo rápido (Ideal para devoluciones de ropa, compras a medias...)")
    col_q1, col_q2 = st.columns(2)
    
    base_qty = float(mov_data.get('quantity', 0.0))
    qty = col_q1.number_input("Cantidad base (€)", min_value=0.0, step=0.01, value=base_qty, key=f"{px}qty_base")
    devolucion = col_q2.number_input("📉 Restar devolución (€)", min_value=0.0, step=0.01, value=0.0, help="Pon aquí lo que te han devuelto", key=f"{px}qty_dev")
    
    # Cálculo en tiempo real de la cantidad final
    final_qty = qty - devolucion

    st.divider()
    
    # --- INTERFAZ DEL FORMULARIO ---
    t_idx = 0 if mov_data.get('type') == 'Gasto' else 1
    n_type = st.selectbox("Tipo", ["Gasto", "Ingreso"], index=t_idx, key=f"{px}type")
    
    try:
        f_dt = datetime.strptime(str(mov_data.get('date', datetime.now()))[:10], "%Y-%m-%d").date()
    except:
        f_dt = datetime.now().date()
        
    n_date = st.date_input("Fecha", f_dt, key=f"{px}date")
    
    f_cs = [c for c in current_cats if c.get('type') == n_type]
    n_cats = [f"{c.get('emoji', '📁')} {c['name']}" for c in f_cs]
    
    c_idx = 0
    for i, c in enumerate(f_cs):
        if str(c.get('id', '')) == str(mov_data.get('category_id', '')):
            c_idx = i
            break
            
    s_cat = st.selectbox("Categoría", n_cats, index=c_idx, key=f"{px}cat") if n_cats else None
    n_notes = st.text_input("Concepto", value=str(mov_data.get('notes', '')), key=f"{px}notes")

    # --- LÓGICA DE GRUPO ---
    new_g_id = None
    new_p_ids = []
    
    if n_type == "Gasto":
        st.divider()
        st.markdown("##### 👥 Gasto Compartido")
        mis_grupos = get_user_groups(u_id)
        
        if mis_grupos:
            opts_g = {g['name']: g['id'] for g in mis_grupos}
            names_g = ["No compartir"] + list(opts_g.keys())
            
            d_idx = 0
            if c_grp:
                for i, name in enumerate(opts_g.keys()):
                    if opts_g[name] == c_grp:
                        d_idx = i + 1
                        break
            
            s_grp = st.selectbox("¿Vincular a un grupo?", names_g, index=d_idx, key=f"{px}selgrp")
            
            if s_grp != "No compartir":
                new_g_id = opts_g[s_grp]
                m_list = get_group_members(new_g_id)
                
                st.write("Participantes:")
                cols = st.columns(3)
                for idx, m in enumerate(m_list):
                    prof = m.get('profiles') or {}
                    if isinstance(prof, list): prof = prof[0] if prof else {}
                    m_n = prof.get('name', 'Usuario')
                    
                    # Verificamos si ya participaba
                    checked = True
                    if new_g_id == c_grp and c_parts:
                        checked = m['user_id'] in c_parts
                        
                    with cols[idx % 3]:
                        if st.checkbox(m_n, value=checked, key=f"{px}chk_{m['user_id']}"):
                            new_p_ids.append(m['user_id'])
                
                if new_p_ids:
                    # Actualizamos la cuota visual para que muestre el cálculo sobre la CANTIDAD FINAL
                    st.info(f"Cuota a repartir: **{(final_qty/len(new_p_ids)):.2f}€** / pers.")

    # --- BOTÓN DE GUARDADO (¡SOLO UNO Y ÚNICO!) ---
    if st.button("Guardar Cambios", type="primary", use_container_width=True, key=f"{px}btn_save"):
        if final_qty <= 0 and qty > 0:
            st.error("⚠️ La cantidad final no puede ser cero o negativa. Revisa la resta.")
        elif s_cat:
            cat_obj = next(c for c in f_cs if f"{c.get('emoji', '📁')} {c['name']}" == s_cat)
            
            payload = {
                "user_id": u_id,
                "quantity": final_qty,  # <--- GUARDAMOS LA CANTIDAD YA RESTADA
                "type": n_type,
                "category_id": cat_obj['id'],
                "date": str(n_date),
                "notes": n_notes
            }
            
            ok, msg = update_shared_expense(m_id, payload, new_g_id, new_p_ids)
            
            if ok:
                if devolucion > 0:
                    st.toast(f"✅ Devolución aplicada. Nuevo total: {final_qty:.2f}€")
                else:
                    st.toast("✅ Gasto actualizado")
                time.sleep(1)
                st.rerun()
            else:
                st.error(f"Error: {msg}")
