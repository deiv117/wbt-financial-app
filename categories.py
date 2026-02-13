import streamlit as st
from database import delete_category
from components import editar_categoria_dialog, crear_categoria_dialog

def render_categories(current_cats):
    st.title("📂 Gestión de Categorías")
    if st.button("➕ Nueva Categoría"): crear_categoria_dialog(st.session_state.user['id'])
    
    ci, cg = st.columns(2)
    for col, t in zip([ci, cg], ["Ingreso", "Gasto"]):
        with col:
            st.subheader(f"{t}s")
            for c in [cat for cat in current_cats if cat.get('type') == t]:
                with st.container(border=True):
                    k1, k2 = st.columns([4, 1])
                    k1.write(f"**{c.get('emoji', '📁')} {c['name']}**")
                    if t == "Gasto": k1.caption(f"Meta: {c['budget']:.2f}€")
                    cb1, cb2 = k2.columns(2)
                    if cb1.button("✏️", key=f"cat_e_{c['id']}", use_container_width=True): editar_categoria_dialog(c)
                    if cb2.button("🗑️", key=f"cat_d_{c['id']}", use_container_width=True):
                        delete_category(c['id'])
                        st.rerun()
