def get_custom_css():
    """Retorna todo el CSS personalizado de la aplicación"""
    return """
    <style>
    /* 1. FONDO DE PANTALLA (Solo para Login) */
    /* Definimos la variable pero la aplicaremos condicionalmente en main.py */
    .bg-login {
        background-image: url("https://images.unsplash.com/photo-1554224155-6726b3ff858f?q=80&w=2022&auto=format&fit=crop");
        background-size: cover;
        background-position: center;
        background-attachment: fixed;
    }

    /* 2. CAJA DE LOGIN REFORMADA (Sin depender de st.form) */
    .login-box {
        background-color: rgba(255, 255, 255, 0.85); /* Fondo sólido semi-transparente para legibilidad */
        backdrop-filter: blur(10px);
        -webkit-backdrop-filter: blur(10px);
        padding: 40px;
        border-radius: 20px;
        border: 1px solid rgba(255, 255, 255, 0.3);
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.3);
        margin-top: 50px;
    }
    
    /* Forzar color de etiquetas en login para que se vean sobre el fondo */
    .login-box label {
        color: #31333F !important;
        font-weight: bold !important;
    }

    /* 3. TEXTOS DE LOGIN */
    .login-title { 
        text-align: center; 
        font-weight: 800; 
        color: #1f1f1f !important; 
        margin-bottom: 20px;
    }

    /* 4. SIDEBAR Y AVATAR */
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

    /* 5. BOTONES DE NAVEGACIÓN (SIDEBAR) */
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
    
    /* Botones de acción (Editar/Borrar) - Mantener pequeños */
    div[data-testid="column"] button {
        padding: 2px 10px !important;
        height: auto !important;
        min-height: 0px !important;
        font-size: 14px !important;
    }
    </style>
    """
