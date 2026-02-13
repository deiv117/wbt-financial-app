import streamlit as st
import pandas as pd
import math
import plotly.graph_objects as go
import calendar
from database import get_historical_income
from datetime import datetime, timedelta
# Importamos las nuevas funciones necesarias (upload_avatar, change_password)
from database import save_input, delete_input, get_categories, delete_category, upsert_profile, save_category, update_input, upload_avatar, change_password
from components import editar_movimiento_dialog, editar_categoria_dialog, crear_categoria_dialog

# --- 1. NUEVA PANTALLA: RESUMEN GLOBAL (Landing Page) ---
def render_main_dashboard(df_all, user_profile):
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
        st.container(border=True)
        st.metric(label="💰 Patrimonio Neto", value=f"{saldo_total:,.2f}€", help="Saldo Inicial + Ingresos - Gastos")
    
    with k2:
        st.container(border=True)
        st.metric(label=f"📅 Ahorro {datetime.now().strftime('%B')}", value=f"{ahorro_mes:,.2f}€", delta=f"{ahorro_mes:,.2f}€")
        
    with k3:
        st.container(border=True)
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
             # Si no hay movimientos pero sí saldo inicial, mostramos mensaje
             st.info(f"Tu patrimonio actual es tu saldo inicial: {saldo_inicial}€. Añade movimientos para ver la evolución gráfica.")
    else:
        st.info("Configura tu saldo inicial en el Perfil o añade movimientos para ver tu evolución.")

# --- 2. GESTIÓN DE MOVIMIENTOS (Tu código original) ---
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
        
        # Selectores de fecha
        sm = c_fil1.selectbox("Mes", ml, index=datetime.now().month-1)
        sa = c_fil2.selectbox("Año", range(2024, 2031), index=datetime.now().year-2024, key="año_mensual")
        
        # --- LÓGICA DE HISTORIAL (NOVEDAD) ---
        # 1. Calculamos el último día del mes seleccionado para buscar la configuración vigente entonces
        import calendar
        from database import get_historical_income # Asegúrate de tener esto importado arriba
        
        month_idx = ml.index(sm) + 1
        # Obtiene el último día del mes (ej: 28, 30 o 31)
        _, last_day = calendar.monthrange(sa, month_idx)
        fecha_analisis = f"{sa}-{month_idx:02d}-{last_day}"
        
        # 2. Recuperamos el sueldo que tenías EN ESA FECHA
        h_data = get_historical_income(user_id, fecha_analisis)
        h_sueldo = float(h_data.get('base_salary', 0) or 0)
        h_extras = float(h_data.get('other_fixed_income', 0) or 0)
        h_total_fijo = h_sueldo + h_extras

        # 3. Mostramos el contexto histórico
        with st.expander(f"ℹ️ Contexto financiero en {sm} {sa}", expanded=False):
            st.write(f"En esa fecha, tu configuración era:")
            st.markdown(f"- Nómina Base: **{h_sueldo:,.2f}€**")
            st.markdown(f"- Otros Ingresos Fijos: **{h_extras:,.2f}€**")
            st.markdown(f"- **Total Fijo: {h_total_fijo:,.2f}€**")

        if not df_all.empty:
            # Filtramos movimientos del mes seleccionado
            df_m = df_all[(df_all['date'].dt.month == month_idx) & (df_all['date'].dt.year == sa)]
            
            # Cálculo de movimientos reales (Manuales)
            im_variable = df_m[df_m['type'] == 'Ingreso']['quantity'].sum()
            gm = df_m[df_m['type'] == 'Gasto']['quantity'].sum()
            
            # El balance real es: Lo que ingresaste fijo (teórico) + variable (manual) - gastos
            # NOTA: Si tú ya metes la nómina como un movimiento manual cada mes, 
            # no sumes 'h_total_fijo' aquí para no duplicar. 
            # Aquí asumo que quieres ver el balance de flujos registrados:
            balance = im_variable - gm
            
            # Métricas
            c_i, c_g, c_b = st.columns(3)
            c_i.metric("Entradas Registradas", f"{im_variable:.2f}€", help="Ingresos añadidos manualmente")
            c_g.metric("Gastos Totales", f"{gm:.2f}€")
            c_b.metric("Balance (Flujo)", f"{balance:.2f}€", delta=f"{balance:.2f}€", delta_color="normal" if balance >= 0 else "inverse")
            
            # Métrica adicional de Ahorro Teórico (Considerando el sueldo fijo histórico)
            ahorro_teorico = (h_total_fijo + im_variable) - gm
            # Solo mostramos esto si el usuario no mete la nómina a mano (para evitar confusión)
            # O lo mostramos como "Capacidad de Ahorro"
            if h_total_fijo > 0:
                st.caption(f"💰 Si sumamos tus ingresos fijos de entonces ({h_total_fijo:,.2f}€), tu capacidad de ahorro real fue de **{ahorro_teorico:,.2f}€**")
            
            st.divider()
            st.subheader("Progreso por Categoría (Semáforo)")
            gcm = df_m[df_m['type'] == 'Gasto'].groupby('category_id')['quantity'].sum().reset_index()
            
            for _, r in pd.merge(pd.DataFrame(cat_g), gcm, left_on='id', right_on='category_id', how='left').fillna(0).iterrows():
                gastado = r['quantity']
                presupuesto = r['budget']
                
                if presupuesto > 0:
                    pct = gastado / presupuesto
                    pct_clamp = min(pct, 1.0)
                    
                    # Lógica del semáforo
                    if pct <= 0.75: color_bar = "#00CC96" # Verde
                    elif pct <= 1.0: color_bar = "#FFC107" # Naranja/Amarillo
                    else: color_bar = "#EF553B" # Rojo
                    
                    # Cálculo de exceso o restante
                    restante = presupuesto - gastado
                    if restante >= 0:
                        txt_restante = f"<span style='color: gray; font-size: 0.9em;'>Quedan {restante:.2f}€</span>"
                    else:
                        txt_restante = f"<span style='color: #EF553B; font-weight: bold; font-size: 0.9em;'>Exceso de {abs(restante):.2f}€</span>"
                    
                    # HTML de la barra de progreso
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
            
            # Línea de Ahorro
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
                presupuesto_anual = r['budget'] * 12 # Objetivo anual
                
                if presupuesto_anual > 0:
                    pct = gastado / presupuesto_anual
                    pct_clamp = min(pct, 1.0)
                    
                    # Lógica del semáforo
                    if pct <= 0.75: color_bar = "#00CC96" # Verde
                    elif pct <= 1.0: color_bar = "#FFC107" # Naranja/Amarillo
                    else: color_bar = "#EF553B" # Rojo
                    
                    # Cálculo de exceso o restante
                    restante = presupuesto_anual - gastado
                    if restante >= 0:
                        txt_restante = f"<span style='color: gray; font-size: 0.9em;'>Quedan {restante:.2f}€</span>"
                    else:
                        txt_restante = f"<span style='color: #EF553B; font-weight: bold; font-size: 0.9em;'>Exceso de {abs(restante):.2f}€</span>"
                    
                    # HTML de la barra de progreso (Fondo transparente para que se adapte al dark mode)
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

# --- 3. CATEGORÍAS (Tu código original) ---
def render_categories(current_cats):
    st.title("📂 Gestión de Categorías")
    if st.button("➕ Nueva Categoría"): 
        crear_categoria_dialog(st.session_state.user['id']) # OJO: Ajuste para el user['id']
    
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

# --- 4. NUEVA VERSIÓN DE PERFIL (Actualizada) ---
def render_profile(user_id, p_data):
    st.title("⚙️ Mi Perfil")
    
    # --- A. DATOS PERSONALES Y AVATAR ---
    with st.container(border=True):
        st.subheader("👤 Datos Personales")
        
        c_ava, c_form = st.columns([1, 2])
        
        with c_ava:
            # Mostrar Avatar (Usamos st.session_state para forzar refresco inmediato)
            current_avatar = st.session_state.user.get('avatar_url')
            if current_avatar:
                st.image(current_avatar, width=150)
            else:
                st.markdown(f"""
                    <div style="width:150px;height:150px;background-color:{p_data.get('profile_color','#636EFA')};
                    border-radius:50%;display:flex;align-items:center;justify-content:center;color:white;font-size:50px;font-weight:bold;">
                    {p_data.get('name','U')[0].upper()}
                    </div>
                """, unsafe_allow_html=True)
            
            uploaded_file = st.file_uploader("Cambiar foto (Máx 5MB)", type=['png', 'jpg', 'jpeg'])
        
        with c_form:
            with st.form("perfil_form"):
                n_name = st.text_input("Nombre", value=p_data.get('name',''))
                n_last = st.text_input("Apellido", value=p_data.get('lastname',''))
                n_color = st.color_picker("Color de Perfil", value=p_data.get('profile_color','#636EFA'))
                
                submitted_perfil = st.form_submit_button("Guardar Datos Personales")
                
                if submitted_perfil:
                    # 1. Subida de Imagen
                    final_avatar_url = p_data.get('avatar_url', '')
                    if uploaded_file:
                        url_nueva = upload_avatar(uploaded_file, user_id)
                        if url_nueva:
                            final_avatar_url = url_nueva
                    
                    # 2. Guardar en BD
                    new_data = {
                        "id": user_id, 
                        "name": n_name, 
                        "lastname": n_last, 
                        "avatar_url": final_avatar_url, 
                        "profile_color": n_color,
                        # Mantener datos financieros
                        "initial_balance": p_data.get('initial_balance', 0),
                        "base_salary": p_data.get('base_salary', 0),
                        "other_fixed_income": p_data.get('other_fixed_income', 0),
                        "payments_per_year": p_data.get('payments_per_year', 12)
                    }
                    
                    success = upsert_profile(new_data)
                    
                    if success:
                        # 3. ACTUALIZACIÓN INMEDIATA DEL ESTADO (TRUCO CLAVE)
                        # Actualizamos la sesión de Streamlit manualmente YA,
                        # así el Sidebar y la foto se ven bien antes de recargar.
                        st.session_state.user.update(new_data)
                        st.toast("✅ Perfil actualizado correctamente")
                        time.sleep(1) # Pequeña pausa para ver el mensaje
                        st.rerun()

    # --- B. DATOS ECONÓMICOS (VERSIONADA) ---
    with st.container(border=True):
        st.subheader("💰 Configuración Financiera")
        st.info("Cualquier cambio aquí se guardará en tu historial. Si ves datos antiguos en gráficas pasadas, es porque usamos el sueldo que tenías entonces.")
        
        with st.form("finance_form"):
            c1, c2 = st.columns(2)
            n_balance = c1.number_input("Saldo Inicial (€)", 
                                        value=float(p_data.get('initial_balance', 0.0) or 0.0), 
                                        help="Patrimonio antes de usar la app.")
            
            n_pagas = c2.slider("Número de pagas", 12, 16, int(p_data.get('payments_per_year', 12) or 12))

            st.divider()
            st.markdown("##### 📥 Ingresos Fijos Mensuales")
            
            ci1, ci2 = st.columns(2)
            n_salary = ci1.number_input("Nómina Base (€)", 
                                       value=float(p_data.get('base_salary', 0.0) or 0.0))
            
            n_other = ci2.number_input("Otros Ingresos Fijos (€)", 
                                       value=float(p_data.get('other_fixed_income', 0.0) or 0.0),
                                       help="Alquileres, donaciones recurrentes, side-hustles...")
            
            total_fijo = n_salary + n_other
            st.caption(f"Total Ingresos Fijos: **{total_fijo:,.2f}€ / mes**")
            
            if st.form_submit_button("💾 Guardar Nueva Configuración Financiera"):
                new_finance = {
                    "id": user_id,
                    "name": p_data.get('name'),
                    "initial_balance": n_balance,
                    "base_salary": n_salary,
                    "other_fixed_income": n_other, # Guardamos el extra
                    "payments_per_year": n_pagas
                }
                success = upsert_profile(new_finance)
                if success:
                    st.session_state.user.update(new_finance) # Actualizar sesión
                    st.success("✅ Datos financieros e histórico actualizados")
                    time.sleep(1)
                    st.rerun()

    # --- C. SEGURIDAD (CAMBIO DE CONTRASEÑA) ---
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

# --- 5. IMPORTAR (Tu código original) ---
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
