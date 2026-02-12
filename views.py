import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
from database import save_input, delete_input, get_categories, delete_category, upsert_profile, save_category, update_input
from components import editar_movimiento_dialog, editar_categoria_dialog, crear_categoria_dialog

def render_dashboard(df_all, current_cats, user_id):
    # --- CSS RESPONSIVE TOTAL ---
    st.markdown("""
        <style>
        /* 1. Forzar que las columnas NO se apilen nunca en horizontal */
        [data-testid="column"] {
            width: calc(100% / 5) !important; /* Aproximado para 5 columnas */
            flex: 1 1 0% !important;
            min-width: 0px !important;
        }

        /* 2. Forzar el contenedor padre a mantener el layout de fila */
        [data-testid="stHorizontalBlock"] {
            display: flex !important;
            flex-direction: row !important;
            flex-wrap: nowrap !important;
            align-items: center !important;
        }

        /* 3. Ajustar márgenes y fuentes en móvil para que quepa todo */
        @media (max-width: 640px) {
            [data-testid="stHorizontalBlock"] {
                gap: 5px !important;
            }
            .stMarkdown div p {
                font-size: 11px !important;
                white-space: nowrap;
                overflow: hidden;
                text-overflow: ellipsis;
            }
            /* Botones más compactos para que quepan en la misma línea */
            .contenedor-acciones-tabla button {
                width: 28px !important;
                height: 28px !important;
            }
        }

        /* Contenedor de acciones */
        .contenedor-acciones-tabla {
            display: flex !important;
            flex-direction: row !important;
            gap: 4px !important;
            justify-content: flex-end !important;
        }
        </style>
    """, unsafe_allow_html=True)

    t1, t2, t3, t4, t5 = st.tabs(["💸 Nueva entrada", "🗄️ Historial", "🔮 Previsión", "📊 Mensual", "📅 Anual"])
    cat_g = [c for c in current_cats if c.get('type') == 'Gasto']
    ml = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]

    with t1:
        # Formulario de entrada (ahora con keys para asegurar limpieza)
        st.subheader("Nuevo Movimiento")
        with st.form("nuevo_mov_form", clear_on_submit=True):
            c1, c2, c3 = st.columns(3)
            qty = c1.number_input("Cantidad (€)", min_value=0.0, step=0.01, key="f_qty")
            t_type = c2.selectbox("Tipo", ["Gasto", "Ingreso"], key="f_type")
            f_mov = c3.date_input("Fecha", datetime.now(), key="f_date")
            
            f_cs = [c for c in current_cats if c.get('type') == t_type]
            # CORRECCIÓN AQUÍ: Se ha corregido el bucle 'for c in f_cs'
            sel = st.selectbox("Categoría", ["Selecciona..."] + [f"{c.get('emoji', '📁')} {c['name']}" for c in f_cs], key="f_cat")
            concepto = st.text_input("Concepto", key="f_note")
            
            if st.form_submit_button("Guardar Movimiento", use_container_width=True):
                if sel != "Selecciona..." and qty > 0:
                    cat_sel = next(c for c in f_cs if f"{c.get('emoji', '📁')} {c['name']}" == sel)
                    save_input({
                        "user_id": user_id, 
                        "quantity": qty, 
                        "type": t_type, 
                        "category_id": cat_sel['id'], 
                        "date": str(f_mov), 
                        "notes": concepto
                    })
                    st.rerun()

        st.divider()
        st.subheader("Últimos movimientos")
        df_rec = df_all.sort_values('date', ascending=False).head(10) if not df_all.empty else pd.DataFrame()
        
        for _, i in df_rec.iterrows():
            # Reducimos a 5 columnas para maximizar el espacio
            cl1, cl2, cl3, cl4, cl5 = st.columns([1, 2, 1.2, 0.4, 1.2])
            cl1.write(f"{i['date'].strftime('%d/%m')}")
            cl2.write(f"{i['cat_display']}")
            cl3.write(f"**{i['quantity']:.1f}€**") # Un solo decimal para ahorrar espacio en móvil
            cl4.write("📉" if i['type'] == "Gasto" else "📈")
            
            with cl5:
                st.markdown('<div class="contenedor-acciones-tabla">', unsafe_allow_html=True)
                # Botones sin columnas internas para evitar el salto de línea de Streamlit
                if st.button("✏️", key=f"e_dash_{i['id']}"): editar_movimiento_dialog(i, current_cats)
                if st.button("🗑️", key=f"d_dash_{i['id']}"): delete_input(i['id']); st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)

    with t2:
        st.subheader("Historial de Movimientos")
        h1, h2 = st.columns(2)
        f_i = h1.date_input("Desde", datetime.now()-timedelta(days=30), key="hi")
        f_f = h2.date_input("Hasta", datetime.now(), key="hf")
        
        if not df_all.empty:
            df_h = df_all[(df_all['date'].dt.date >= f_i) & (df_all['date'].dt.date <= f_f)].sort_values('date', ascending=False)
            if not df_h.empty:
                for _, i in df_h.iterrows():
                    cl1, cl2, cl3, cl4, cl5 = st.columns([1, 2, 1.2, 0.4, 1.2])
                    cl1.write(f"{i['date'].strftime('%d/%m')}")
                    cl2.write(f"{i['cat_display']}")
                    cl3.write(f"**{i['quantity']:.1f}€**")
                    cl4.write("📉" if i['type'] == "Gasto" else "📈")
                    with cl5:
                        st.markdown('<div class="contenedor-acciones-tabla">', unsafe_allow_html=True)
                        if st.button("✏️", key=f"e_hist_{i['id']}"): editar_movimiento_dialog(i, current_cats)
                        if st.button("🗑️", key=f"d_hist_{i['id']}"): delete_input(i['id']); st.rerun()
                        st.markdown('</div>', unsafe_allow_html=True)

    with t3:
        st.subheader("🔮 Previsión y Comparativa")
        if not df_all.empty:
            df_mes_actual = df_all[(df_all['date'].dt.month == datetime.now().month) & (df_all['date'].dt.year == datetime.now().year)]
            gastos_cat = df_mes_actual[df_mes_actual['type'] == 'Gasto'].groupby('category_id')['quantity'].sum().reset_index()
            df_prev = pd.DataFrame(cat_g)
            if not df_prev.empty:
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
        c_fil1, c_fil2 = st.columns(2)
        sm = c_fil1.selectbox("Mes", ml, index=datetime.now().month-1)
        sa = c_fil2.selectbox("Año", range(2024, 2031), index=datetime.now().year-2024, key="año_mensual")
        
        if not df_all.empty:
            df_m = df_all[(df_all['date'].dt.month == ml.index(sm)+1) & (df_all['date'].dt.year == sa)]
            im = df_m[df_m['type'] == 'Ingreso']['quantity'].sum()
            gm = df_m[df_m['type'] == 'Gasto']['quantity'].sum()
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
        san = st.selectbox("Seleccionar Año", range(2024, 2031), index=datetime.now().year-2024, key="año_anual")
        if not df_all.empty:
            df_an = df_all[df_all['date'].dt.year == san]
            ia = df_an[df_an['type'] == 'Ingreso']['quantity'].sum()
            ga = df_an[df_an['type'] == 'Gasto']['quantity'].sum()
            ba = ia - ga
            
            a_i, a_g, a_b = st.columns(3)
            a_i.metric(f"Ingresos {san}", f"{ia:.2f}€")
            a_g.metric(f"Gastos {san}", f"{ga:.2f}€")
            a_b.metric(f"Balance Anual", f"{ba:.2f}€", delta=f"{ba:.2f}€", delta_color="normal" if ba >= 0 else "inverse")
            
            dfe = df_an.copy()
            dfe['mes_num'] = dfe['date'].dt.month
            rm = dfe.pivot_table(index='mes_num', columns='type', values='quantity', aggfunc='sum').fillna(0).reindex(range(1,13), fill_value=0)
            for t in ['Ingreso', 'Gasto']: 
                if t not in rm.columns: rm[t] = 0
            
            fig = go.Figure()
            fig.add_trace(go.Bar(x=ml, y=rm['Ingreso'], name='Ingreso', marker_color='#00CC96'))
            fig.add_trace(go.Bar(x=ml, y=rm['Gasto'], name='Gasto', marker_color='#EF553B'))
            fig.update_layout(barmode='group', margin=dict(l=20, r=20, t=20, b=20))
            st.plotly_chart(fig, use_container_width=True)

def render_categories(current_cats):
    st.title("📂 Gestión de Categorías")
    if st.button("➕ Nueva Categoría"): crear_categoria_dialog(st.session_state.user.id)
    
    ci, cg = st.columns(2)
    for col, t in zip([ci, cg], ["Ingreso", "Gasto"]):
        with col:
            st.subheader(f"{t}s")
            for c in [cat for cat in current_cats if cat.get('type') == t]:
                with st.container(border=True):
                    # Aquí usamos columnas normales sin el wrapper horizontal
                    k1, k2 = st.columns([4, 1])
                    k1.write(f"**{c.get('emoji', '📁')} {c['name']}**")
                    if t == "Gasto": k1.caption(f"Meta: {c['budget']:.2f}€")
                    with k2:
                        if st.button("✏️", key=f"cat_e_{c['id']}"): editar_categoria_dialog(c)
                        if st.button("🗑️", key=f"cat_d_{c['id']}"): delete_category(c['id']); st.rerun()

def render_profile(user_id, p_data):
    st.title("⚙️ Mi Perfil")
    with st.form("p_form"):
        c1, c2 = st.columns(2)
        n_name = c1.text_input("Nombre", value=p_data.get('name',''))
        n_last = c1.text_input("Apellido", value=p_data.get('lastname',''))
        n_color = c1.color_picker("Color de Perfil", value=p_data.get('profile_color','#636EFA'))
        n_avatar = c2.text_input("URL Avatar", value=p_data.get('avatar_url',''))
        if st.form_submit_button("Actualizar Perfil"):
            upsert_profile({"id": user_id, "name": n_name, "lastname": n_last, "avatar_url": n_avatar, "profile_color": n_color})
            st.rerun()

def render_import(current_cats, user_id):
    st.title("📥 Importar Movimientos")
    
    with st.expander("📖 Guía de Columnas Sugeridas", expanded=True):
        st.write("Para una importación exitosa, asegúrate de que tu archivo tenga estas columnas:")
        st.table({
            "Columna": ["Tipo", "Cantidad", "Categoría", "Fecha", "Concepto"],
            "Descripción": ["Gasto o Ingreso", "Ej: 12.50", "Nombre exacto de categoría", "AAAA-MM-DD", "Descripción libre"]
        })

    ej_cat = current_cats[0]['name'] if current_cats else "Varios"
    df_template = pd.DataFrame([{
        "Tipo": "Gasto", "Cantidad": 0.00, "Categoría": ej_cat, 
        "Fecha": datetime.now().strftime("%Y-%m-%d"), "Concepto": "Ejemplo"
    }])
    
    st.download_button(
        label="📥 Descargar Plantilla CSV",
        data=df_template.to_csv(index=False).encode('utf-8'),
        file_name="plantilla_importacion.csv",
        mime="text/csv",
        use_container_width=True
    )
    
    st.divider()
    up = st.file_uploader("Subir Archivo (CSV o Excel)", type=["csv", "xlsx"])
    
    if up:
        try:
            df = pd.read_csv(up, sep=None, engine='python') if up.name.endswith('.csv') else pd.read_excel(up)
            st.write("### Vista previa")
            st.dataframe(df.head(3), use_container_width=True)
            
            cols = df.columns.tolist()
            def find_col(name): return cols.index(name) if name in cols else 0
            
            c1, c2 = st.columns(2)
            sel_tipo = c1.selectbox("Columna Tipo", cols, index=find_col("Tipo"))
            sel_qty = c1.selectbox("Columna Cantidad", cols, index=find_col("Cantidad"))
            sel_cat = c1.selectbox("Columna Categoría", cols, index=find_col("Categoría"))
            sel_date = c2.selectbox("Columna Fecha", cols, index=find_col("Fecha"))
            sel_note = c2.selectbox("Columna Concepto", cols, index=find_col("Concepto"))
            
            if st.button("🚀 Procesar Importación", use_container_width=True):
                cat_lookup = {c['name'].upper().strip(): c['id'] for c in current_cats}
                count = 0
                for _, r in df.iterrows():
                    try:
                        name_clean = str(r[sel_cat]).upper().strip()
                        if name_clean in cat_lookup:
                            raw_qty = str(r[sel_qty]).replace('€','').replace(',','.')
                            save_input({
                                "user_id": user_id, 
                                "quantity": float(raw_qty),
                                "type": "Ingreso" if "ING" in str(r[sel_tipo]).upper() else "Gasto",
                                "category_id": cat_lookup[name_clean],
                                "date": str(pd.to_datetime(r[sel_date]).date()),
                                "notes": str(r[sel_note]) if pd.notna(r[sel_note]) else ""
                            })
                            count += 1
                    except: continue
                st.success(f"✅ Se han importado {count} movimientos."); st.rerun()
        except Exception as e:
            st.error(f"Error al leer el archivo: {e}")
