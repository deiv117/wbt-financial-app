import streamlit as st
from supabase import create_client, Client
import pandas as pd
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go

# 1. CONEXIÓN SEGURA CON SUPABASE
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

st.set_page_config(page_title="Mis Gastos", page_icon="💰", layout="wide")

# --- CONTROL DE SESIÓN ---
if 'user' not in st.session_state:
    st.session_state.user = None

# --- SIDEBAR (MENÚ LATERAL) ---
with st.sidebar:
    st.header("💰 Mi App de Gastos")
    
    if not st.session_state.user:
        email = st.text_input("Correo electrónico")
        password = st.text_input("Contraseña", type="password")
        if st.button("Entrar"):
            try:
                res = supabase.auth.sign_in_with_password({"email": email, "password": password})
                st.session_state.user = res.user
                st.rerun()
            except: st.error("Error de acceso")
        menu_opcion = "📊 Cuadro de Mando"
    else:
        # CONSULTA SEGURA DEL PERFIL PARA EL SALUDO
        res_p = supabase.table("profiles").select("name").eq("id", st.session_state.user.id).maybe_single().execute()
        p_sidebar = res_p.data if (hasattr(res_p, 'data') and res_p.data) else {}
        nombre_user = p_sidebar.get('name') if p_sidebar.get('name') else st.session_state.user.email
        
        st.write(f"Hola, **{nombre_user}** 👋")
        
        st.divider()
        menu_opcion = st.radio("Navegación", ["📊 Cuadro de Mando", "⚙️ Perfil"])
        st.divider()
        
        # IMPORTACIÓN CSV (Mantenida en sidebar por utilidad)
        st.subheader("📥 Importar Datos")
        template_data = "fecha,cantidad,categoria\n2026-02-12,15.50,Alimentacion"
        st.download_button(label="📄 Plantilla CSV", data=template_data, file_name="plantilla.csv", mime="text/csv")
        uploaded_file = st.file_uploader("Subir CSV", type=["csv"])
        if uploaded_file and st.button("🚀 Importar"):
            try:
                df_imp = pd.read_csv(uploaded_file)
                res_c = supabase.table("user_categories").select("*").execute()
                cat_map = {c['name'].upper(): (c['id'], c['type']) for c in res_c.data}
                rows = []
                for _, row in df_imp.iterrows():
                    c_up = str(row['categoria']).upper()
                    if c_up in cat_map:
                        c_id, c_type = cat_map[c_up]
                        rows.append({"user_id": st.session_state.user.id, "quantity": float(row['cantidad']), "type": c_type, "category_id": c_id, "date": str(row['fecha'])})
                if rows:
                    supabase.table("user_imputs").insert(rows).execute()
                    st.success(f"¡{len(rows)} registros importados!")
                    st.rerun()
            except: st.error("Error al procesar archivo")

        if st.button("Cerrar Sesión"):
            supabase.auth.sign_out()
            st.session_state.user = None
            st.rerun()

# --- FUNCIONES DIALOG ---
@st.dialog("➕ Nueva Categoría")
def crear_categoria_dialog():
    name = st.text_input("Nombre")
    c_type = st.selectbox("Tipo", ["Gasto", "Ingreso"])
    budget = st.number_input("Presupuesto Mensual (€)", min_value=0.0) if c_type == "Gasto" else 0.0
    if st.button("Guardar"):
        if name:
            supabase.table("user_categories").insert({"user_id": st.session_state.user.id, "name": name, "type": c_type, "budget": budget}).execute()
            st.rerun()

# --- LÓGICA DE CONTENIDO ---
if st.session_state.user:
    
    # 1. PÁGINA PERFIL
    if menu_opcion == "⚙️ Perfil":
        st.title("⚙️ Configuración de Perfil")
        p_res = supabase.table("profiles").select("*").eq("id", st.session_state.user.id).maybe_single().execute()
        p_data = p_res.data if (hasattr(p_res, 'data') and p_res.data) else {}
        
        col_p1, col_p2 = st.columns([1, 2])
        with col_p1:
            if p_data.get('avatar_url'): st.image(p_data['avatar_url'], width=150)
            else: st.info("Sin foto configurada")
            new_avatar = st.text_input("URL Avatar", value=p_data.get('avatar_url', ""))
        with col_p2:
            with st.form("perfil_form"):
                n_name = st.text_input("Nombre", value=p_data.get('name', ""))
                n_lastname = st.text_input("Apellido", value=p_data.get('lastname', ""))
                n_social = st.toggle("Elegible para gastos en grupo", value=p_data.get('social_active', False))
                if st.form_submit_button("Actualizar Perfil"):
                    payload = {"id": st.session_state.user.id, "name": n_name, "lastname": n_lastname, "avatar_url": new_avatar, "social_active": n_social, "updated_at": str(datetime.now())}
                    supabase.table("profiles").upsert(payload).execute()
                    st.success("¡Perfil actualizado!")
                    st.rerun()

    # 2. PÁGINA CUADRO DE MANDO
    else:
        st.title("📊 Panel de Control")
        tab_gastos, tab_historial, tab_categorias, tab_prevision, tab_informes, tab_anual = st.tabs([
            "💸 Movimientos", "🗄️ Historial", "⚙️ Categorías", "🔮 Previsión", "📊 Mensual", "📅 Anual"
        ])

        # Carga de datos global
        res_cats = supabase.table("user_categories").select("*").execute()
        current_cats = sorted(res_cats.data, key=lambda x: x['name'].lower()) if res_cats.data else []
        res_all = supabase.table("user_imputs").select("*, user_categories(name)").execute()
        df_all = pd.DataFrame(res_all.data) if res_all.data else pd.DataFrame()
        if not df_all.empty: df_all['date'] = pd.to_datetime(df_all['date'])
        cat_g = [c for c in current_cats if c.get('type') == 'Gasto']

        # --- TAB: MOVIMIENTOS ---
        with tab_gastos:
            st.subheader("Nuevo Registro")
            c1, c2, c3 = st.columns(3)
            qty = c1.number_input("Cantidad (€)", min_value=0.0, step=0.01)
            t_type = c2.selectbox("Tipo", ["Gasto", "Ingreso"])
            f_mov = c3.date_input("Fecha", datetime.now())
            f_cats = [c for c in current_cats if c.get('type') == t_type]
            if f_cats:
                sel_cat = st.selectbox("Categoría", options=["Selecciona..."] + [c['name'] for c in f_cats])
                if st.button("Guardar") and sel_cat != "Selecciona...":
                    c_id = next(c['id'] for c in f_cats if c['name'] == sel_cat)
                    supabase.table("user_imputs").insert({"user_id": st.session_state.user.id, "quantity": qty, "type": t_type, "category_id": c_id, "date": str(f_mov)}).execute()
                    st.rerun()
            st.divider()
            res_recent = supabase.table("user_imputs").select("*, user_categories(name)").order("date", desc=True).limit(20).execute()
            for i in (res_recent.data if res_recent.data else []):
                cl1, cl2, cl3, cl4 = st.columns([2, 1, 1, 1])
                cl1.write(f"**{i['date']}** | {i['user_categories']['name'] if i['user_categories'] else 'S/C'}")
                cl2.write(f"{i['quantity']:.2f}€")
                cl3.write("📉" if i['type'] == "Gasto" else "📈")
                if cl4.button("🗑️", key=f"del_{i['id']}"):
                    supabase.table("user_imputs").delete().eq("id", i['id']).execute()
                    st.rerun()

        # --- TAB: HISTORIAL ---
        with tab_historial:
            st.subheader("🗄️ Historial Completo")
            h1, h2, h3 = st.columns(3)
            f_i, f_f = h1.date_input("Desde", datetime.now()-timedelta(days=30)), h2.date_input("Hasta", datetime.now())
            f_t = h3.selectbox("Filtrar por", ["Todos", "Gasto", "Ingreso"])
            if not df_all.empty:
                df_h = df_all[(df_all['date'].dt.date >= f_i) & (df_all['date'].dt.date <= f_f)]
                if f_t != "Todos": df_h = df_h[df_h['type'] == f_t]
                if not df_h.empty:
                    page = st.number_input("Página", min_value=1, value=1)
                    start = (page-1)*50
                    df_p = df_h.iloc[start:start+50].copy()
                    df_p['Categoría'] = df_p['user_categories'].apply(lambda x: x['name'] if x else 'S/C')
                    st.dataframe(df_p[['date', 'Categoría', 'quantity', 'type']].rename(columns={'quantity':'Importe (€)'}), use_container_width=True, hide_index=True)

        # --- TAB: CATEGORÍAS ---
        with tab_categorias:
            if st.button("➕ Añadir Categoría"): crear_categoria_dialog()
            c_ing, c_gas = st.columns(2)
            for col, t in zip([c_ing, c_gas], ["Ingreso", "Gasto"]):
                with col:
                    st.markdown(f"### {t}s")
                    for c in [cat for cat in current_cats if cat.get('type') == t]:
                        with st.container(border=True):
                            st.write(f"**{c['name']}**")
                            if t == "Gasto": st.caption(f"Presupuesto: {c['budget']:.2f}€")
                            if st.button("🗑️", key=f"dc_{c['id']}"):
                                supabase.table("user_categories").delete().eq("id", c['id']).execute()
                                st.rerun()

        # --- TAB: PREVISIÓN ---
        with tab_prevision:
            st.subheader("🔮 Previsión Mensual Teórica")
            total_p = sum(c['budget'] for c in cat_g)
            media_i = df_all[df_all['type']=='Ingreso'].groupby(df_all['date'].dt.to_period('M'))['quantity'].sum().mean() if not df_all.empty else 0
            with st.container(border=True):
                m1, m2, m3 = st.columns(3)
                m1.metric("Gasto Presupuestado", f"{total_p:.2f}€")
                m2.metric("Media Ingresos", f"{media_i:.2f}€")
                m3.metric("Ahorro Potencial", f"{(media_i - total_p):.2f}€")
            st.divider()
            if cat_g:
                col_g1, col_g2 = st.columns(2)
                with col_g1: st.plotly_chart(px.pie(pd.DataFrame(cat_g), values='budget', names='name', hole=0.4, title="Reparto de Gastos"), use_container_width=True)
                with col_g2:
                    df_prev_tab = pd.DataFrame(cat_g)[['name', 'budget']].rename(columns={'name':'Categoría','budget':'Presupuesto'})
                    df_prev_tab['Presupuesto'] = df_prev_tab['Presupuesto'].map('{:.2f}€'.format)
                    st.dataframe(df_prev_tab, hide_index=True, use_container_width=True)

        # --- TAB: MENSUAL ---
        with tab_informes:
            st.subheader("Resumen Mensual")
            im1, im2 = st.columns(2)
            meses_lista = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
            s_m, s_a = im1.selectbox("Mes", meses_lista, index=datetime.now().month-1), im2.selectbox("Año ", range(2024, 2030), index=datetime.now().year-2024)
            if not df_all.empty:
                df_m = df_all[(df_all['date'].dt.month == meses_lista.index(s_m)+1) & (df_all['date'].dt.year == s_a)]
                if not df_m.empty:
                    i_m, g_m = df_m[df_m['type'] == 'Ingreso']['quantity'].sum(), df_m[df_m['type'] == 'Gasto']['quantity'].sum()
                    with st.container(border=True):
                        c1, c2, c3 = st.columns(3)
                        c1.metric("Ingresos", f"{i_m:.2f}€")
                        c2.metric("Gastos", f"{g_m:.2f}€")
                        c3.metric("Ahorro", f"{(i_m - g_m):.2f}€")
                    st.divider()
                    st.subheader("Semáforo de Gastos")
                    g_cat_m = df_m[df_m['type'] == 'Gasto'].groupby('category_id')['quantity'].sum().reset_index()
                    for _, r in pd.merge(pd.DataFrame(cat_g), g_cat_m, left_on='id', right_on='category_id', how='left').fillna(0).iterrows():
                        p = r['quantity'] / r['budget'] if r['budget'] > 0 else 0
                        st.write(f"{'🟢' if p < 0.8 else '🟡' if p <= 1.0 else '🔴'} **{r['name']}**: {r['quantity']:.2f}€ / {r['budget']:.2f}€")
                        st.progress(min(p, 1.0))

        # --- TAB: ANUAL ---
        with tab_anual:
            st.subheader("Resumen Anual")
            s_an = st.selectbox("Seleccionar Año", range(2024, 2030), index=datetime.now().year-2024)
            if not df_all.empty:
                df_an = df_all[df_all['date'].dt.year == s_an]
                if not df_an.empty:
                    i_an, g_an = df_an[df_an['type'] == 'Ingreso']['quantity'].sum(), df_an[df_an['type'] == 'Gasto']['quantity'].sum()
                    with st.container(border=True):
                        ca1, ca2, ca3 = st.columns(3)
                        ca1.metric("Ingresos Anuales", f"{i_an:.2f}€")
                        ca2.metric("Gastos Anuales", f"{g_an:.2f}€")
                        ca3.metric("Balance Total", f"{(i_an - g_an):.2f}€")
                    st.divider()
                    # Gráfica mixta
                    df_evo = df_an.copy()
                    df_evo['mes_num'] = df_evo['date'].dt.month
                    res_mes = df_evo.pivot_table(index='mes_num', columns='type', values='quantity', aggfunc='sum').fillna(0)
                    for t in ['Ingreso', 'Gasto']: 
                        if t not in res_mes.columns: res_mes[t] = 0
                    res_mes['Ahorro'] = res_mes['Ingreso'] - res_mes['Gasto']
                    res_mes = res_mes.reindex(range(1, 13), fill_value=0)
                    fig = go.Figure()
                    fig.add_trace(go.Bar(x=meses_lista, y=res_mes['Ingreso'], name='Ingreso', marker_color='#00CC96'))
                    fig.add_trace(go.Bar(x=meses_lista, y=res_mes['Gasto'], name='Gasto', marker_color='#EF553B'))
                    fig.add_trace(go.Scatter(x=meses_lista, y=res_mes['Ahorro'], name='Ahorro Neto', line=dict(color='#636EFA', width=4)))
                    fig.update_layout(barmode='group', height=400)
                    st.plotly_chart(fig, use_container_width=True)
                    st.divider()
                    st.subheader("Control Anual (Meta x12)")
                    g_cat_an = df_an[df_an['type'] == 'Gasto'].groupby('category_id')['quantity'].sum().reset_index()
                    for _, r in pd.merge(pd.DataFrame(cat_g), g_cat_an, left_on='id', right_on='category_id', how='left').fillna(0).iterrows():
                        b_an, p_an = r['budget'] * 12, r['quantity'] / (r['budget']*12) if r['budget'] > 0 else 0
                        st.write(f"{'🟢' if p_an < 0.8 else '🟡' if p_an <= 1 else '🔴'} **{r['name']}**: {r['quantity']:.2f}€ / {b_an:.2f}€")
                        st.progress(min(p_an, 1.0))

else:
    st.info("Inicia sesión en el panel lateral para empezar.")
