# database_groups.py
import streamlit as st # <-- ¡CRÍTICO PARA LOS CHIVATOS!
from database import supabase

# ==========================================
# 1. CORE DE GRUPOS (Crear, Leer, Borrar)
# ==========================================

def create_group(name, emoji, color, user_id):
    try:
        group_data = {"name": name, "emoji": emoji, "color": color, "created_by": user_id}
        res = supabase.table("groups").insert(group_data).execute()
        
        if res.data:
            group_id = res.data[0]['id']
            member_data = {"group_id": group_id, "user_id": user_id}
            supabase.table("group_members").insert(member_data).execute()
            return True, "Grupo creado con éxito"
        return False, "Error al crear grupo."
    except Exception as e:
        return False, str(e)

def get_user_groups(user_id):
    """Obtiene todos los grupos a los que pertenece el usuario."""
    try:
        # ¡CORREGIDO! Añadimos emoji y color al select
        res = supabase.table("group_members") \
            .select("group_id, groups(id, name, emoji, color, created_by, created_at)") \
            .eq("user_id", user_id) \
            .execute()
            
        if res.data:
            groups_list = []
            for item in res.data:
                group_info = item.get('groups')
                if group_info:
                    groups_list.append({
                        'id': group_info['id'],
                        'name': group_info['name'],
                        'emoji': group_info.get('emoji', '👥'), # Recuperamos el emoji
                        'color': group_info.get('color', '#636EFA'), # Recuperamos el color
                        'created_by': group_info['created_by'],
                        'created_at': group_info['created_at']
                    })
            groups_list.sort(key=lambda x: x['created_at'], reverse=True)
            return groups_list
        return []
    except Exception as e:
        print(f"Error obteniendo grupos: {e}")
        return []

def get_group_info(group_id):
    """Obtiene los datos y configuración general de un grupo"""
    try:
        res = supabase.table("groups").select("*").eq("id", group_id).execute()
        return res.data[0] if res.data else None
    except Exception as e:
        print(f"Error obteniendo info del grupo: {e}")
        return None

def delete_group(group_id):
    """Elimina un grupo (borrando primero a los miembros)."""
    try:
        supabase.table("group_members").delete().eq("group_id", group_id).execute()
        supabase.table("groups").delete().eq("id", group_id).execute()
        return True
    except Exception as e:
        print(f"Error borrando grupo: {e}")
        return False


# ==========================================
# 2. GESTIÓN DE MIEMBROS
# ==========================================

def get_group_members(group_id):
    """Obtiene la lista de usuarios con chivato de errores"""
    try:
        res = supabase.table("group_members").select("user_id, leave_status, profiles(name, lastname, avatar_url, profile_color)").eq("group_id", group_id).execute()
        return res.data or []
    except Exception as e:
        st.error(f"🛑 Error DB (Leyendo Miembros): {e}")
        return []

def remove_group_member(group_id, target_user_id):
    """Elimina a un usuario con chivato de errores"""
    try:
        supabase.table("group_members").delete().eq("group_id", group_id).eq("user_id", target_user_id).execute()
        return True
    except Exception as e:
        st.error(f"🛑 Error DB (Eliminando Miembro): {e}")
        return False

def request_leave_group(group_id, user_id):
    """Solicita salir del grupo con chivato de errores"""
    try:
        supabase.table("group_members").update({"leave_status": "pending"}).eq("group_id", group_id).eq("user_id", user_id).execute()
        return True
    except Exception as e:
        st.error(f"🛑 Error DB (Pidiendo Salir): {e}")
        return False

def resolve_leave_request(group_id, target_user_id, approve=True):
    """El admin aprueba o rechaza la solicitud de salida"""
    try:
        if approve:
            supabase.table("group_members").delete().eq("group_id", group_id).eq("user_id", target_user_id).execute()
        else:
            supabase.table("group_members").update({"leave_status": "none"}).eq("group_id", group_id).eq("user_id", target_user_id).execute()
        return True
    except Exception as e:
        st.error(f"🛑 Error DB (Resolviendo Solicitud): {e}")
        return False


# ==========================================
# 3. SISTEMA DE INVITACIONES
# ==========================================

def send_invitation(group_id, email):
    try:
        data = {"group_id": group_id, "invited_email": email.lower().strip()}
        supabase.table("group_invitations").insert(data).execute()
        return True, "Invitación enviada"
    except Exception as e:
        return False, str(e)

def get_my_invitations(email):
    try:
        res = supabase.table("group_invitations") \
            .select("*, groups(name, emoji)") \
            .eq("invited_email", email.lower().strip()) \
            .eq("status", "pending") \
            .execute()
        return res.data or []
    except:
        return []

def get_invitations_count(email):
    """Cuenta cuántas invitaciones pendientes tiene el usuario"""
    try:
        res = supabase.table("group_invitations") \
            .select("id", count="exact") \
            .eq("invited_email", email.lower().strip()) \
            .eq("status", "pending") \
            .execute()
        return res.count if res.count else 0
    except Exception as e:
        print(f"Error contando invitaciones: {e}")
        return 0

def respond_invitation(invitation_id, group_id, user_id, accept=True):
    try:
        status = "accepted" if accept else "rejected"
        supabase.table("group_invitations").update({"status": status}).eq("id", invitation_id).execute()
        if accept:
            supabase.table("group_members").insert({"group_id": group_id, "user_id": user_id}).execute()
        return True
    except:
        return False


# ==========================================
# 4. AJUSTES DEL GRUPO
# ==========================================

def update_group_setting(group_id, setting_name, value):
    """Actualiza un ajuste específico con chivato de errores"""
    try:
        supabase.table("groups").update({setting_name: value}).eq("id", group_id).execute()
        return True
    except Exception as e:
        st.error(f"🛑 Error DB (Guardando Ajuste): {e}")
        return False

def update_group_details(group_id, name, emoji, color):
    """Actualiza detalles del grupo con chivato de errores"""
    try:
        supabase.table("groups").update({
            "name": name,
            "emoji": emoji,
            "color": color
        }).eq("id", group_id).execute()
        return True, "Grupo actualizado correctamente"
    except Exception as e:
        st.error(f"🛑 Error DB (Actualizando Grupo): {e}")
        return False, str(e)

def add_shared_expense(group_id, movement_data, member_ids):
    """
    Versión reforzada: Inserta el movimiento personal y vincula el gasto de grupo.
    """
    try:
        # 1. Insertar en 'movements' (Asegúrate de que los nombres de columnas coinciden con tu DB)
        # Nota: Usamos 'quantity' o 'amount' según lo que use tu save_input original
        res_mov = supabase.table("movements").insert({
            "user_id": movement_data['user_id'],
            "quantity": movement_data['quantity'], # O 'amount'
            "type": movement_data['type'],
            "category_id": movement_data['category_id'],
            "date": movement_data['date'],
            "notes": movement_data['notes']
        }).execute()
        
        if res_mov.data:
            mov_id = res_mov.data[0]['id']
            
            # 2. Insertar en 'group_expenses'
            expense_data = {
                "group_id": group_id,
                "movement_id": mov_id,
                "paid_by": movement_data['user_id'],
                "description": movement_data['notes'],
                "total_amount": movement_data['quantity']
            }
            res_exp = supabase.table("group_expenses").insert(expense_data).execute()
            
            if res_exp.data:
                exp_id = res_exp.data[0]['id']
                # 3. Crear los repartos (Splits)
                cuota = movement_data['quantity'] / len(member_ids)
                splits = []
                for mid in member_ids:
                    splits.append({
                        "expense_id": exp_id,
                        "user_id": mid,
                        "amount_owed": cuota,
                        "is_settled": False
                    })
                supabase.table("group_expense_splits").insert(splits).execute()
                return True, "Gasto guardado en personal y grupo"
        
        return False, "Error al insertar movimiento"
    except Exception as e:
        st.error(f"Error en add_shared_expense: {e}")
        return False, str(e)

def get_group_expenses(group_id):
    """Obtiene el historial de gastos compartidos de un grupo"""
    try:
        res = supabase.table("group_expenses") \
            .select("*, profiles(name), group_expense_splits(user_id, amount_owed)") \
            .eq("group_id", group_id) \
            .order("date", ascending=False) \
            .execute()
        return res.data or []
    except Exception as e:
        print(f"Error obteniendo gastos del grupo: {e}")
        return []
