# database_groups.py
from database import supabase

def create_group(name, user_id):
    """
    Crea un nuevo grupo y automáticamente añade al creador como el primer miembro.
    """
    try:
        # 1. Insertar el grupo en la tabla 'groups'
        group_data = {"name": name, "created_by": user_id}
        res = supabase.table("groups").insert(group_data).execute()
        
        if res.data:
            group_id = res.data[0]['id']
            # 2. Insertar al creador en la tabla 'group_members'
            # (Usamos created_at como especificaste, aunque Supabase lo rellena solo si tiene default now())
            member_data = {"group_id": group_id, "user_id": user_id}
            supabase.table("group_members").insert(member_data).execute()
            
            return True, "Grupo creado con éxito"
        return False, "No se pudo crear el grupo."
    except Exception as e:
        return False, f"Error: {str(e)}"

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
