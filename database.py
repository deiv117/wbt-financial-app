import sqlite3
from datetime import datetime

DB_NAME = 'finance.db'

def init_db():
    """Inicializa la base de datos y crea las tablas si no existen"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    # Tabla Usuarios (Añadido email)
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE,
            name TEXT,
            lastname TEXT,
            password TEXT,
            avatar_url TEXT,
            profile_color TEXT
        )
    ''')
    
    # Tabla Categorías
    c.execute('''
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            name TEXT,
            type TEXT, -- 'Ingreso' o 'Gasto'
            emoji TEXT,
            budget REAL,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    ''')
    
    # Tabla Movimientos
    c.execute('''
        CREATE TABLE IF NOT EXISTS movements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            quantity REAL,
            type TEXT,
            category_id INTEGER,
            date TEXT,
            notes TEXT,
            FOREIGN KEY(user_id) REFERENCES users(id),
            FOREIGN KEY(category_id) REFERENCES categories(id)
        )
    ''')
    
    conn.commit()
    conn.close()

# --- FUNCIONES DE USUARIO ---

def create_user(username, password, email):
    """Crea un nuevo usuario y sus categorías por defecto"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    try:
        # Verificar si ya existe el email
        c.execute('SELECT id FROM users WHERE email = ?', (email,))
        if c.fetchone():
            return False # El usuario ya existe

        # 1. Crear Usuario
        # NOTA: En producción, aquí deberíamos hashear la contraseña
        c.execute('''
            INSERT INTO users (name, email, password, profile_color) 
            VALUES (?, ?, ?, ?)
        ''', (username, email, password, '#636EFA'))
        
        user_id = c.lastrowid
        
        # 2. Crear Categorías por Defecto para el nuevo usuario
        default_cats = [
            ('Nómina', 'Ingreso', '💰', 0),
            ('Ahorro', 'Ingreso', '🐷', 0),
            ('Vivienda', 'Gasto', '🏠', 600),
            ('Supermercado', 'Gasto', '🛒', 300),
            ('Transporte', 'Gasto', '🚌', 50),
            ('Ocio', 'Gasto', '🎉', 150),
            ('Restaurantes', 'Gasto', '🍔', 100),
            ('Salud', 'Gasto', '💊', 50)
        ]
        
        for nombre, tipo, emoji, presupuesto in default_cats:
            c.execute('''
                INSERT INTO categories (user_id, name, type, emoji, budget)
                VALUES (?, ?, ?, ?, ?)
            ''', (user_id, nombre, tipo, emoji, presupuesto))
        
        conn.commit()
        return True
    except Exception as e:
        print(f"Error creando usuario: {e}")
        return False
    finally:
        conn.close()

def get_user(email_or_name):
    """Busca un usuario por email o nombre (para el login)"""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    # Buscamos por email O por nombre (para dar flexibilidad)
    c.execute('SELECT * FROM users WHERE email = ? OR name = ?', (email_or_name, email_or_name))
    user = c.fetchone()
    conn.close()
    return user

def upsert_profile(user_data):
    """Actualiza o inserta datos del perfil"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''
        UPDATE users 
        SET name = ?, lastname = ?, avatar_url = ?, profile_color = ?
        WHERE id = ?
    ''', (user_data['name'], user_data.get('lastname',''), user_data.get('avatar_url',''), user_data.get('profile_color','#636EFA'), user_data['id']))
    conn.commit()
    conn.close()

# --- FUNCIONES DE MOVIMIENTOS ---

def save_input(data):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''
        INSERT INTO movements (user_id, quantity, type, category_id, date, notes)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (data['user_id'], data['quantity'], data['type'], data['category_id'], data['date'], data['notes']))
    conn.commit()
    conn.close()

def update_input(data):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''
        UPDATE movements 
        SET quantity=?, type=?, category_id=?, date=?, notes=?
        WHERE id=?
    ''', (data['quantity'], data['type'], data['category_id'], data['date'], data['notes'], data['id']))
    conn.commit()
    conn.close()

def delete_input(mov_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('DELETE FROM movements WHERE id = ?', (mov_id,))
    conn.commit()
    conn.close()

def get_transactions(user_id):
    import pandas as pd
    conn = sqlite3.connect(DB_NAME)
    query = '''
        SELECT m.id, m.date, m.quantity, m.type, m.notes, m.category_id,
               c.name as cat_name, c.emoji as cat_emoji, c.budget
        FROM movements m
        LEFT JOIN categories c ON m.category_id = c.id
        WHERE m.user_id = ?
    '''
    df = pd.read_sql_query(query, conn, params=(user_id,))
    conn.close()
    
    if not df.empty:
        df['date'] = pd.to_datetime(df['date'])
        df['cat_display'] = df.apply(lambda x: f"{x['cat_emoji'] if x['cat_emoji'] else '📁'} {x['cat_name'] if x['cat_name'] else 'General'}", axis=1)
    return df

# --- FUNCIONES DE CATEGORÍAS ---

def get_categories(user_id):
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute('SELECT * FROM categories WHERE user_id = ?', (user_id,))
    cats = [dict(row) for row in c.fetchall()]
    conn.close()
    
    # Si no hay categorías (usuario nuevo antiguo), creamos una por defecto
    if not cats:
        save_category({'user_id': user_id, 'name': 'General', 'type': 'Gasto', 'emoji': '📁', 'budget': 0})
        return get_categories(user_id)
        
    return cats

def save_category(data):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''
        INSERT INTO categories (user_id, name, type, emoji, budget)
        VALUES (?, ?, ?, ?, ?)
    ''', (data['user_id'], data['name'], data['type'], data.get('emoji','📁'), data.get('budget',0)))
    conn.commit()
    conn.close()

def delete_category(cat_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('DELETE FROM categories WHERE id = ?', (cat_id,))
    # Opcional: Borrar movimientos de esa categoría o moverlos a "General"
    conn.commit()
    conn.close()
