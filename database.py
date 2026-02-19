import streamlit as st
from supabase import create_client, Client
import pandas as pd
from datetime import datetime
import time

# --- MODIFICACIÓN PARA MULTIUSUARIO (SESIONES INDEPENDIENTES) ---
def get_supabase_client() -> Client:
    """
    Crea o recupera el cliente de Supabase específico para la sesión actual.
    Esto evita colisiones entre diferentes dispositivos/usuarios.
    """
    if 'supabase_client' not in st.session_state:
        url = st.secrets["supabase"]["url"]
        key = st.secrets["supabase"]["key"]
        st.session_state.supabase_client = create_client(url, key)
    return st.session_state.supabase_client

# Definimos una propiedad dinámica para que el resto de tus funciones
# sigan usando la variable 'supabase' sin tener que cambiar todo el código.
@property
def supabase():
    return get_supabase_client()

# Reemplazamos la inicialización estática por la llamada a la función
supabase = get_supabase_client()

def init_db():
    pass

# --- AUTENTICACIÓN Y USUARIO ---

def login_user(email, password):
    # Aseguramos que usamos el cliente de la sesión actual
    client = get_supabase_client()
    try:
        response = client.auth.sign_in_with_password({"email": email, "password": password})
        return response.user
    except Exception as e:
        print(f"Error login: {e}")
        return None

def register_user(email, password, name, lastname=""):
    client = get_supabase_client()
    try:
        auth_response = client.auth.sign_up({
            "email": email, 
            "password": password,
            "options": {"data": {"first_name": name}}
        })
        
        if not auth_response.user:
            return False, "No se pudo crear el usuario."

        user_uuid = auth_response.user.id

        profile_data = {
            "id": user_uuid,
            "name": name,
            "lastname": lastname,
            "profile_color": "#636EFA",
            "social_active": False,
            "initial_balance": 0,
            "base_salary": 0,
            "payments_per_year": 12
        }
        client.table('profiles').insert(profile_data).execute()
        crear_categorias_default(user_uuid)
        
        return True, "Usuario creado correctamente."

    except Exception as e:
        return False, str(e)

def recover_password(email):
    client = get_supabase_client()
    try:
        client.auth.reset_password_email(email)
        return True, "Correo de recuperación enviado."
    except Exception as e:
        return False, f"Error: {str(e)}"

def change_password(new_password):
    """Cambia la contraseña del usuario logueado"""
    client = get_supabase_client()
    try:
        client.auth.update_user({"password": new_password})
        return True, "Contraseña actualizada."
    except Exception as e:
        return False, str(e)

# --- PERFIL Y AVATAR ---

def get_user_profile(user_id):
    """Obtiene el perfil del usuario mostrando errores reales si los hay"""
    client = get_supabase_client()
    try:
        res = client.table('profiles').select('*').eq('id', user_id).execute()
        
        # Si la librería devuelve un error en el objeto
        if hasattr(res, 'error') and res.error:
            st.error(f"🛑 Error de lectura en Supabase: {res.error}")
            return None
            
        if res.data:
            return res.data[0]
        return None
        
    except Exception as e:
        st.error(f"🛑 Excepción leyendo el perfil: {e}")
        return None

def upload_avatar(file, user_id):
    """Sube avatar con límite de 5MB y Cache Busting"""
    client = get_supabase_client()
    try:
        MAX_SIZE = 5 * 1024 * 1024
        if file.size > MAX_SIZE:
            st.error("⚠️ La imagen es demasiado grande. Máximo 5MB.")
            return None

        file_path = f"{user_id}/avatar.png" 
        
        client.storage.from_("avatars").upload(
            path=file_path,
            file=file.getvalue(),
            file_options={"content-type": file.type, "upsert": "true"}
        )
        
        public_url = client.storage.from_("avatars").get_public_url(file_path)
        timestamp_url = f"{public_url}?v={int(time.time())}"
        
        return timestamp_url
    except Exception as e:
        st.error(f"Error subiendo imagen: {e}")
        return None

def upsert_profile(profile_data):
    """Guarda/Actualiza el perfil aislando el historial para evitar bloqueos"""
    client = get_supabase_client()
    try:
        user_id = profile_data.get('id')
        
        # 1. Intentamos actualizar el perfil (o crearlo si no existe)
        res = client.table('profiles').update(profile_data).eq('id', user_id).execute()
        
        if hasattr(res, 'error') and res.error:
            st.error(f"🛑 Error al actualizar el perfil: {res.error}")
            return False
            
        if not res.data:
            res_insert = client.table('profiles').insert(profile_data).execute()
            if hasattr(res_insert, 'error') and res_insert.error:
                st.error(f"🛑 Error al crear el perfil: {res_insert.error}")
                return False

        # 2. Guardamos el historial en un bloque SEPARADO y PROTEGIDO
        try:
            today = datetime.now().strftime("%Y-%m-%d")
            history_data = {
                "user_id": user_id,
                "base_salary": profile_data.get('base_salary', 0),
                "other_fixed_income": profile_data.get('other_fixed_income', 0),
                "other_income_frequency": profile_data.get('other_income_frequency', 1),
                "valid_from": today
            }
            # Intentamos upsert en lugar de insert por si ya guardó hoy
            client.table('income_history').upsert(history_data).execute()
        except Exception as e:
            # Si esto falla (por ejemplo por la Primary Key), lo ignoramos silenciosamente
            # Lo importante es que tu nombre (Paso 1) ya está guardado.
            pass
            
        return True
        
    except Exception as e:
        st.error(f"🛑 Excepción general guardando el perfil: {e}")
        return False
        
def get_historical_income(user_id, target_date):
    client = get_supabase_client()
    try:
        res = client.table('income_history') \
            .select('*') \
            .eq('user_id', user_id) \
            .lte('valid_from', target_date) \
            .order('valid_from', desc=True) \
            .limit(1) \
            .execute()
        
        if res.data:
            return res.data[0]
        else:
            return get_user_profile(user_id)
    except Exception as e:
        return {'base_salary': 0, 'other_fixed_income': 0}

# --- CATEGORÍAS ---

def crear_categorias_default(user_uuid):
    client = get_supabase_client()
    default_cats = [
        {'user_id': user_uuid, 'name': 'Nómina', 'type': 'Ingreso', 'emoji': '💰', 'budget': 0},
        {'user_id': user_uuid, 'name': 'Ahorro', 'type': 'Ingreso', 'emoji': '🐷', 'budget': 0},
        {'user_id': user_uuid, 'name': 'Vivienda', 'type': 'Gasto', 'emoji': '🏠', 'budget': 600},
        {'user_id': user_uuid, 'name': 'Supermercado', 'type': 'Gasto', 'emoji': '🛒', 'budget': 300},
        {'user_id': user_uuid, 'name': 'Transporte', 'type': 'Gasto', 'emoji': '🚌', 'budget': 50},
        {'user_id': user_uuid, 'name': 'Ocio', 'type': 'Gasto', 'emoji': '🎉', 'budget': 150},
        {'user_id': user_uuid, 'name': 'Restaurantes', 'type': 'Gasto', 'emoji': '🍔', 'budget': 100},
        {'user_id': user_uuid, 'name': 'Salud', 'type': 'Gasto', 'emoji': '💊', 'budget': 50}
    ]
    try:
        client.table('user_categories').insert(default_cats).execute()
    except Exception as e:
        print(f"Error default cats: {e}")

def get_categories(user_uuid):
    client = get_supabase_client()
    try:
        res = client.table('user_categories').select('*').eq('user_id', user_uuid).execute()
        cats = res.data
        if not cats:
            crear_categorias_default(user_uuid)
            return get_categories(user_uuid)
        return cats
    except Exception as e:
        return []

def save_category(data):
    client = get_supabase_client()
    try:
        client.table('user_categories').insert({
            "user_id": data['user_id'],
            "name": data['name'],
            "type": data['type'],
            "emoji": data.get('emoji', '📁'),
            "budget": data.get('budget', 0),
            "budget_type": data.get('budget_type', 'fixed'),
            "budget_percent": data.get('budget_percent', 0)
        }).execute()
    except Exception as e:
        st.error(f"Error guardando categoría: {e}")

def update_category(cat_id, data):
    client = get_supabase_client()
    try:
        client.table('user_categories').update({
            "name": data['name'],
            "emoji": data.get('emoji', '📁'),
            "budget": data.get('budget', 0),
            "budget_type": data.get('budget_type', 'fixed'),
            "budget_percent": data.get('budget_percent', 0)
        }).eq('id', cat_id).execute()
    except Exception as e:
        st.error(f"Error actualizando categoría: {e}")

def delete_category(cat_id):
    client = get_supabase_client()
    try:
        client.table('user_categories').delete().eq('id', cat_id).execute()
    except Exception as e:
        st.error(f"Error: {e}")

# --- MOVIMIENTOS ---

def save_input(data):
    client = get_supabase_client()
    # Si esto falla, lanzará una excepción directamente a views.py, 
    # bloqueando el rerun() y mostrándote el error real.
    client.table('user_imputs').insert({
        "user_id": data['user_id'],
        "quantity": data['quantity'],
        "type": data['type'],
        "category_id": data['category_id'],
        "date": str(data['date']),
        "notes": data['notes'],
        "group_id": data.get('group_id', None)
    }).execute()

def update_input(data):
    client = get_supabase_client()
    try:
        client.table('user_imputs').update({
            "quantity": data['quantity'],
            "type": data['type'],
            "category_id": data['category_id'],
            "date": str(data['date']),
            "notes": data['notes']
        }).eq('id', data['id']).execute()
    except Exception as e:
        st.error(f"Error update input: {e}")

def delete_input(mov_id):
    client = get_supabase_client()
    try:
        # 1. Primero buscamos si este movimiento estaba en algún grupo y lo borramos de allí
        client.table('group_expenses').delete().eq('movement_id', mov_id).execute()
        
        # 2. Luego borramos el movimiento personal original
        client.table('user_imputs').delete().eq('id', mov_id).execute()
    except Exception as e:
        import streamlit as st
        st.error(f"Error delete input: {e}")

def get_transactions(user_uuid):
    client = get_supabase_client()
    try:
        # Añadimos groups(name, emoji) al JOIN
        response = client.table('user_imputs') \
            .select('*, user_categories(name, emoji, budget), groups(name, emoji)') \
            .eq('user_id', user_uuid) \
            .execute()
        
        data = response.data
        if not data: return pd.DataFrame()
            
        flat_data = []
        for row in data:
            cat = row.get('user_categories') or {}
            grp = row.get('groups') or {} # Extraemos info del grupo
            
            flat_row = row.copy()
            del flat_row['user_categories']
            if 'groups' in flat_row: del flat_row['groups']
            
            flat_row['cat_name'] = cat.get('name', 'General')
            flat_row['cat_emoji'] = cat.get('emoji', '📁')
            flat_row['budget'] = cat.get('budget', 0)
            
            # Guardamos los datos del grupo en la fila
            flat_row['group_name'] = grp.get('name', None)
            flat_row['group_emoji'] = grp.get('emoji', '👥')
            
            flat_data.append(flat_row)
            
        df = pd.DataFrame(flat_data)
        if not df.empty:
            df['date'] = pd.to_datetime(df['date'])
            df['cat_display'] = df.apply(lambda x: f"{x['cat_emoji']} {x['cat_name']}", axis=1)
        return df
    except Exception as e:
        print(f"Error cargando transacciones: {e}")
        return pd.DataFrame()

def recalculate_category_budgets(user_id, new_total_income):
    client = get_supabase_client()
    try:
        response = client.table('user_categories').select('*').eq('user_id', user_id).eq('budget_type', 'percentage').execute()
        cats = response.data

        count = 0
        if cats:
            for cat in cats:
                percent = float(cat.get('budget_percent', 0) or 0)
                if percent > 0:
                    new_euro_budget = (new_total_income * percent) / 100
                    client.table('user_categories').update({"budget": new_euro_budget}).eq('id', cat['id']).execute()
                    count += 1
        
        return count
    except Exception as e:
        print(f"Error recalculando presupuestos: {e}") 
        return 0

def save_bulk_inputs(data_list):
    """Guarda múltiples registros de una sola vez (Bulk Insert)"""
    client = get_supabase_client()
    
    chunk_size = 500 # Subimos de 500 en 500 para ser seguros
    total_inserted = 0
    
    for i in range(0, len(data_list), chunk_size):
        chunk = data_list[i:i + chunk_size]
        
        # El método insert() de Supabase acepta una lista de diccionarios enteros
        res = client.table('user_imputs').insert(chunk).execute()
        
        if hasattr(res, 'error') and res.error:
            raise Exception(f"Error en bloque: {res.error}")
            
        total_inserted += len(chunk)
        
    return total_inserted
