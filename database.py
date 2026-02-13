import sqlite3
import pandas as pd
from datetime import datetime

DB_NAME = 'finance.db'

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    # Tabla Usuarios
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
            type TEXT,
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
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    try:
        c.execute('SELECT id FROM users WHERE email = ?', (email,))
        if c.fetchone():
            return False 

        c.execute('''
            INSERT INTO users (name, email, password, profile_color) 
            VALUES (?, ?, ?, ?)
        ''', (username, email, password, '#636EFA'))
        
        user_id = c.lastrowid
        
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
        print(f"Error: {e}")
        return False
    finally:
        conn.close()

def get_user(email_or_name):
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute('SELECT * FROM users WHERE email = ? OR name = ?', (email_or_name, email_or_name))
    row = c.fetchone()
    conn.close()
    if row:
        return dict(row)
    return None

def upsert_profile(user_data):
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
    conn = sqlite3.connect(DB_NAME)
    query = '''
        SELECT m.id, m.date, m.quantity, m.type, m.notes, m.category_id,
               c.name as cat_name, c.emoji as cat_emoji, c.budget
        FROM movements m
        LEFT JOIN categories c ON m.category_id = c.id
        WHERE m.user_id = ?
    '''
    try:
        df = pd.read_sql_query(query, conn, params=(user_id,))
        if not df.empty:
            df['date'] = pd.to_datetime(df['date'])
            # Simplificación para evitar errores
            def format_cat(row):
                emoji = row['cat_emoji'] if row['cat_emoji'] else '📁'
                name = row['cat_name'] if row['cat_name'] else 'General'
                return f"{emoji} {name}"
            
            df['cat_display'] = df.apply(format_cat, axis=1)
    except Exception:
        df = pd.DataFrame()
    finally:
        conn.close()
    return df

# --- FUNCIONES DE CATEGORÍAS ---

def save_category(data):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''
        INSERT INTO categories (user_id, name, type, emoji, budget)
        VALUES (?, ?, ?, ?, ?)
    ''', (data['user_id'], data['name'], data['type'], data.get('emoji','📁'), data.get('budget',0)))
    conn.commit()
    conn.close()

# ESTA ES LA FUNCIÓN QUE FALTABA
def update_category(data):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''
        UPDATE categories 
        SET name=?, emoji=?, budget=?
        WHERE id=?
    ''', (data['name'], data.get('emoji', '📁'), data.get('budget', 0), data['id']))
    conn.commit()
    conn.close()

def get_categories(user_id):
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute('SELECT * FROM categories WHERE user_id = ?', (user_id,))
    rows = c.fetchall()
    conn.close()
    
    cats = [dict(row) for row in rows]
    
    if not cats:
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("INSERT INTO categories (user_id, name, type, emoji, budget) VALUES (?, 'General', 'Gasto', '📁', 0)", (user_id,))
        conn.commit()
        conn.close()
        return get_categories(user_id)
        
    return cats

def delete_category(cat_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('DELETE FROM categories WHERE id = ?', (cat_id,))
    conn.commit()
    conn.close()
