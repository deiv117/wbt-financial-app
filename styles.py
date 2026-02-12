# styles.py

def get_custom_css():
    """Retorna todo el CSS personalizado de la aplicación"""
    return """
    <style>
    /* =========================================
       1. ESTILOS GENERALES
       ========================================= */
    h1, h2, h3 { color: #31333F; }

    /* Ajustes globales para evitar desbordamiento horizontal en móviles */
    .block-container {
        padding-left: 0.5rem !important;
        padding-right: 0.5rem !important;
        max-width: 100% !important;
    }

    /* =========================================
       2. SIDEBAR Y AVATAR
       ========================================= */
    .sidebar-user-container { 
        display: flex; 
        flex-direction: column; 
        align-items: center; 
        justify-content: center; 
        text-align: center; 
        padding: 10px 0 20px 0; 
    }
    .avatar-circle { 
        width: 80px; 
        height: 80px; 
        border-radius: 50%; 
        display: flex; 
        align-items: center; 
        justify-content: center; 
        color: white; 
        font-weight: bold; 
        font-size: 28px; 
        margin-bottom: 10px; 
        border: 2px solid #636EFA; 
        object-fit: cover; 
    }

    /* =========================================
       3. BOTONES SIDEBAR
       ========================================= */
    .stSidebar div.stButton > button { 
        width: 100%; 
        border-radius: 10px; 
        border: 1px solid rgba(128, 128, 128, 0.2); 
        background-color: transparent; 
        transition: all 0.3s ease; 
        text-align: left; 
        padding: 10px 15px; 
    }
    .stSidebar div.stButton > button:hover { 
        border-color: #636EFA; 
        background-color: rgba(99, 110, 250, 0.1); 
    }

    /* =========================================
       4. TABLAS RESPONSIVE Y FILAS
       ========================================= */
    
    /* Forzar fila horizontal y permitir que los elementos se encojan sin scroll */
    [data-testid="stHorizontalBlock"] {
        display: flex !important;
        flex-direction: row !important;
        flex-wrap: nowrap !important;
        align-items: center !important;
        width: 100% !important;
        gap: 2px !important;
    }

    /* Columnas flexibles que NO empujan el ancho (Evita scroll horizontal) */
    [data-testid="column"] {
        flex: 1 1 auto !important;
        min-width: 0px !important; /* Vital: permite que la columna sea más pequeña que su contenido */
        padding: 0px !important;
        overflow: hidden !important; 
    }

    /* Alineación vertical de inputs en tablas */
    .st-emotion-cache-1permvm {
        align-items: center;
    }

    /* =========================================
       5. BOTONES DE ACCIÓN (Lápiz / Basura)
       ========================================= */
    
    /* Contenedor específico para alinear botones a la derecha */
    .contenedor-acciones-tabla {
        display: flex !important;
        flex-direction: row !important;
        gap: 4px !important;
        justify-content: flex-end !important;
        align-items: center !important;
        width: 100% !important;
        padding-right: 2px !important;
    }
    
    /* Estilo de los botones dentro de la tabla */
    .contenedor-acciones-tabla button {
        height: 30px !important;
        width: 34px !important;
        padding: 0px !important;
        margin: 0px !important;
        min-height: 30px !important;
        border-radius: 6px !important;
        font-size: 14px !important;
        border: 1px solid #f0f2f6 !important;
    }

    /* =========================================
       6. ESTILOS PARA MÓVIL (Max-width 640px)
       ========================================= */
    @media (max-width: 640px) {
        /* Texto más pequeño y truncado con '...' */
        .stMarkdown div p {
            font-size: 11px !important;
            white-space: nowrap !important;
            overflow: hidden !important;
            text-overflow: ellipsis !important;
            line-height: 1.2 !important;
        }
        
        /* Ajuste de métricas */
        [data-testid="stMetricValue"] {
            font-size: 18px !important;
        }
        
        /* Botones ultra compactos en móvil */
        .contenedor-acciones-tabla button {
            width: 24px !important;
            height: 24px !important;
            font-size: 10px !important;
        }
        
        /* Reducir gap vertical */
        div[data-testid="stVerticalBlock"] > div {
            gap: 0.2rem !important;
        }
    }

    /* =========================================
       7. PARCHES ESPECÍFICOS DE STREAMLIT
       ========================================= */
    /* Login Box (Nota: las clases hash pueden cambiar con actualizaciones) */
    .st-emotion-cache-1ne20ew {
        background-color: #fff;
    }

    /* Botones genéricos en columnas (Legacy support) */
    div[data-testid="column"] button {
        padding: 2px 10px !important;
    }
    </style>
    """
