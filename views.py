import streamlit as st
import pandas as pd
import math
import time
import plotly.graph_objects as go
import calendar
from datetime import datetime, timedelta
# Importamos las funciones de base de datos y componentes
from database import (save_input, delete_input, get_categories, delete_category, 
                      upsert_profile, save_category, update_input, upload_avatar, 
                      change_password, get_historical_income)
from components import editar_movimiento_dialog, editar_categoria_dialog, crear_categoria_dialog

# --- 1. NUEVA PANTALLA: RESUMEN GLOBAL (Landing Page) ---
def render_main_dashboard(df_all, user_profile):
    # --- CSS CORONA: IGUALAR ALTURA DE TARJETAS ---
    st.markdown("""
        <style>
        /* Busca contenedores con borde que TENGAN dentro una métrica y les fuerza altura */
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

    # --- CÁLCULO DE KPIs ---
    
    # Recuperamos el saldo inicial del perfil (si es None pone 0)
    saldo_inicial = user_profile.get('initial_balance', 0) or 0
    
    if not df_all.empty:
        # A. Saldo Total Histórico (Incluyendo Saldo Inicial)
        total_ingresos = df_all[df_all['type'] == 'Ingreso']['quantity'].sum()
        total_gastos = df_all[df_all['type'] == 'Gasto']['quantity'].sum()
        
        # FÓRMULA MAESTRA: Lo que tenía al principio + Lo que he ganado - Lo que he gastado
        saldo_total = saldo_inicial + total_ingresos - total_gastos

        # B. Ahorro Este Mes
        hoy = datetime.now()
        df_mes = df_all[(df_all['date'].dt.month == hoy.month) & (df_all['date'].dt.year == hoy.year)]
        ingresos_mes = df_mes[df_mes['type'] == 'Ingreso']['quantity'].sum()
        gastos_mes = df_mes[df_mes['type'] == 'Gasto']['quantity'].sum()
        ahorro_mes = ingresos_mes - gastos_mes
    else:
        saldo_total = saldo_inicial
        ahorro_mes = 0

    # --- TARJETAS DE MÉTRICAS (KPIs) ---
    k1, k2, k3 = st.columns(3)

    with k1:
        with st.container(border=True):
            # Truco: delta=" " (espacio) reserva el hueco vertical para igualar altura
            st.metric(label="💰 Patrimonio Neto", value=f"{saldo_total:,.2f}€", delta=" ", delta_color="off", help="Saldo Inicial + Ingresos - Gastos")
    
    with k2:
        with st.container(border=True):
            st.metric(label=f"📅 Ahorro {datetime.now().strftime('%B')}", value=f"{ahorro_mes:,.2f}€", delta=f"{ahorro_mes:,.2f}€")
        
    with k3:
        with st.container(border=True):
            st.metric(label="👥 Grupos (Deuda)", value="0.00€", delta="Próximamente", delta_color="off")

    st.divider()

    # --- GRÁFICO DE EVOLUCIÓN DE PATRIMONIO ---
    st.subheader("📈 Evolución de tu Patrimonio")
    
    # Mostramos gráfico si hay movimientos O si hay saldo inicial configurado
    if not df_all.empty or saldo_inicial > 0:
        df_chart = df_all.copy().sort_values('date') if not df_all.empty else pd.DataFrame(columns=['date', 'quantity', 'type'])
        
        # Lógica para construir la línea temporal
        if not df_chart.empty:
            df_chart['real_qty'] = df_chart.apply(lambda x: x['quantity'] if x['type'] == 'Ingreso' else -x['quantity'], axis=1)
            # El acumulado empieza sumando el saldo inicial
            df_chart['saldo_acumulado'] = df_chart['real_qty'].cumsum() + saldo_inicial
            
            # Agrupar por día para evitar dientes de sierra en el mismo día
            df_daily = df_chart.groupby('date')['saldo_acumulado'].last().reset_index()
            
            # Truco visual: Añadir un punto al inicio (fecha del primer mov - 1 día) con el saldo inicial
            # para que el gráfico arranque desde el saldo inicial y no desde 0
            fecha_inicio = df_daily['date'].min() - timedelta(days=1)
            row_inicio = pd.DataFrame({'date': [fecha_inicio], 'saldo_acumulado': [saldo_inicial]})
            df_daily = pd.concat([row_inicio, df_daily]).sort_values('date')

            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=df_daily['date'], 
                y=df_daily['saldo_acumulado'],
                fill='tozeroy',
                mode='lines',
                line=dict(color='#636EFA', width=3),
                name='Saldo'
            ))

            fig.update_layout(
                margin=dict(l=0, r=0, t=10, b=0),
                yaxis_title="Euros (€)",
                hovermode="x unified",
                height=350
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
             st.info(f"Tu patrimonio actual es tu saldo inicial: {saldo_inicial}€. Añade movimientos para ver la evolución gráfica.")
    else:
        st.info("Configura tu saldo inicial en el Perfil o añade movimientos para ver tu evolución.")

# --- 2. GESTIÓN DE MOVIMIENTOS ---
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
            [data-testid="stVerticalBlockBorderWrapper"] [data-testid="stHorizontalBlock"] [data-testid="stHorizontalBlock"] {
                flex-direction: row !important;
                gap: 8px !important;
                margin-top: 5px !important;
            }
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
            with st.container(border=True):
                col_info, col_btn = st.columns([4, 1])
                with col_info:
                    color_q = "red" if i['type'] == 'Gasto' else "green"
                    signo = "-" if i['type'] == 'Gasto' else "+"
                    st.markdown(f"**{i['cat_display']}** &nbsp;|&nbsp; :{color_q}[**{signo}{i['quantity']:.2f}€**]")
                    notas_txt = i['notes'] if i['notes'] else 'Sin concepto'
                    st.caption(f"📅 {i['date'].strftime('%d/%m/%Y')} &nbsp;|&nbsp; 📝 _{notas_txt}_")
                
                with col_btn:
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
        
        # --- CÁLCULOS PREVIOS ---
        tp = sum(c['budget'] for c in cat_g)
        # Calculamos la media de ingresos (puedes usar el histórico que creamos o la media de la tabla)
        mi = df_all[df_all['type']=='Ingreso']['quantity'].sum() / len(df_all['date'].dt.to_period('M').unique()) if not df_all.empty else 0
        ahorro_potencial = mi - tp

        # --- PRIMERO: LAS TRES COLUMNAS CON MÉTRICAS ---
        st.markdown("#### Resumen de Objetivos")
        m1, m2, m3 = st.columns(3)
        
        with m1:
            with st.container(border=True):
                st.metric("Límite Gastos", f"{tp:,.2f}€", help="Suma de todos tus presupuestos mensuales")
        
        with m2:
            with st.container(border=True):
                st.metric("Ingresos Medios", f"{mi:,.2f}€", help="Media de ingresos reales registrados")
        
        with m3:
            with st.container(border=True):
                color_ahorro = "normal" if ahorro_potencial > 0 else "inverse"
                st.metric("Ahorro Potencial", f"{ahorro_potencial:,.2f}€", 
                          delta=f"{(ahorro_potencial/mi*100):.1f}%" if mi > 0 else None,
                          delta_color=color_ahorro)

        st.divider()

        # --- SEGUNDO: LA TABLA DETALLADA POR CATEGORÍAS ---
        st.markdown("#### Detalle por Categoría (Mes Actual)")
        if not df_all.empty:
            # Filtramos solo el mes actual para la comparativa de la tabla
            hoy = datetime.now()
            df_mes_actual = df_all[(df_all['date'].dt.month == hoy.month) & (df_all['date'].dt.year == hoy.year)]
            
            # Agrupamos gastos reales por categoría
            gastos_cat = df_mes_actual[df_mes_actual['type'] == 'Gasto'].groupby('category_id')['quantity'].sum().reset_index()
            
            # Unimos con la lista de categorías de gasto
            df_prev = pd.DataFrame(cat_g)
            if not df_prev.empty:
                df_prev = pd.merge(df_prev, gastos_cat, left_on='id', right_on='category_id', how='left').fillna(0)
                df_prev['Diferencia'] = df_prev['budget'] - df_prev['quantity']
                
                # Formateamos la tabla para que se vea profesional
                st.dataframe(
                    df_prev[['emoji', 'name', 'budget', 'quantity', 'Diferencia']].rename(
                        columns={'emoji':'Icono', 'name':'Categoría', 'budget':'Presupuesto (€)', 'quantity':'Gastado (€)'}
                    ), 
                    use_container_width=True, 
                    hide_index=True
                )
        else:
            st.info("Añade movimientos para ver la comparativa detallada.")

    with t4:
        st.subheader("Análisis Mensual")
        c_fil1, c_fil2 = st.columns(2)
        
        sm = c_fil1.selectbox("Mes", ml, index=datetime.now().month-1)
        sa = c_fil2.selectbox("Año", range(2024, 2031), index=datetime.now().year-2024, key="año_mensual")
        
        # --- LÓGICA DE HISTORIAL ---
        import calendar
        from database import get_historical_income
        
        month_idx = ml.index(sm) + 1
        _, last_day = calendar.monthrange(sa, month_idx)
        fecha_analisis = f"{sa}-{month_idx:02d}-{last_day}"
        
        h_data = get_historical_income(user_id, fecha_analisis)
        h_sueldo = float(h_data.get('base_salary', 0) or 0)
        h_extras = float(h_data.get('other_fixed_income', 0) or 0)
        h_freq = int(h_data.get('other_income_frequency', 1) or 1) 
        
        h_extras_mensualizados = h_extras / h_freq if h_freq > 0 else 0
        h_total_previsto = h_sueldo + h_extras_mensualizados

        if not df_all.empty:
            df_m = df_all[(df_all['date'].dt.month == month_idx) & (df_all['date'].dt.year == sa)]
            
            im_real = df_m[df_m['type'] == 'Ingreso']['quantity'].sum()
            gm_real = df_m[df_m['type'] == 'Gasto']['quantity'].sum()
            ahorro_real = im_real - gm_real
            
            # Métricas principales
            c_i, c_g, c_b = st.columns(3)
            c_i.metric("Ingresos Reales", f"{im_real:,.2f}€")
            c_g.metric("Gastos Reales", f"{gm_real:,.2f}€")
            c_b.metric("Ahorro Neto", f"{ahorro_real:,.2f}€", delta=f"{ahorro_real:,.2f}€")
            
            # --- MENSAJE PERSONALIZADO Y MOTIVADOR ---
            st.write("---")
            if im_real > h_total_previsto:
                exceso_ingreso = im_real - h_total_previsto
                st.success(f"🌟 **¡Enhorabuena!** Este mes has ingresado **{exceso_ingreso:,.2f}€ más** de lo previsto. Tu ahorro neto real ha sido de **{ahorro_real:,.2f}€**. ¡Sigue así!")
            elif ahorro_real > 0:
                st.info(f"✅ Buen trabajo. Has logrado terminar el mes con un ahorro de **{ahorro_real:,.2f}€**.")
            else:
                st.warning(f"⚠️ Este mes los gastos han superado a los ingresos por **{abs(ahorro_real):,.2f}€**. ¡Toca revisar el presupuesto!")
            
            st.divider()
            st.subheader("Progreso por Categoría (Semáforo)")
            gcm = df_m[df_m['type'] == 'Gasto'].groupby('category_id')['quantity'].sum().reset_index()
            
            for _, r in pd.merge(pd.DataFrame(cat_g), gcm, left_on='id', right_on='category_id', how='left').fillna(0).iterrows():
                gastado = r['quantity']
                presupuesto = r['budget']
                
                if presupuesto > 0:
                    pct = gastado / presupuesto
                    pct_clamp = min(pct, 1.0)
                    if pct <= 0.75: color_bar = "#00CC96"
                    elif pct <= 1.0: color_bar = "#FFC107"
                    else: color_bar = "#EF553B"
                    
                    restante = presupuesto - gastado
                    if restante >= 0:
                        txt_restante = f"<span style='color: gray; font-size: 0.9em;'>Quedan {restante:.2f}€</span>"
                    else:
                        txt_restante = f"<span style='color: #EF553B; font-weight: bold; font-size: 0.9em;'>Exceso de {abs(restante):.2f}€</span>"
                    
                    html_bar = f"""
                    <div style="margin-bottom: 15px;">
                        <div style="display: flex; justify-content: space-between; margin-bottom: 5px; font-family: sans-serif;">
                            <span><strong>{r.get('emoji','📁')} {r['name']}</strong> ({gastado:.2f}€ / {presupuesto:.2f}€)</span>
                            {txt_restante}
                        </div>
                        <div style="width: 100%; background-color: rgba(128, 128, 128, 0.2); border-radius: 5px; height: 12px;">
                            <div style="width: {pct_clamp * 100}%; background-color: {color_bar}; height: 12px; border-radius: 5px; transition: width 0.5s ease;"></div>
                        </div>
                    </div>
                    """
                    st.markdown(html_bar, unsafe_allow_html=True)

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
            
            rm['Ahorro'] = rm['Ingreso'] - rm['Gasto']
            
            fig = go.Figure()
            fig.add_trace(go.Bar(x=ml, y=rm['Ingreso'], name='Ingreso', marker_color='#00CC96'))
            fig.add_trace(go.Bar(x=ml, y=rm['Gasto'], name='Gasto', marker_color='#EF553B'))
            fig.add_trace(go.Scatter(x=ml, y=rm['Ahorro'], name='Ahorro', mode='lines+markers', line=dict(color='#636EFA', width=3), marker=dict(size=8)))
            
            fig.update_layout(barmode='group', margin=dict(l=20, r=20, t=20, b=20), legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
            st.plotly_chart(fig, use_container_width=True)

            st.divider()
            st.subheader("Progreso Anual por Categoría")
            st.caption("_(Presupuesto mensual configurado multiplicado por 12)_")
            
            gcm_anual = df_an[df_an['type'] == 'Gasto'].groupby('category_id')['quantity'].sum().reset_index()
            
            for _, r in pd.merge(pd.DataFrame(cat_g), gcm_anual, left_on='id', right_on='category_id', how='left').fillna(0).iterrows():
                gastado = r['quantity']
                presupuesto_anual = r['budget'] * 12
                
                if presupuesto_anual > 0:
                    pct = gastado / presupuesto_anual
                    pct_clamp = min(pct, 1.0)
                    if pct <= 0.75: color_bar = "#00CC96"
                    elif pct <= 1.0: color_bar = "#FFC107"
                    else: color_bar = "#EF553B"
                    
                    restante = presupuesto_anual - gastado
                    if restante >= 0:
                        txt_restante = f"<span style='color: gray; font-size: 0.9em;'>Quedan {restante:.2f}€</span>"
                    else:
                        txt_restante = f"<span style='color: #EF553B; font-weight: bold; font-size: 0.9em;'>Exceso de {abs(restante):.2f}€</span>"
                    
                    html_bar = f"""
                    <div style="margin-bottom: 15px;">
                        <div style="display: flex; justify-content: space-between; margin-bottom: 5px; font-family: sans-serif;">
                            <span><strong>{r.get('emoji','📁')} {r['name']}</strong> ({gastado:.2f}€ / {presupuesto_anual:.2f}€)</span>
                            {txt_restante}
                        </div>
                        <div style="width: 100%; background-color: rgba(128, 128, 128, 0.2); border-radius: 5px; height: 12px;">
                            <div style="width: {pct_clamp * 100}%; background-color: {color_bar}; height: 12px; border-radius: 5px; transition: width 0.5s ease;"></div>
                        </div>
                    </div>
                    """
                    st.markdown(html_bar, unsafe_allow_html=True)

# --- 3. CATEGORÍAS ---
def render_categories(current_cats):
    st.title("📂 Gestión de Categorías")
    if st.button("➕ Nueva Categoría"): 
        crear_categoria_dialog(st.session_state.user['id'])
    
    ci, cg = st.columns(2)
    for col, t in zip([ci, cg], ["Ingreso", "Gasto"]):
        with col:
            st.subheader(f"{t}s")
            for c in [cat for cat in current_cats if cat.get('type') == t]:
                with st.container(border=True):
                    k1, k2 = st.columns([4, 1])
                    k1.write(f"**{c.get('emoji', '📁')} {c['name']}**")
                    if t == "Gasto": 
                        k1.caption(f"Meta: {c['budget']:.2f}€")
                    with k2:
                        kb1, kb2 = st.columns(2)
                        with kb1:
                            if st.button("✏️", key=f"cat_e_{c['id']}", use_container_width=True): 
                                editar_categoria_dialog(c)
                        with kb2:
                            if st.button("🗑️", key=f"cat_d_{c['id']}", use_container_width=True): 
                                delete_category(c['id'])
                                st.rerun()

# --- 4. PERFIL (VERSIÓN BLINDADA Y COMPLETA) ---
def render_profile(user_id, p_data):
    st.title("⚙️ Mi Perfil")
    
    with st.container(border=True):
        st.subheader("👤 Datos Personales")
        c_ava, c_form = st.columns([1, 2])
        
        with c_ava:
            # 1. Recuperamos la URL del avatar
            avatar_url = p_data.get('avatar_url')
            
            # 2. Lógica Segura para la Inicial
            # Si 'name' es None o "" (vacío), usamos 'Usuario' para evitar el error de índice [0]
            raw_name = p_data.get('name')
            name_safe = raw_name if raw_name and raw_name.strip() else 'Usuario'
            initial = name_safe[0].upper()
            
            # Color de fondo
            p_color = p_data.get('profile_color', '#636EFA')

            # 3. Mostramos Imagen o Círculo con Inicial
            if avatar_url:
                st.image(avatar_url, width=150)
            else:
                st.markdown(f'''
                    <div style="width:150px;height:150px;
                    background-color:{p_color};
                    border-radius:50%; display:flex; align-items:center;
                    justify-content:center; color:white;
                    font-size:50px; font-weight:bold;">
                    {initial}
                    </div>
                ''', unsafe_allow_html=True)
            
            uploaded_file = st.file_uploader("Cambiar foto (Máx 5MB)", type=['png', 'jpg', 'jpeg'])
        
        with c_form:
            with st.form("perfil_form"):
                # Usamos ( ... or "") para asegurar que no se rompa si el dato es None
                n_name = st.text_input("Nombre", value=p_data.get('name') or "")
                n_last = st.text_input("Apellido", value=p_data.get('lastname') or "")
                n_color = st.color_picker("Color de Perfil", value=p_color)
                n_social = st.toggle("Modo Social", value=p_data.get('social_active', False))
                
                st.divider()
                st.subheader("💰 Configuración Financiera")

                # Aseguramos tipos numéricos
                n_balance = st.number_input("Saldo Inicial (€)", value=float(p_data.get('initial_balance', 0) or 0))
                n_salary = st.number_input("Nómina Base (€)", value=float(p_data.get('base_salary', 0) or 0))
                
                # Configuración de Ingresos Extra
                c_other1, c_other2 = st.columns(2)
                n_other = c_other1.number_input("Otros Ingresos (€)", value=float(p_data.get('other_fixed_income', 0) or 0))
                
                # Mapa de frecuencias
                freq_map = {1: "Mensual", 2: "Bimestral", 3: "Trimestral", 6: "Semestral", 12: "Anual"}
                curr_freq_val = int(p_data.get('other_income_frequency', 1) or 1)
                
                # Buscamos el índice correcto para el selectbox
                try:
                    freq_idx = list(freq_map.keys()).index(curr_freq_val)
                except ValueError:
                    freq_idx = 0 # Por defecto Mensual si falla

                freq_txt = c_other2.selectbox("Frecuencia", list(freq_map.values()), index=freq_idx)
                # Convertimos el texto seleccionado de vuelta a número (clave del diccionario)
                n_freq = [k for k, v in freq_map.items() if v == freq_txt][0]

                n_pagas = st.slider("Pagas al año", 12, 16, int(p_data.get('payments_per_year', 12) or 12))
                
                if st.form_submit_button("💾 Guardar Todo"):
                    # A. Subida de Avatar
                    final_avatar = avatar_url
                    if uploaded_file:
                        new_url = upload_avatar(uploaded_file, user_id)
                        if new_url: final_avatar = new_url
                    
                    # B. Preparar datos para guardar
                    new_data = {
                        "id": user_id,
                        "name": n_name,
                        "lastname": n_last,
                        "profile_color": n_color,
                        "social_active": n_social,
                        "avatar_url": final_avatar,
                        "initial_balance": n_balance,
                        "base_salary": n_salary,
                        "other_fixed_income": n_other, 
                        "other_income_frequency": n_freq,
                        "payments_per_year": n_pagas
                    }
                    
                    # C. Guardar en Base de Datos
                    if upsert_profile(new_data):
                        # D. LA MAGIA: Recalcular presupuestos por % automáticamente
                        monthly_extras = n_other / n_freq if n_freq > 0 else 0
                        total_monthly = n_salary + monthly_extras
                        
                        from database import recalculate_category_budgets
                        n_updated = recalculate_category_budgets(user_id, total_monthly)
                        
                        # E. Actualizar sesión y recargar
                        st.session_state.user.update(new_data)
                        
                        msg = "✅ Perfil actualizado."
                        if n_updated > 0:
                            msg += f" Se han recalculado {n_updated} categorías automáticamente."
                        
                        st.success(msg)
                        time.sleep(1.5)
                        st.rerun()

    # --- B. DATOS ECONÓMICOS ---
    with st.container(border=True):
        st.subheader("💰 Configuración Financiera")
        st.info("Cualquier cambio aquí se guardará en tu historial.")
        
        with st.form("finance_form"):
            st.markdown("##### 🏦 Patrimonio Base")
            n_balance = st.number_input("Saldo Inicial en cuentas (€)", 
                                        value=float(p_data.get('initial_balance', 0.0) or 0.0), 
                                        help="Dinero total disponible antes de empezar a usar la app.")
            
            st.divider()
            
            st.markdown("##### 💼 Nómina y Pagas")
            c_nom1, c_nom2 = st.columns(2)
            
            n_salary = c_nom1.number_input("Nómina Base Mensual (€)", 
                                       value=float(p_data.get('base_salary', 0.0) or 0.0),
                                       help="Lo que ingresas limpio al mes.")
                                       
            n_pagas = c_nom2.slider("Número de pagas al año", 12, 16, int(p_data.get('payments_per_year', 12) or 12))

            st.markdown("##### ➕ Ingresos Adicionales Recurrentes")
            c_ext1, c_ext2 = st.columns(2)
            
            n_other = c_ext1.number_input("Cantidad (€)", 
                                       value=float(p_data.get('other_fixed_income', 0.0) or 0.0),
                                       help="Alquileres, bonos fijos, ayudas, etc.")
            
            freq_options = {1: "Cada Mes (Mensual)", 2: "Cada 2 Meses (Bimestral)", 3: "Cada 3 Meses (Trimestral)", 
                            6: "Cada 6 Meses (Semestral)", 12: "Cada Año (Anual)"}
            
            current_freq_val = int(p_data.get('other_income_frequency', 1) or 1)
            keys_list = list(freq_options.keys())
            try:
                idx_freq = keys_list.index(current_freq_val)
            except ValueError:
                idx_freq = 0
                
            sel_freq_txt = c_ext2.selectbox("Frecuencia de cobro", list(freq_options.values()), index=idx_freq)
            n_freq = [k for k, v in freq_options.items() if v == sel_freq_txt][0]

            mensual_extra_real = n_other / n_freq if n_freq > 0 else 0
            total_mensual_estimado = n_salary + mensual_extra_real
            
            st.caption(f"📊 **Resumen:** Cobras **{n_salary:,.2f}€** de nómina + **{n_other:,.2f}€** ({sel_freq_txt}).") 
            st.caption(f"💰 Esto equivale a un ingreso medio mensual de aprox: **{total_mensual_estimado:,.2f}€**")
            
            if st.form_submit_button("💾 Guardar Nueva Configuración Financiera"):
                # Calculamos el nuevo ingreso total antes de guardar
                total_nuevo = n_salary + (n_other / n_freq if n_freq > 0 else 0)
                
                new_finance = {
                    "id": user_id,
                    "initial_balance": n_balance,
                    "base_salary": n_salary,
                    "other_fixed_income": n_other, 
                    "other_income_frequency": n_freq,
                    "payments_per_year": n_pagas
                }
                
                success = upsert_profile(new_finance)
                if success:
                    # --- LA MAGIA OCURRE AQUÍ ---
                    from database import recalculate_category_budgets # Import local para evitar ciclos
                    recalculate_category_budgets(user_id, total_nuevo)
                    
                    st.session_state.user.update(new_finance)
                    st.success("✅ Datos y presupuestos actualizados")
                    time.sleep(1)
                    st.rerun()

    # --- C. SEGURIDAD ---
    with st.expander("🔐 Seguridad y Contraseña"):
        with st.form("pass_form"):
            p1 = st.text_input("Nueva Contraseña", type="password")
            p2 = st.text_input("Confirmar Contraseña", type="password")
            
            if st.form_submit_button("Cambiar Contraseña"):
                if p1 == p2 and len(p1) >= 6:
                    ok, msg = change_password(p1)
                    if ok:
                        st.success("✅ Contraseña actualizada correctamente")
                    else:
                        st.error(f"Error: {msg}")
                else:
                    st.error("Las contraseñas no coinciden o son muy cortas.")

# --- 5. IMPORTAR ---
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
