import sqlite3
from config import DB_FILE, USERS

def get_conn():
    return sqlite3.connect(DB_FILE)

def init_db():
    conn = get_conn()
    c = conn.cursor()
    # إنشاء جدول الأوردرات
    c.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT,
            clientName TEXT,
            clientPhone TEXT,
            province TEXT,
            address TEXT,
            sender TEXT,
            price REAL,
            received REAL DEFAULT 0,
            shipping REAL DEFAULT 0,
            status TEXT DEFAULT 'قيد التوصيل',
            notes TEXT DEFAULT '',
            logs TEXT DEFAULT '',
            supply TEXT DEFAULT '',
            agent TEXT DEFAULT ''
        )
    ''')
    # إنشاء جدول المستخدمين
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL,
            role TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

def query_db(query, args=(), one=False):
    conn = get_conn()
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute(query, args)
    rv = c.fetchall()
    conn.commit()
    conn.close()
    return (rv[0] if rv else None) if one else rv

def insert_orders_bulk(data):
    conn = get_conn()
    c = conn.cursor()
    c.executemany('''
        INSERT INTO orders (code, clientName, clientPhone, province, address, sender, price, agent, status, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', data)
    conn.commit()
    conn.close()

def insert_users_bulk(data):
    conn = get_conn()
    c = conn.cursor()
    c.executemany('''
        INSERT OR IGNORE INTO users (username, password, role)
        VALUES (?, ?, ?)
    ''', data)
    conn.commit()
    conn.close()