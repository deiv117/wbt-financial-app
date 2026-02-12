# styles.py

def get_custom_css():
    """Retorna todo el CSS personalizado de la aplicación"""
    return """
    <style>
    /* =========================================
       0. CORE RESPONSIVE FIX (LA CLAVE)
       ========================================= */
    
    /* 1. Eliminar el padding gigante de Streamlit en móviles */
    .block-container {
        padding-top: 1rem !important;
        padding-bottom: 1rem !important;
        padding-left: 0.5rem !important;
        padding-right: 0.5rem !important;
        max-width: 100vw !important;
    }

    /* 2. Forzar que las columnas NUNCA tengan ancho mínimo fijo */
    [data-testid="column"] {
        width: auto !important;
        flex: 1 1 auto !important;
        min-width: 10px !important; /* Permite que la columna se encoja muchísimo */
    }

    /* 3. Evitar que la tabla se desborde horizontalmente */
    [data-testid="stHorizontalBlock"] {
        width: 100% !important;
        min-width: 100% !important;
        gap: 0.2rem !important; /* Reducimos el hueco entre columnas al mínimo */
        overflow-x: hidden !important; /* Cortar lo que sobresalga sí o sí */
    }

    /* =========================================
       1. ESTILOS GENERALES
       ========================================= */
    h1, h2, h3 { color: #31333F; }

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
       4. BOTONES DE ACCIÓN (Lápiz / Basura)
       ========================================= */
    .contenedor-acciones-tabla {
        display: flex !important;
        flex-direction: row !important;
        gap: 2px !important; /* Menos espacio entre botones */
        justify-content: flex-end !important;
        align-items: center !important;
        width: 100% !important;
    }
    
    .contenedor-acciones-tabla button {
        height: 28px !important;
        width: 28px !important; /* Más cuadrados */
        padding: 0px !important;
        margin: 0px !important;
        min-height: 28px !important;
        border-radius: 4px !important;
        font-size: 12px !important;
        border: 1px solid #e0e0e0 !important;
        background-color: white !important;
    }

    /* =========================================
       5. ESTILOS ESPECÍFICOS PARA MÓVIL (< 640px)
       ========================================= */
    @media (max-width: 640px) {
        /* Texto de la tabla mucho más pequeño para que quepa */
        .stMarkdown p {
            font-size: 11px !important;
            line-height: 1.2 !important;
        }

        /* Ocultar scrollbars si aparecen */
        ::-webkit-scrollbar {
            width: 0px;
            background: transparent;
        }

        /* Ajuste extremo de botones en móvil */
        .contenedor-acciones-tabla button {
            width: 24px !important;
            height: 24px !important;
            font-size: 10px !important;
        }
        
        /* Reducir tamaño de títulos */
        h1 { font-size: 1.5rem !important; }
        h2 { font-size: 1.2rem !important; }
        h3 { font-size: 1rem !important; }
    }

    /* =========================================
       6. PARCHES VARIOS
       ========================================= */
    .st-emotion-cache-1ne20ew { background-color: #fff; }
    
    /* Input alignment fix */
    .st-emotion-cache-1permvm { align-items: center; }
    
    /* Optimización Formulario */
    [data-testid="stForm"] div[data-testid="stVerticalBlock"] { gap: 0.5rem !important; }
    </style>
    """
