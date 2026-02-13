import streamlit as st
import pandas as pd
import math
import calendar
import plotly.graph_objects as go
from datetime import datetime, timedelta
from database import save_input, delete_input, get_historical_income
from components import editar_movimiento_dialog

def render_dashboard(df_all, current_cats, user_id):
    st.markdown("""
        <style>
        [data-testid="column"] { flex: 1 1 auto !important; }
        @media (max-width: 640px) {
            [data-testid="stVerticalBlockBorderWrapper"] [data-testid="stHorizontalBlock"] [data-testid="stHorizontalBlock"] {
                flex-direction: row !important; gap: 8px !important; margin-top: 5px !important;
            }
            [data-testid="stVerticalBlockBorderWrapper"] [data-testid="stHorizontalBlock"] [data-testid="stHorizontalBlock"] > [data-testid="column"] {
                width: 50% !important; flex: 1 1 50% !important; min-width: 0 !important;
            }
        }
        </style>
    """, unsafe_allow_html=True)

    t1, t2, t3, t4, t5 = st.tabs(["💸 Nueva entrada", "🗄️ Historial", "🔮 Previsión", "📊 Mensual", "📅 Anual"])
    cat_g = [c for c in current_cats if c.get('type') == 'Gasto']
    ml = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]

    with t1:
        st.subheader("Nuevo Movimiento")
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
                    save_input({"user_id": user_id, "quantity": qty, "type": t_type, "category_id": cat_sel['id'], "date": str(f_mov), "notes": concepto})
                    st.rerun()
        
        st.divider()
        st.subheader("Últimos movimientos")
        df_rec = df_all.sort_values('date', ascending=False).head(10) if not df_all.empty else pd.DataFrame()
        for _, i in df_rec.iterrows():
            with st.container(border=True):
                col_info, col_btn = st.columns([4, 1])
                with col_info:
                    color_q, signo = ("red", "-") if i['type'] == 'Gasto' else ("green", "+")
                    st.markdown(f"**{i['cat_display']}** | :{color_q}[**{signo}{i['quantity']:.2f}€**]")
                    st.caption(f"📅 {i['date'].strftime('%d/%m/%Y')} | 📝 _{i['notes'] or 'Sin concepto'}_")
                with col_btn:
                    cb_e, cb_d = st.columns(2)
                    if cb_e.button("✏️", key=f"e_dash_{i['id']}", use_container_width=True): editar_movimiento_dialog(i, current_cats)
                    if cb_d.button("🗑️", key=f"d_dash_{i['id']}", use_container_width=True):
                        delete_input(i['id'])
                        st.rerun()

    with t2:
        st.subheader("Historial de Movimientos")
        h1, h2 = st.columns(2)
        f_i, f_f = h1.date_input("Desde", datetime.now()-timedelta(days=30), key="hi"), h2.date_input("Hasta", datetime.now(), key="hf")
        if not df_all.empty:
            df_h = df_all[(df_all['date'].dt.date >= f_i) & (df_all['date'].dt.date <= f_f)].sort_values('date', ascending=False)
            if df_h.empty: st.info("No hay movimientos.")
            else:
                st.divider()
                rows_per_page = st.selectbox("Registros por página:", [10, 25, 50, 100], index=2)
                total_pages = math.ceil(len(df_h) / rows_per_page)
                current_page = st.number_input(f"Página (de {total_pages})", min_value=1, max_value=total_pages, value=1)
                start_idx = (current_page - 1) * rows_per_page
                for _, i in df_h.iloc[start_idx:start_idx + rows_per_page].iterrows():
                    with st.container(border=True):
                        col_info, col_btn = st.columns([4, 1])
                        with col_info:
                            color_q, signo = ("red", "-") if i['type'] == 'Gasto' else ("green", "+")
                            st.markdown(f"**{i['cat_display']}** | :{color_q}[**{signo}{i['quantity']:.2f}€**]")
                            st.caption(f"📅 {i['date'].strftime('%d/%m/%Y')} | 📝 _{i['notes'] or 'Sin concepto'}_")
                        with col_btn:
                            cb1, cb2 = st.columns(2)
                            if cb1.button("✏️", key=f"e_hist_{i['id']}", use_container_width=True): editar_movimiento_dialog(i, current_cats)
                            if cb2.button("🗑️", key=f"d_hist_{i['id']}", use_container_width=True):
                                delete_input(i['id'])
                                st.rerun()

    with t3:
        st.subheader("🔮 Previsión y Comparativa")
        tp = sum(c['budget'] for c in cat_g)
        mi = df_all[df_all['type']=='Ingreso']['quantity'].sum() / len(df_all['date'].dt.to_period('M').unique()) if not df_all.empty else 0
        ahorro_pot = mi - tp
        st.markdown("#### Resumen de Objetivos")
        m1, m2, m3 = st.columns(3)
        with m1: st.container(border=True).metric("Límite Gastos", f"{tp:,.2f}€")
        with m2: st.container(border=True).metric("Ingresos Medios", f"{mi:,.2f}€")
        with m3: st.container(border=True).metric("Ahorro Potencial", f"{ahorro_pot:,.2f}€", delta=f"{(ahorro_pot/mi*100):.1f}%" if mi > 0 else None)
        
        st.divider()
        st.markdown("#### Detalle por Categoría (Mes Actual)")
        if not df_all.empty:
            df_mes = df_all[(df_all['date'].dt.month == datetime.now().month) & (df_all['date'].dt.year == datetime.now().year)]
            gastos_cat = df_mes[df_mes['type'] == 'Gasto'].groupby('category_id')['quantity'].sum().reset_index()
            df_prev = pd.merge(pd.DataFrame(cat_g), gastos_cat, left_on='id', right_on='category_id', how='left').fillna(0)
            df_prev['Diferencia'] = df_prev['budget'] - df_prev['quantity']
            st.dataframe(df_prev[['emoji', 'name', 'budget', 'quantity', 'Diferencia']].rename(columns={'emoji':'Icono', 'name':'Categoría', 'budget':'Presupuesto (€)', 'quantity':'Gastado (€)'}), use_container_width=True, hide_index=True)

    with t4:
        st.subheader("Análisis Mensual")
        c1, c2 = st.columns(2)
        sm, sa = c1.selectbox("Mes", ml, index=datetime.now().month-1), c2.selectbox("Año", range(2024, 2031), index=datetime.now().year-2024)
        m_idx = ml.index(sm) + 1
        h_data = get_historical_income(user_id, f"{sa}-{m_idx:02d}-{calendar.monthrange(sa, m_idx)[1]}")
        h_prev = float(h_data.get('base_salary', 0)) + (float(h_data.get('other_fixed_income', 0)) / int(h_data.get('other_income_frequency', 1)))
        
        if not df_all.empty:
            df_m = df_all[(df_all['date'].dt.month == m_idx) & (df_all['date'].dt.year == sa)]
            im, gm = df_m[df_m['type'] == 'Ingreso']['quantity'].sum(), df_m[df_m['type'] == 'Gasto']['quantity'].sum()
            ahorro = im - gm
            st.columns(3)[0].metric("Ingresos Reales", f"{im:,.2f}€")
            st.columns(3)[1].metric("Gastos Reales", f"{gm:,.2f}€")
            st.columns(3)[2].metric("Ahorro Neto", f"{ahorro:,.2f}€", delta=f"{ahorro:,.2f}€")
            
            if im > h_prev: st.success(f"🌟 ¡Enhorabuena! Has ingresado {im-h_prev:,.2f}€ más de lo previsto.")
            
            st.divider()
            gcm = df_m[df_m['type'] == 'Gasto'].groupby('category_id')['quantity'].sum().reset_index()
            for _, r in pd.merge(pd.DataFrame(cat_g), gcm, left_on='id', right_on='category_id', how='left').fillna(0).iterrows():
                if r['budget'] > 0:
                    pct = min(r['quantity'] / r['budget'], 1.0)
                    color = "#00CC96" if pct <= 0.75 else "#FFC107" if pct <= 1.0 else "#EF553B"
                    st.markdown(f"**{r.get('emoji','📁')} {r['name']}** ({r['quantity']:.2f}€ / {r['budget']:.2f}€)")
                    st.markdown(f'<div style="width:100%; background:rgba(128,128,128,0.2); height:12px; border-radius:5px;"><div style="width:{pct*100}%; background:{color}; height:12px; border-radius:5px;"></div></div>', unsafe_allow_html=True)

    with t5:
        st.subheader(f"Análisis Anual")
        san = st.selectbox("Seleccionar Año", range(2024, 2031), index=datetime.now().year-2024)
        if not df_all.empty:
            df_an = df_all[df_all['date'].dt.year == san]
            ia, ga = df_an[df_an['type'] == 'Ingreso']['quantity'].sum(), df_an[df_an['type'] == 'Gasto']['quantity'].sum()
            st.columns(3)[2].metric("Balance Anual", f"{ia-ga:.2f}€", delta=f"{ia-ga:.2f}€")
            
            dfe = df_an.copy()
            dfe['mes_num'] = dfe['date'].dt.month
            rm = dfe.pivot_table(index='mes_num', columns='type', values='quantity', aggfunc='sum').fillna(0).reindex(range(1,13), fill_value=0)
            fig = go.Figure()
            fig.add_trace(go.Bar(x=ml, y=rm.get('Ingreso', 0), name='Ingreso', marker_color='#00CC96'))
            fig.add_trace(go.Bar(x=ml, y=rm.get('Gasto', 0), name='Gasto', marker_color='#EF553B'))
            st.plotly_chart(fig, use_container_width=True)
