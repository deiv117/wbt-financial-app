import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta

def render_main_dashboard(df_all, user_profile):
    st.markdown("""
        <style>
        div[data-testid="stVerticalBlockBorderWrapper"]:has(div[data-testid="stMetric"]) {
            min-height: 130px;
            display: flex;
            flex-direction: column;
            justify-content: center;
        }
        </style>
    """, unsafe_allow_html=True)

    st.title(f"👋 Hola, {user_profile.get('name', 'Usuario')}")
    st.caption("Aquí tienes el pulso de tu economía hoy.")

    saldo_inicial = user_profile.get('initial_balance', 0) or 0
    
    if not df_all.empty:
        total_ingresos = df_all[df_all['type'] == 'Ingreso']['quantity'].sum()
        total_gastos = df_all[df_all['type'] == 'Gasto']['quantity'].sum()
        saldo_total = saldo_inicial + total_ingresos - total_gastos

        hoy = datetime.now()
        df_mes = df_all[(df_all['date'].dt.month == hoy.month) & (df_all['date'].dt.year == hoy.year)]
        ahorro_mes = df_mes[df_mes['type'] == 'Ingreso']['quantity'].sum() - df_mes[df_mes['type'] == 'Gasto']['quantity'].sum()
    else:
        saldo_total = saldo_inicial
        ahorro_mes = 0

    k1, k2, k3 = st.columns(3)
    with k1:
        with st.container(border=True):
            st.metric(label="💰 Patrimonio Neto", value=f"{saldo_total:,.2f}€", delta=" ", delta_color="off")
    with k2:
        with st.container(border=True):
            st.metric(label=f"📅 Ahorro {datetime.now().strftime('%B')}", value=f"{ahorro_mes:,.2f}€", delta=f"{ahorro_mes:,.2f}€")
    with k3:
        with st.container(border=True):
            st.metric(label="👥 Grupos (Deuda)", value="0.00€", delta="Próximamente", delta_color="off")

    st.divider()
    st.subheader("📈 Evolución de tu Patrimonio")
    
    if not df_all.empty or saldo_inicial > 0:
        df_chart = df_all.copy().sort_values('date') if not df_all.empty else pd.DataFrame(columns=['date', 'quantity', 'type'])
        if not df_chart.empty:
            df_chart['real_qty'] = df_chart.apply(lambda x: x['quantity'] if x['type'] == 'Ingreso' else -x['quantity'], axis=1)
            df_chart['saldo_acumulado'] = df_chart['real_qty'].cumsum() + saldo_inicial
            df_daily = df_chart.groupby('date')['saldo_acumulado'].last().reset_index()
            
            fecha_inicio = df_daily['date'].min() - timedelta(days=1)
            row_inicio = pd.DataFrame({'date': [fecha_inicio], 'saldo_acumulado': [saldo_inicial]})
            df_daily = pd.concat([row_inicio, df_daily]).sort_values('date')

            fig = go.Figure()
            fig.add_trace(go.Scatter(x=df_daily['date'], y=df_daily['saldo_acumulado'], fill='tozeroy', mode='lines', line=dict(color='#636EFA', width=3)))
            fig.update_layout(margin=dict(l=0, r=0, t=10, b=0), yaxis_title="Euros (€)", hovermode="x unified", height=350)
            st.plotly_chart(fig, use_container_width=True)
