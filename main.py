import streamlit as st
from supabase import create_client, Client
import pandas as pd
from datetime import datetime, timedelta
import io

# 1. CONEXIÓN SEGURA CON SUPABASE
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

st.set_page_config(page_title="Mis Gastos", page_icon="💰", layout="wide")
st.title("💰 Mi App de Gastos")

# --- CONTROL DE SESIÓN ---
if 'user' not in st.session_state:
    st.session_state.user = None

with st.sidebar:
    st.header("Acceso")
    if not st.session_state.user:
        email = st.text_input("Correo electrónico")
        password = st.text_input("Contraseña", type="password")
        if st.button("Entrar"):
            try:
                res = supabase.auth.sign_in_with_password({"email": email, "password": password})
                st.session_state.user = res.user
                st.rerun()
            except: st.error("Error de acceso")
    else:
        st.write(f"Conectado como: **{st.session_state.user.email}**")
        if st.button("Cerrar Sesión"):
            supabase.auth.sign_out()
            st.session_state.user = None
            st.rerun()

# --- FUNCIONES POP-UP (DIALOGS) ---
@st.dialog("➕ Crear Nueva Categoría")
def crear_categoria_dialog(current_cats):
    name = st.text_input("Nombre de categoría")
    c_type = st.selectbox("Tipo", ["Gasto", "Ingreso"])
    budget = 0.0
    if c_type == "Gasto":
        budget = st.number_input("Presupuesto Mensual (€)", min_value=0.0, step=10.0)
    
    if st.button("Guardar"):
        exists = any(c['name'].upper() == name.upper() and c.get('type') == c_type for c in current_cats)
        if exists:
            st.error("Ya existe esta categoría.")
        elif name:
            supabase.table("user_categories").insert({
                "user_id": st.session_state.user.id, 
                "name": name, "type": c_type, "budget": budget
            }).execute()
            st.rerun()

# --- CONTENIDO PRINCIPAL ---
if st.session_state.user:
    tab_gastos, tab_historial, tab_categorias, tab_prevision, tab_informes, tab_anual = st.tabs([
        "💸 Movimientos", "🗄️ Historial", "⚙️ Categorías", "🔮 Previsión", "📊 Mensual", "📅 Anual"
    ])

    # Carga de datos base
    res_cats = supabase.table("user_categories").select("*").execute()
    current_cats = sorted(res_cats.data, key=lambda x: x['name'].lower()) if res_cats.data else []
    
    inputs_res = supabase.table("user_imputs").select("*, user_categories(name)").execute()
    df_all = pd.DataFrame(inputs_res.data) if inputs_res.data else pd.DataFrame()
    if not df_all.empty:
        df_all['date'] = pd.to_datetime(df_all['date'])

    # --- PESTAÑA: MOVIMIENTOS ---
    with tab_gastos:
        st.subheader("Nuevo Registro")
        col_q, col_t, col_d = st.columns(3)
        qty = col_q.number_input("Cantidad (€)", min_value=0.0, step=0.01)
        t_type = col_t.selectbox("Tipo", ["Gasto", "Ingreso"])
        fecha_mov = col_d.date_input("Fecha", datetime.now())
        
        filtered_cats = [c for c in current_cats if c.get('type') == t_type]
        if filtered_cats:
            cat_list = [c['name'] for c in filtered_cats]
            sel_cat_name = st.selectbox("Categoría", options=["Selecciona..."] + cat_list)
            if st.button("Guardar Registro") and sel_cat_name != "Selecciona...":
                c_id = next(c['id'] for c in filtered_cats if c['name'] == sel_cat_name)
                supabase.table("user_imputs").insert({
                    "user_id": st.session_state.user.id, "quantity": qty, 
                    "type": t_type, "category_id": c_id, "date": str(fecha_mov)
                }).execute()
                st.success("¡Registrado!")
                st.rerun()
        
        st.divider()
        st.subheader("Últimos 20 movimientos")
        res_recent = supabase.table("user_imputs").select("*, user_categories(name)").order("date", desc=True).limit(20).execute()
        if res_recent.data:
            for i in res_recent.data:
                c1, c2, c3, c4 = st.columns([2, 1, 1, 1])
                c1.write(f"**{i['date']}** | {i['user_categories']['name'] if i['user_categories'] else 'S/C'}")
                c2.write(f"{i['quantity']:.2f}€")
                c3.write("📉 Gasto" if i['type'] == "Gasto" else "📈 Ingreso")
                if c4.button("🗑️", key=f"del_rec_{i['id']}"):
                    supabase.table("user_imputs").delete().eq("id", i['id']).execute()
                    st.rerun()

    # --- PESTAÑA: HISTORIAL E IMPORTACIÓN ---
    with tab_historial:
        st.subheader("🗄️ Historial Completo")
        col_h1, col_h2, col_h3 = st.columns(3)
        f_inicio = col_h1.date_input("Desde", datetime.now() - timedelta(days=30))
        f_fin = col_h2.date_input("Hasta", datetime.now())
        f_tipo = col_h3.selectbox("Tipo de movimiento", ["Todos", "Gasto", "Ingreso"])

        if not df_all.empty:
            df_h = df_all[(df_all['date'].dt.date >= f_inicio) & (df_all['date'].dt.date <= f_fin)]
            if f_tipo != "Todos":
                df_h = df_h[df_h['type'] == f_tipo]
            
            if not df_h.empty:
                items_per_page = 50
                total_p = max(1, (len(df_h) // items_per_page) + (1 if len(df_h) % items_per_page > 0 else 0))
                page = st.number_input("Página", min_value=1, max_value=total_p, step=1)
                
                start = (page - 1) * items_per_page
                df_pag = df_h.iloc[start : start + items_per_page].copy()
                df_pag['Categoría'] = df_pag['user_categories'].apply(lambda x: x['name'] if x else 'S/C')
                df_pag['Fecha'] = df_pag['date'].dt.strftime('%Y-%m-%d')
                st.dataframe(df_pag[['Fecha', 'Categoría', 'quantity', 'type']].rename(columns={'quantity': 'Importe (€)'}), use_container_width=True, hide_index=True)
            else: st.info("No hay datos para estos filtros.")
        
        st.divider()
        # --- SECCIÓN IMPORTACIÓN CSV ---
        with st.expander("📥 Importación Masiva desde CSV"):
            st.markdown("""
            **Instrucciones:** El archivo debe tener las columnas: `fecha`, `cantidad`, `tipo` (Gasto/Ingreso) y `categoria`.
            """)
            uploaded_file = st.file_uploader("Subir archivo CSV", type=["csv"])
            
            if uploaded_file:
                try:
                    df_import = pd.read_csv(uploaded_file)
                    st.write("Vista previa de los datos a importar:")
                    st.dataframe(df_import.head())
                    
                    if st.button("Confirmar Importación"):
                        success_count = 0
                        error_count = 0
                        
                        # Mapeo de nombres a IDs para evitar consultas constantes
                        cat_map = {c['name'].upper(): (c['id'], c['type']) for c in current_cats}
                        
                        rows_to_insert = []
                        for _, row in df_import.iterrows():
                            cat_name_up = str(row['categoria']).upper()
                            if cat_name_up in cat_map:
                                c_id, c_type = cat_map[cat_name_up]
                                rows_to_insert.append({
                                    "user_id": st.session_state.user.id,
                                    "quantity": float(row['cantidad']),
                                    "type": c_type,
                                    "category_id": c_id,
                                    "date": str(row['fecha'])
                                })
                                success_count += 1
                            else:
                                error_count += 1
                        
                        if rows_to_insert:
                            supabase.table("user_imputs").insert(rows_to_insert).execute()
                            st.success(f"¡Éxito! Se han importado {success_count} registros.")
                            if error_count > 0:
                                st.warning(f"Se saltaron {error_count} filas porque la categoría no existe en la app.")
                            st.rerun()
                except Exception as e:
                    st.error(f"Error al procesar el archivo: {e}")

    # --- PESTAÑA: CATEGORÍAS ---
    with tab_categorias:
        st.subheader("Gestión de Categorías")
        if st.button("➕ Añadir Categoría"): crear_categoria_dialog(current_cats)
        st.divider()
        col_c1, col_c2 = st.columns(2)
        
        for idx, (col, t) in enumerate(zip([col_c1, col_c2], ["Ingreso", "Gasto"])):
            with col:
                st.markdown(f"### {'📈' if t=='Ingreso' else '📉'} {t}s")
                for c in [cat for cat in current_cats if cat.get('type') == t]:
                    with st.container(border=True):
                        st.write(f"**{c['name']}**")
                        if t == "Gasto": st.caption(f"Presupuesto: {c['budget']:.2f}€")
                        b1, b2 = st.columns(2)
                        if b1.button("📝", key=f"edit_{c['id']}"): st.session_state[f"ed_mode_{c['id']}"] = True
                        if b2.button("🗑️", key=f"del_cat_{c['id']}"):
                            supabase.table("user_categories").delete().eq("id", c['id']).execute()
                            st.rerun()
                        
                        if st.session_state.get(f"ed_mode_{c['id']}", False):
                            with st.form(f"f_ed_{c['id']}"):
                                n_name = st.text_input("Nombre", value=c['name'])
                                n_budget = st.number_input("Presupuesto", value=float(c['budget'])) if t == "Gasto" else 0.0
                                if st.form_submit_button("Actualizar"):
                                    supabase.table("user_categories").update({"name": n_name, "budget": n_budget}).eq("id", c['id']).execute()
                                    st.session_state[f"ed_mode_{c['id']}"] = False
                                    st.rerun()

    # --- PESTAÑA: PREVISIÓN ---
    with tab_prevision:
        st.subheader("🔮 Previsión Mensual Teórica")
        cat_g = [c for c in current_cats if c.get('type') == 'Gasto']
        total_p = sum(c['budget'] for c in cat_g)
        media_i = df_all[df_all['type']=='Ingreso'].groupby(df_all['date'].dt.to_period('M'))['quantity'].sum().mean() if not df_all.empty else 0
        
        with st.container(border=True):
            m1, m2, m3 = st.columns(3)
            m1.metric("Gasto Presupuestado", f"{total_p:.2f}€")
            m2.metric("Media Ingresos Reales", f"{media_i:.2f}€")
            m3.metric("Ahorro Potencial", f"{(media_i - total_p):.2f}€")
        
        st.divider()
        if cat_g:
            col_g1, col_g2 = st.columns(2)
            with col_g1:
                st.plotly_chart(px.pie(pd.DataFrame(cat_g), values='budget', names='name', hole=0.4, title="Reparto de Presupuestos"), use_container_width=True)
            with col_g2:
                df_p_table = pd.DataFrame(cat_g)[['name', 'budget']]
                df_p_table.columns = ['Categoría', 'Presupuesto']
                df_p_table['Presupuesto'] = df_p_table['Presupuesto'].map('{:.2f}€'.format)
                st.dataframe(df_p_table, hide_index=True, use_container_width=True)

    # --- PESTAÑA: MENSUAL ---
    with tab_informes:
        st.subheader("Resumen Mensual")
        col_m1, col_m2 = st.columns(2)
        meses = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
        sel_m = col_m1.selectbox("Mes", meses, index=datetime.now().month-1)
        sel_a = col_m2.selectbox("Año", range(datetime.now().year-2, datetime.now().year+1), index=2)
        
        if not df_all.empty:
            df_m = df_all[(df_all['date'].dt.month == meses.index(sel_m)+1) & (df_all['date'].dt.year == sel_a)]
            if not df_m.empty:
                i_m = df_m[df_m['type'] == 'Ingreso']['quantity'].sum()
                g_m = df_m[df_m['type'] == 'Gasto']['quantity'].sum()
                
                with st.container(border=True):
                    c1, c2, c3 = st.columns(3)
                    c1.metric("Ingresos", f"{i_m:.2f}€")
                    c2.metric("Gastos", f"{g_m:.2f}€")
                    c3.metric("Ahorro", f"{(i_m - g_m):.2f}€")
                
                st.divider()
                st.subheader("Semáforo de Gastos")
                g_cat_m = df_m[df_m['type'] == 'Gasto'].groupby('category_id')['quantity'].sum().reset_index()
                cat_g_list = [c for c in current_cats if c.get('type') == 'Gasto']
                if cat_g_list:
                    rep_m = pd.merge(pd.DataFrame(cat_g_list), g_cat_m, left_on='id', right_on='category_id', how='left').fillna(0)
                    for _, r in rep_m.iterrows():
                        porc = r['quantity'] / r['budget'] if r['budget'] > 0 else 0
                        color = "🟢" if porc < 0.8 else "🟡" if porc <= 1.0 else "🔴"
                        st.write(f"{color} **{r['name']}**: {r['quantity']:.2f}€ / {r['budget']:.2f}€")
                        st.progress(min(porc, 1.0))
            else: st.info("Sin datos para este periodo.")

    # --- PESTAÑA: ANUAL ---
    with tab_anual:
        st.subheader("Resumen Anual")
        sel_an = st.selectbox("Año Seleccionado", range(datetime.now().year-2, datetime.now().year+1), index=2)
        if not df_all.empty:
            df_an = df_all[df_all['date'].dt.year == sel_an]
            if not df_an.empty:
                i_an = df_an[df_an['type'] == 'Ingreso']['quantity'].sum()
                g_an = df_an[df_an['type'] == 'Gasto']['quantity'].sum()
                
                with st.container(border=True):
                    ca1, ca2, ca3 = st.columns(3)
                    ca1.metric("Ingresos", f"{i_an:.2f}€")
                    ca2.metric("Gastos", f"{g_an:.2f}€")
                    ca3.metric("Balance", f"{(i_an - g_an):.2f}€")
                
                st.divider()
                st.subheader("Control Anual (Meta x12)")
                g_cat_an = df_an[df_an['type'] == 'Gasto'].groupby('category_id')['quantity'].sum().reset_index()
                cat_g_an = [c for c in current_cats if c.get('type') == 'Gasto']
                if cat_g_an:
                    rep_an = pd.merge(pd.DataFrame(cat_g_an), g_cat_an, left_on='id', right_on='category_id', how='left').fillna(0)
                    for _, r in rep_an.iterrows():
                        b_an = r['budget'] * 12
                        porc_an = r['quantity'] / b_an if b_an > 0 else 0
                        color_an = "🟢" if porc_an < 0.8 else "🟡" if porc_an <= 1.0 else "🔴"
                        st.write(f"{color_an} **{r['name']}**: {r['quantity']:.2f}€ / {b_an:.2f}€")
                        st.progress(min(porc_an, 1.0))
            else: st.info("No hay datos registrados para este año.")
else:
    st.info("Inicia sesión para continuar.")
