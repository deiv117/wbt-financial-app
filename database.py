import sqlite3
import pandas as pd # Movemos pandas aquí arriba para evitar errores ocultos
from datetime import datetime

DB_NAME = 'finance.db'

def init_db():
    """Inicializa la base de datos y crea las tablas si no existen"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    # Tabla Usuarios (Con columna email)
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
    """Crea un nuevo usuario y sus categorías por defecto"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    try:
        # Verificar si el email ya existe
        c.execute('SELECT id FROM users WHERE email = ?', (email,))
        if c.fetchone():
            return False 

        # Crear Usuario (Contraseña en texto plano por ahora para simplificar)
        # Nota: En un entorno real, usaríamos hash para la contraseña
        c.execute('''
            INSERT INTO users (name, email, password, profile_color) 
            VALUES (?, ?, ?, ?)
        ''', (username, email, password, '#636EFA'))
        
        user_id = c.lastrowid
        
        # Categorías por defecto
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
    """Busca un usuario por email o nombre"""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute('SELECT * FROM users WHERE email = ? OR name = ?', (email_or_name, email_or_name))
    user = c.fetchone()
    conn.close()
    
    # Convertimos el objeto Row a un diccionario normal de Python para evitar problemas
    if user:
        return dict(user)
    return None

def upsert_profile(user_data):
    """Actualiza el perfil del usuario"""
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
    ''', (data['user_id
