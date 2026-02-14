# database_groups.py
from database import supabase

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

def send_invitation(group_id, email):
    try:
        data = {"group_id": group_id, "invited_email": email.lower().strip()}
        supabase.table("group_invitations").insert(data).execute()
        return True, "Invitación enviada"
    except Exception as e:
        return False, str(e)

def get_my_invitations(email):
    try:
        # Traemos la invitación y los datos del grupo (JOIN)
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
        # Usamos count="exact" para que Supabase nos devuelva el número sin traer todos los datos
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
        # 1. Actualizar estado de la invitación
        supabase.table("group_invitations").update({"status": status}).eq("id", invitation_id).execute()
        
        # 2. Si acepta, añadirlo a la tabla de miembros
        if accept:
            supabase.table("group_members").insert({"group_id": group_id, "user_id": user_id}).execute()
        return True
    except:
        return False

def get_user_groups(user_id):
    """
    Obtiene todos los grupos a los que pertenece el usuario.
    Hace un JOIN (select anidado) entre group_members y groups.
    """
    try:
        # Buscamos en group_members y traemos los datos del grupo asociado
        res = supabase.table("group_members") \
            .select("group_id, groups(id, name, created_by, created_at)") \
            .eq("user_id", user_id) \
            .execute()
            
        if res.data:
            # Limpiamos el JSON resultante para que sea fácil de leer en la UI
            groups_list = []
            for item in res.data:
                group_info = item.get('groups')
                if group_info:
                    groups_list.append({
                        'id': group_info['id'],
                        'name': group_info['name'],
                        'created_by': group_info['created_by'],
                        'created_at': group_info['created_at']
                    })
            # Ordenamos por fecha de creación (los más recientes primero)
            groups_list.sort(key=lambda x: x['created_at'], reverse=True)
            return groups_list
        return []
    except Exception as e:
        print(f"Error obteniendo grupos: {e}")
        return []

def get_group_members(group_id):
    """Obtiene la lista de usuarios que pertenecen a un grupo específico"""
    try:
        # Hacemos un JOIN con la tabla profiles para traernos su nombre y color
        res = supabase.table("group_members") \
            .select("user_id, profiles(name, lastname, avatar_url, profile_color)") \
            .eq("group_id", group_id) \
            .execute()
        return res.data or []
    except Exception as e:
        print(f"Error obteniendo miembros del grupo: {e}")
        return []

def delete_group(group_id):
    """
    Elimina un grupo. 
    Primero borra los miembros para evitar errores de clave foránea.
    """
    try:
        # 1. Borrar miembros asociados
        supabase.table("group_members").delete().eq("group_id", group_id).execute()
        # 2. Borrar el grupo
        supabase.table("groups").delete().eq("id", group_id).execute()
        return True
    except Exception as e:
        print(f"Error borrando grupo: {e}")
        return False
