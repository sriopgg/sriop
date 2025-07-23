
import sqlite3
import logging
from datetime import datetime
from typing import Optional, List, Tuple, Dict, Any
from config import DB_PATH

logger = logging.getLogger(__name__)

class DatabaseError(Exception):
    """Custom exception for database operations"""
    pass

def get_connection() -> sqlite3.Connection:
    """Get database connection with row factory"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initialize database and create tables"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Users table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            last_name TEXT,
            balance REAL DEFAULT 0.0,
            is_blocked INTEGER DEFAULT 0,
            join_date TEXT,
            last_activity TEXT
        )
        ''')
        
        # Add missing columns if they don't exist
        try:
            cursor.execute('ALTER TABLE users ADD COLUMN first_name TEXT')
        except sqlite3.OperationalError:
            pass
        
        try:
            cursor.execute('ALTER TABLE users ADD COLUMN last_name TEXT')
        except sqlite3.OperationalError:
            pass
        
        try:
            cursor.execute('ALTER TABLE users ADD COLUMN last_activity TEXT')
        except sqlite3.OperationalError:
            pass
        
        try:
            cursor.execute('ALTER TABLE users ADD COLUMN is_blocked INTEGER DEFAULT 0')
        except sqlite3.OperationalError:
            pass
        
        # Transactions table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            tx_type TEXT,
            amount REAL,
            trx_id TEXT,
            status TEXT DEFAULT 'completed',
            description TEXT,
            timestamp TEXT,
            FOREIGN KEY (user_id) REFERENCES users (user_id)
        )
        ''')
        
        # Signed APKs table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS signed_apks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            file_name TEXT,
            file_id TEXT,
            original_size INTEGER,
            signed_size INTEGER,
            sign_time TEXT,
            FOREIGN KEY (user_id) REFERENCES users (user_id)
        )
        ''')
        
        # Support messages table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS support_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            message_id INTEGER,
            message_text TEXT,
            admin_reply TEXT,
            status TEXT DEFAULT 'pending',
            created_at TEXT,
            replied_at TEXT,
            FOREIGN KEY (user_id) REFERENCES users (user_id)
        )
        ''')
        
        # Settings table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT,
            updated_at TEXT
        )
        ''')
        
        # Initialize default settings
        cursor.execute('''
        INSERT OR IGNORE INTO settings (key, value, updated_at) 
        VALUES ('sign_price_trx', '3.0', ?)
        ''', (datetime.now().isoformat(),))
        
        conn.commit()
        conn.close()
        logger.info("Database initialized successfully")
        
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise DatabaseError(f"Database initialization failed: {e}")

# User Operations
def add_user(user_id: int, username: str = None, first_name: str = None, last_name: str = None) -> bool:
    """Add new user or update existing user info"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        current_time = datetime.now().isoformat()
        
        cursor.execute('''
        INSERT OR REPLACE INTO users 
        (user_id, username, first_name, last_name, join_date, last_activity, is_blocked, balance)
        VALUES (?, ?, ?, ?, 
                COALESCE((SELECT join_date FROM users WHERE user_id = ?), ?),
                ?,
                COALESCE((SELECT is_blocked FROM users WHERE user_id = ?), 0),
                COALESCE((SELECT balance FROM users WHERE user_id = ?), 0.0))
        ''', (user_id, username, first_name, last_name, user_id, current_time, current_time, user_id, user_id))
        
        conn.commit()
        conn.close()
        return True
        
    except Exception as e:
        logger.error(f"Failed to add/update user {user_id}: {e}")
        return False

def get_user(user_id: int) -> Optional[Dict[str, Any]]:
    """Get user information"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
        row = cursor.fetchone()
        conn.close()
        
        return dict(row) if row else None
        
    except Exception as e:
        logger.error(f"Failed to get user {user_id}: {e}")
        return None

def update_user_activity(user_id: int):
    """Update user's last activity timestamp"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
        UPDATE users SET last_activity = ? WHERE user_id = ?
        ''', (datetime.now().isoformat(), user_id))
        
        conn.commit()
        conn.close()
        
    except Exception as e:
        logger.error(f"Failed to update activity for user {user_id}: {e}")

def get_user_balance(user_id: int) -> float:
    """Get user's current balance"""
    user = get_user(user_id)
    return user['balance'] if user else 0.0

def update_balance(user_id: int, amount: float, tx_type: str = None, description: str = None) -> bool:
    """Update user balance and create transaction record"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Update balance
        cursor.execute('''
        UPDATE users SET balance = balance + ? WHERE user_id = ?
        ''', (amount, user_id))
        
        # Add transaction record
        if tx_type:
            add_transaction(user_id, tx_type, amount, description=description, cursor=cursor)
        
        conn.commit()
        conn.close()
        return True
        
    except Exception as e:
        logger.error(f"Failed to update balance for user {user_id}: {e}")
        return False

def block_user(user_id: int, blocked: bool = True) -> bool:
    """Block or unblock user"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
        UPDATE users SET is_blocked = ? WHERE user_id = ?
        ''', (int(blocked), user_id))
        
        conn.commit()
        conn.close()
        return cursor.rowcount > 0
        
    except Exception as e:
        logger.error(f"Failed to block/unblock user {user_id}: {e}")
        return False

def is_user_blocked(user_id: int) -> bool:
    """Check if user is blocked"""
    user = get_user(user_id)
    return bool(user and user.get('is_blocked', 0))

# Transaction Operations
def add_transaction(user_id: int, tx_type: str, amount: float, trx_id: str = None, 
                   status: str = 'completed', description: str = None, cursor=None) -> bool:
    """Add transaction record"""
    try:
        should_close = cursor is None
        if cursor is None:
            conn = get_connection()
            cursor = conn.cursor()
        
        cursor.execute('''
        INSERT INTO transactions 
        (user_id, tx_type, amount, trx_id, status, description, timestamp)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (user_id, tx_type, amount, trx_id, status, description, datetime.now().isoformat()))
        
        if should_close:
            conn.commit()
            conn.close()
            
        return True
        
    except Exception as e:
        logger.error(f"Failed to add transaction for user {user_id}: {e}")
        return False

def get_user_transactions(user_id: int, limit: int = 5) -> List[Dict[str, Any]]:
    """Get user's recent transactions"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
        SELECT * FROM transactions 
        WHERE user_id = ? 
        ORDER BY timestamp DESC 
        LIMIT ?
        ''', (user_id, limit))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
        
    except Exception as e:
        logger.error(f"Failed to get transactions for user {user_id}: {e}")
        return []

# APK Operations
def add_signed_apk(user_id: int, file_name: str, file_id: str, 
                  original_size: int = 0, signed_size: int = 0) -> bool:
    """Record signed APK information"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
        INSERT INTO signed_apks 
        (user_id, file_name, file_id, original_size, signed_size, sign_time)
        VALUES (?, ?, ?, ?, ?, ?)
        ''', (user_id, file_name, file_id, original_size, signed_size, datetime.now().isoformat()))
        
        conn.commit()
        conn.close()
        return True
        
    except Exception as e:
        logger.error(f"Failed to record signed APK for user {user_id}: {e}")
        return False

# Support Operations
def add_support_message(user_id: int, message_id: int, message_text: str) -> bool:
    """Add support message"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
        INSERT INTO support_messages 
        (user_id, message_id, message_text, created_at)
        VALUES (?, ?, ?, ?)
        ''', (user_id, message_id, message_text, datetime.now().isoformat()))
        
        conn.commit()
        conn.close()
        return True
        
    except Exception as e:
        logger.error(f"Failed to add support message: {e}")
        return False

# Admin Operations
def get_total_users() -> int:
    """Get total number of users"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT COUNT(*) as count FROM users')
        result = cursor.fetchone()
        conn.close()
        
        return result['count']
        
    except Exception as e:
        logger.error(f"Failed to get total users: {e}")
        return 0

def get_total_balance() -> float:
    """Get sum of all user balances"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT COALESCE(SUM(balance), 0) as total FROM users')
        result = cursor.fetchone()
        conn.close()
        
        return result['total']
        
    except Exception as e:
        logger.error(f"Failed to get total balance: {e}")
        return 0.0

def get_all_user_ids() -> List[int]:
    """Get all user IDs for broadcasting"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT user_id FROM users WHERE is_blocked = 0')
        rows = cursor.fetchall()
        conn.close()
        
        return [row['user_id'] for row in rows]
        
    except Exception as e:
        logger.error(f"Failed to get all user IDs: {e}")
        return []

def find_user_by_username(username: str) -> Optional[Dict[str, Any]]:
    """Find user by username"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
        row = cursor.fetchone()
        conn.close()
        
        return dict(row) if row else None
        
    except Exception as e:
        logger.error(f"Failed to find user by username {username}: {e}")
        return None

# Settings Operations
def get_setting(key: str, default: str = None) -> str:
    """Get setting value"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT value FROM settings WHERE key = ?', (key,))
        row = cursor.fetchone()
        conn.close()
        
        return row['value'] if row else default
        
    except Exception as e:
        logger.error(f"Failed to get setting {key}: {e}")
        return default

def set_setting(key: str, value: str) -> bool:
    """Set setting value"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
        INSERT OR REPLACE INTO settings (key, value, updated_at)
        VALUES (?, ?, ?)
        ''', (key, value, datetime.now().isoformat()))
        
        conn.commit()
        conn.close()
        return True
        
    except Exception as e:
        logger.error(f"Failed to set setting {key}: {e}")
        return False
