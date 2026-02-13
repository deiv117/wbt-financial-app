import streamlit as st
from supabase import create_client, Client
import pandas as pd
from datetime import datetime

# Inicializar cliente Supabase
@st.cache_resource
def init_connection():
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"]["key"]
    return create_client(url, key)

supabase: Client = init_connection()

def init_db():
    # En Supabase las tablas ya están creadas.
    pass

# --- AUTENTICACIÓN Y USUARIO (Supabase Auth + Profiles) ---

def login_user(email, password):
    """Inicia sesión usando Supabase Auth"""
    try:
        response = supabase.auth.sign_in_with_password({"email": email, "password": password})
        return response.user
    except Exception as e:
        print(f"Error login: {e}")
        return None
        
def recover_password(email):
    """Envía un correo para restablecer la contraseña"""
    try:
        # Esto envía el email usando la plantilla que acabas de configurar
        supabase.auth.reset_password_email(email)
        return True, "Correo de recuperación enviado. Revisa tu bandeja de entrada (y spam)."
    except Exception as e:
        return False, f"Error: {str(e)}"
        
def register_user(email, password, name, lastname=""):
    """Registra usuario en Auth y crea su perfil público y categorías"""
    try:
        # 1. Crear usuario en Supabase Auth
        auth_response = supabase.auth.sign_up({
            "email": email, 
            "password": password,
            "options": {
                "data": {"first_name": name} # Metadatos opcionales
            }
        })
        
        if not auth_response.user:
            return False, "No se pudo crear el usuario."

        user_uuid = auth_response.user.id

        # 2. Crear entrada en tabla 'profiles'
        profile_data = {
            "id": user_uuid,
            "name": name,
            "lastname": lastname,
            "profile_color": "#636EFA",
            "social_active": False
        }
        supabase.table('profiles').insert(profile_data).execute()
        
        # 3. Crear Categorías por defecto en 'user_categories'
        crear_categorias_default(user_uuid)
        
        return True, "Usuario creado correctamente."

    except Exception as e:
        return False, str(e)

def get_user_profile(user_uuid):
    """Obtiene los datos de la tabla profiles"""
    try:
        res = supabase.table('profiles').select('*').eq('id', user_uuid).execute()
        if res.data:
            return res.data[0]
        return None
    except Exception as e:
        print(f"Error recuperando perfil: {e}")
        return None

def upsert_profile(profile_data):
    """Actualiza la tabla profiles"""
    try:
        # 'updated_at' debería ser automático si tienes un trigger, 
        # pero lo mandamos por si acaso
        update_data = {
            "name": profile_data['name'],
            "lastname": profile_data.get('lastname', ''),
            "avatar_url": profile_data.get('avatar_url', ''),
            "profile_color": profile_data.get('profile_color', '#636EFA'),
            "updated_at": datetime.now().isoformat()
        }
        supabase.table('profiles').update(update_data).eq('id', profile_data['id']).execute()
    except Exception as e:
        st.error(f"Error actualizando perfil: {e}")

# --- GESTIÓN DE CATEGORÍAS (user_categories) ---

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
        print(f"Error creando categorías default: {e}")

def get_categories(user_uuid):
    try:
        res = supabase.table('user_categories').select('*').eq('user_id', user_uuid).execute()
        cats = res.data
        if not cats:
            crear_categorias_default(user_uuid)
            return get_categories(user_uuid)
        return cats
    except Exception as e:
        print(f"Error get_categories: {e}")
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
        st.error(f"Error guardando categoría: {e}")

def update_category(data):
    try:
        supabase.table('user_categories').update({
            "name": data['name'],
            "emoji": data.get('emoji', '📁'),
            "budget": data.get('budget', 0)
        }).eq('id', data['id']).execute()
    except Exception as e:
        st.error(f"Error actualizando categoría: {e}")

def delete_category(cat_id):
    try:
        supabase.table('user_categories').delete().eq('id', cat_id).execute()
    except Exception as e:
        st.error(f"Error borrando categoría: {e}")

# --- GESTIÓN DE MOVIMIENTOS (user_imputs) ---

def save_input(data):
    try:
        # Nota: Corregido 'user_imputs' según tu schema (ojo si es inputs o imputs en tu tabla real)
        # Asumo 'user_imputs' tal cual me lo has escrito.
        supabase.table('user_imputs').insert({
            "user_id": data['user_id'],
            "quantity": data['quantity'],
            "type": data['type'],
            "category_id": data['category_id'],
            "date": str(data['date']),
            "notes": data['notes'],
            "group_id": data.get('group_id', None) # Preparado para el futuro
        }).execute()
    except Exception as e:
        st.error(f"Error guardando movimiento: {e}")

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
        st.error(f"Error actualizando movimiento: {e}")

def delete_input(mov_id):
    try:
        supabase.table('user_imputs').delete().eq('id', mov_id).execute()
    except Exception as e:
        st.error(f"Error borrando movimiento: {e}")

def get_transactions(user_uuid):
    try:
        # Join con user_categories
        response = supabase.table('user_imputs') \
            .select('*, user_categories(name, emoji, budget)') \
            .eq('user_id', user_uuid) \
            .execute()
        
        data = response.data
        if not data:
            return pd.DataFrame()
            
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
        print(f"Error get_transactions: {e}")
        return pd.DataFrame()
