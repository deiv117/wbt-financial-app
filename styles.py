# styles.py
def get_custom_css():
    """Retorna el CSS base de la aplicación"""
    return """
    <style>
    /* 1. ESTILOS GENERALES DE TEXTO */
    h1, h2, h3 { color: #31333F; }

    /* 2. SIDEBAR Y AVATAR */
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

    /* 3. BOTONES SIDEBAR */
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
    
    /* 4. BOTONES PEQUEÑOS EN TABLAS (Necesario para los iconos) */
    div[data-testid="column"] button {
        padding: 2px 10px !important;
        height: auto !important;
        min-height: 0px !important;
        font-size: 14px !important;
    }

    /* 5. PARCHES */
    .st-emotion-cache-1ne20ew { background-color: #fff; }
    /*.st-emotion-cache-1permvm { align-items: center; }*/

    /* =========================================
       7. TARJETAS DE MOVIMIENTOS (NUEVO)
       ========================================= */
    .movimiento-card {
        background-color: white;
        border: 1px solid #f0f2f6;
        border-radius: 10px;
        padding: 15px;
        margin-bottom: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    
    .movimiento-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 8px rgba(0,0,0,0.1);
        border-color: #636EFA;
    }

    .card-top {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 5px;
    }
    
    .card-amount {
        font-weight: bold;
        font-size: 1.1em;
    }
    
    .gasto-color { color: #EF553B; }
    .ingreso-color { color: #00CC96; }
    
    .card-date {
        font-size: 0.8em;
        color: #888;
    }
    
    .card-note {
        font-size: 0.9em;
        color: #555;
        font-style: italic;
    }
    
    /* Contenedor de acciones dentro de la tarjeta */
    .card-actions {
        display: flex;
        justify-content: flex-end;
        gap: 5px;
        margin-top: 10px;
        padding-top: 10px;
        border-top: 1px solid #f0f2f6;
    }
    </style>
    """
