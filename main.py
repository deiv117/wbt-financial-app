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

# --- ESTILOS CSS PARA DISEÑO MODERNO ---
st.markdown("""
    <style>
    /* Estilo para los botones del menú lateral */
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
    /* Imagen de perfil circular */
    .profile-pic {
        border-radius: 50%;
        width: 60px;
        height: 60px;
        object-fit: cover;
        border: 2px solid #636EFA;
    }
    .user-name {
        font-weight: bold;
        font-size: 1.1em;
        margin-bottom: 0px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- CONTROL DE SESIÓN ---
if 'user' not in st.session_state:
    st.session_state.user = None
if 'menu_actual' not in st.session_state:
    st.session_state.menu_actual = "📊 Panel"

# --- SIDEBAR (NAVEGACIÓN MODERNA) ---
with st.sidebar:
    st.header("💰 Finanzas App")
    
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
        # Consulta de perfil para el encabezado
        res_p = supabase.table("profiles").select("*").eq("id", st.session_state.user.id).maybe_single().execute()
        p_sidebar = res_p.data if (hasattr(res_p, 'data') and res_p.data) else {}
        nombre_user = p_sidebar.get('name', st.session_state.user.email)
        avatar = p_sidebar.get('avatar_url', "https://www.w3schools.com/howto/img_avatar.png")

        # Header de usuario
        col_s1, col_s2 = st.columns([1, 3])
        with col_s1:
            st.markdown(f'<img src="{avatar}" class="profile-pic">', unsafe_allow_html=True)
        with col_s2:
            st.markdown(f'<p class="user-name">{nombre_user}</p>', unsafe_allow_html=True)
            if st.button("Salir", key="logout"):
                supabase.auth.sign_out()
                st.session_state.user = None
                st.rerun()
        
        st.divider()
        # Botones de navegación
        if st.button("📊 Panel de Control"):
            st.session_state.menu_actual = "📊 Panel"
            st.rerun()
        if st.button("⚙️ Configuración Perfil"):
            st.session_state.menu_actual = "⚙️ Perfil"
            st.rerun()
        if st.button("📥 Importar Movimientos"):
            st.session_state.menu_actual = "📥 Importar"
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
    
    # 1. PÁGINA: PERFIL
    if st.session_state.menu_actual == "⚙️ Perfil":
        st.title("⚙️ Configuración de Perfil")
        p_res = supabase.table("profiles").select("*").eq("id", st.session_state.user.id).maybe_single().execute()
        p_data = p_res.data if (hasattr(p_res, 'data') and p_res.data) else {}
        
        col_p1, col_p2 = st.columns([1, 2])
        with col_p1:
            if p_data.get('avatar_url'): st.image(p_data['avatar_url'], width=180)
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

    # 2. PÁGINA: IMPORTAR
    elif st.session_state.menu_actual == "📥 Importar":
        st.title("📥 Centro de Importación")
        col_i1, col_i2 = st.columns(2)
        with col_i1:
            with st.container(border=True):
                st.subheader("1. Plantilla")
                t_data = "fecha,cantidad,categoria\n2026-02-12,15.50,Alimentacion"
                st.download_button(label="📄 Descargar Plantilla .CSV", data=t_data, file_name="plantilla.csv")
        with col_i2:
            with st.container(border=True):
                st.subheader("2. Subir Archivo")
                uploaded_file = st.file_uploader("Selecciona CSV", type=["csv"])
                if uploaded_file and st.button("🚀 Iniciar Importación"):
                    try:
                        df_imp = pd.read_csv(uploaded_file)
                        res_c = supabase.table("user_categories").select("*").execute()
                        cat_map = {c['name'].upper(): (c['id'], c['type']) for c in res_c.data}
                        rows = []
                        for _, row in df_imp.iterrows():
                            c_up = str(row['categoria']).upper()
                            if c_up in cat_map:
                                cid, ctyp = cat_map[c_up]
                                rows.append({"user_id": st.session_state.user.id, "quantity": float(row['cantidad']), "type": ctyp, "category_id": cid, "date": str(row['fecha'])})
                        if rows:
                            supabase.table("user_imputs").insert(rows).execute()
                            st.success(f"¡{len(rows)} movimientos importados!")
                    except: st.error("Error al procesar el archivo")

    # 3. PÁGINA: PANEL (TABS RESTAURADOS)
    else:
        st.title("📊 Cuadro de Mando")
        tab_gastos, tab_historial, tab_categorias, tab_prevision, tab_mensual, tab_anual = st.tabs([
            "💸 Movimientos", "🗄️ Historial", "⚙️ Categorías", "🔮 Previsión", "📊 Mensual", "📅 Anual"
        ])

        # CARGA DE DATOS GLOBAL
        res_cats = supabase.table("user_categories").select("*").execute()
        current_cats = sorted(res_cats.data, key=lambda x: x['name'].lower()) if res_cats.data else []
        res_all = supabase.table("user_imputs").select("*, user_categories(name)").execute()
        df_all = pd.DataFrame(res_all.data) if res_all.data else pd.DataFrame()
        if not df_all.empty: df_all['date'] = pd.to_datetime(df_all['date'])
        cat_g = [c for c in current_cats if c.get('type') == 'Gasto']

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
            res_recent = supabase.table("user_imputs").select("*, user_categories(name)").order("date", desc=True).limit(10).execute()
            for i in (res_recent.data if res_recent.data else []):
                cl1, cl2, cl3, cl4 = st.columns([2, 1, 1, 1])
                cl1.write(f"**{i['date']}** | {i['user_categories']['name'] if i['user_categories'] else 'S/C'}")
                cl2.write(f"{i['quantity']:.2f}€")
                cl3.write("📉" if i['type'] == "Gasto" else "📈")
                if cl4.button("🗑️", key=f"del_{i['id']}"):
                    supabase.table("user_imputs").delete().eq("id", i['id']).execute()
                    st.rerun()

        with tab_historial:
            h1, h2, h3 = st.columns(3)
            f_i, f_f = h1.date_input("Desde", datetime.now()-timedelta(days=30)), h2.date_input("Hasta", datetime.now())
            f_t = h3.selectbox("Filtrar", ["Todos", "Gasto", "Ingreso"])
            if not df_all.empty:
                df_h = df_all[(df_all['date'].dt.date >= f_i) & (df_all['date'].dt.date <= f_f)]
                if f_t != "Todos": df_h = df_h[df_h['type'] == f_t]
                st.dataframe(df_h[['date', 'quantity', 'type']].rename(columns={'quantity':'Importe'}), use_container_width=True, hide_index=True)

        with tab_categorias:
            if st.button("➕ Añadir Categoría"): crear_categoria_dialog()
            col_ing, col_gas = st.columns(2)
            for col, t in zip([col_ing, col_gas], ["Ingreso", "Gasto"]):
                with col:
                    st.markdown(f"### {t}s")
                    for c in [cat for cat in current_cats if cat.get('type') == t]:
                        with st.container(border=True):
                            st.write(f"**{c['name']}**")
                            if t == "Gasto": st.caption(f"Presupuesto: {c['budget']:.2f}€")
                            if st.button("🗑️", key=f"dc_{c['id']}"):
                                supabase.table("user_categories").delete().eq("id", c['id']).execute()
                                st.rerun()

        with tab_prevision:
            total_p = sum(c['budget'] for c in cat_g)
            media_i = df_all[df_all['type']=='Ingreso'].groupby(df_all['date'].dt.to_period('M'))['quantity'].sum().mean() if not df_all.empty else 0
            st.metric("Gasto Teórico", f"{total_p:.2f}€", delta=f"{(media_i - total_p):.2f}€ Ahorro")
            if cat_g:
                st.plotly_chart(px.pie(pd.DataFrame(cat_g), values='budget', names='name', hole=0.4), use_container_width=True)

        with tab_mensual:
            meses_list = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
            m_sel = st.selectbox("Mes", meses_list, index=datetime.now().month-1)
            if not df_all.empty:
                df_m = df_all[df_all['date'].dt.month == meses_list.index(m_sel)+1]
                if not df_m.empty:
                    g_cat_m = df_m[df_m['type'] == 'Gasto'].groupby('category_id')['quantity'].sum().reset_index()
                    for _, r in pd.merge(pd.DataFrame(cat_g), g_cat_m, left_on='id', right_on='category_id', how='left').fillna(0).iterrows():
                        p = r['quantity'] / r['budget'] if r['budget'] > 0 else 0
                        st.write(f"{'🔴' if p > 1 else '🟡' if p > 0.8 else '🟢'} **{r['name']}**: {r['quantity']:.2f}€ / {r['budget']:.2f}€")
                        st.progress(min(p, 1.0))

        with tab_anual:
            s_an = st.selectbox("Año", range(2024, 2030), index=datetime.now().year-2024)
            if not df_all.empty:
                df_an = df_all[df_all['date'].dt.year == s_an]
                if not df_an.empty:
                    # Gráfica mixta
                    df_evo = df_an.copy()
                    df_evo['mes_num'] = df_evo['date'].dt.month
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
else:
    st.info("Inicia sesión para empezar.")
