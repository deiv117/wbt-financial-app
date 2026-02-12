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

# --- ESTILOS CSS ADAPTATIVOS ---
st.markdown("""
    <style>
    .stApp {
        background-image: url("https://images.unsplash.com/photo-1554224155-6726b3ff858f?q=80&w=2022&auto=format&fit=crop");
        background-size: cover;
        background-position: center;
        background-attachment: fixed;
    }
    [data-testid="stForm"] {
        background-color: rgba(255, 255, 255, 0.05);
        backdrop-filter: blur(15px);
        -webkit-backdrop-filter: blur(15px);
        padding: 40px;
        border-radius: 20px;
        border: 1px solid rgba(255, 255, 255, 0.2);
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37);
    }
    .login-title { text-align: center; font-weight: 800; color: white !important; text-shadow: 2px 2px 4px rgba(0,0,0,0.5); }
    .login-subtitle { text-align: center; color: #f0f2f6 !important; text-shadow: 1px 1px 2px rgba(0,0,0,0.5); }
    .sidebar-user-container { display: flex; flex-direction: column; align-items: center; justify-content: center; text-align: center; padding: 10px 0 20px 0; }
    .avatar-circle { width: 80px; height: 80px; border-radius: 50%; display: flex; align-items: center; justify-content: center; color: white; font-weight: bold; font-size: 28px; margin-bottom: 10px; border: 2px solid #636EFA; object-fit: cover; }
    div.stButton > button { width: 100%; border-radius: 10px; border: 1px solid rgba(128, 128, 128, 0.2); background-color: transparent; transition: all 0.3s ease; text-align: left; padding: 10px 15px; }
    div.stButton > button:hover { border-color: #636EFA; background-color: rgba(99, 110, 250, 0.1); }
    </style>
    """, unsafe_allow_html=True)

# --- CONTROL DE SESIÓN CORREGIDO ---
if 'user' not in st.session_state:
    try:
        # Intentamos recuperar sesión persistente
        res_session = supabase.auth.get_session()
        if res_session and res_session.user:
            st.session_state.user = res_session.user
        else:
            st.session_state.user = None
    except:
        st.session_state.user = None

if 'menu_actual' not in st.session_state:
    st.session_state.menu_actual = "📊 Panel"

# --- LÓGICA DE LOGIN O CONTENIDO ---
if not st.session_state.user:
    _, col_login, _ = st.columns([1, 1.5, 1])
    with col_login:
        st.write("#")
        with st.form("login_form"):
            st.markdown("<h1 class='login-title'>💰 Finanzas App</h1>", unsafe_allow_html=True)
            st.markdown("<p class='login-subtitle'>Identifícate para gestionar tus ahorros</p>", unsafe_allow_html=True)
            email = st.text_input("Email")
            password = st.text_input("Contraseña", type="password")
            recordarme = st.checkbox("Mantener sesión iniciada (1h)", value=True)
            
            submit = st.form_submit_button("Entrar", use_container_width=True)
            
            if submit:
                try:
                    # Al hacer el login, actualizamos directamente el session_state
                    res = supabase.auth.sign_in_with_password({"email": email, "password": password})
                    if res.user:
                        st.session_state.user = res.user
                        st.rerun() # ESTE RERUN ES CLAVE: Recarga la página ya con el usuario detectado
                except Exception as e:
                    st.error("Acceso denegado. Revisa tus credenciales.")
else:
    # Quitar fondo de imagen dentro de la app
    st.markdown("<style>.stApp { background-image: none !important; }</style>", unsafe_allow_html=True)

    # --- SIDEBAR NAVEGACIÓN ---
    with st.sidebar:
        # Recuperamos datos del perfil
        res_p = supabase.table("profiles").select("*").eq("id", st.session_state.user.id).maybe_single().execute()
        p_data = res_p.data if (hasattr(res_p, 'data') and res_p.data) else {}
        
        nombre, apellido = p_data.get('name', ''), p_data.get('lastname', '')
        avatar_url, bg_color = p_data.get('avatar_url', ""), p_data.get('profile_color', "#636EFA")
        
        iniciales = ((nombre[0] if nombre else "") + (apellido[0] if apellido else "")).upper()
        if not iniciales: iniciales = st.session_state.user.email[0].upper()

        st.markdown('<div class="sidebar-user-container">', unsafe_allow_html=True)
        if avatar_url:
            st.markdown(f'<img src="{avatar_url}" class="avatar-circle">', unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="avatar-circle" style="background-color: {bg_color};">{iniciales}</div>', unsafe_allow_html=True)
        st.markdown(f"**{nombre} {apellido}**")
        
        if st.button("Cerrar Sesión"):
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

    # --- LÓGICA DE PÁGINAS ---
    if st.session_state.menu_actual == "⚙️ Perfil":
        st.title("⚙️ Mi Perfil")
        with st.form("perfil_form"):
            c1, c2 = st.columns(2)
            n_name = c1.text_input("Nombre", value=p_data.get('name', ""))
            n_last = c1.text_input("Apellido", value=p_data.get('lastname', ""))
            n_color = c1.color_picker("Color de Avatar", value=p_data.get('profile_color', "#636EFA"))
            n_avatar = c2.text_input("URL Foto de Perfil", value=p_data.get('avatar_url', ""))
            n_social = c2.toggle("Modo Social (Grupos)", value=p_data.get('social_active', False))
            if st.form_submit_button("Guardar Cambios"):
                payload = {"id": st.session_state.user.id, "name": n_name, "lastname": n_last, "avatar_url": n_avatar, "profile_color": n_color, "social_active": n_social, "updated_at": str(datetime.now())}
                supabase.table("profiles").upsert(payload).execute()
                st.success("Perfil actualizado"); st.rerun()

    elif st.session_state.menu_actual == "📥 Importar":
        st.title("📥 Importación de Datos")
        col_i1, col_i2 = st.columns(2)
        with col_i1:
            st.info("Descarga la plantilla y rellénala con tus datos.")
            st.download_button("📄 Descargar Plantilla .CSV", "fecha,cantidad,categoria\n2026-02-12,15.50,Alimentacion", "plantilla.csv")
        with col_i2:
            up = st.file_uploader("Sube tu archivo CSV", type=["csv"])
            if up and st.button("🚀 Iniciar Importación"):
                try:
                    df_imp = pd.read_csv(up)
                    res_c = supabase.table("user_categories").select("*").execute()
                    cat_map = {c['name'].upper(): (c['id'], c['type']) for c in res_c.data}
                    rows = [{"user_id": st.session_state.user.id, "quantity": float(r['cantidad']), "type": cat_map[str(r['categoria']).upper()][1], "category_id": cat_map[str(r['categoria']).upper()][0], "date": str(r['fecha'])} for _, r in df_imp.iterrows() if str(r['categoria']).upper() in cat_map]
                    if rows: supabase.table("user_imputs").insert(rows).execute(); st.success(f"{len(rows)} movimientos importados!")
                except: st.error("Error al procesar el archivo.")

    else:
        # --- PANEL PRINCIPAL ---
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
            f_cs = [c for c in current_cats if c.get('type') == t_type]
            if f_cs:
                sel = st.selectbox("Categoría", ["Selecciona..."] + [c['name'] for c in f_cs])
                if st.button("Guardar") and sel != "Selecciona...":
                    cid = next(c['id'] for c in f_cs if c['name'] == sel)
                    supabase.table("user_imputs").insert({"user_id": st.session_state.user.id, "quantity": qty, "type": t_type, "category_id": cid, "date": str(f_mov)}).execute(); st.rerun()
            st.divider()
            res_rec = supabase.table("user_imputs").select("*, user_categories(name)").order("date", desc=True).limit(10).execute()
            for i in (res_rec.data if res_rec.data else []):
                cl1, cl2, cl3, cl4 = st.columns([2, 1, 1, 1])
                cl1.write(f"**{i['date']}** | {i['user_categories']['name'] if i['user_categories'] else 'S/C'}")
                cl2.write(f"{i['quantity']:.2f}€")
                cl3.write("📉" if i['type'] == "Gasto" else "📈")
                if cl4.button("🗑️", key=f"d_{i['id']}"): supabase.table("user_imputs").delete().eq("id", i['id']).execute(); st.rerun()

        with tab_hist:
            st.subheader("🗄️ Historial")
            h1, h2, h3 = st.columns(3)
            f_i, f_f = h1.date_input("Desde", datetime.now()-timedelta(days=30)), h2.date_input("Hasta", datetime.now())
            f_t = h3.selectbox("Filtrar por tipo", ["Todos", "Gasto", "Ingreso"])
            if not df_all.empty:
                df_h = df_all[(df_all['date'].dt.date >= f_i) & (df_all['date'].dt.date <= f_f)]
                if f_t != "Todos": df_h = df_h[df_h['type'] == f_t]
                st.dataframe(df_h[['date', 'quantity', 'type']].sort_values('date', ascending=False), use_container_width=True, hide_index=True)

        with tab_cat:
            if st.button("➕ Añadir Categoría"): crear_categoria_dialog()
            ci, cg = st.columns(2)
            for col, t in zip([ci, cg], ["Ingreso", "Gasto"]):
                with col:
                    st.subheader(f"{t}s")
                    for c in [cat for cat in current_cats if cat.get('type') == t]:
                        with st.container(border=True):
                            st.write(f"**{c['name']}**")
                            if t == "Gasto": st.caption(f"Meta: {c['budget']:.2f}€")
                            if st.button("Borrar", key=f"b_{c['id']}"): supabase.table("user_categories").delete().eq("id", c['id']).execute(); st.rerun()

        with tab_prev:
            st.subheader("🔮 Previsión Teórica")
            tp = sum(c['budget'] for c in cat_g)
            mi = df_all[df_all['type']=='Ingreso'].groupby(df_all['date'].dt.to_period('M'))['quantity'].sum().mean() if not df_all.empty else 0
            with st.container(border=True):
                m1, m2, m3 = st.columns(3)
                m1.metric("Gasto Presupuestado", f"{tp:.2f}€")
                m2.metric("Media Ingresos", f"{mi:.2f}€")
                m3.metric("Ahorro Potencial", f"{(mi - tp):.2f}€")
            st.divider()
            if cat_g:
                col_g1, col_g2 = st.columns(2)
                with col_g1: st.plotly_chart(px.pie(pd.DataFrame(cat_g), values='budget', names='name', hole=0.4), use_container_width=True)
                with col_g2: st.dataframe(pd.DataFrame(cat_g)[['name', 'budget']].rename(columns={'name':'Categoría','budget':'Presupuesto'}), hide_index=True, use_container_width=True)

        with tab_mes:
            st.subheader("Resumen Mensual")
            ml = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
            im1, im2 = st.columns(2)
            sm, sa = im1.selectbox("Selecciona Mes", ml, index=datetime.now().month-1), im2.selectbox("Año", range(2024, 2030), index=datetime.now().year-2024)
            if not df_all.empty:
                df_m = df_all[(df_all['date'].dt.month == ml.index(sm)+1) & (df_all['date'].dt.year == sa)]
                if not df_m.empty:
                    im, gm = df_m[df_m['type'] == 'Ingreso']['quantity'].sum(), df_m[df_m['type'] == 'Gasto']['quantity'].sum()
                    with st.container(border=True):
                        c1, c2, c3 = st.columns(3)
                        c1.metric("Ingresos", f"{im:.2f}€")
                        c2.metric("Gastos", f"{gm:.2f}€")
                        c3.metric("Ahorro", f"{(im - gm):.2f}€", delta=f"{(im - gm):.2f}€")
                    st.divider()
                    gcm = df_m[df_m['type'] == 'Gasto'].groupby('category_id')['quantity'].sum().reset_index()
                    for _, r in pd.merge(pd.DataFrame(cat_g), gcm, left_on='id', right_on='category_id', how='left').fillna(0).iterrows():
                        p = r['quantity'] / r['budget'] if r['budget'] > 0 else 0
                        st.write(f"{'🟢' if p < 0.8 else '🟡' if p <= 1 else '🔴'} **{r['name']}**: {r['quantity']:.2f}€ / {r['budget']:.2f}€")
                        st.progress(min(p, 1.0))

        with tab_anual:
            st.subheader("Resumen Anual")
            san = st.selectbox("Seleccionar Año ", range(2024, 2030), index=datetime.now().year-2024)
            if not df_all.empty:
                df_an = df_all[df_all['date'].dt.year == san]
                if not df_an.empty:
                    ia, ga = df_an[df_an['type'] == 'Ingreso']['quantity'].sum(), df_an[df_an['type'] == 'Gasto']['quantity'].sum()
                    with st.container(border=True):
                        ca1, ca2, ca3 = st.columns(3)
                        ca1.metric("Ingresos Anuales", f"{ia:.2f}€")
                        ca2.metric("Gastos Anuales", f"{ga:.2f}€")
                        ca3.metric("Balance Total", f"{(ia - ga):.2f}€", delta=f"{(ia - ga):.2f}€")
                    st.divider()
                    dfe = df_an.copy(); dfe['mes_num'] = dfe['date'].dt.month
                    rm = dfe.pivot_table(index='mes_num', columns='type', values='quantity', aggfunc='sum').fillna(0).reindex(range(1,13), fill_value=0)
                    for t in ['Ingreso', 'Gasto']: 
                        if t not in rm.columns: rm[t] = 0
                    rm['Ahorro'] = rm['Ingreso'] - rm['Gasto']
                    fig = go.Figure()
                    fig.add_trace(go.Bar(x=ml, y=rm['Ingreso'], name='Ingreso', marker_color='#00CC96'))
                    fig.add_trace(go.Bar(x=ml, y=rm['Gasto'], name='Gasto', marker_color='#EF553B'))
                    fig.add_trace(go.Scatter(x=ml, y=rm['Ahorro'], name='Ahorro Neto', line=dict(color='#636EFA', width=4)))
                    st.plotly_chart(fig, use_container_width=True)
                    st.divider()
                    st.subheader("Meta Anual (Meta x12)")
                    gca = df_an[df_an['type'] == 'Gasto'].groupby('category_id')['quantity'].sum().reset_index()
                    for _, r in pd.merge(pd.DataFrame(cat_g), gca, left_on='id', right_on='category_id', how='left').fillna(0).iterrows():
                        b12, p12 = r['budget']*12, r['quantity']/(r['budget']*12) if r['budget']>0 else 0
                        st.write(f"{'🟢' if p12 < 0.8 else '🟡' if p12 <= 1 else '🔴'} **{r['name']}**: {r['quantity']:.2f}€ / {b12:.2f}€")
                        st.progress(min(p12, 1.0))
