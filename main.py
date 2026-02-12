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

# --- FUNCIONES DIALOG ---
@st.dialog("➕ Nueva Categoría")
def crear_categoria_dialog():
    lista_emojis = ["📁", "💰", "🍔", "🏠", "🚗", "🛒", "🔌", "🎬", "🏥", "✈️", "👔", "🎓", "🎁", "🏋️", "🍹", "📱", "🐾", "💡", "🛠️", "🍕"]
    c1, c2 = st.columns([1, 2])
    emoji_sel = c1.selectbox("Emoji", lista_emojis)
    emoji_custom = c1.text_input("U otro...", value="")
    emoji_final = emoji_custom if emoji_custom else emoji_sel
    name = c2.text_input("Nombre")
    c_type = st.selectbox("Tipo", ["Gasto", "Ingreso"])
    budget = st.number_input("Presupuesto Mensual (€)", min_value=0.0) if c_type == "Gasto" else 0.0
    if st.button("Guardar"):
        if name:
            supabase.table("user_categories").insert({"user_id": st.session_state.user.id, "name": name, "type": c_type, "budget": budget, "emoji": emoji_final}).execute()
            st.rerun()

@st.dialog("✏️ Editar Categoría")
def editar_categoria_dialog(cat_data):
    lista_emojis = ["📁", "💰", "🍔", "🏠", "🚗", "🛒", "🔌", "🎬", "🏥", "✈️", "👔", "🎓", "🎁", "🏋️", "🍹", "📱", "🐾", "💡", "🛠️", "🍕"]
    c1, c2 = st.columns([1, 2])
    try: idx = lista_emojis.index(cat_data.get('emoji', '📁'))
    except: idx = 0
    emoji_sel = c1.selectbox("Emoji", lista_emojis, index=idx)
    emoji_custom = c1.text_input("U otro...", value="")
    emoji_final = emoji_custom if emoji_custom else emoji_sel
    new_name = c2.text_input("Nombre", value=cat_data['name'])
    new_budget = 0.0
    if cat_data['type'] == 'Gasto':
        new_budget = st.number_input("Presupuesto Mensual (€)", value=float(cat_data['budget']), min_value=0.0)
    if st.button("Actualizar Categoría"):
        if new_name:
            supabase.table("user_categories").update({"name": new_name, "emoji": emoji_final, "budget": new_budget}).eq("id", cat_data['id']).execute()
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
    try:
        cat_actual_str = f"{mov_data['user_categories']['emoji']} {mov_data['user_categories']['name']}"
        idx_cat = opciones.index(cat_actual_str)
    except:
        idx_cat = 0
    n_sel_cat = st.selectbox("Categoría", opciones, index=idx_cat)
    n_notes = st.text_input("Concepto", value=str(mov_data.get('notes') or ''))
    if st.button("Guardar Cambios"):
        cat_obj = next(c for c in f_cs if f"{c.get('emoji', '📁')} {c['name']}" == n_sel_cat)
        supabase.table("user_imputs").update({
            "quantity": n_qty, "date": str(n_date), "type": n_type,
            "category_id": cat_obj['id'], "notes": n_notes
        }).eq("id", mov_data['id']).execute()
        st.rerun()

# --- LÓGICA DE LOGIN ---
if not st.session_state.user:
    _, col_login, _ = st.columns([1, 1.5, 1])
    with col_login:
        st.write("#")
        with st.form("login_form"):
            st.markdown("<h1 class='login-title'>💰 Finanzas App</h1>", unsafe_allow_html=True)
            email = st.text_input("Email")
            password = st.text_input("Contraseña", type="password")
            if st.form_submit_button("Entrar", use_container_width=True):
                try:
                    res = supabase.auth.sign_in_with_password({"email": email, "password": password})
                    if res.user:
                        st.session_state.user = res.user
                        st.rerun()
                except: st.error("Acceso denegado.")
else:
    # --- ARREGLO DEL FONDO ---
    st.markdown("<style>.stApp { background-image: none !important; }</style>", unsafe_allow_html=True)

    # --- SIDEBAR ---
    with st.sidebar:
        res_p = supabase.table("profiles").select("*").eq("id", st.session_state.user.id).maybe_single().execute()
        p_data = res_p.data if (hasattr(res_p, 'data') and res_p.data) else {}
        nombre, apellido = p_data.get('name', ''), p_data.get('lastname', '')
        avatar_url, bg_color = p_data.get('avatar_url', ""), p_data.get('profile_color', "#636EFA")
        iniciales = ((nombre[0] if nombre else "") + (apellido[0] if apellido else "")).upper()
        if not iniciales: iniciales = st.session_state.user.email[0].upper()

        st.markdown('<div class="sidebar-user-container">', unsafe_allow_html=True)
        if avatar_url: st.markdown(f'<img src="{avatar_url}" class="avatar-circle">', unsafe_allow_html=True)
        else: st.markdown(f'<div class="avatar-circle" style="background-color: {bg_color};">{iniciales}</div>', unsafe_allow_html=True)
        st.markdown(f"**{nombre} {apellido}**")
        if st.button("Cerrar Sesión"):
            supabase.auth.sign_out(); st.session_state.user = None; st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
        st.divider()
        if st.button("📊 Panel de Control"): st.session_state.menu_actual = "📊 Panel"; st.rerun()
        if st.button("📂 Configurar Categorías"): st.session_state.menu_actual = "📂 Categorías"; st.rerun()
        if st.button("⚙️ Perfil"): st.session_state.menu_actual = "⚙️ Perfil"; st.rerun()
        if st.button("📥 Importar"): st.session_state.menu_actual = "📥 Importar"; st.rerun()

    # --- CARGA DE DATOS ---
    res_cats = supabase.table("user_categories").select("*").execute()
    current_cats = sorted(res_cats.data, key=lambda x: x['name'].lower()) if res_cats.data else []
    res_all = supabase.table("user_imputs").select("*, user_categories(id, name, emoji, budget)").execute()
    df_all = pd.DataFrame(res_all.data) if res_all.data else pd.DataFrame()
    if not df_all.empty:
        df_all['date'] = pd.to_datetime(df_all['date'])
        df_all['cat_display'] = df_all['user_categories'].apply(lambda x: f"{x.get('emoji', '📁')} {x.get('name', 'S/C')}" if x else "📁 S/C")
        df_all['notes'] = df_all['notes'].fillna('')
    cat_g = [c for c in current_cats if c.get('type') == 'Gasto']

    # --- PÁGINAS ---
    if st.session_state.menu_actual == "📂 Categorías":
        st.title("📂 Gestión de Categorías")
        if st.button("➕ Nueva Categoría"): crear_categoria_dialog()
        ci, cg = st.columns(2)
        for col, t in zip([ci, cg], ["Ingreso", "Gasto"]):
            with col:
                st.subheader(f"{t}s")
                for c in [cat for cat in current_cats if cat.get('type') == t]:
                    with st.container(border=True):
                        k1, k2, k3 = st.columns([4, 1, 1])
                        k1.write(f"**{c.get('emoji', '📁')} {c['name']}**")
                        if t == "Gasto": k1.caption(f"Meta: {c['budget']:.2f}€")
                        if k2.button("✏️", key=f"cat_e_{c['id']}"): editar_categoria_dialog(c)
                        if k3.button("🗑️", key=f"cat_d_{c['id']}"): supabase.table("user_categories").delete().eq("id", c['id']).execute(); st.rerun()

    elif st.session_state.menu_actual == "⚙️ Perfil":
        st.title("⚙️ Mi Perfil")
        with st.form("p_form"):
            c1, c2 = st.columns(2)
            n_name = c1.text_input("Nombre", value=nombre)
            n_last = c1.text_input("Apellido", value=apellido)
            n_color = c1.color_picker("Color", value=bg_color)
            n_avatar = c2.text_input("URL Foto", value=avatar_url)
            if st.form_submit_button("Guardar"):
                supabase.table("profiles").upsert({"id": st.session_state.user.id, "name": n_name, "lastname": n_last, "avatar_url": n_avatar, "profile_color": n_color}).execute(); st.rerun()

    elif st.session_state.menu_actual == "📥 Importar":
        st.title("📥 Importar CSV")
        up = st.file_uploader("Archivo", type=["csv"])
        if up and st.button("Procesar"):
            try:
                df_imp = pd.read_csv(up)
                cat_map = {c['name'].upper(): (c['id'], c['type']) for c in current_cats}
                rows = [{"user_id": st.session_state.user.id, "quantity": float(r['cantidad']), "type": cat_map[str(r['categoria']).upper()][1], "category_id": cat_map[str(r['categoria']).upper()][0], "date": str(r['fecha']), "notes": str(r.get('concepto', ''))} for _, r in df_imp.iterrows() if str(r['categoria']).upper() in cat_map]
                if rows: supabase.table("user_imputs").insert(rows).execute(); st.success("Listo"); st.rerun()
            except: st.error("Error en formato")

    else:
        # --- PANEL PRINCIPAL ---
        st.title("📊 Cuadro de Mando")
        t1, t2, t3, t4, t5 = st.tabs(["💸 Registro", "🗄️ Historial", "🔮 Previsión", "📊 Mensual", "📅 Anual"])

        with t1:
            st.subheader("Nuevo Movimiento")
            c1, c2, c3 = st.columns(3)
            qty = c1.number_input("Cantidad (€)", min_value=0.0)
            t_type = c2.selectbox("Tipo", ["Gasto", "Ingreso"])
            f_mov = c3.date_input("Fecha", datetime.now())
            f_cs = [c for c in current_cats if c.get('type') == t_type]
            if f_cs:
                sel = st.selectbox("Categoría", ["Selecciona..."] + [f"{c.get('emoji', '📁')} {c['name']}" for c in f_cs])
                concepto = st.text_input("Concepto")
                if st.button("Guardar") and sel != "Selecciona...":
                    cat_sel = next(c for c in f_cs if f"{c.get('emoji', '📁')} {c['name']}" == sel)
                    supabase.table("user_imputs").insert({"user_id": st.session_state.user.id, "quantity": qty, "type": t_type, "category_id": cat_sel['id'], "date": str(f_mov), "notes": concepto}).execute(); st.rerun()
            st.divider()
            st.subheader("Últimos movimientos")
            res_rec = supabase.table("user_imputs").select("*, user_categories(id, name, emoji)").order("date", desc=True).limit(10).execute()
            for i in (res_rec.data or []):
                cat_obj = i.get('user_categories') or {}
                cl1, cl2, cl3, cl4, cl5, cl6 = st.columns([1.5, 1.5, 1.5, 1, 0.4, 0.4])
                cl1.write(f"**{i['date']}**")
                cl2.write(f"{cat_obj.get('emoji','📁')} {cat_obj.get('name','S/C')}")
                cl3.write(f"_{str(i.get('notes') or '')}_")
                cl4.write(f"**{i['quantity']:.2f}€**")
                cl5.write("📉" if i['type'] == "Gasto" else "📈")
                if cl6.button("✏️", key=f"e_{i['id']}"): editar_movimiento_dialog(i, current_cats)
                if cl6.button("🗑️", key=f"d_{i['id']}"): supabase.table("user_imputs").delete().eq("id", i['id']).execute(); st.rerun()

        with t2:
            st.subheader("Historial")
            h1, h2 = st.columns(2)
            f_i, f_f = h1.date_input("Desde", datetime.now()-timedelta(days=30), key="hi"), h2.date_input("Hasta", datetime.now(), key="hf")
            if not df_all.empty:
                df_h = df_all[(df_all['date'].dt.date >= f_i) & (df_all['date'].dt.date <= f_f)]
                df_h_display = df_h[['date', 'cat_display', 'notes', 'quantity', 'type']].rename(columns={'notes': 'Concepto', 'date': 'Fecha', 'cat_display': 'Categoría', 'quantity': 'Cantidad', 'type': 'Tipo'})
                st.dataframe(df_h_display.sort_values('Fecha', ascending=False), use_container_width=True, hide_index=True)

        with t3:
            st.subheader("🔮 Previsión y Comparativa")
            if not df_all.empty:
                df_mes_actual = df_all[(df_all['date'].dt.month == datetime.now().month) & (df_all['date'].dt.year == datetime.now().year)]
                gastos_cat = df_mes_actual[df_mes_actual['type'] == 'Gasto'].groupby('category_id')['quantity'].sum().reset_index()
                df_prev = pd.DataFrame(cat_g)
                df_prev = pd.merge(df_prev, gastos_cat, left_on='id', right_on='category_id', how='left').fillna(0)
                df_prev['Diferencia'] = df_prev['budget'] - df_prev['quantity']
                st.dataframe(df_prev[['emoji', 'name', 'budget', 'quantity', 'Diferencia']].rename(columns={'emoji':'Icono', 'name':'Categoría', 'budget':'Presupuesto (€)', 'quantity':'Gastado (€)'}), use_container_width=True, hide_index=True)
            tp = sum(c['budget'] for c in cat_g)
            mi = df_all[df_all['type']=='Ingreso'].groupby(df_all['date'].dt.to_period('M'))['quantity'].sum().mean() if not df_all.empty else 0
            m1, m2, m3 = st.columns(3)
            m1.metric("Límite Gastos", f"{tp:.2f}€")
            m2.metric("Ingresos Medios", f"{mi:.2f}€")
            m3.metric("Ahorro Potencial", f"{(mi - tp):.2f}€")

        with t4:
            st.subheader("Análisis Mensual")
            # --- FILTRO COMBINADO MES Y AÑO ---
            ml = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
            c_fil1, c_fil2 = st.columns(2)
            sm = c_fil1.selectbox("Mes", ml, index=datetime.now().month-1)
            sa = c_fil2.selectbox("Año", range(2024, 2031), index=datetime.now().year-2024, key="año_mensual")
            
            if not df_all.empty:
                df_m = df_all[(df_all['date'].dt.month == ml.index(sm)+1) & (df_all['date'].dt.year == sa)]
                im, gm = df_m[df_m['type'] == 'Ingreso']['quantity'].sum(), df_m[df_m['type'] == 'Gasto']['quantity'].sum()
                balance = im - gm
                
                c_i, c_g, c_b = st.columns(3)
                c_i.metric("Ingresos", f"{im:.2f}€")
                c_g.metric("Gastos", f"{gm:.2f}€")
                c_b.metric("Balance", f"{balance:.2f}€", delta=f"{balance:.2f}€", delta_color="normal" if balance >= 0 else "inverse")
                
                st.divider()
                gcm = df_m[df_m['type'] == 'Gasto'].groupby('category_id')['quantity'].sum().reset_index()
                for _, r in pd.merge(pd.DataFrame(cat_g), gcm, left_on='id', right_on='category_id', how='left').fillna(0).iterrows():
                    p = r['quantity'] / r['budget'] if r['budget'] > 0 else 0
                    st.write(f"**{r.get('emoji','📁')} {r['name']}** ({r['quantity']:.2f} / {r['budget']:.2f}€)")
                    st.progress(min(p, 1.0))

        with t5:
            st.subheader("Análisis Anual")
            # --- FILTRO POR AÑO ---
            san = st.selectbox("Seleccionar Año", range(2024, 2031), index=datetime.now().year-2024, key="año_anual")
            
            if not df_all.empty:
                df_an = df_all[df_all['date'].dt.year == san]
                ia, ga = df_an[df_an['type'] == 'Ingreso']['quantity'].sum(), df_an[df_an['type'] == 'Gasto']['quantity'].sum()
                ba = ia - ga
                
                a_i, a_g, a_b = st.columns(3)
                a_i.metric(f"Total Ingresos {san}", f"{ia:.2f}€")
                a_g.metric(f"Total Gastos {san}", f"{ga:.2f}€")
                a_b.metric(f"Ahorro Acumulado {san}", f"{ba:.2f}€", delta=f"{ba:.2f}€", delta_color="normal" if ba >= 0 else "inverse")
                
                dfe = df_an.copy(); dfe['mes_num'] = dfe['date'].dt.month
                rm = dfe.pivot_table(index='mes_num', columns='type', values='quantity', aggfunc='sum').fillna(0).reindex(range(1,13), fill_value=0)
                for t in ['Ingreso', 'Gasto']: 
                    if t not in rm.columns: rm[t] = 0
                
                fig = go.Figure()
                fig.add_trace(go.Bar(x=ml, y=rm['Ingreso'], name='Ingreso', marker_color='#00CC96'))
                fig.add_trace(go.Bar(x=ml, y=rm['Gasto'], name='Gasto', marker_color='#EF553B'))
                st.plotly_chart(fig, use_container_width=True)
