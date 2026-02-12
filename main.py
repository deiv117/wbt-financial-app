with tab_mov:
            st.subheader("Nuevo Registro")
            c1, c2, c3 = st.columns(3)
            qty = c1.number_input("Cantidad (€)", min_value=0.0, step=0.01)
            t_type = c2.selectbox("Tipo", ["Gasto", "Ingreso"])
            f_mov = c3.date_input("Fecha", datetime.now())
            c4, c5 = st.columns([1, 2])
            f_cs = [c for c in current_cats if c.get('type') == t_type]
            if f_cs:
                opciones = ["Selecciona..."] + [f"{c.get('emoji', '📁')} {c['name']}" for c in f_cs]
                sel = c4.selectbox("Categoría", opciones)
                concepto = c5.text_input("Concepto / Notas")
                if st.button("Guardar") and sel != "Selecciona...":
                    cat_sel = next(c for c in f_cs if f"{c.get('emoji', '📁')} {c['name']}" == sel)
                    supabase.table("user_imputs").insert({
                        "user_id": st.session_state.user.id, 
                        "quantity": qty, 
                        "type": t_type, 
                        "category_id": cat_sel['id'], 
                        "date": str(f_mov), 
                        "notes": concepto
                    }).execute(); st.rerun()
            
            st.divider()
            st.subheader("Últimos 10 movimientos")
            res_rec = supabase.table("user_imputs").select("*, user_categories(id, name, emoji)").order("date", desc=True).limit(10).execute()
            
            for i in (res_rec.data if res_rec.data else []):
                # Limpieza de seguridad para evitar el TypeError
                cat_obj = i.get('user_categories') if i.get('user_categories') else {}
                cat_str = f"{cat_obj.get('emoji', '📁')} {cat_obj.get('name', 'S/C')}"
                
                # Esta es la corrección clave para evitar el error con notes:
                nota_texto = str(i.get('notes') or "") 
                resumen_nota = f" - *{nota_texto[:20]}...*" if nota_texto else ""
                
                cl1, cl2, cl3, cl4, cl5 = st.columns([2.5, 1, 0.8, 0.4, 0.4])
                cl1.markdown(f"**{i['date']}** | {cat_str}{resumen_nota}")
                cl2.write(f"{i['quantity']:.2f}€")
                cl3.write("📉" if i['type'] == "Gasto" else "📈")
                if cl4.button("✏️", key=f"emov_{i['id']}"): editar_movimiento_dialog(i, current_cats)
                if cl5.button("🗑️", key=f"dmov_{i['id']}"): supabase.table("user_imputs").delete().eq("id", i['id']).execute(); st.rerun()
