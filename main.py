import streamlit as st
from supabase import create_client, Client
import pandas as pd
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go
from styles import get_custom_css

# 1. CONEXIÓN SEGURA CON SUPABASE
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

st.set_page_config(page_title="Mis Gastos", page_icon="💰", layout="wide")

# --- APLICAMOS ESTILOS ---
st.markdown(get_custom_css(), unsafe_allow_html=True)

# --- CONTROL DE SESIÓN ---
if 'user' not in st.session_state:
    try:
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
                    res = supabase.auth.sign_in_with_password({"email": email, "password": password})
                    if res.user:
                        st.session_state.user = res.user
                        st.rerun()
                except Exception as e:
                    st.error("Acceso denegado. Revisa tus credenciales.")
else:
    st.markdown("<style>.stApp { background-image: none !important; }</style>", unsafe_allow_html=True)

    # --- SIDEBAR NAVEGACIÓN ---
    with st.sidebar:
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

    # --- FUNCIONES DIALOG (CREAR Y EDITAR) ---
    @st.dialog("➕ Nueva Categoría")
    def crear_categoria_dialog():
        lista_emojis = ["📁", "💰", "🍔", "🏠", "🚗", "🛒", "🔌", "🎬", "🏥", "✈️", "👔", "🎓", "🎁", "🏋️", "🍹", "📱", "🐾", "💡", "🛠️", "🍕"]
        c1, c2 = st.columns([1, 2])
        emoji_sel = c1.selectbox("Emoji", lista_emojis)
        emoji_custom = c1.text_input("U otro...", value="", help="Pega aquí tu propio emoji")
        emoji_final = emoji_custom if emoji_custom else emoji_sel
        
        name = c2.text_input("Nombre")
        c_type = st.selectbox("Tipo", ["Gasto", "Ingreso"])
        budget = st.number_input("Presupuesto Mensual (€)", min_value=0.0) if c_type == "Gasto" else 0.0
        if st.button("Guardar"):
            if name:
                supabase.table("user_categories").insert({
                    "user_id": st.session_state.user.id, 
                    "name": name, 
                    "type": c_type, 
                    "budget": budget,
                    "emoji": emoji_final
                }).execute()
                st.rerun()

    @st.dialog("✏️ Editar Categoría")
    def editar_categoria_dialog(cat_data):
        lista_emojis = ["📁", "💰", "🍔", "🏠", "🚗", "🛒", "🔌", "🎬", "🏥", "✈️", "👔", "🎓", "🎁", "🏋️", "🍹", "📱", "🐾", "💡", "🛠️", "🍕"]
        c1, c2 = st.columns([1, 2])
        try:
            idx = lista_emojis.index(cat_data.get('emoji', '📁'))
        except:
            idx = 0
        emoji_sel = c1.selectbox("Emoji", lista_emojis, index=idx)
        emoji_custom = c1.text_input("U otro...", value="")
        emoji_final = emoji_custom if emoji_custom else emoji_sel
        
        new_name = c2.text_input("Nombre", value=cat_data['name'])
        new_budget = 0.0
        if cat_data['type'] == 'Gasto':
            new_budget = st.number_input("Presupuesto Mensual (€)", value=float(cat_data['budget']), min_value=0.0)
            
        if st.button("Actualizar Datos"):
            if new_name:
                supabase.table("user_categories").update({
                    "name": new_name,
                    "emoji": emoji_final,
                    "budget": new_budget
                }).eq("id", cat_data['id']).execute()
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
            st.download_button("📄 Descargar Plantilla .CSV", "fecha,cantidad,categoria,concepto\n2026-02-12,15.50,Alimentacion,Compra Semanal", "plantilla.csv")
        with col_i2:
            up = st.file_uploader("Sube tu archivo CSV", type=["csv"])
            if up and st.button("🚀 Iniciar Importación"):
                try:
                    df_imp = pd.read_csv(up)
                    res_c = supabase.table("user_categories").select("*").execute()
                    cat_map = {c['name'].upper(): (c['id'], c['type']) for c in res_c.data}
                    rows = []
                    for _, r in df_imp.iterrows():
                        if str(r['categoria']).upper() in cat_map:
                            nota = str(r['concepto']) if 'concepto' in df_imp.columns else ''
                            rows.append({
                                "user_id": st.session_state.user.id, "quantity": float(r['cantidad']), 
                                "type": cat_map[str(r['categoria']).upper()][1], "category_id": cat_map[str(r['categoria']).upper()][0], 
                                "date": str(r['fecha']), "notes": nota
                            })
                    if rows: supabase.table("user_imputs").insert(rows).execute(); st.success(f"{len(rows)} movimientos importados!")
                except: st.error("Error al procesar el archivo.")

    else:
        # --- PANEL PRINCIPAL ---
        st.title("📊 Cuadro de Mando")
        tab_mov, tab_hist, tab_cat, tab_prev, tab_mes, tab_anual = st.tabs(["💸 Movimientos", "🗄️ Historial", "⚙️ Categorías", "🔮 Previsión", "📊 Mensual", "📅 Anual"])

        res_cats = supabase.table("user_categories").select("*").execute()
        current_cats = sorted(res_cats.data, key=lambda x: x['name'].lower()) if res_cats.data else []
        res_all = supabase.table("user_imputs").select("*, user_categories(name, emoji)").execute()
        df_all = pd.DataFrame(res_all.data) if res_all.data else pd.DataFrame()
        
        if not df_all.empty: 
            df_all['date'] = pd.to_datetime(df_all['date'])
            df_all['cat_display'] = df_all['user_categories'].apply(lambda x: f"{x.get('emoji', '📁')} {x.get('name', 'S/C')}" if x else "📁 S/C")
            df_all['notes'] = df_all['notes'].fillna('') 
        
        cat_g = [c for c in current_cats if c.get('type') == 'Gasto']

        with tab_mov:
            st.subheader("Nuevo Registro")
            c1, c2, c3 = st.columns(3)
            qty = c1.number_input("Cantidad (€)", min_value=0.0, step=0.01)
            t_type = c2.selectbox("Tipo", ["Gasto", "Ingreso"])
            f_mov = c3.date_input("Fecha", datetime.now())
            c4, c5 = st.columns([1, 2])
            f_cs = [c for c in current_cats if c.get('type') == t_type]
            if f_cs:
                opciones = ["Selecciona..."] + [f"{c.get('emoji', '📁')} {c['name']}" for c in f_cs]
                sel = c4.selectbox("Categoría", opciones)
                concepto = c5.text_input("Concepto / Notas", placeholder="Ej: Cena, Compra...")
                if st.button("Guardar") and sel != "Selecciona...":
                    cat_sel = next(c for c in f_cs if f"{c.get('emoji', '📁')} {c['name']}" == sel)
                    supabase.table("user_imputs").insert({
                        "user_id": st.session_state.user.id, "quantity": qty, "type": t_type, 
                        "category_id": cat_sel['id'], "date": str(f_mov), "notes": concepto
                    }).execute(); st.rerun()
            st.divider()
            res_rec = supabase.table("user_imputs").select("*, user_categories(name, emoji)").order("date", desc=True).limit(10).execute()
            for i in (res_rec.data if res_rec.data else []):
                cat_obj = i['user_categories'] if i['user_categories'] else {}
                cat_str = f"{cat_obj.get('emoji', '📁')} {cat_obj.get('name', 'S/C')}"
                notas = f" - *{i['notes']}*" if i.get('notes') else ""
                cl1, cl2, cl3, cl4 = st.columns([3, 1, 1, 0.5])
                cl1.markdown(f"**{i['date']}** | {cat_str}{notas}")
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
                st.dataframe(df_h[['date', 'cat_display', 'notes', 'quantity', 'type']].rename(columns={'date':'Fecha','cat_display':'Categoría','notes':'Concepto','quantity':'Cantidad (€)','type':'Tipo'}).sort_values('Fecha', ascending=False), use_container_width=True, hide_index=True)

        with tab_cat:
            if st.button("➕ Añadir Categoría"): crear_categoria_dialog()
            ci, cg = st.columns(2)
            for col, t in zip([ci, cg], ["Ingreso", "Gasto"]):
                with col:
                    st.subheader(f"{t}s")
                    for c in [cat for cat in current_cats if cat.get('type') == t]:
                        with st.container(border=True):
                            k1, k2, k3 = st.columns([4, 1, 1])
                            with k1:
                                st.write(f"**{c.get('emoji', '📁')} {c['name']}**")
                                if t == "Gasto": st.caption(f"Meta: {c['budget']:.2f}€")
                            with k2:
                                if st.button("✏️", key=f"ed_{c['id']}"): editar_categoria_dialog(c)
                            with k3:
                                if st.button("🗑️", key=f"b_{c['id']}"): 
                                    supabase.table("user_categories").delete().eq("id", c['id']).execute(); st.rerun()

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
                df_pie = pd.DataFrame(cat_g)
                df_pie['display'] = df_pie.apply(lambda x: f"{x.get('emoji','📁')} {x['name']}", axis=1)
                with col_g1: st.plotly_chart(px.pie(df_pie, values='budget', names='display', hole=0.4), use_container_width=True)
                with col_g2: st.dataframe(df_pie[['display', 'budget']].rename(columns={'display':'Categoría','budget':'Presupuesto'}), hide_index=True, use_container_width=True)

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
                        c1.metric("Ingresos", f"{im:.2f}€"); c2.metric("Gastos", f"{gm:.2f}€"); c3.metric("Ahorro", f"{(im - gm):.2f}€")
                    st.divider()
                    gcm = df_m[df_m['type'] == 'Gasto'].groupby('category_id')['quantity'].sum().reset_index()
                    for _, r in pd.merge(pd.DataFrame(cat_g), gcm, left_on='id', right_on='category_id', how='left').fillna(0).iterrows():
                        p = r['quantity'] / r['budget'] if r['budget'] > 0 else 0
                        label = f"{r.get('emoji','📁')} {r['name']}"
                        st.write(f"{'🟢' if p < 0.8 else '🟡' if p <= 1 else '🔴'} **{label}**: {r['quantity']:.2f}€ / {r['budget']:.2f}€")
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
                        ca1.metric("Ingresos Anuales", f"{ia:.2f}€"); ca2.metric("Gastos Anuales", f"{ga:.2f}€"); ca3.metric("Balance Total", f"{(ia - ga):.2f}€")
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
