import streamlit as st
from supabase import create_client, Client
import pandas as pd
from datetime import datetime
import time

# Inicializar cliente Supabase
@st.cache_resource
def init_connection():
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"]["key"]
    return create_client(url, key)

supabase: Client = init_connection()

def init_db():
    pass

# --- AUTENTICACIÓN Y USUARIO ---

def login_user(email, password):
    try:
        response = supabase.auth.sign_in_with_password({"email": email, "password": password})
        return response.user
    except Exception as e:
        print(f"Error login: {e}")
        return None

def register_user(email, password, name, lastname=""):
    try:
        auth_response = supabase.auth.sign_up({
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
        supabase.table('profiles').insert(profile_data).execute()
        crear_categorias_default(user_uuid)
        
        return True, "Usuario creado correctamente."

    except Exception as e:
        return False, str(e)

def recover_password(email):
    try:
        supabase.auth.reset_password_email(email)
        return True, "Correo de recuperación enviado."
    except Exception as e:
        return False, f"Error: {str(e)}"

def change_password(new_password):
    """Cambia la contraseña del usuario logueado"""
    try:
        supabase.auth.update_user({"password": new_password})
        return True, "Contraseña actualizada."
    except Exception as e:
        return False, str(e)

# --- PERFIL Y AVATAR ---

def get_user_profile(user_uuid):
    try:
        res = supabase.table('profiles').select('*').eq('id', user_uuid).execute()
        if res.data:
            return res.data[0]
        return None
    except Exception as e:
        print(f"Error recuperando perfil: {e}")
        return None

def upload_avatar(file, user_id):
    """Sube avatar con límite de 5MB y Cache Busting"""
    try:
        # 1. VALIDACIÓN DE TAMAÑO (5MB = 5 * 1024 * 1024 bytes)
        MAX_SIZE = 5 * 1024 * 1024
        if file.size > MAX_SIZE:
            st.error("⚠️ La imagen es demasiado grande. Máximo 5MB.")
            return None

        file_ext = file.name.split('.')[-1]
        # Usamos siempre el mismo nombre de archivo para no llenar el bucket de basura,
        # pero añadimos un parámetro de versión en la URL luego.
        file_path = f"{user_id}/avatar.png" 
        
        # Subir archivo (Upsert=True sobrescribe el anterior)
        supabase.storage.from_("avatars").upload(
            path=file_path,
            file=file.getvalue(),
            file_options={"content-type": file.type, "upsert": "true"}
        )
        
        # 2. CACHE BUSTING: Añadimos ?v=timestamp para obligar al navegador a recargarla
        # Supabase devuelve la URL base, nosotros le pegamos el truco.
        public_url = supabase.storage.from_("avatars").get_public_url(file_path)
        timestamp_url = f"{public_url}?v={int(time.time())}"
        
        return timestamp_url
    except Exception as e:
        st.error(f"Error subiendo imagen: {e}")
        return None

def upsert_profile(user_data):
    """Actualiza perfil y guarda historial de sueldo si cambia"""
    try:
        # 1. Actualizar tabla PROFILES
        update_data = {
            "name": user_data['name'],
            "lastname": user_data.get('lastname', ''),
            "avatar_url": user_data.get('avatar_url', ''),
            "profile_color": user_data.get('profile_color', '#636EFA'),
            "initial_balance": user_data.get('initial_balance', 0),
            "base_salary": user_data.get('base_salary', 0),
            "other_fixed_income": user_data.get('other_fixed_income', 0),
            "other_income_frequency": user_data.get('other_income_frequency', 1), # <--- NUEVO
            "payments_per_year": user_data.get('payments_per_year', 12),
            "updated_at": datetime.now().isoformat()
        }
        supabase.table('profiles').update(update_data).eq('id', user_data['id']).execute()

        # 2. GESTIÓN DEL HISTORIAL (La Máquina del Tiempo)
        today = datetime.now().strftime("%Y-%m-%d")
        
        # Insertamos el nuevo registro histórico
        history_data = {
            "user_id": user_data['id'],
            "base_salary": user_data.get('base_salary', 0),
            "other_fixed_income": user_data.get('other_fixed_income', 0),
            "other_income_frequency": user_data.get('other_income_frequency', 1), # <--- NUEVO
            "valid_from": today
        }
        supabase.table('income_history').insert(history_data).execute()

        return True
    except Exception as e:
        st.error(f"Error actualizando perfil: {e}")
        return False
        
def get_historical_income(user_id, target_date):
    """Busca cuánto cobraba el usuario en una fecha específica"""
    try:
        # Buscamos el registro más reciente que sea ANTERIOR o IGUAL a la fecha target
        res = supabase.table('income_history') \
            .select('*') \
            .eq('user_id', user_id) \
            .lte('valid_from', target_date) \
            .order('valid_from', desc=True) \
            .limit(1) \
            .execute()
        
        if res.data:
            return res.data[0]
        else:
            # Si no hay historial antiguo, devolvemos el actual del perfil por defecto
            return get_user_profile(user_id)
    except Exception as e:
        return {'base_salary': 0, 'other_fixed_income': 0}

# --- CATEGORÍAS (Igual que antes) ---

def crear_categorias_default(user_uuid):
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
        supabase.table('user_categories').insert(default_cats).execute()
    except Exception as e:
        print(f"Error default cats: {e}")

def get_categories(user_uuid):
    try:
        res = supabase.table('user_categories').select('*').eq('user_id', user_uuid).execute()
        cats = res.data
        if not cats:
            crear_categorias_default(user_uuid)
            return get_categories(user_uuid)
        return cats
    except Exception as e:
        return []

def save_category(data):
    try:
        supabase.table('user_categories').insert({
            "user_id": data['user_id'],
            "name": data['name'],
            "type": data['type'],
            "emoji": data.get('emoji', '📁'),
            "budget": data.get('budget', 0)
        }).execute()
    except Exception as e:
        st.error(f"Error: {e}")

def update_category(data):
    try:
        supabase.table('user_categories').update({
            "name": data['name'],
            "emoji": data.get('emoji', '📁'),
            "budget": data.get('budget', 0)
        }).eq('id', data['id']).execute()
    except Exception as e:
        st.error(f"Error: {e}")

def delete_category(cat_id):
    try:
        supabase.table('user_categories').delete().eq('id', cat_id).execute()
    except Exception as e:
        st.error(f"Error: {e}")

# --- MOVIMIENTOS (Igual que antes) ---

def save_input(data):
    try:
        supabase.table('user_imputs').insert({
            "user_id": data['user_id'],
            "quantity": data['quantity'],
            "type": data['type'],
            "category_id": data['category_id'],
            "date": str(data['date']),
            "notes": data['notes'],
            "group_id": data.get('group_id', None)
        }).execute()
    except Exception as e:
        st.error(f"Error input: {e}")

def update_input(data):
    try:
        supabase.table('user_imputs').update({
            "quantity": data['quantity'],
            "type": data['type'],
            "category_id": data['category_id'],
            "date": str(data['date']),
            "notes": data['notes']
        }).eq('id', data['id']).execute()
    except Exception as e:
        st.error(f"Error update input: {e}")

def delete_input(mov_id):
    try:
        supabase.table('user_imputs').delete().eq('id', mov_id).execute()
    except Exception as e:
        st.error(f"Error delete input: {e}")

def get_transactions(user_uuid):
    try:
        response = supabase.table('user_imputs') \
            .select('*, user_categories(name, emoji, budget)') \
            .eq('user_id', user_uuid) \
            .execute()
        
        data = response.data
        if not data: return pd.DataFrame()
            
        flat_data = []
        for row in data:
            cat = row.get('user_categories') or {}
            flat_row = row.copy()
            del flat_row['user_categories']
            flat_row['cat_name'] = cat.get('name', 'General')
            flat_row['cat_emoji'] = cat.get('emoji', '📁')
            flat_row['budget'] = cat.get('budget', 0)
            flat_data.append(flat_row)
            
        df = pd.DataFrame(flat_data)
        if not df.empty:
            df['date'] = pd.to_datetime(df['date'])
            df['cat_display'] = df.apply(lambda x: f"{x['cat_emoji']} {x['cat_name']}", axis=1)
        return df
    except Exception as e:
        return pd.DataFrame()
