# database_groups.py
import streamlit as st # <-- ¡CRÍTICO PARA LOS CHIVATOS!
from database import get_supabase_client

# ==========================================
# 1. CORE DE GRUPOS (Crear, Leer, Borrar)
# ==========================================

def create_group(name, emoji, color, user_id):
    client = get_supabase_client()
    try:
        group_data = {"name": name, "emoji": emoji, "color": color, "created_by": user_id}
        res = client.table("groups").insert(group_data).execute()
        
        if res.data:
            group_id = res.data[0]['id']
            member_data = {"group_id": group_id, "user_id": user_id}
            client.table("group_members").insert(member_data).execute()
            return True, "Grupo creado con éxito"
        return False, "Error al crear grupo."
    except Exception as e:
        return False, str(e)

def get_user_groups(user_id):
    """Obtiene todos los grupos a los que pertenece el usuario."""
    client = get_supabase_client()
    try:
        # ¡CORREGIDO! Añadimos emoji y color al select
        res = client.table("group_members") \
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
    client = get_supabase_client()
    try:
        res = client.table("groups").select("*").eq("id", group_id).execute()
        return res.data[0] if res.data else None
    except Exception as e:
        print(f"Error obteniendo info del grupo: {e}")
        return None

def delete_group(group_id):
    """Elimina un grupo (borrando primero a los miembros)."""
    client = get_supabase_client()
    try:
        client.table("group_members").delete().eq("group_id", group_id).execute()
        client.table("groups").delete().eq("id", group_id).execute()
        return True
    except Exception as e:
        print(f"Error borrando grupo: {e}")
        return False


# ==========================================
# 2. GESTIÓN DE MIEMBROS
# ==========================================

def get_group_members(group_id):
    """Obtiene la lista de usuarios con chivato de errores"""
    client = get_supabase_client()
    try:
        res = client.table("group_members").select("user_id, leave_status, profiles(name, lastname, avatar_url, profile_color)").eq("group_id", group_id).execute()
        return res.data or []
    except Exception as e:
        st.error(f"🛑 Error DB (Leyendo Miembros): {e}")
        return []

def remove_group_member(group_id, target_user_id):
    """Elimina a un usuario con chivato de errores"""
    client = get_supabase_client()
    try:
        client.table("group_members").delete().eq("group_id", group_id).eq("user_id", target_user_id).execute()
        return True
    except Exception as e:
        st.error(f"🛑 Error DB (Eliminando Miembro): {e}")
        return False

def request_leave_group(group_id, user_id):
    """Solicita salir del grupo con chivato de errores"""
    client = get_supabase_client()
    try:
        client.table("group_members").update({"leave_status": "pending"}).eq("group_id", group_id).eq("user_id", user_id).execute()
        return True
    except Exception as e:
        st.error(f"🛑 Error DB (Pidiendo Salir): {e}")
        return False

def resolve_leave_request(group_id, target_user_id, approve=True):
    """El admin aprueba o rechaza la solicitud de salida"""
    client = get_supabase_client()
    try:
        if approve:
            client.table("group_members").delete().eq("group_id", group_id).eq("user_id", target_user_id).execute()
        else:
            client.table("group_members").update({"leave_status": "none"}).eq("group_id", group_id).eq("user_id", target_user_id).execute()
        return True
    except Exception as e:
        st.error(f"🛑 Error DB (Resolviendo Solicitud): {e}")
        return False


# ==========================================
# 3. SISTEMA DE INVITACIONES
# ==========================================

def send_invitation(group_id, email):
    client = get_supabase_client()
    try:
        data = {"group_id": group_id, "invited_email": email.lower().strip()}
        client.table("group_invitations").insert(data).execute()
        return True, "Invitación enviada"
    except Exception as e:
        return False, str(e)

def get_my_invitations(email):
    client = get_supabase_client()
    try:
        res = client.table("group_invitations") \
            .select("*, groups(name, emoji)") \
            .eq("invited_email", email.lower().strip()) \
            .eq("status", "pending") \
            .execute()
        return res.data or []
    except:
        return []

def get_invitations_count(email):
    """Cuenta cuántas invitaciones pendientes tiene el usuario"""
    client = get_supabase_client()
    try:
        res = client.table("group_invitations") \
            .select("id", count="exact") \
            .eq("invited_email", email.lower().strip()) \
            .eq("status", "pending") \
            .execute()
        return res.count if res.count else 0
    except Exception as e:
        print(f"Error contando invitaciones: {e}")
        return 0

def respond_invitation(invitation_id, group_id, user_id, accept=True):
    client = get_supabase_client()
    try:
        status = "accepted" if accept else "rejected"
        client.table("group_invitations").update({"status": status}).eq("id", invitation_id).execute()
        if accept:
            client.table("group_members").insert({"group_id": group_id, "user_id": user_id}).execute()
        return True
    except:
        return False


# ==========================================
# 4. AJUSTES DEL GRUPO
# ==========================================

def update_group_setting(group_id, setting_name, value):
    """Actualiza un ajuste específico con chivato de errores"""
    client = get_supabase_client()
    try:
        client.table("groups").update({setting_name: value}).eq("id", group_id).execute()
        return True
    except Exception as e:
        st.error(f"🛑 Error DB (Guardando Ajuste): {e}")
        return False

def update_group_details(group_id, name, emoji, color):
    """Actualiza detalles del grupo con chivato de errores"""
    client = get_supabase_client()
    try:
        client.table("groups").update({
            "name": name,
            "emoji": emoji,
            "color": color
        }).eq("id", group_id).execute()
        return True, "Grupo actualizado correctamente"
    except Exception as e:
        st.error(f"🛑 Error DB (Actualizando Grupo): {e}")
        return False, str(e)

def add_shared_expense(group_id, movement_data, member_ids):
    """Inserta el movimiento personal en user_imputs y vincula el gasto de grupo"""
    client = get_supabase_client()
    try:
        # 1. Guardar primero tu movimiento personal en TU TABLA REAL
        res_mov = client.table("user_imputs").insert({
            "user_id": movement_data['user_id'],
            "quantity": movement_data['quantity'],
            "type": movement_data['type'],
            "category_id": movement_data['category_id'],
            "date": movement_data['date'],
            "notes": movement_data['notes'],
            "group_id": group_id # ¡Aprovechamos la columna que ya tenías creada!
        }).execute()
        
        if not res_mov.data:
            return False, "La base de datos no devolvió el ID del movimiento"
            
        mov_id = res_mov.data[0]['id']
        
        # 2. Registrar el ticket en el Grupo
        expense_data = {
            "group_id": group_id,
            "movement_id": mov_id,
            "paid_by": movement_data['user_id'],
            "description": movement_data.get('notes', 'Gasto compartido'), 
            "total_amount": movement_data.get('quantity', 0)
        }
        res_exp = client.table("group_expenses").insert(expense_data).execute()
        
        if not res_exp.data:
            return False, "Error al crear el ticket de grupo en group_expenses"
            
        exp_id = res_exp.data[0]['id']
        
        # 3. Crear los repartos (A quién le toca pagar qué)
        cuota = movement_data.get('quantity', 0) / len(member_ids)
        splits = []
        for mid in member_ids:
            splits.append({
                "expense_id": exp_id,
                "user_id": mid,
                "amount_owed": cuota,
                "is_settled": False
            })
            
        client.table("group_expense_splits").insert(splits).execute()
        return True, "Gasto compartido registrado"
        
    except Exception as e:
        st.error(f"🛑 Error Técnico DB: {e}") 
        return False, str(e)

def get_group_expenses(group_id):
    """Obtiene el historial de gastos del grupo uniendo perfiles y repartos"""
    import streamlit as st
    client = get_supabase_client()
    try:
        res = client.table("group_expenses") \
            .select("*, profiles(name), group_expense_splits(user_id, amount_owed)") \
            .eq("group_id", group_id) \
            .order("date", desc=True) \
            .execute() # <-- Fíjate en el desc=True
        return res.data or []
    except Exception as e:
        st.error(f"🛑 Error DB (Cargando Historial de Gastos): {e}")
        return []
