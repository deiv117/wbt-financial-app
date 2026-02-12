import streamlit as st
import pandas as pd
import math
import plotly.graph_objects as go
from datetime import datetime, timedelta
from database import save_input, delete_input, get_categories, delete_category, upsert_profile, save_category, update_input
from components import editar_movimiento_dialog, editar_categoria_dialog, crear_categoria_dialog

def render_dashboard(df_all, current_cats, user_id):
    # --- CSS MÁGICO PARA TARJETAS MÓVILES ---
    st.markdown("""
        <style>
        /* 1. Comportamiento fluido normal de las columnas */
        [data-testid="column"] {
            flex: 1 1 auto !important;
        }

        /* 2. RESPONSIVE MÓVIL: Botones 50/50 exactos dentro de las tarjetas */
        @media (max-width: 640px) {
            /* Forzamos que la sub-columna de botones se mantenga en horizontal */
            [data-testid="stVerticalBlockBorderWrapper"] [data-testid="stHorizontalBlock"] [data-testid="stHorizontalBlock"] {
                flex-direction: row !important;
                gap: 8px !important;
                margin-top: 5px !important;
            }
            /* Le damos el 50% del ancho a cada botón */
            [data-testid="stVerticalBlockBorderWrapper"] [data-testid="stHorizontalBlock"] [data-testid="stHorizontalBlock"] > [data-testid="column"] {
                width: 50% !important;
                flex: 1 1 50% !important;
                min-width: 0 !important;
            }
        }
        </style>
    """, unsafe_allow_html=True)

    t1, t2, t3, t4, t5 = st.tabs(["💸 Nueva entrada", "🗄️ Historial", "🔮 Previsión", "📊 Mensual", "📅 Anual"])
    cat_g = [c for c in current_cats if c.get('type') == 'Gasto']
    ml = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]

    with t1:
        st.subheader("Nuevo Movimiento")
        # Formulario auto-limpiable
        with st.form("nuevo_movimiento_form", clear_on_submit=True):
            c1, c2, c3 = st.columns(3)
            qty = c1.number_input("Cantidad (€)", min_value=0.0, step=0.01)
            t_type = c2.selectbox("Tipo", ["Gasto", "Ingreso"])
            f_mov = c3.date_input("Fecha", datetime.now())
            
            f_cs = [c for c in current_cats if c.get('type') == t_type]
            
            sel = st.selectbox("Categoría", ["Selecciona..."] + [f"{c.get('emoji', '📁')} {c['name']}" for c in f_cs])
            concepto = st.text_input("Concepto")
            
            if st.form_submit_button("Guardar Movimiento", use_container_width=True):
                if sel != "Selecciona...":
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
            with st.container(border=True): # Tarjeta
                col_info, col_btn = st.columns([4, 1])
                
                with col_info:
                    color_q = "red" if i['type'] == 'Gasto' else "green"
                    signo = "-" if i['type'] == 'Gasto' else "+"
                    st.markdown(f"**{i['cat_display']}** &nbsp;|&nbsp; :{color_q}[**{signo}{i['quantity']:.2f}€**]")
                    notas_txt = i['notes'] if i['notes'] else 'Sin concepto'
                    st.caption(f"📅 {i['date'].strftime('%d/%m/%Y')} &nbsp;|&nbsp; 📝 _{notas_txt}_")
                
                with col_btn:
                    # Botones side-by-side que se expanden (50/50 en móvil)
                    cb_e, cb_d = st.columns(2)
                    with cb_e:
                        if st.button("✏️", key=f"e_dash_{i['id']}", use_container_width=True): 
                            editar_movimiento_dialog(i, current_cats)
                    with cb_d:
                        if st.button("🗑️", key=f"d_dash_{i['id']}", use_container_width=True): 
                            delete_input(i['id'])
                            st.rerun()

    with t2:
        st.subheader("Historial de Movimientos")
        h1, h2 = st.columns(2)
        f_i = h1.date_input("Desde", datetime.now()-timedelta(days=30), key="hi")
        f_f = h2.date_input("Hasta", datetime.now(), key="hf")
        
        if not df_all.empty:
            df_h = df_all[(df_all['date'].dt.date >= f_i) & (df_all['date'].dt.date <= f_f)].sort_values('date', ascending=False)
            
            if df_h.empty:
                st.info("No hay movimientos en este rango de fechas.")
            else:
                st.divider()
                
                # --- PAGINACIÓN ---
                total_items = len(df_h)
                col_pag1, col_pag2, col_pag3 = st.columns([1, 1, 2])
                rows_per_page = col_pag1.selectbox("Registros por página:", [10, 25, 50, 100], index=2)
                total_pages = math.ceil(total_items / rows_per_page)
                current_page = col_pag2.number_input(f"Página (de {total_pages})", min_value=1, max_value=total_pages, value=1)
                
                start_idx = (current_page - 1) * rows_per_page
                end_idx = min(start_idx + rows_per_page, total_items)
                col_pag3.caption(f"<br>Viendo registros **{start_idx + 1}** a **{end_idx}** de un total de **{total_items}**", unsafe_allow_html=True)
                
                st.markdown("---")
                df_page = df_h.iloc[start_idx:end_idx]
                
                # --- TARJETAS HISTORIAL ---
                for _, i in df_page.iterrows():
                    with st.container(border=True):
                        col_info, col_btn = st.columns([4, 1])
                        
                        with col_info:
                            color_q = "red" if i['type'] == 'Gasto' else "green"
                            signo = "-" if i['type'] == 'Gasto' else "+"
                            st.markdown(f"**{i['cat_display']}** &nbsp;|&nbsp; :{color_q}[**{signo}{i['quantity']:.2f}€**]")
                            notas_txt = i['notes'] if i['notes'] else 'Sin concepto'
                            st.caption(f"📅 {i['date'].strftime('%d/%m/%Y')} &nbsp;|&nbsp; 📝 _{notas_txt}_")
                        
                        with col_btn:
                            cb1, cb2 = st.columns(2)
                            with cb1:
                                if st.button("✏️", key=f"e_hist_{i['id']}", use_container_width=True): 
                                    editar_movimiento_dialog(i, current_cats)
                            with cb2:
                                if st.button("🗑️", key=f"d_hist_{i['id']}", use_container_width=True): 
                                    delete_input(i['id'])
                                    st.rerun()

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
            
            # --- NUEVO: CÁLCULO DE LA LÍNEA DE AHORRO ---
            rm['Ahorro'] = rm['Ingreso'] - rm['Gasto']
            
            fig = go.Figure()
            fig.add_trace(go.Bar(x=ml, y=rm['Ingreso'], name='Ingreso', marker_color='#00CC96'))
            fig.add_trace(go.Bar(x=ml, y=rm['Gasto'], name='Gasto', marker_color='#EF553B'))
            # --- NUEVO: AÑADIMOS LA LÍNEA DE AHORRO AL GRÁFICO ---
            fig.add_trace(go.Scatter(x=ml, y=rm['Ahorro'], name='Ahorro', mode='lines+markers', line=dict(color='#636EFA', width=3), marker=dict(size=8)))
            
            fig.update_layout(barmode='group', margin=dict(l=20, r=20, t=20, b=20), legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
            st.plotly_chart(fig, use_container_width=True)

            # --- NUEVO: CÁLCULO ANUAL DE GASTOS POR CATEGORÍA ---
            st.divider()
            st.subheader("Presupuesto Anual por Categoría")
            st.caption("_(Presupuesto mensual configurado multiplicado por 12)_")
            
            gcm_anual = df_an[df_an['type'] == 'Gasto'].groupby('category_id')['quantity'].sum().reset_index()
            # Unimos los gastos anuales con la tabla de categorías
            for _, r in pd.merge(pd.DataFrame(cat_g), gcm_anual, left_on='id', right_on='category_id', how='left').fillna(0).iterrows():
                presupuesto_anual = r['budget'] * 12 # Multiplicamos la estimación por 12
                p = r['quantity'] / presupuesto_anual if presupuesto_anual > 0 else 0
                st.write(f"**{r.get('emoji','📁')} {r['name']}** ({r['quantity']:.2f} / {presupuesto_anual:.2f}€)")
                st.progress(min(p, 1.0))

def render_categories(current_cats):
    st.title("📂 Gestión de Categorías")
    if st.button("➕ Nueva Categoría"): 
        crear_categoria_dialog(st.session_state.user.id)
    
    ci, cg = st.columns(2)
    for col, t in zip([ci, cg], ["Ingreso", "Gasto"]):
        with col:
            st.subheader(f"{t}s")
            for c in [cat for cat in current_cats if cat.get('type') == t]:
                with st.container(border=True):
                    # Aquí usamos columnas normales sin el wrapper horizontal
                    k1, k2 = st.columns([4, 1])
                    k1.write(f"**{c.get('emoji', '📁')} {c['name']}**")
                    if t == "Gasto": 
                        k1.caption(f"Meta: {c['budget']:.2f}€")
                    with k2:
                        # Botones 50/50 aplicados a las categorías también
                        kb1, kb2 = st.columns(2)
                        with kb1:
                            if st.button("✏️", key=f"cat_e_{c['id']}", use_container_width=True): 
                                editar_categoria_dialog(c)
                        with kb2:
                            if st.button("🗑️", key=f"cat_d_{c['id']}", use_container_width=True): 
                                delete_category(c['id'])
                                st.rerun()

def render_profile(user_id, p_data):
    st.title("⚙️ Mi Perfil")
    with st.form("p_form"):
        c1, c2 = st.columns(2)
        n_name = c1.text_input("Nombre", value=p_data.get('name',''))
        n_last = c1.text_input("Apellido", value=p_data.get('lastname',''))
        n_color = c1.color_picker("Color de Perfil", value=p_data.get('profile_color','#636EFA'))
        n_avatar = c2.text_input("URL Avatar", value=p_data.get('avatar_url',''))
        if st.form_submit_button("Actualizar Perfil"):
            upsert_profile({
                "id": user_id, 
                "name": n_name, 
                "lastname": n_last, 
                "avatar_url": n_avatar, 
                "profile_color": n_color
            })
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
                    except:
                        continue
                st.success(f"✅ Se han importado {count} movimientos.")
                st.rerun()
        except Exception as e:
            st.error(f"Error al leer el archivo: {e}")
