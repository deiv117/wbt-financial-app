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
        df_rec = df_all.sort_values('date', ascending=False).head(10) if not df_all.empty else pd.DataFrame()
        for _, i in df_rec.iterrows():
            cl1, cl2, cl3, cl4, cl5, cl6 = st.columns([1.5, 1.5, 2, 1, 0.4, 0.4])
            cl1.write(f"**{i['date'].date()}**")
            cl2.write(f"{i['cat_display']}")
            cl3.write(f"_{i['notes']}_")
            cl4.write(f"**{i['quantity']:.2f}€**")
            cl5.write("📉" if i['type'] == "Gasto" else "📈")
            if cl6.button("✏️", key=f"e_dash_{i['id']}"): editar_movimiento_dialog(i, current_cats)
            if cl6.button("🗑️", key=f"d_dash_{i['id']}"): delete_input(i['id']); st.rerun()

    with t2:
        st.subheader("Historial de Movimientos")
        h1, h2 = st.columns(2)
        f_i, f_f = h1.date_input("Desde", datetime.now()-timedelta(days=30), key="hi"), h2.date_input("Hasta", datetime.now(), key="hf")
        
        if not df_all.empty:
            df_h = df_all[(df_all['date'].dt.date >= f_i) & (df_all['date'].dt.date <= f_f)].sort_values('date', ascending=False)
            
            if df_h.empty:
                st.info("No hay movimientos en este rango de fechas.")
            else:
                st.divider()
                # Cabecera de la lista
                hc1, hc2, hc3, hc4, hc5, hc6 = st.columns([1.5, 1.5, 2, 1, 0.4, 0.4])
                hc1.caption("FECHA")
                hc2.caption("CATEGORÍA")
                hc3.caption("CONCEPTO")
                hc4.caption("CANTIDAD")
                
                for _, i in df_h.iterrows():
                    cl1, cl2, cl3, cl4, cl5, cl6 = st.columns([1.5, 1.5, 2, 1, 0.4, 0.4])
                    cl1.write(f"{i['date'].date()}")
                    cl2.write(f"{i['cat_display']}")
                    cl3.write(f"{i['notes']}")
                    cl4.write(f"**{i['quantity']:.2f}€**")
                    cl5.write("📉" if i['type'] == "Gasto" else "📈")
                    # Usamos prefijo 'h_' en el key para que no colisionen con los del Dashboard
                    if cl6.button("✏️", key=f"e_hist_{i['id']}"): editar_movimiento_dialog(i, current_cats)
                    if cl6.button("🗑️", key=f"d_hist_{i['id']}"): delete_input(i['id']); st.rerun()

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
            dfe = df_an
