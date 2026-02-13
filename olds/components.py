import streamlit as st
import pandas as pd
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

@st.dialog("✏️ Editar Movimiento")
def editar_movimiento_dialog(mov_data, categorias_disponibles):
    st.subheader("Modificar Registro")
    c1, c2 = st.columns(2)
    n_qty = c1.number_input("Cantidad (€)", value=float(mov_data['quantity']), min_value=0.0, step=0.01)
    n_date = c2.date_input("Fecha", value=pd.to_datetime(mov_data['date']).date())
    n_type = st.selectbox("Tipo", ["Gasto", "Ingreso"], index=0 if mov_data['type'] == 'Gasto' else 1)
    
    f_cs = [c for c in categorias_disponibles if c['type'] == n_type]
    opciones = [f"{c.get('emoji', '📁')} {c['name']}" for c in f_cs]
    
    # Intento de encontrar el índice de la categoría actual
    try:
        # Si la estructura viene de un join de Supabase
        if 'user_categories' in mov_data:
            cat_actual_str = f"{mov_data['user_categories']['emoji']} {mov_data['user_categories']['name']}"
        else:
            # Si viene del DataFrame aplanado que creamos en get_transactions
            cat_actual_str = f"{mov_data['cat_emoji']} {mov_data['cat_name']}"
        idx_cat = opciones.index(cat_actual_str)
    except:
        idx_cat = 0
        
    n_sel_cat = st.selectbox("Categoría", opciones, index=idx_cat)
    n_notes = st.text_input("Concepto", value=str(mov_data.get('notes') or ''))
    
    if st.button("Guardar Cambios"):
        cat_obj = next(c for c in f_cs if f"{c.get('emoji', '📁')} {c['name']}" == n_sel_cat)
        update_input(mov_data['id'], {
            "quantity": n_qty, 
            "date": str(n_date), 
            "type": n_type,
            "category_id": cat_obj['id'], 
            "notes": n_notes
        })
        st.rerun()
