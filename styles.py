# styles.py

def get_custom_css():
    return """
    <style>
    /* =========================================
       0. CORE RESPONSIVE FIX (FUERZA HORIZONTAL)
       ========================================= */
    
    /* Eliminar márgenes excesivos */
    .block-container {
        padding-top: 1rem !important;
        padding-left: 0.2rem !important;
        padding-right: 0.2rem !important;
        max-width: 100vw !important;
    }

    /* OBLIGAR a que las columnas se mantengan en fila en el móvil */
    @media (max-width: 640px) {
        [data-testid="stHorizontalBlock"] {
            display: flex !important;
            flex-direction: row !important; /* ESTO ES LA CLAVE */
            flex-wrap: nowrap !important;
            overflow-x: hidden !important;
            align-items: center !important;
            gap: 2px !important;
        }

        /* Ajustar el ancho de las columnas para que quepan */
        [data-testid="column"] {
            min-width: 0px !important;
            flex: 1 1 auto !important;
            padding: 0 !important;
        }

        /* Texto más grande y legible en móvil */
        .stMarkdown p {
            font-size: 13px !important; /* Aumentado de 11 a 13px */
            line-height: 1.2 !important;
            white-space: nowrap !important; /* No permitir saltos de línea */
            overflow: hidden !important;
            text-overflow: ellipsis !important; /* Puntos suspensivos si no cabe */
        }
        
        /* Ocultar elementos menos importantes si es necesario */
        /* .hide-mobile { display: none !important; } */
    }

    /* =========================================
       1. ESTILOS DE BOTONES Y ACCIONES
       ========================================= */
    
    .contenedor-acciones-tabla {
        display: flex !important;
        flex-direction: row !important;
        justify-content: flex-end !important;
        align-items: center !important;
        gap: 2px !important;
        width: 100% !important;
    }
    
    /* Botones más grandes para dedos */
    .contenedor-acciones-tabla button {
        width: 28px !important;
        height: 28px !important;
        padding: 0px !important;
        min-height: 28px !important;
        border-radius: 4px !important;
        border: 1px solid #e0e0e0 !important;
        font-size: 12px !important;
    }

    /* =========================================
       2. FORMULARIO Y GENERAL
       ========================================= */
    [data-testid="stForm"] div[data-testid="stVerticalBlock"] { gap: 0.5rem !important; }
    h1, h2, h3 { color: #31333F; }
    
    /* Input alignment fix */
    .st-emotion-cache-1permvm { align-items: center; }

    /* Login Box */
    .st-emotion-cache-1ne20ew { background-color: #fff; }
    </style>
    """
