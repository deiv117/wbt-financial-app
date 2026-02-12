def get_custom_css():
    """Retorna todo el CSS personalizado de la aplicación"""
    return """
    <style>
    /* 1. CAJA DE LOGIN */
    .login-box {
        background-color: white;
        padding: 40px;
        border-radius: 20px;
        border: 1px solid rgba(0, 0, 0, 0.1);
        box-shadow: 0 10px 25px rgba(0,0,0,0.2);
        margin-top: 20px;
    }
    
    /* Forzar visibilidad de textos en login */
    .login-box label, .login-box p, .login-box h1 {
        color: #31333F !important;
    }

    /* 2. TEXTO TITULO */
    .login-title { 
        text-align: center; 
        font-weight: 800; 
        margin-bottom: 25px;
        font-size: 2.5rem;
    }

    /* 3. SIDEBAR Y AVATAR */
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

    /* 4. BOTONES DE NAVEGACIÓN (SIDEBAR) */
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
    
    /* Botones de acción pequeños en tablas */
    div[data-testid="column"] button {
        padding: 2px 10px !important;
        height: auto !important;
        min-height: 0px !important;
        font-size: 14px !important;
    }
    </style>
    """
