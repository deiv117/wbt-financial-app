# Cabecera de views.py
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
from database import save_input, delete_input, get_categories, delete_category, upsert_profile, save_category, update_input
from components import editar_movimiento_dialog, editar_categoria_dialog, crear_categoria_dialog

def render_dashboard(df_all, current_cats, user_id):
    t1, t2, t3, t4, t5 = st.tabs(["💸 Nueva entrada", "🗄️ Historial", "🔮 Previsión", "📊 Mensual", "📅 Anual"])
    cat_g = [c for c in current_cats if c.get('type') == 'Gasto']
    ml = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]

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
                save_input({"user_id": user_id, "quantity": qty, "type": t_type, "category_id": cat_sel['id'], "date": str(f_mov), "notes": concepto})
                st.rerun()
        st.divider()
        st.subheader("Últimos movimientos")
        # Mostramos los últimos 10
        df_rec = df_all.sort_values('date', ascending=False).head(10) if not df_all.empty else pd.DataFrame()
        for _, i in df_rec.iterrows():
            cl1, cl2, cl3, cl4, cl5, cl6 = st.columns([1.5, 1.5, 2, 1, 0.4, 0.4])
            cl1.write(f"**{i['date'].date()}**")
            cl2.write(f"{i['cat_display']}")
            cl3.write(f"_{i['notes']}_")
            cl4.write(f"**{i['quantity']:.2f}€**")
            cl5.write("📉" if i['type'] == "Gasto" else "📈")
            if cl6.button("✏️", key=f"e_{i['id']}"): editar_movimiento_dialog(i, current_cats)
            if cl6.button("🗑️", key=f"d_{i['id']}"): delete_input(i['id']); st.rerun()

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

def render_categories(current_cats):
    st.title("📂 Gestión de Categorías")
    if st.button("➕ Nueva Categoría"): crear_categoria_dialog(st.session_state.user.id)
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
                    if k3.button("🗑️", key=f"cat_d_{c['id']}"): delete_category(c['id']); st.rerun()

def render_profile(user_id, p_data):
    st.title("⚙️ Mi Perfil")
    with st.form("p_form"):
        c1, c2 = st.columns(2)
        n_name = c1.text_input("Nombre", value=p_data.get('name',''))
        n_last = c1.text_input("Apellido", value=p_data.get('lastname',''))
        n_color = c1.color_picker("Color", value=p_data.get('profile_color','#636EFA'))
        n_avatar = c2.text_input("URL Foto", value=p_data.get('avatar_url',''))
        if st.form_submit_button("Guardar"):
            upsert_profile({"id": user_id, "name": n_name, "lastname": n_last, "avatar_url": n_avatar, "profile_color": n_color})
            st.rerun()

def render_import(current_cats, user_id):
    st.title("📥 Importar Datos")
    
    # --- GENERACIÓN DE PLANTILLA ---
    # Definimos las columnas que pediste
    columnas_necesarias = ["Tipo", "Cantidad", "Categoría", "Fecha", "Concepto"]
    
    # Creamos un ejemplo real basado en las categorías del usuario si existen
    ej_cat = current_cats[0]['name'] if current_cats else "Comida"
    
    df_template = pd.DataFrame([
        {
            "Tipo": "Gasto",
            "Cantidad": 50.25,
            "Categoría": ej_cat,
            "Fecha": datetime.now().strftime("%Y-%m-%d"),
            "Concepto": "Ejemplo de gasto"
        },
        {
            "Tipo": "Ingreso",
            "Cantidad": 1500.00,
            "Categoría": "Nómina",
            "Fecha": datetime.now().strftime("%Y-%m-%d"),
            "Concepto": "Sueldo mensual"
        }
    ])

    st.info("Utiliza la plantilla CSV para asegurar que los datos se importan correctamente.")
    
    # Botón de descarga
    st.download_button(
        label="📥 Descargar Plantilla CSV",
        data=df_template.to_csv(index=False).encode('utf-8'),
        file_name="plantilla_gastos.csv",
        mime="text/csv",
        key="download_csv_template"
    )
    
    st.divider()

    # --- SUBIDA DE ARCHIVO ---
    up = st.file_uploader("Selecciona tu archivo (CSV o Excel)", type=["csv", "xlsx"])
    
    if up:
        try:
            # Lectura del archivo
            df = pd.read_csv(up) if up.name.endswith('.csv') else pd.read_excel(up)
            
            st.write("### Vista previa de tus datos")
            st.dataframe(df.head(5), use_container_width=True)
            
            cols = df.columns.tolist()
            
            # Función para intentar emparejar columnas automáticamente
            def auto_match(name):
                return cols.index(name) if name in cols else 0

            st.subheader("Mapeo de Columnas")
            st.caption("Asegúrate de que cada campo apunte a la columna correcta de tu archivo.")
            
            c1, c2 = st.columns(2)
            sel_tipo = c1.selectbox("Campo: Tipo", cols, index=auto_match("Tipo"))
            sel_qty = c1.selectbox("Campo: Cantidad", cols, index=auto_match("Cantidad"))
            sel_cat = c1.selectbox("Campo: Categoría", cols, index=auto_match("Categoría"))
            sel_date = c2.selectbox("Campo: Fecha", cols, index=auto_match("Fecha"))
            sel_note = c2.selectbox("Campo: Concepto", cols, index=auto_match("Concepto"))
            
            if st.button("🚀 Iniciar Importación", use_container_width=True):
                # Diccionario para buscar IDs de categorías
                cat_lookup = {c['name'].upper().strip(): (c['id'], c['type']) for c in current_cats}
                
                success, errors = 0, 0
                
                for _, r in df.iterrows():
                    try:
                        nombre_cat = str(r[sel_cat]).upper().strip()
                        
                        if nombre_cat in cat_lookup:
                            c_id, c_type = cat_lookup[nombre_cat]
                            
                            # Limpieza de cantidad (maneja strings con comas)
                            raw_qty = str(r[sel_qty]).replace('€', '').replace(' ', '').replace(',', '.')
                            
                            # Determinar tipo final (priorizamos lo que diga el CSV si contiene 'Ing')
                            row_tipo = "Ingreso" if "ING" in str(r[sel_tipo]).upper() else "Gasto"
                            
                            save_input({
                                "user_id": user_id,
                                "quantity": float(raw_qty),
                                "type": row_tipo,
                                "category_id": c_id,
                                "date": str(pd.to_datetime(r[sel_date]).date()),
                                "notes": str(r[sel_note]) if pd.notna(r[sel_note]) else ""
                            })
                            success += 1
                        else:
                            errors += 1
                    except Exception as e:
                        errors += 1
                
                if success > 0:
                    st.success(f"✅ Se han importado {success} movimientos correctamente.")
                if errors > 0:
                    st.warning(f"⚠️ Se saltaron {errors} filas (categoría no encontrada o datos corruptos).")
                
                st.rerun()

        except Exception as e:
            st.error(f"Error al procesar el archivo: {e}")
