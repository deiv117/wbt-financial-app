# styles.py

def get_custom_css():
    """Retorna todo el CSS personalizado de la aplicación"""
    return """
    <style>
    /* 1. FONDO DE PANTALLA GENERAL */
    .stApp {
        background-image: url("https://images.unsplash.com/photo-1554224155-6726b3ff858f?q=80&w=2022&auto=format&fit=crop");
        background-size: cover;
        background-position: center;
        background-attachment: fixed;
    }

    /* 2. CAJA DE LOGIN (GLASSMORPHISM) */
    [data-testid="stForm"] {
        background-color: rgba(255, 255, 255, 0.05);
        backdrop-filter: blur(15px);
        -webkit-backdrop-filter: blur(15px);
        padding: 40px;
        border-radius: 20px;
        border: 1px solid rgba(255, 255, 255, 0.2);
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37);
    }

    /* 3. TEXTOS DE LOGIN */
    .login-title { 
        text-align: center; 
        font-weight: 800; 
        color: white !important; 
        text-shadow: 2px 2px 4px rgba(0,0,0,0.5); 
    }
    .login-subtitle { 
        text-align: center; 
        color: #f0f2f6 !important; 
        text-shadow: 1px 1px 2px rgba(0,0,0,0.5); 
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

    /* 5. BOTONES PERSONALIZADOS */
    div.stButton > button { 
        width: 100%; 
        border-radius: 10px; 
        border: 1px solid rgba(128, 128, 128, 0.2); 
        background-color: transparent; 
        transition: all 0.3s ease; 
        text-align: left; 
        padding: 10px 15px; 
    }
    div.stButton > button:hover { 
        border-color: #636EFA; 
        background-color: rgba(99, 110, 250, 0.1); 
    }

    .login-box {
        background-color: var(--secondary-background-color); /* Usa el color del tema de Streamlit */
        padding: 2rem;
        border-radius: 15px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        border: 1px solid rgba(128,128,128,0.2);
    }
    
    .login-title {
        text-align: center;
        color: var(--text-color);
        margin-bottom: 2rem;
    }
    </style>
    """
