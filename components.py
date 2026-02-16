import streamlit as st
import pandas as pd
import time
from datetime import datetime
from database import update_input
# ¡Añadimos las herramientas de grupo que necesitamos!
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
    # Metemos los imports dentro para asegurar que no falte ninguno en tu archivo
    import streamlit as st
    import time
    from datetime import datetime
    from database_groups import get_user_groups, get_group_members, update_shared_expense, get_expense_participants
    
    # Extracción segura de datos iniciales
    mov_id = mov_data.get('id')
    user_id = mov_data.get('user_id')
    current_group = mov_data.get('group_id')
    
    current_participants = get_expense_participants(mov_id) if current_group else []
    
    n_qty = st.number_input("Cantidad (€)", value=float(mov_data.get('quantity', 0.0)), min_value=0.0, step=0.01)
    
    t_index = 0 if mov_data.get('type') == 'Gasto' else 1
    n_type = st.selectbox("Tipo", ["Gasto", "Ingreso"], index=t_index)
    
    try:
        f_date = datetime.strptime(str(mov_data.get('date', datetime.now()))[:10], "%Y-%m-%d").date()
    except:
        f_date = datetime.now().date()
        
    n_date = st.date_input("Fecha", f_date)
    
    f_cs = [c for c in current_cats if c.get('type') == n_type]
    nombres_cats = [f"{c.get('emoji', '📁')} {c['name']}" for c in f_cs]
    
    c_idx = 0
    for i, c in enumerate(f_cs):
        if str(c.get('id', '')) == str(mov_data.get('category_id', '')):
            c_idx = i
            break
            
    # Línea blindada contra errores
    if nombres_cats and c_idx < len(nombres_cats):
        sel_cat = st.selectbox("Categoría", nombres_cats, index=c_idx)
    else:
        sel_cat = st.selectbox("Categoría", nombres_cats) if nombres_cats else None
        
    n_notes = st.text_input("Concepto", value=str(mov_data.get('notes', '')))

    # --- EDICIÓN DE GASTO COMPARTIDO ---
    new_shared_group_id = None
    new_participantes_ids = []
    
    if n_type == "Gasto":
        st.divider()
        st.markdown("##### 👥 Gasto Compartido")
        mis_grupos = get_user_groups(user_id)
        
        if mis_grupos:
            opciones_grupos = {g['name']: g['id'] for g in mis_grupos}
            nombres_grupos = ["No compartir"] + list(opciones_grupos.keys())
            
            # Pre-seleccionar el grupo si ya existía
            def_index = 0
            if current_group:
                for i, g_name in enumerate(opciones_grupos.keys()):
                    if opciones_grupos[g_name] == current_group:
                        def_index = i + 1
                        break
            
            sel_grupo = st.selectbox("¿Vincular a un grupo?", nombres_grupos, index=def_index)
            
            if sel_grupo != "No compartir":
                new_shared_group_id = opciones_grupos[sel_grupo]
                miembros = get_group_members(new_shared_group_id)
                
                st.write("Selecciona quién participa en este gasto:")
                cols_miembros = st.columns(3)
                for idx, m in enumerate(miembros):
                    prof = m.get('profiles') or {}
                    if isinstance(prof, list): prof = prof[0] if prof else {}
                    m_nombre = prof.get('name', 'Usuario')
                    
                    is_checked = True
                    if new_shared_group_id == current_group and current_participants:
                        is_checked = m['user_id'] in current_participants
                        
                    with cols_miembros[idx % 3]:
                        if st.checkbox(f"{m_nombre}", value=is_checked, key=f"edit_p_{m['user_id']}"):
                            new_participantes_ids.append(m['user_id'])
                
                if new_participantes_ids:
                    cuota = n_qty / len(new_participantes_ids)
                    st.info(f"Reparto: **{cuota:.2f}€** por persona")
    
    # --- GUARDAR Y ACTUALIZAR ---
    if st.button("Guardar Cambios", type="primary", use_container_width=True):
        if sel_cat:
            cat_obj = next(c for c in f_cs if f"{c.get('emoji', '📁')} {c['name']}" == sel_cat)
            
            new_mov_data = {
                "user_id": user_id,
                "quantity": n_qty,
                "type": n_type,
                "category_id": cat_obj['id'],
                "date": str(n_date),
                "notes": n_notes
            }
            
            ok, msg = update_shared_expense(mov_id, new_mov_data, new_shared_group_id, new_participantes_ids)
            
            if ok:
                st.toast("✅ Gasto actualizado correctamente")
                time.sleep(1)
                st.rerun()
            else:
                st.error(f"Error: {msg}")
            
    # --- GUARDAR Y ACTUALIZAR ---
    if st.button("Guardar Cambios", type="primary", use_container_width=True):
        if sel_cat:
            cat_obj = next(c for c in f_cs if f"{c.get('emoji', '📁')} {c['name']}" == sel_cat)
            
            new_mov_data = {
                "user_id": mov_data['user_id'],
                "quantity": n_qty,
                "type": n_type,
                "category_id": cat_obj['id'],
                "date": str(n_date),
                "notes": n_notes
            }
            
            # Usamos nuestra super-función que hace todo a la vez
            ok, msg = update_shared_expense(mov_data['id'], new_mov_data, new_shared_group_id, new_participantes_ids)
            
            if ok:
                st.toast("✅ Gasto actualizado correctamente")
                time.sleep(1)
                st.rerun()
            else:
                st.error(f"Error: {msg}")
