import streamlit as st
from supabase import create_client, Client
import pandas as pd
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go
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

# --- SIDEBAR (MENÚ LATERAL) ---
with st.sidebar:
    st.header("👤 Usuario")
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
        st.write(f"Conectado: **{st.session_state.user.email}**")
        if st.button("Cerrar Sesión"):
            supabase.auth.sign_out()
            st.session_state.user = None
            st.rerun()
        
        st.divider()
        st.header("📥 Importación CSV")
        template_data = "fecha,cantidad,categoria\n2026-02-11,15.50,Alimentacion\n2026-02-12,500.00,Nomina"
        st.download_button(label="📄 Descargar Plantilla CSV", data=template_data, file_name="plantilla.csv", mime="text/csv")
        
        uploaded_file = st.file_uploader("Subir CSV", type=["csv"])
        if uploaded_file and st.button("🚀 Confirmar Importación"):
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
            except: st.error("Error al procesar")

# --- FUNCIONES ---
@st.dialog("➕ Nueva Categoría")
def crear_categoria_dialog(current_cats):
    name = st.text_input("Nombre")
    c_type = st.selectbox("Tipo", ["Gasto", "Ingreso"])
    budget = st.number_input("Presupuesto Mensual (€)", min_value=0.0) if c_type == "Gasto" else 0.0
    if st.button("Guardar"):
        if name:
            supabase.table("user_categories").insert({"user_id": st.session_state.user.id, "name": name, "type": c_type, "budget": budget}).execute()
            st.rerun()

# --- CARGA DE DATOS ---
if st.session_state.user:
    tab_gastos, tab_historial, tab_categorias, tab_prevision, tab_informes, tab_anual = st.tabs([
        "💸 Movimientos", "🗄️ Historial", "⚙️ Categorías", "🔮 Previsión", "📊 Mensual", "📅 Anual"
    ])

    res_cats = supabase.table("user_categories").select("*").execute()
    current_cats = sorted(res_cats.data, key=lambda x: x['name'].lower()) if res_cats.data else []
    res_all = supabase.table("user_imputs").select("*, user_categories(name)").execute()
    df_all = pd.DataFrame(res_all.data) if res_all.data else pd.DataFrame()
    if not df_all.empty: df_all['date'] = pd.to_datetime(df_all['date'])

    # 1. MOVIMIENTOS
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
        st.subheader("Últimos 20 movimientos")
        res_r = supabase.table("user_imputs").select("*, user_categories(name)").order("date", desc=True).limit(20).execute()
        for i in (res_r.data if res_r.data else []):
            col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
            col1.write(f"**{i['date']}** | {i['user_categories']['name'] if i['user_categories'] else 'S/C'}")
            col2.write(f"{i['quantity']:.2f}€")
            col3.write("📉" if i['type'] == "Gasto" else "📈")
            if col4.button("🗑️", key=f"del_{i['id']}"):
                supabase.table("user_imputs").delete().eq("id", i['id']).execute()
                st.rerun()

    # 2. HISTORIAL
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

    # 3. CATEGORÍAS
    with tab_categorias:
        if st.button("➕ Añadir Categoría"): crear_categoria_dialog(current_cats)
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

    # 4. PREVISIÓN
    with tab_prevision:
        st.subheader("🔮 Previsión Mensual Teórica")
        cat_g = [c for c in current_cats if c.get('type') == 'Gasto']
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
            with col_g1:
                st.plotly_chart(px.pie(pd.DataFrame(cat_g), values='budget', names='name', hole=0.4, title="Reparto de Gastos Previstos"), use_container_width=True)
            with col_g2:
                st.write("**Detalle de Presupuestos**")
                df_prev_tab = pd.DataFrame(cat_g)[['name', 'budget']]
                df_prev_tab.columns = ['Categoría', 'Presupuesto']
                df_prev_tab['Presupuesto'] = df_prev_tab['Presupuesto'].map('{:.2f}€'.format)
                st.dataframe(df_prev_tab, hide_index=True, use_container_width=True)

    # 5. MENSUAL
    with tab_informes:
        st.subheader("Resumen Mensual")
        im1, im2 = st.columns(2)
        meses = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
        s_m, s_a = im1.selectbox("Mes", meses, index=datetime.now().month-1), im2.selectbox("Año ", range(2024, 2030), index=datetime.now().year-2024)
        if not df_all.empty:
            df_m = df_all[(df_all['date'].dt.month == meses.index(s_m)+1) & (df_all['date'].dt.year == s_a)]
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
                    emoji = "🟢" if p < 0.8 else "🟡" if p <= 1.0 else "🔴"
                    st.write(f"{emoji} **{r['name']}**: {r['quantity']:.2f}€ / {r['budget']:.2f}€")
                    st.progress(min(p, 1.0))

    # 6. ANUAL (CON GRÁFICA DE EVOLUCIÓN Y LÍNEA DE AHORRO)
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
                st.subheader("📈 Evolución y Ahorro Neto")
                
                # --- PREPARACIÓN DE DATOS PARA LA GRÁFICA ---
                meses_labels = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
                df_evo = df_an.copy()
                df_evo['mes_num'] = df_evo['date'].dt.month
                
                # Agrupamos ingresos y gastos por mes
                res_mes = df_evo.pivot_table(index='mes_num', columns='type', values='quantity', aggfunc='sum').fillna(0)
                # Aseguramos que existan ambas columnas para evitar errores
                for t in ['Ingreso', 'Gasto']:
                    if t not in res_mes.columns: res_mes[t] = 0
                
                res_mes['Ahorro'] = res_mes['Ingreso'] - res_mes['Gasto']
                res_mes = res_mes.reindex(range(1, 13), fill_value=0)
                res_mes['NombreMes'] = meses_labels

                # --- CREACIÓN DE GRÁFICA MIXTA (BAR + LINE) ---
                fig = go.Figure()
                # Barras de Ingresos
                fig.add_trace(go.Bar(x=meses_labels, y=res_mes['Ingreso'], name='Ingreso', marker_color='#00CC96'))
                # Barras de Gastos
                fig.add_trace(go.Bar(x=meses_labels, y=res_mes['Gasto'], name='Gasto', marker_color='#EF553B'))
                # Línea de Ahorro Neto
                fig.add_trace(go.Scatter(x=meses_labels, y=res_mes['Ahorro'], name='Ahorro Neto', 
                                         line=dict(color='#636EFA', width=4), marker=dict(size=8)))

                fig.update_layout(
                    barmode='group',
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                    margin=dict(l=20, r=20, t=50, b=20),
                    height=450,
                    yaxis_title="Euros (€)"
                )
                st.plotly_chart(fig, use_container_width=True)
                
                st.divider()
                st.subheader("Control Anual (Meta x12)")
                g_cat_an = df_an[df_an['type'] == 'Gasto'].groupby('category_id')['quantity'].sum().reset_index()
                for _, r in pd.merge(pd.DataFrame(cat_g), g_cat_an, left_on='id', right_on='category_id', how='left').fillna(0).iterrows():
                    b_an, p_an = r['budget'] * 12, r['quantity'] / (r['budget']*12) if r['budget'] > 0 else 0
                    st.write(f"{'🟢' if p_an < 0.8 else '🟡' if p_an <= 1 else '🔴'} **{r['name']}**: {r['quantity']:.2f}€ / {b_an:.2f}€")
                    st.progress(min(p_an, 1.0))
            else:
                st.info("No hay datos para el año seleccionado.")
else:
    st.info("Inicia sesión para empezar.")
