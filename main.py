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

# --- ESTILOS CSS PARA DISEÑO MODERNO Y CENTRADO ---
st.markdown("""
    <style>
    .sidebar-user-container {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        text-align: center;
        padding: 10px 0 20px 0;
    }
    .avatar-circle {
        width: 80px;
        height: 80px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        color: white;
        font-weight: bold;
        font-size: 28px;
        margin-bottom: 10px;
        border: 2px solid #ffffff33;
        object-fit: cover;
    }
    .user-name-sidebar {
        font-weight: bold;
        font-size: 1.1em;
        margin-bottom: 5px;
        color: #31333F;
    }
    div.stButton > button {
        width: 100%;
        border-radius: 10px;
        border: 1px solid #f0f2f6;
        background-color: transparent;
        transition: all 0.3s ease;
        text-align: left;
        padding: 10px 15px;
    }
    div.stButton > button:hover {
        background-color: #f0f2f6;
        border-color: #636EFA;
    }
    </style>
    """, unsafe_allow_html=True)

# --- CONTROL DE SESIÓN ---
if 'user' not in st.session_state:
    st.session_state.user = None
if 'menu_actual' not in st.session_state:
    st.session_state.menu_actual = "📊 Panel"

# --- SIDEBAR (NAVEGACIÓN) ---
with st.sidebar:
    if not st.session_state.user:
        st.header("🔑 Acceso")
        email = st.text_input("Correo electrónico")
        password = st.text_input("Contraseña", type="password")
        if st.button("Entrar"):
            try:
                res = supabase.auth.sign_in_with_password({"email": email, "password": password})
                st.session_state.user = res.user
                st.rerun()
            except: st.error("Error de acceso")
    else:
        res_p = supabase.table("profiles").select("*").eq("id", st.session_state.user.id).maybe_single().execute()
        p_data = res_p.data if (hasattr(res_p, 'data') and res_p.data) else {}
        
        nombre = p_data.get('name', '')
        apellido = p_data.get('lastname', '')
        avatar_url = p_data.get('avatar_url', "")
        bg_color = p_data.get('profile_color', "#636EFA")
        
        iniciales = (nombre[0] if nombre else "") + (apellido[0] if apellido else "")
        if not iniciales: iniciales = st.session_state.user.email[0].upper()
        
        st.markdown('<div class="sidebar-user-container">', unsafe_allow_html=True)
        if avatar_url:
            st.markdown(f'<img src="{avatar_url}" class="avatar-circle">', unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="avatar-circle" style="background-color: {bg_color};">{iniciales.upper()}</div>', unsafe_allow_html=True)
        
        st.markdown(f'<p class="user-name-sidebar">{nombre} {apellido}</p>', unsafe_allow_html=True)
        if st.button("Cerrar Sesión", key="logout_btn"):
            supabase.auth.sign_out()
            st.session_state.user = None
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
        
        st.divider()
        if st.button("📊 Panel de Control"): st.session_state.menu_actual = "📊 Panel"; st.rerun()
        if st.button("⚙️ Configuración Perfil"): st.session_state.menu_actual = "⚙️ Perfil"; st.rerun()
        if st.button("📥 Importar Movimientos"): st.session_state.menu_actual = "📥 Importar"; st.rerun()

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
    
    if st.session_state.menu_actual == "⚙️ Perfil":
        st.title("⚙️ Mi Perfil")
        res_p = supabase.table("profiles").select("*").eq("id", st.session_state.user.id).maybe_single().execute()
        p_data = res_p.data if (hasattr(res_p, 'data') and res_p.data) else {}
        with st.form("perfil_form_ext"):
            c1, c2 = st.columns(2)
            n_name = c1.text_input("Nombre", value=p_data.get('name', ""))
            n_last = c1.text_input("Apellido", value=p_data.get('lastname', ""))
            n_color = c1.color_picker("Color de Avatar", value=p_data.get('profile_color', "#636EFA"))
            n_avatar = c2.text_input("URL Foto de Perfil", value=p_data.get('avatar_url', ""))
            n_social = c2.toggle("Modo Social (Grupos)", value=p_data.get('social_active', False))
            if st.form_submit_button("Guardar Cambios"):
                payload = {"id": st.session_state.user.id, "name": n_name, "lastname": n_last, "avatar_url": n_avatar, "profile_color": n_color, "social_active": n_social, "updated_at": str(datetime.now())}
                supabase.table("profiles").upsert(payload).execute()
                st.success("¡Perfil actualizado!"); st.rerun()

    elif st.session_state.menu_actual == "📥 Importar":
        st.title("📥 Importación CSV")
        col_i1, col_i2 = st.columns(2)
        with col_i1:
            st.info("Descarga la plantilla y rellénala respetando los nombres de tus categorías.")
            t_data = "fecha,cantidad,categoria\n2026-02-12,15.50,Alimentacion"
            st.download_button("📄 Descargar Plantilla .CSV", t_data, "plantilla.csv")
        with col_i2:
            up = st.file_uploader("Sube el archivo", type=["csv"])
            if up and st.button("🚀 Iniciar Importación"):
                try:
                    df = pd.read_csv(up)
                    res_c = supabase.table("user_categories").select("*").execute()
                    cat_map = {c['name'].upper(): (c['id'], c['type']) for c in res_c.data}
                    rows = []
                    for _, r in df.iterrows():
                        c_up = str(r['categoria']).upper()
                        if c_up in cat_map:
                            rows.append({"user_id": st.session_state.user.id, "quantity": float(r['cantidad']), "type": cat_map[c_up][1], "category_id": cat_map[c_up][0], "date": str(r['fecha'])})
                    if rows: supabase.table("user_imputs").insert(rows).execute(); st.success(f"¡{len(rows)} movimientos importados!")
                except: st.error("Error al procesar el archivo.")

    else:
        st.title("📊 Cuadro de Mando")
        tab_mov, tab_hist, tab_cat, tab_prev, tab_mes, tab_anual = st.tabs(["💸 Movimientos", "🗄️ Historial", "⚙️ Categorías", "🔮 Previsión", "📊 Mensual", "📅 Anual"])

        res_cats = supabase.table("user_categories").select("*").execute()
        current_cats = sorted(res_cats.data, key=lambda x: x['name'].lower()) if res_cats.data else []
        res_all = supabase.table("user_imputs").select("*, user_categories(name)").execute()
        df_all = pd.DataFrame(res_all.data) if res_all.data else pd.DataFrame()
        if not df_all.empty: df_all['date'] = pd.to_datetime(df_all['date'])
        cat_g = [c for c in current_cats if c.get('type') == 'Gasto']

        with tab_mov:
            st.subheader("Nuevo Registro")
            c1, c2, c3 = st.columns(3)
            qty = c1.number_input("Cantidad (€)", min_value=0.0, step=0.01)
            t_type = c2.selectbox("Tipo", ["Gasto", "Ingreso"])
            f_mov = c3.date_input("Fecha", datetime.now())
            f_cats = [c for c in current_cats if c.get('type') == t_type]
            if f_cats:
                sel = st.selectbox("Categoría", ["Selecciona..."] + [c['name'] for c in f_cats])
                if st.button("Guardar") and sel != "Selecciona...":
                    c_id = next(c['id'] for c in f_cats if c['name'] == sel)
                    supabase.table("user_imputs").insert({"user_id": st.session_state.user.id, "quantity": qty, "type": t_type, "category_id": c_id, "date": str(f_mov)}).execute(); st.rerun()
            st.divider()
            res_rec = supabase.table("user_imputs").select("*, user_categories(name)").order("date", desc=True).limit(10).execute()
            for i in (res_rec.data if res_rec.data else []):
                col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
                col1.write(f"**{i['date']}** | {i['user_categories']['name'] if i['user_categories'] else 'S/C'}")
                col2.write(f"{i['quantity']:.2f}€")
                col3.write("📉" if i['type'] == "Gasto" else "📈")
                if col4.button("🗑️", key=f"del_{i['id']}"): supabase.table("user_imputs").delete().eq("id", i['id']).execute(); st.rerun()

        with tab_hist:
            st.subheader("🗄️ Historial Completo")
            h1, h2, h3 = st.columns(3)
            f_i, f_f = h1.date_input("Desde", datetime.now()-timedelta(days=30)), h2.date_input("Hasta", datetime.now())
            f_t = h3.selectbox("Filtrar", ["Todos", "Gasto", "Ingreso"])
            if not df_all.empty:
                df_h = df_all[(df_all['date'].dt.date >= f_i) & (df_all['date'].dt.date <= f_f)]
                if f_t != "Todos": df_h = df_h[df_h['type'] == f_t]
                page = st.number_input("Página", min_value=1, value=1)
                start = (page-1)*50
                st.dataframe(df_h.iloc[start:start+50][['date', 'quantity', 'type']].rename(columns={'quantity':'Importe'}), use_container_width=True, hide_index=True)

        with tab_cat:
            if st.button("➕ Añadir Categoría"): crear_categoria_dialog()
            c_ing, c_gas = st.columns(2)
            for col, t in zip([c_ing, c_gas], ["Ingreso", "Gasto"]):
                with col:
                    st.markdown(f"### {t}s")
                    for c in [cat for cat in current_cats if cat.get('type') == t]:
                        with st.container(border=True):
                            st.write(f"**{c['name']}**")
                            if t == "Gasto": st.caption(f"Presupuesto: {c['budget']:.2f}€")
                            if st.button("🗑️", key=f"dc_{c['id']}"): supabase.table("user_categories").delete().eq("id", c['id']).execute(); st.rerun()

        with tab_prev:
            st.subheader("🔮 Previsión Teórica")
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
                    df_p_tab = pd.DataFrame(cat_g)[['name', 'budget']].rename(columns={'name':'Categoría','budget':'Presupuesto'})
                    df_p_tab['Presupuesto'] = df_p_tab['Presupuesto'].map('{:.2f}€'.format)
                    st.dataframe(df_p_tab, hide_index=True, use_container_width=True)

        with tab_mes:
            st.subheader("Resumen Mensual")
            meses_list = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
            im1, im2 = st.columns(2)
            s_m, s_a = im1.selectbox("Mes", meses_list, index=datetime.now().month-1), im2.selectbox("Año ", range(2024, 2030), index=datetime.now().year-2024)
            if not df_all.empty:
                df_m = df_all[(df_all['date'].dt.month == meses_list.index(s_m)+1) & (df_all['date'].dt.year == s_a)]
                if not df_m.empty:
                    i_m, g_m = df_m[df_m['type'] == 'Ingreso']['quantity'].sum(), df_m[df_m['type'] == 'Gasto']['quantity'].sum()
                    with st.container(border=True):
                        c1, c2, c3 = st.columns(3)
                        c1.metric("Ingresos", f"{i_m:.2f}€")
                        c2.metric("Gastos", f"{g_m:.2f}€")
                        c3.metric("Ahorro", f"{(i_m - g_m):.2f}€", delta=f"{(i_m - g_m):.2f}€", delta_color="normal")
                    st.divider()
                    st.subheader("Semáforo de Gastos")
                    g_cat_m = df_m[df_m['type'] == 'Gasto'].groupby('category_id')['quantity'].sum().reset_index()
                    for _, r in pd.merge(pd.DataFrame(cat_g), g_cat_m, left_on='id', right_on='category_id', how='left').fillna(0).iterrows():
                        p = r['quantity'] / r['budget'] if r['budget'] > 0 else 0
                        st.write(f"{'🟢' if p < 0.8 else '🟡' if p <= 1.0 else '🔴'} **{r['name']}**: {r['quantity']:.2f}€ / {r['budget']:.2f}€")
                        st.progress(min(p, 1.0))

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
                        ca3.metric("Balance Total", f"{(i_an - g_an):.2f}€", delta=f"{(i_an - g_an):.2f}€")
                    st.divider()
                    df_evo = df_an.copy(); df_evo['mes_num'] = df_evo['date'].dt.month
                    res_mes = df_evo.pivot_table(index='mes_num', columns='type', values='quantity', aggfunc='sum').fillna(0)
                    for t in ['Ingreso', 'Gasto']: 
                        if t not in res_mes.columns: res_mes[t] = 0
                    res_mes['Ahorro'] = res_mes['Ingreso'] - res_mes['Gasto']
                    res_mes = res_mes.reindex(range(1, 13), fill_value=0)
                    fig = go.Figure()
                    fig.add_trace(go.Bar(x=meses_list, y=res_mes['Ingreso'], name='Ingreso', marker_color='#00CC96'))
                    fig.add_trace(go.Bar(x=meses_list, y=res_mes['Gasto'], name='Gasto', marker_color='#EF553B'))
                    fig.add_trace(go.Scatter(x=meses_list, y=res_mes['Ahorro'], name='Ahorro Neto', line=dict(color='#636EFA', width=4)))
                    st.plotly_chart(fig, use_container_width=True)
                    st.divider()
                    st.subheader("Control Anual (Meta x12)")
                    g_cat_an = df_an[df_an['type'] == 'Gasto'].groupby('category_id')['quantity'].sum().reset_index()
                    for _, r in pd.merge(pd.DataFrame(cat_g), g_cat_an, left_on='id', right_on='category_id', how='left').fillna(0).iterrows():
                        b_an = r['budget'] * 12
                        p_an = r['quantity'] / b_an if b_an > 0 else 0
                        st.write(f"{'🟢' if p_an < 0.8 else '🟡' if p_an <= 1 else '🔴'} **{r['name']}**: {r['quantity']:.2f}€ / {b_an:.2f}€")
                        st.progress(min(p_an, 1.0))
else:
    st.info("Inicia sesión para empezar.")
