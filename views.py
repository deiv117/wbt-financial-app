import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
from database import save_input, delete_input, get_categories, delete_category, upsert_profile, save_category, update_input
from components import editar_movimiento_dialog, editar_categoria_dialog, crear_categoria_dialog

def render_dashboard(df_all, current_cats, user_id):
    # El CSS ya está cargado en main.py desde styles.py

    t1, t2, t3, t4, t5 = st.tabs(["💸 Nueva", "🗄️ Historial", "🔮 Prev", "📊 Mes", "📅 Año"])
    cat_g = [c for c in current_cats if c.get('type') == 'Gasto']
    ml = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]

    # --- PESTAÑA 1: NUEVA ENTRADA ---
    with t1:
        st.subheader("Nuevo Movimiento")
        
        # Formulario optimizado 2x2 para móvil
        with st.form("nuevo_mov_form", clear_on_submit=True):
            # Fila 1
            c1, c2 = st.columns(2)
            qty = c1.number_input("Cantidad (€)", min_value=0.0, step=0.01, key="f_qty")
            t_type = c2.selectbox("Tipo", ["Gasto", "Ingreso"], key="f_type")
            
            # Fila 2
            c3, c4 = st.columns(2)
            f_mov = c3.date_input("Fecha", datetime.now(), key="f_date")
            
            f_cs = [c for c in current_cats if c.get('type') == t_type]
            opciones_cat = ["Selecciona..."] + [f"{c.get('emoji', '📁')} {c['name']}" for c in f_cs]
            sel = c4.selectbox("Categoría", opciones_cat, key="f_cat")
            
            # Fila 3
            concepto = st.text_input("Concepto (Opcional)", key="f_note")
            
            if st.form_submit_button("💾 Guardar", use_container_width=True):
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
                    st.success("✅ Guardado")
                    st.rerun()
                else:
                    st.error("Revisa cantidad y categoría.")

        st.divider()
        st.subheader("Últimos")
        df_rec = df_all.sort_values('date', ascending=False).head(10) if not df_all.empty else pd.DataFrame()
        
        for _, i in df_rec.iterrows():
            # LAYOUT MÓVIL OPTIMIZADO (4 Columnas)
            # Quitamos la columna de icono (flecha) para que quepa todo bien.
            # Pesos: Fecha(1), Cat(3), Precio(1.5), Acciones(1.2)
            col_date, col_cat, col_qty, col_actions = st.columns([1, 3, 1.5, 1.2])
            
            col_date.write(f"**{i['date'].strftime('%d')}**") # Solo mostramos el día para ahorrar espacio
            col_cat.write(f"{i['cat_display']}")
            col_qty.write(f"**{i['quantity']:.0f}€**") # Sin decimales si es entero (visual)
            
            with col_actions:
                st.markdown('<div class="contenedor-acciones-tabla">', unsafe_allow_html=True)
                if st.button("✏️", key=f"e_d_{i['id']}"): editar_movimiento_dialog(i, current_cats)
                if st.button("🗑️", key=f"d_d_{i['id']}"): delete_input(i['id']); st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)

    # --- PESTAÑA 2: HISTORIAL ---
    with t2:
        st.subheader("Historial")
        h1, h2 = st.columns(2)
        f_i = h1.date_input("Desde", datetime.now()-timedelta(days=30), key="hi")
        f_f = h2.date_input("Hasta", datetime.now(), key="hf")
        
        if not df_all.empty:
            df_h = df_all[(df_all['date'].dt.date >= f_i) & (df_all['date'].dt.date <= f_f)].sort_values('date', ascending=False)
            if not df_h.empty:
                for _, i in df_h.iterrows():
                    # Mismo layout de 4 columnas
                    col_date, col_cat, col_qty, col_actions = st.columns([1, 3, 1.5, 1.2])
                    
                    col_date.write(f"{i['date'].strftime('%d/%m')}")
                    col_cat.write(f"{i['cat_display']}")
                    col_qty.write(f"**{i['quantity']:.0f}€**")
                    
                    with col_actions:
                        st.markdown('<div class="contenedor-acciones-tabla">', unsafe_allow_html=True)
                        if st.button("✏️", key=f"e_h_{i['id']}"): editar_movimiento_dialog(i, current_cats)
                        if st.button("🗑️", key=f"d_h_{i['id']}"): delete_input(i['id']); st.rerun()
                        st.markdown('</div>', unsafe_allow_html=True)
            else:
                st.info("Sin datos.")

    # --- PESTAÑA 3: PREVISIÓN ---
    with t3:
        st.subheader("Previsión")
        if not df_all.empty:
            df_mes_actual = df_all[(df_all['date'].dt.month == datetime.now().month) & (df_all['date'].dt.year == datetime.now().year)]
            gastos_cat = df_mes_actual[df_mes_actual['type'] == 'Gasto'].groupby('category_id')['quantity'].sum().reset_index()
            df_prev = pd.DataFrame(cat_g)
            if not df_prev.empty:
                df_prev = pd.merge(df_prev, gastos_cat, left_on='id', right_on='category_id', how='left').fillna(0)
                df_prev['Restante'] = df_prev['budget'] - df_prev['quantity']
                st.dataframe(df_prev[['emoji', 'name', 'budget', 'quantity', 'Restante']].rename(columns={'emoji':'Icono', 'name':'Categoría', 'budget':'Presupuesto', 'quantity':'Gastado'}), use_container_width=True, hide_index=True)
        
        tp = sum(c['budget'] for c in cat_g)
        mi = df_all[df_all['type']=='Ingreso'].groupby(df_all['date'].dt.to_period('M'))['quantity'].sum().mean() if not df_all.empty else 0
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Presupuesto", f"{tp:.0f}€")
        c2.metric("Ingresos Medios", f"{mi:.0f}€")
        c3.metric("Ahorro Potencial", f"{(mi - tp):.0f}€")

    # --- PESTAÑA 4: MENSUAL ---
    with t4:
        st.subheader("Balance Mes")
        c1, c2 = st.columns(2)
        sm = c1.selectbox("Mes", ml, index=datetime.now().month-1)
        sa = c2.selectbox("Año", range(2024, 2031), index=datetime.now().year-2024, key="am")
        
        if not df_all.empty:
            df_m = df_all[(df_all['date'].dt.month == ml.index(sm)+1) & (df_all['date'].dt.year == sa)]
            im = df_m[df_m['type'] == 'Ingreso']['quantity'].sum()
            gm = df_m[df_m['type'] == 'Gasto']['quantity'].sum()
            bal = im - gm
            
            m1, m2, m3 = st.columns(3)
            m1.metric("Ing", f"{im:.0f}€")
            m2.metric("Gas", f"{gm:.0f}€")
            m3.metric("Bal", f"{bal:.0f}€", delta_color="normal")
            
            st.divider()
            gcm = df_m[df_m['type'] == 'Gasto'].groupby('category_id')['quantity'].sum().reset_index()
            for _, r in pd.merge(pd.DataFrame(cat_g), gcm, left_on='id', right_on='category_id', how='left').fillna(0).iterrows():
                p = r['quantity'] / r['budget'] if r['budget'] > 0 else 0
                st.write(f"**{r.get('emoji','')} {r['name']}** ({r['quantity']:.0f}/{r['budget']:.0f})")
                st.progress(min(p, 1.0))

    # --- PESTAÑA 5: ANUAL ---
    with t5:
        st.subheader("Balance Año")
        san = st.selectbox("Año", range(2024, 2031), index=datetime.now().year-2024, key="aa")
        if not df_all.empty:
            df_an = df_all[df_all['date'].dt.year == san]
            ia = df_an[df_an['type'] == 'Ingreso']['quantity'].sum()
            ga = df_an[df_an['type'] == 'Gasto']['quantity'].sum()
            ba = ia - ga
            
            c1, c2, c3 = st.columns(3)
            c1.metric("Ing", f"{ia:.0f}€")
            c2.metric("Gas", f"{ga:.0f}€")
            c3.metric("Bal", f"{ba:.0f}€", delta_color="normal")
            
            dfe = df_an.copy()
            dfe['m'] = dfe['date'].dt.month
            rm = dfe.pivot_table(index='m', columns='type', values='quantity', aggfunc='sum').fillna(0).reindex(range(1,13), fill_value=0)
            
            fig = go.Figure()
            fig.add_trace(go.Bar(x=ml, y=rm.get('Ingreso', []), name='Ing', marker_color='#00CC96'))
            fig.add_trace(go.Bar(x=ml, y=rm.get('Gasto', []), name='Gas', marker_color='#EF553B'))
            fig.update_layout(margin=dict(l=10, r=10, t=10, b=10), showlegend=False)
            st.plotly_chart(fig, use_container_width=True)

def render_categories(current_cats):
    st.title("📂 Categorías")
    if st.button("➕ Crear"): crear_categoria_dialog(st.session_state.user.id)
    
    ci, cg = st.columns(2)
    for col, t in zip([ci, cg], ["Ingreso", "Gasto"]):
        with col:
            st.caption(f"{t}s")
            for c in [cat for cat in current_cats if cat.get('type') == t]:
                with st.container(border=True):
                    c1, c2 = st.columns([3, 1])
                    c1.write(f"**{c.get('emoji', '')} {c['name']}**")
                    with c2:
                        if st.button("✏️", key=f"ce_{c['id']}"): editar_categoria_dialog(c)
                        if st.button("🗑️", key=f"cd_{c['id']}"): delete_category(c['id']); st.rerun()

def render_profile(user_id, p_data):
    st.title("⚙️ Perfil")
    with st.form("p_form"):
        c1, c2 = st.columns(2)
        n_name = c1.text_input("Nombre", value=p_data.get('name',''))
        n_last = c1.text_input("Apellido", value=p_data.get('lastname',''))
        n_color = c1.color_picker("Color", value=p_data.get('profile_color','#636EFA'))
        n_avatar = c2.text_input("Avatar URL", value=p_data.get('avatar_url',''))
        if st.form_submit_button("Guardar"):
            upsert_profile({"id": user_id, "name": n_name, "lastname": n_last, "avatar_url": n_avatar, "profile_color": n_color})
            st.rerun()

def render_import(current_cats, user_id):
    st.title("📥 Importar")
    
    with st.expander("📖 Ayuda CSV", expanded=False):
        st.write("Columnas: Tipo, Cantidad, Categoría, Fecha, Concepto")

    ej_cat = current_cats[0]['name'] if current_cats else "General"
    df_template = pd.DataFrame([{
        "Tipo": "Gasto", "Cantidad": 0.00, "Categoría": ej_cat, 
        "Fecha": datetime.now().strftime("%Y-%m-%d"), "Concepto": "Ejemplo"
    }])
    
    st.download_button("📥 Bajar Plantilla", df_template.to_csv(index=False).encode('utf-8'), "plantilla.csv", "text/csv")
    
    st.divider()
    up = st.file_uploader("Subir CSV/Excel", type=["csv", "xlsx"])
    
    if up:
        try:
            df = pd.read_csv(up, sep=None, engine='python') if up.name.endswith('.csv') else pd.read_excel(up)
            st.dataframe(df.head(3), use_container_width=True)
            
            cols = df.columns.tolist()
            def find_col(name): return cols.index(name) if name in cols else 0
            
            c1, c2 = st.columns(2)
            sel_tipo = c1.selectbox("Columna Tipo", cols, index=find_col("Tipo"))
            sel_qty = c1.selectbox("Columna Cantidad", cols, index=find_col("Cantidad"))
            sel_cat = c1.selectbox("Columna Categoría", cols, index=find_col("Categoría"))
            sel_date = c2.selectbox("Columna Fecha", cols, index=find_col("Fecha"))
            sel_note = c2.selectbox("Columna Concepto", cols, index=find_col("Concepto"))
            
            if st.button("🚀 Importar"):
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
                st.success(f"✅ {count} importados")
                st.rerun()
        except Exception as e:
            st.error(f"Error: {e}")
