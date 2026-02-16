import streamlit as st
import pandas as pd
import math
import time
import plotly.graph_objects as go
import calendar
from streamlit_option_menu import option_menu 
from datetime import datetime, timedelta

# Importamos las funciones de base de datos y componentes
from database import (save_input, delete_input, get_categories, delete_category, 
                      upsert_profile, save_category, update_input, upload_avatar, 
                      change_password, get_historical_income)

# Importaciones para gestión de grupos y gastos
from database_groups import (get_user_groups, get_group_members, add_shared_expense, get_locked_movements)

from components import editar_movimiento_dialog, editar_categoria_dialog, crear_categoria_dialog

# --- ESTILOS CSS GLOBALES Y LIBRERÍA DE ICONOS ---
BOOTSTRAP_ICONS_LINK = '<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.10.5/font/bootstrap-icons.css">'

CUSTOM_CSS = """
<style>
@import url("https://cdn.jsdelivr.net/npm/bootstrap-icons@1.10.5/font/bootstrap-icons.css");

h1 .bi, h3 .bi, h5 .bi { vertical-align: -3px; margin-right: 10px; color: #636EFA; }

div[data-testid="stButton"] button:has(span:contains("edit")) {
    border-color: #FFC107 !important; color: #FFC107 !important; background-color: rgba(255, 193, 7, 0.1) !important; border-radius: 8px;
}
div[data-testid="stButton"] button:has(span:contains("edit")):hover {
    background-color: #FFC107 !important; color: #000000 !important; border-color: #FFC107 !important; transform: scale(1.02);
}

div[data-testid="stButton"] button:has(span:contains("delete")) {
    border-color: #FF4B4B !important; color: #FF4B4B !important; background-color: rgba(255, 75, 75, 0.1) !important; border-radius: 8px;
}
div[data-testid="stButton"] button:has(span:contains("delete")):hover {
    background-color: #FF4B4B !important; color: #FFFFFF !important; border-color: #FF4B4B !important; transform: scale(1.02);
}

div[data-testid="stVerticalBlockBorderWrapper"]:has(div[data-testid="stMetric"]) {
    min-height: 130px; display: flex; flex-direction: column; justify-content: center;
}
</style>
"""

def render_header(icon_name, text):
    st.markdown(f'{BOOTSTRAP_ICONS_LINK}<h1><i class="bi bi-{icon_name}"></i> {text}</h1>', unsafe_allow_html=True)

def render_subheader(icon_name, text):
    st.markdown(f'{BOOTSTRAP_ICONS_LINK}<h3><i class="bi bi-{icon_name}"></i> {text}</h3>', unsafe_allow_html=True)

def render_small_header(icon_name, text):
    st.markdown(f'{BOOTSTRAP_ICONS_LINK}<h5><i class="bi bi-{icon_name}"></i> {text}</h5>', unsafe_allow_html=True)

@st.dialog("Eliminar Movimiento")
def confirmar_borrar_movimiento(id_mov):
    st.markdown(f'{BOOTSTRAP_ICONS_LINK}<p style="font-size:16px;"><i class="bi bi-question-circle" style="color:#636EFA;"></i> ¿Estás seguro de que quieres eliminar este movimiento?</p>', unsafe_allow_html=True)
    st.markdown('<div style="color:#842029; background-color:#f8d7da; border:1px solid #f5c2c7; padding:10px; border-radius:5px; margin-bottom:20px;"><i class="bi bi-exclamation-triangle-fill"></i> Esta acción no se puede deshacer.</div>', unsafe_allow_html=True)
    col_no, col_si = st.columns(2)
    with col_si:
        if st.button(":material/delete: Sí, Eliminar", type="primary", use_container_width=True):
            delete_input(id_mov)
            st.rerun()
    with col_no:
        if st.button("Cancelar", use_container_width=True):
            st.rerun()

@st.dialog("Eliminar Categoría")
def confirmar_borrar_categoria(id_cat):
    st.markdown(f'{BOOTSTRAP_ICONS_LINK}<p style="font-size:16px;"><i class="bi bi-question-circle" style="color:#636EFA;"></i> ¿Seguro que quieres borrar esta categoría?</p>', unsafe_allow_html=True)
    st.markdown('<div style="color:#084298; background-color:#cfe2ff; border:1px solid #b6d4fe; padding:10px; border-radius:5px; margin-bottom:20px;"><i class="bi bi-info-circle-fill"></i> Los movimientos asociados no se borrarán, pero perderán su categoría.</div>', unsafe_allow_html=True)
    col_no, col_si = st.columns(2)
    with col_si:
        if st.button(":material/delete: Sí, Eliminar", type="primary", use_container_width=True):
            delete_category(id_cat)
            st.rerun()
    with col_no:
        if st.button("Cancelar", use_container_width=True):
            st.rerun()

# --- 1. RESUMEN GLOBAL ---
def render_main_dashboard(df_all, user_profile):
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

    render_header("house", "Resumen Global")
    st.caption(f"Hola de nuevo, {user_profile.get('name', 'Usuario')}. Aquí tienes el pulso de tu economía.")

    # --- CÁLCULO DE KPIs ---
    saldo_inicial = user_profile.get('initial_balance', 0) or 0
    user_id = user_profile.get('id') # Extraemos el ID para buscar las deudas
    
    if not df_all.empty:
        total_ingresos = df_all[df_all['type'] == 'Ingreso']['quantity'].sum()
        total_gastos = df_all[df_all['type'] == 'Gasto']['quantity'].sum()
        saldo_total = saldo_inicial + total_ingresos - total_gastos

        hoy = datetime.now()
        df_mes = df_all[(df_all['date'].dt.month == hoy.month) & (df_all['date'].dt.year == hoy.year)]
        ingresos_mes = df_mes[df_mes['type'] == 'Ingreso']['quantity'].sum()
        gastos_mes = df_mes[df_mes['type'] == 'Gasto']['quantity'].sum()
        ahorro_mes = ingresos_mes - gastos_mes
    else:
        saldo_total = saldo_inicial
        ahorro_mes = 0

    # --- LÓGICA DE LA DEUDA GLOBAL ---
    from database_groups import get_total_user_debt
    deuda_neta = get_total_user_debt(user_id)
    
    if deuda_neta > 0:
        deuda_str = f"+{deuda_neta:,.2f}€"
        deuda_delta = "Te deben"
        delta_color = "normal" # Se pondrá verde
    elif deuda_neta < 0:
        deuda_str = f"{deuda_neta:,.2f}€" # Ya lleva el signo menos implícito
        deuda_delta = "Debes"
        delta_color = "inverse" # Se pondrá rojo
    else:
        deuda_str = "0.00€"
        deuda_delta = "Al día"
        delta_color = "off" # Gris neutral

    # --- TARJETAS CON ALTURA AUTOMÁTICA (Igualadas por contenido) ---
    k1, k2, k3 = st.columns(3)
    with k1:
        with st.container(border=True):
            # Usamos un guion "-" en el delta para que la tarjeta crezca igual que las demás
            st.metric(label="💰 Patrimonio Neto", value=f"{saldo_total:,.2f}€", delta="-", delta_color="off", help="Saldo Inicial + Ingresos - Gastos")
    with k2:
        with st.container(border=True):
            st.metric(label=f"📅 Ahorro {datetime.now().strftime('%B')}", value=f"{ahorro_mes:,.2f}€", delta=f"{ahorro_mes:,.2f}€")
    with k3:
        with st.container(border=True):
            st.metric(label="👥 Grupos (Balance)", value=deuda_str, delta=deuda_delta, delta_color=delta_color)

    st.divider()

    render_subheader("graph-up", "Evolución de tu Patrimonio")
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
            fig.add_trace(go.Scatter(x=df_daily['date'], y=df_daily['saldo_acumulado'], fill='tozeroy', mode='lines', line=dict(color='#636EFA', width=3), name='Saldo'))
            fig.update_layout(margin=dict(l=0, r=0, t=10, b=0), yaxis_title="Euros (€)", hovermode="x unified", height=350)
            st.plotly_chart(fig, use_container_width=True)
        else:
             st.info(f"Tu patrimonio actual es tu saldo inicial: {saldo_inicial}€. Añade movimientos para ver la evolución gráfica.")
    else:
        st.info("Configura tu saldo inicial en el Perfil o añade movimientos para ver tu evolución.")

# --- 2. GESTIÓN DE MOVIMIENTOS ---
def render_dashboard(df_all, current_cats, user_id):
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)
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

    render_header("wallet2", "Movimientos")

    selected = option_menu(
        menu_title=None,
        options=["Nueva", "Historial", "Previsión", "Mensual", "Anual"],
        icons=["plus-circle", "clock-history", "graph-up-arrow", "calendar-month", "calendar3"],
        orientation="horizontal",
        default_index=0,
        styles={
            "container": {"padding": "0!important", "background-color": "transparent"},
            "icon": {"color": "orange", "font-size": "16px"}, 
            "nav-link": {"font-size": "14px", "text-align": "center", "margin": "0px", "--hover-color": "#eee"},
            "nav-link-selected": {"background-color": "#636EFA"},
        }
    )

    cat_g = [c for c in current_cats if c.get('type') == 'Gasto']
    ml = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]

    # Obtenemos los movimientos bloqueados (candado)
    locked_movs = get_locked_movements()

    # --- A. NUEVA ENTRADA ---
    if selected == "Nueva":
        render_subheader("plus-circle", "Añadir Transacción")
        
        if 'reset_key' not in st.session_state: 
            st.session_state.reset_key = 0

        with st.container(border=True):
            c1, c2, c3 = st.columns(3)
            qty = c1.number_input("Cantidad (€)", min_value=0.0, step=0.01, key=f"qty_{st.session_state.reset_key}")
            t_type = c2.selectbox("Tipo", ["Gasto", "Ingreso"])
            f_mov = c3.date_input("Fecha", datetime.now())
            
            f_cs = [c for c in current_cats if c.get('type') == t_type]
            sel = st.selectbox("Categoría", ["Selecciona..."] + [f"{c.get('emoji', '📁')} {c['name']}" for c in f_cs], key=f"cat_{st.session_state.reset_key}")
            
            concepto = st.text_input("Concepto", key=f"conc_{st.session_state.reset_key}")

            shared_group_id = None
            participantes_ids = []
            
            if t_type == "Gasto":
                st.divider()
                st.markdown("##### 👥 Gasto Compartido")
                mis_grupos = get_user_groups(user_id)
                
                if mis_grupos:
                    opciones_grupos = {g['name']: g['id'] for g in mis_grupos}
                    sel_grupo = st.selectbox("¿Vincular a un grupo?", ["No compartir"] + list(opciones_grupos.keys()), key="grupo_persistente")
                    
                    if sel_grupo != "No compartir":
                        shared_group_id = opciones_grupos[sel_grupo]
                        miembros = get_group_members(shared_group_id)
                        
                        st.write("Selecciona quién participa en este gasto:")
                        cols_miembros = st.columns(3)
                        for idx, m in enumerate(miembros):
                            prof = m.get('profiles') or {}
                            if isinstance(prof, list): prof = prof[0] if prof else {}
                            m_nombre = prof.get('name', 'Usuario')
                            
                            with cols_miembros[idx % 3]:
                                if st.checkbox(f"{m_nombre}", value=True, key=f"p_{m['user_id']}"):
                                    participantes_ids.append(m['user_id'])
                        
                        if participantes_ids:
                            cuota = qty / len(participantes_ids)
                            st.info(f"Reparto: **{cuota:.2f}€** por persona")
                else:
                    st.caption("No tienes grupos creados.")

            st.divider()
            if st.button("Guardar Movimiento", type="primary", use_container_width=True):
                if sel != "Selecciona...":
                    cat_sel = next(c for c in f_cs if f"{c.get('emoji', '📁')} {c['name']}" == sel)
                    
                    mov_data = {
                        "user_id": user_id, 
                        "quantity": qty, 
                        "type": t_type, 
                        "category_id": cat_sel['id'], 
                        "date": str(f_mov), 
                        "notes": concepto
                    }

                    exito = False
                    if shared_group_id and participantes_ids:
                        ok, msg = add_shared_expense(shared_group_id, mov_data, participantes_ids)
                        if ok: 
                            st.success("✅ Gasto compartido guardado")
                            exito = True
                        else: st.error(f"❌ Error DB: {msg}")
                    else:
                        try:
                            save_input(mov_data)
                            st.success("✅ Movimiento personal guardado")
                            exito = True
                        except Exception as e:
                            st.error(f"❌ Error DB: {e}")
                    
                    if exito:
                        st.session_state.reset_key += 1
                        time.sleep(0.5)
                        st.rerun()
                else:
                    st.warning("⚠️ Debes seleccionar una categoría.")
                  
        st.divider()
        st.subheader("Últimos movimientos")
        
        if not df_all.empty:
            df_rec = df_all.sort_values('date', ascending=False).head(10)
            
            for _, i in df_rec.iterrows():
                with st.container(border=True):
                    col_info, col_btn = st.columns([4, 1])
                    with col_info:
                        color_q = "red" if i['type'] == 'Gasto' else "green"
                        signo = "-" if i['type'] == 'Gasto' else "+"
                        
                        etiqueta_grupo = ""
                        if 'group_name' in i and pd.notna(i['group_name']) and i['group_name']:
                            etiqueta_grupo = f" &nbsp; | &nbsp; **{i.get('group_emoji', '👥')} {i['group_name']}**"
                            
                        is_locked = i['id'] in locked_movs
                        candado_str = "🔒 " if is_locked else ""
                            
                        st.markdown(f"**{candado_str}{i['cat_display']}**{etiqueta_grupo} &nbsp;|&nbsp; :{color_q}[**{signo}{i['quantity']:.2f}€**]")
                        
                        fecha_str = i['date'].strftime('%d/%m/%Y') if hasattr(i['date'], 'strftime') else i['date']
                        st.caption(f"📅 {fecha_str} &nbsp;|&nbsp; 📝 _{i['notes'] or 'Sin concepto'}_")
                    
                    with col_btn:
                        cb_e, cb_d = st.columns(2)
                        with cb_e:
                            if st.button(":material/edit:", key=f"e_dash_{i['id']}", disabled=is_locked, use_container_width=True): 
                                editar_movimiento_dialog(i, current_cats)
                        with cb_d:
                            if st.button(":material/delete:", key=f"d_dash_{i['id']}", type="primary", use_container_width=True): 
                                confirmar_borrar_movimiento(i['id'])
        else:
            st.info("Aún no tienes movimientos registrados.")
          
    # --- B. HISTORIAL ---
    elif selected == "Historial":
        render_subheader("clock-history", "Historial Completo")
        
        h1, h2 = st.columns(2)
        f_i = h1.date_input("Desde", datetime.now()-timedelta(days=30), key="hi")
        f_f = h2.date_input("Hasta", datetime.now(), key="hf")
        
        if not df_all.empty:
            df_h = df_all[(df_all['date'].dt.date >= f_i) & (df_all['date'].dt.date <= f_f)].sort_values('date', ascending=False)
            
            if df_h.empty:
                st.info("No hay movimientos en este rango.")
            else:
                st.divider()
                total_items = len(df_h)
                col_pag1, col_pag2, col_pag3 = st.columns([1, 1, 2])
                rows_per_page = col_pag1.selectbox("Registros:", [10, 25, 50, 100], index=0)
                total_pages = math.ceil(total_items / rows_per_page)
                current_page = col_pag2.number_input(f"Pág (de {total_pages})", 1, total_pages, 1)
                
                start_idx = (current_page - 1) * rows_per_page
                end_idx = min(start_idx + rows_per_page, total_items)
                col_pag3.markdown(f"<br>Viendo **{start_idx + 1}-{end_idx}** de **{total_items}**", unsafe_allow_html=True)
                
                st.markdown("---")
                df_sel = df_h.iloc[start_idx:end_idx]
                
                for _, i in df_sel.iterrows():
                    with st.container(border=True):
                        col_info, col_btn = st.columns([4, 1])
                        with col_info:
                            color_q = "red" if i['type'] == 'Gasto' else "green"
                            signo = "-" if i['type'] == 'Gasto' else "+"
                            
                            etiqueta_grupo = ""
                            if 'group_name' in i and pd.notna(i['group_name']) and i['group_name']:
                                etiqueta_grupo = f" &nbsp; | &nbsp; **{i.get('group_emoji', '👥')} {i['group_name']}**"
                                
                            is_locked = i['id'] in locked_movs
                            candado_str = "🔒 " if is_locked else ""
                            
                            st.markdown(f"**{candado_str}{i['cat_display']}**{etiqueta_grupo} &nbsp;|&nbsp; :{color_q}[**{signo}{i['quantity']:.2f}€**]")
                            
                            fecha_str = i['date'].strftime('%d/%m/%Y') if hasattr(i['date'], 'strftime') else i['date']
                            st.caption(f"📅 {fecha_str} &nbsp;|&nbsp; 📝 _{i['notes'] or 'Sin concepto'}_")
                
                        with col_btn:
                            c_ed, c_de = st.columns(2)
                            with c_ed:
                                if st.button(":material/edit:", key=f"hi_ed_{i['id']}", disabled=is_locked, use_container_width=True):
                                    editar_movimiento_dialog(i, current_cats)
                            with c_de:
                                if st.button(":material/delete:", key=f"hi_de_{i['id']}", type="primary", use_container_width=True):
                                    confirmar_borrar_movimiento(i['id'])

    # --- C. PREVISIÓN ---
    elif selected == "Previsión":
        render_subheader("graph-up-arrow", "Previsión y Comparativa")
        
        p_data = st.session_state.user if 'user' in st.session_state else {}
        n_salary = float(p_data.get('base_salary', 0) or 0)
        n_other = float(p_data.get('other_fixed_income', 0) or 0)
        n_freq = int(p_data.get('other_income_frequency', 1) or 1)
        
        ingresos_fijos = n_salary + (n_other / n_freq if n_freq > 0 else 0)
        limite_gastos = sum(float(c.get('budget', 0) or 0) for c in cat_g)
        ahorro_teorico = ingresos_fijos - limite_gastos

        render_small_header("bullseye", "El Plan Maestro")
        m1, m2, m3 = st.columns(3)
        with m1: 
            with st.container(border=True): 
                st.metric("Ingresos Fijos (Plan)", f"{ingresos_fijos:,.2f}€", help="Nómina + Extras fijos mensuales de tu Perfil")
        with m2: 
            with st.container(border=True): 
                st.metric("Límite de Gastos", f"{limite_gastos:,.2f}€", help="La suma total de tus presupuestos configurados")
        with m3: 
            with st.container(border=True): 
                color_ahorro = "normal" if ahorro_teorico > 0 else "inverse"
                pct_ahorro = f"{(ahorro_teorico/ingresos_fijos*100):.1f}%" if ingresos_fijos > 0 else None
                st.metric("Ahorro Teórico", f"{ahorro_teorico:,.2f}€", delta=pct_ahorro, delta_color=color_ahorro, help="Lo que te sobrará si cumples tu plan")

        st.divider()

        col_s1, col_s2 = st.columns([1, 2])
        
        with col_s1:
            render_small_header("heart-pulse", "Salud Financiera")
            tasa_ahorro = (ahorro_teorico / ingresos_fijos * 100) if ingresos_fijos > 0 else 0
            ratio_cob = (ingresos_fijos / limite_gastos) if limite_gastos > 0 else 0
            
            estado_tasa = "🟢 Óptimo" if tasa_ahorro >= 20 else ("🟡 Mejorable" if tasa_ahorro > 0 else "🔴 Peligro")
            estado_ratio = "🟢 Sobrado" if ratio_cob >= 1.2 else ("🟡 Ajustado" if ratio_cob >= 1 else "🔴 Insuficiente")
            
            with st.container(border=True):
                st.markdown(f"<p style='margin-bottom:0px; color:gray; font-size:14px;'>Tasa de Ahorro</p><h3 style='margin-top:0px;'>{tasa_ahorro:.1f}% <span style='font-size:16px; font-weight:normal;'>{estado_tasa}</span></h3>", unsafe_allow_html=True)
            with st.container(border=True):
                st.markdown(f"<p style='margin-bottom:0px; color:gray; font-size:14px;'>Cobertura de Gastos</p><h3 style='margin-top:0px;'>{ratio_cob:.2f}x <span style='font-size:16px; font-weight:normal;'>{estado_ratio}</span></h3>", unsafe_allow_html=True)

        with col_s2:
            render_small_header("crystal-ball", "Proyección a 12 meses")
            
            saldo_inicial = float(p_data.get('initial_balance', 0) or 0)
            if not df_all.empty:
                ti = df_all[df_all['type'] == 'Ingreso']['quantity'].sum()
                tg = df_all[df_all['type'] == 'Gasto']['quantity'].sum()
                saldo_actual = saldo_inicial + ti - tg
            else:
                saldo_actual = saldo_inicial
            
            saldo_futuro = saldo_actual + (ahorro_teorico * 12)
            st.caption(f"Si cumples tu plan, dentro de un año tendrás **{saldo_futuro:,.2f}€** ahorrados.")
            
            meses_proj = [datetime.now() + timedelta(days=30*i) for i in range(13)]
            saldos_proj = [saldo_actual + (ahorro_teorico * i) for i in range(13)]
            
            fig_p = go.Figure()
            fig_p.add_trace(go.Scatter(x=meses_proj, y=saldos_proj, fill='tozeroy', mode='lines', line=dict(color='#00CC96', width=3)))
            fig_p.update_layout(height=180, margin=dict(l=0, r=0, t=10, b=0), yaxis_title="Euros (€)", hovermode="x unified")
            st.plotly_chart(fig_p, use_container_width=True)

        st.divider()
        render_small_header("search", "Reality Check (Plan vs. Realidad)")
        st.write("Compara tus presupuestos con tu media histórica de gastos reales.")
        
        if not df_all.empty:
            df_gastos = df_all[df_all['type'] == 'Gasto']
            
            if not df_gastos.empty:
                unique_months = df_gastos['date'].dt.to_period('M').nunique()
                meses_hist = max(1, unique_months)
                
                hist_cat = df_gastos.groupby('category_id')['quantity'].sum().reset_index()
                hist_cat['Media_Histórica'] = hist_cat['quantity'] / meses_hist
                
                hoy = datetime.now()
                df_mes_actual = df_gastos[(df_gastos['date'].dt.month == hoy.month) & (df_gastos['date'].dt.year == hoy.year)]
                act_cat = df_mes_actual.groupby('category_id')['quantity'].sum().reset_index()
                act_cat.rename(columns={'quantity': 'Gastado_Mes'}, inplace=True)
                
                df_prev = pd.DataFrame(cat_g)
                if not df_prev.empty:
                    df_prev = pd.merge(df_prev, act_cat[['category_id', 'Gastado_Mes']], left_on='id', right_on='category_id', how='left').fillna(0)
                    df_prev = pd.merge(df_prev, hist_cat[['category_id', 'Media_Histórica']], left_on='id', right_on='category_id', how='left').fillna(0)
                    
                    def get_estado(row):
                        if row['budget'] == 0 and row['Media_Histórica'] > 0: return "⚠️ Sin Presup"
                        elif row['Media_Histórica'] > row['budget'] * 1.1: return "🔴 Irrealista"
                        elif row['Media_Histórica'] < row['budget'] * 0.5 and row['budget'] > 0: return "🔵 Holgado"
                        else: return "✅ OK"
                    
                    df_prev['Estado'] = df_prev.apply(get_estado, axis=1)
                    
                    df_display = df_prev[['emoji', 'name', 'budget', 'Gastado_Mes', 'Media_Histórica', 'Estado']].rename(
                        columns={'emoji': 'Ico', 'name': 'Categoría', 'budget': 'Presupuesto (€)', 
                                 'Gastado_Mes': 'Gastado Mes (€)', 'Media_Histórica': 'Media Hist. (€)', 'Estado': 'Eval'}
                    )
                    
                    df_display['Presupuesto (€)'] = df_display['Presupuesto (€)'].round(2)
                    df_display['Gastado Mes (€)'] = df_display['Gastado Mes (€)'].round(2)
                    df_display['Media Hist. (€)'] = df_display['Media Hist. (€)'].round(2)
                    
                    st.dataframe(df_display, use_container_width=True, hide_index=True)
            else: st.info("Aún no tienes gastos para calcular la media histórica.")
        else: st.info("Añade movimientos de gasto para comparar tu plan.")

    # --- D. MENSUAL ---
    elif selected == "Mensual":
        render_subheader("calendar-month", "Análisis Mensual")
        
        c_fil1, c_fil2 = st.columns(2)
        sm = c_fil1.selectbox("Mes", ml, index=datetime.now().month-1)
        sa = c_fil2.selectbox("Año", range(2024, 2031), index=datetime.now().year-2024, key="año_mensual")
        
        month_idx = ml.index(sm) + 1
        _, last_day = calendar.monthrange(sa, month_idx)
        fecha_analisis = f"{sa}-{month_idx:02d}-{last_day}"
        
        h_data = get_historical_income(user_id, fecha_analisis)
        h_sueldo = float(h_data.get('base_salary', 0) or 0)
        h_extras = float(h_data.get('other_fixed_income', 0) or 0)
        h_freq = int(h_data.get('other_income_frequency', 1) or 1) 
        h_total_previsto = h_sueldo + (h_extras / h_freq if h_freq > 0 else 0)

        if not df_all.empty:
            df_m = df_all[(df_all['date'].dt.month == month_idx) & (df_all['date'].dt.year == sa)]
            im_real = df_m[df_m['type'] == 'Ingreso']['quantity'].sum()
            gm_real = df_m[df_m['type'] == 'Gasto']['quantity'].sum()
            ahorro_real = im_real - gm_real
            
            c_i, c_g, c_b = st.columns(3)
            c_i.metric("Ingresos Reales", f"{im_real:,.2f}€")
            c_g.metric("Gastos Reales", f"{gm_real:,.2f}€")
            c_b.metric("Ahorro Neto", f"{ahorro_real:,.2f}€", delta=f"{ahorro_real:,.2f}€")
            
            st.write("---")
            if im_real > h_total_previsto:
                st.success(f"🌟 **¡Enhorabuena!** Has ingresado **{im_real - h_total_previsto:,.2f}€ más** de lo previsto.")
            elif ahorro_real > 0:
                st.info(f"✅ Buen trabajo. Has ahorrado **{ahorro_real:,.2f}€**.")
            else:
                st.warning(f"⚠️ Este mes los gastos han superado a los ingresos por **{abs(ahorro_real):,.2f}€**.")
            
            st.divider()
            st.subheader("Progreso por Categoría")
            gcm = df_m[df_m['type'] == 'Gasto'].groupby('category_id')['quantity'].sum().reset_index()
            
            for _, r in pd.merge(pd.DataFrame(cat_g), gcm, left_on='id', right_on='category_id', how='left').fillna(0).iterrows():
                gastado = r['quantity']
                presupuesto = r['budget']
                if presupuesto > 0:
                    pct = min(gastado / presupuesto, 1.0)
                    color_bar = "#00CC96" if pct <= 0.75 else "#FFC107" if pct <= 1.0 else "#EF553B"
                    restante = presupuesto - gastado
                    txt_rest = f"<span style='color:gray;'>Quedan {restante:.2f}€</span>" if restante >= 0 else f"<span style='color:#EF553B;font-weight:bold;'>Exceso {abs(restante):.2f}€</span>"
                    
                    st.markdown(f"""
                    <div style="margin-bottom:15px;">
                        <div style="display:flex;justify-content:space-between;margin-bottom:5px;">
                            <span><strong>{r.get('emoji','📁')} {r['name']}</strong> ({gastado:.2f}€ / {presupuesto:.2f}€)</span>
                            {txt_rest}
                        </div>
                        <div style="width:100%;background:rgba(128,128,128,0.2);border-radius:5px;height:12px;">
                            <div style="width:{pct*100}%;background:{color_bar};height:12px;border-radius:5px;"></div>
                        </div>
                    </div>""", unsafe_allow_html=True)

    # --- E. ANUAL ---
    elif selected == "Anual":
        render_subheader("calendar3", "Análisis Anual")
        san = st.selectbox("Seleccionar Año", range(2024, 2031), index=datetime.now().year-2024, key="año_anual")
        
        if not df_all.empty:
            df_an = df_all[df_all['date'].dt.year == san]
            ia = df_an[df_an['type'] == 'Ingreso']['quantity'].sum()
            ga = df_an[df_an['type'] == 'Gasto']['quantity'].sum()
            ba = ia - ga
            
            a_i, a_g, a_b = st.columns(3)
            a_i.metric(f"Ingresos {san}", f"{ia:.2f}€")
            a_g.metric(f"Gastos {san}", f"{ga:.2f}€")
            a_b.metric(f"Balance", f"{ba:.2f}€", delta=f"{ba:.2f}€", delta_color="normal" if ba >= 0 else "inverse")
            
            dfe = df_an.copy()
            dfe['mes_num'] = dfe['date'].dt.month
            rm = dfe.pivot_table(index='mes_num', columns='type', values='quantity', aggfunc='sum').fillna(0).reindex(range(1,13), fill_value=0)
            for t in ['Ingreso', 'Gasto']: 
                if t not in rm.columns: rm[t] = 0
            rm['Ahorro'] = rm['Ingreso'] - rm['Gasto']
            
            fig = go.Figure()
            fig.add_trace(go.Bar(x=ml, y=rm['Ingreso'], name='Ingreso', marker_color='#00CC96'))
            fig.add_trace(go.Bar(x=ml, y=rm['Gasto'], name='Gasto', marker_color='#EF553B'))
            fig.add_trace(go.Scatter(x=ml, y=rm['Ahorro'], name='Ahorro', mode='lines+markers', line=dict(color='#636EFA', width=3)))
            fig.update_layout(barmode='group', margin=dict(l=20, r=20, t=20, b=20), legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
            st.plotly_chart(fig, use_container_width=True)

            st.divider()
            st.subheader("Progreso Anual por Categoría")
            gcm_anual = df_an[df_an['type'] == 'Gasto'].groupby('category_id')['quantity'].sum().reset_index()
            for _, r in pd.merge(pd.DataFrame(cat_g), gcm_anual, left_on='id', right_on='category_id', how='left').fillna(0).iterrows():
                gastado = r['quantity']
                presupuesto_anual = r['budget'] * 12
                if presupuesto_anual > 0:
                    pct = min(gastado / presupuesto_anual, 1.0)
                    color_bar = "#00CC96" if pct <= 0.75 else "#FFC107" if pct <= 1.0 else "#EF553B"
                    restante = presupuesto_anual - gastado
                    txt_rest = f"<span style='color:gray;'>Quedan {restante:.2f}€</span>" if restante >= 0 else f"<span style='color:#EF553B;font-weight:bold;'>Exceso {abs(restante):.2f}€</span>"
                    st.markdown(f"""
                    <div style="margin-bottom:15px;">
                        <div style="display:flex;justify-content:space-between;margin-bottom:5px;">
                            <span><strong>{r.get('emoji','📁')} {r['name']}</strong> ({gastado:.2f}€ / {presupuesto_anual:.2f}€)</span>
                            {txt_rest}
                        </div>
                        <div style="width:100%;background:rgba(128,128,128,0.2);border-radius:5px;height:12px;">
                            <div style="width:{pct*100}%;background:{color_bar};height:12px;border-radius:5px;"></div>
                        </div>
                    </div>""", unsafe_allow_html=True)

# --- 3. CATEGORÍAS ---
def render_categories(current_cats):
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)
    render_header("list-task", "Gestión de Categorías")
    
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
                        if c.get('budget_type') == 'percentage':
                            k1.caption(f"Meta: {c['budget']:.2f}€ ({c.get('budget_percent',0)}%)")
                        else:
                            k1.caption(f"Meta: {c['budget']:.2f}€")
                    with k2:
                        kb1, kb2 = st.columns(2)
                        with kb1:
                            if st.button(":material/edit:", key=f"cat_e_{c['id']}", use_container_width=True): 
                                editar_categoria_dialog(c)
                        with kb2:
                            if st.button(":material/delete:", key=f"cat_d_{c['id']}", type="primary", use_container_width=True): 
                                confirmar_borrar_categoria(c['id'])

# --- 4. PERFIL ---
def render_profile(user_id, p_data):
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)
    render_header("person-gear", "Mi Perfil")
    
    with st.container(border=True):
        render_subheader("person-lines-fill", "Datos Personales")
        c_ava, c_form = st.columns([1, 2])
        
        with c_ava:
            avatar_url = p_data.get('avatar_url')
            raw_name = p_data.get('name')
            name_safe = raw_name if raw_name and raw_name.strip() else 'Usuario'
            initial = name_safe[0].upper()
            p_color = p_data.get('profile_color', '#636EFA')

            if avatar_url: st.image(avatar_url, width=150)
            else:
                st.markdown(f'<div style="width:150px;height:150px;background-color:{p_color};border-radius:50%;display:flex;align-items:center;justify-content:center;color:white;font-size:50px;font-weight:bold;">{initial}</div>', unsafe_allow_html=True)
            uploaded_file = st.file_uploader("Cambiar foto (Máx 5MB)", type=['png', 'jpg', 'jpeg'])
        
        with c_form:
            with st.form("perfil_form"):
                n_name = st.text_input("Nombre", value=p_data.get('name') or "")
                n_last = st.text_input("Apellido", value=p_data.get('lastname') or "")
                n_color = st.color_picker("Color de Perfil", value=p_color)
                n_social = st.toggle("Modo Social", value=p_data.get('social_active', False))
                
                if st.form_submit_button(":material/save: Guardar Datos"):
                    final_avatar = avatar_url
                    if uploaded_file:
                        new_url = upload_avatar(uploaded_file, user_id)
                        if new_url: final_avatar = new_url
                    new_data = {**p_data, "name": n_name, "lastname": n_last, "profile_color": n_color, "social_active": n_social, "avatar_url": final_avatar}
                    if upsert_profile(new_data):
                        st.session_state.user.update(new_data)
                        st.rerun()

    with st.container(border=True):
        render_subheader("cash-coin", "Configuración Financiera")
        st.info("ℹ️ Cualquier cambio en tu sueldo o ingresos fijos se guardará en tu historial.")
        
        with st.form("finance_form"):
            render_small_header("bank", "Patrimonio Base")
            n_balance = st.number_input("Saldo Inicial (€)", value=float(p_data.get('initial_balance', 0) or 0))
            
            st.divider()
            render_small_header("briefcase", "Nómina y Pagas")
            col_n1, col_n2 = st.columns(2)
            n_salary = col_n1.number_input("Nómina Base Mensual (€)", value=float(p_data.get('base_salary', 0) or 0))
            n_pagas = col_n2.slider("Pagas al año", 12, 16, int(p_data.get('payments_per_year', 12) or 12))

            render_small_header("graph-up-arrow", "Ingresos Adicionales")
            col_ex1, col_ex2 = st.columns(2)
            n_other = col_ex1.number_input("Cantidad Extra (€)", value=float(p_data.get('other_fixed_income', 0) or 0))
            
            freq_map = {1: "Mensual", 2: "Bimestral", 3: "Trimestral", 6: "Semestral", 12: "Anual"}
            curr_freq_val = int(p_data.get('other_income_frequency', 1) or 1)
            try: freq_idx = list(freq_map.keys()).index(curr_freq_val)
            except ValueError: freq_idx = 0

            freq_txt = col_ex2.selectbox("Frecuencia", list(freq_map.values()), index=freq_idx)
            n_freq = [k for k, v in freq_map.items() if v == freq_txt][0]

            mensual_extra = n_other / n_freq if n_freq > 0 else 0
            total_est = n_salary + mensual_extra
            st.caption(f"💰 Ingreso medio mensual estimado: **{total_est:,.2f}€**")

            if st.form_submit_button(":material/save: Guardar Finanzas"):
                new_data = {"id": user_id, "initial_balance": n_balance, "base_salary": n_salary, "other_fixed_income": n_other, "other_income_frequency": n_freq, "payments_per_year": n_pagas}
                full_update = {**p_data, **new_data}
                if upsert_profile(full_update):
                    from database import recalculate_category_budgets
                    n_updated = recalculate_category_budgets(user_id, total_est) or 0
                    st.session_state.user.update(full_update)
                    msg = "✅ Configuración financiera guardada."
                    if n_updated > 0: msg += f" Se han actualizado {n_updated} presupuestos."
                    st.success(msg)
                    time.sleep(1.5)
                    st.rerun()

    with st.expander("Seguridad y Contraseña", icon=":material/lock:"):
        render_subheader("shield-lock", "Seguridad")
        with st.form("pass_form"):
            p1 = st.text_input("Nueva Contraseña", type="password")
            p2 = st.text_input("Confirmar Contraseña", type="password")
            if st.form_submit_button("Cambiar Contraseña"):
                if p1 == p2 and len(p1) >= 6:
                    ok, msg = change_password(p1)
                    if ok: st.success("✅ Contraseña actualizada")
                    else: st.error(f"Error: {msg}")
                else: st.error("Las contraseñas no coinciden o son muy cortas.")

# --- 5. IMPORTAR ---
def render_import(current_cats, user_id):
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)
    render_header("cloud-upload", "Importar Movimientos")
    
    with st.expander("📖 Guía de Columnas Sugeridas", expanded=True):
        st.table({
            "Columna": ["Tipo", "Cantidad", "Categoría", "Fecha", "Concepto"],
            "Descripción": ["Gasto o Ingreso", "Ej: 12.50", "Nombre exacto", "AAAA-MM-DD", "Descripción"]
        })

    ej_cat = current_cats[0]['name'] if current_cats else "Varios"
    df_template = pd.DataFrame([{"Tipo": "Gasto", "Cantidad": 0.00, "Categoría": ej_cat, "Fecha": datetime.now().strftime("%Y-%m-%d"), "Concepto": "Ejemplo"}])
    st.download_button("📥 Descargar Plantilla CSV", df_template.to_csv(index=False).encode('utf-8'), "plantilla_importacion.csv", "text/csv")
    
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
                st.success(f"✅ Se han importado {count} movimientos.")
                st.rerun()
        except Exception as e: st.error(f"Error al leer el archivo: {e}")
