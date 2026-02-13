import streamlit as st
import pandas as pd
from datetime import datetime
from database import save_input

def render_import(current_cats, user_id):
    st.title("📥 Importar Movimientos")
    st.download_button(label="📥 Descargar Plantilla", data=pd.DataFrame([{"Tipo": "Gasto", "Cantidad": 0.00, "Categoría": "Varios", "Fecha": datetime.now().strftime("%Y-%m-%d"), "Concepto": "Ejemplo"}]).to_csv(index=False), file_name="plantilla.csv")
    
    up = st.file_uploader("Subir Archivo", type=["csv", "xlsx"])
    if up:
        df = pd.read_csv(up) if up.name.endswith('.csv') else pd.read_excel(up)
        if st.button("🚀 Procesar Importación"):
            cat_lookup = {c['name'].upper(): c['id'] for c in current_cats}
            for _, r in df.iterrows():
                if str(r['Categoría']).upper() in cat_lookup:
                    save_input({"user_id": user_id, "quantity": r['Cantidad'], "type": r['Tipo'], "category_id": cat_lookup[str(r['Categoría']).upper()], "date": str(r['Fecha']), "notes": r['Concepto']})
            st.success("Importación completada.")
