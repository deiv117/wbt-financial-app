import streamlit as st

# Configuración de la página
st.set_page_config(page_title="Mis Gastos", page_icon="💰")

st.title("💰 Mi App de Gastos Personales")

# --- BARRA LATERAL (LOGIN) ---
with st.sidebar:
    st.header("Acceso")
    email = st.text_input("Correo electrónico")
    password = st.text_input("Contraseña", type="password")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Iniciar Sesión"):
            st.info("Aquí conectaremos con Supabase pronto...")
    with col2:
        if st.button("Registrarse"):
            st.info("Creando tu usuario...")

# --- CUERPO PRINCIPAL ---
st.subheader("Añadir nuevo gasto")
concepto = st.text_input("Concepto (ej. Cena)")
monto = st.number_input("Cantidad (€)", min_value=0.0, step=0.01)

if st.button("Guardar Gasto"):
    st.success(f"Gasto de {monto}€ en '{concepto}' anotado (en tu imaginación por ahora)!")
