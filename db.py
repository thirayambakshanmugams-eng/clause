"""
Database management module for ClauseGuard multi-user system using SQLite.
"""

import os
import sqlite3
import json
from config import Config

DB_PATH = os.path.join(Config.BASE_DIR, 'clauseguard.db')


def get_db():
    """Get a database connection."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Initialize database tables for users and analysis history."""
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Create Users table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create History table (per user)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS history (
                id TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                filename TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                total_clauses INTEGER NOT NULL,
                summary_json TEXT NOT NULL,
                document_info_json TEXT NOT NULL,
                analysis_data_json TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
            )
        ''')
        
        conn.commit()


def create_user(username, email, password_hash):
    """Create a new user. Returns (success, user_dict_or_error_msg)."""
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)',
                (username.lower().strip(), email.lower().strip(), password_hash)
            )
            user_id = cursor.lastrowid
            conn.commit()
            return True, {'id': user_id, 'username': username, 'email': email}
    except sqlite3.IntegrityError as e:
        err_msg = str(e).lower()
        if 'username' in err_msg:
            return False, 'Username is already taken.'
        elif 'email' in err_msg:
            return False, 'Email address is already registered.'
        return False, 'Username or Email already exists.'


def get_user_by_login(identifier):
    """Get a user by username or email."""
    identifier = identifier.lower().strip()
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            'SELECT * FROM users WHERE username = ? OR email = ?',
            (identifier, identifier)
        )
        row = cursor.fetchone()
        if row:
            return dict(row)
        return None


def add_history_entry(user_id, item_id, filename, timestamp, total_clauses, summary, doc_info, full_analysis):
    """Save an analysis history entry for a user."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO history 
            (id, user_id, filename, timestamp, total_clauses, summary_json, document_info_json, analysis_data_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            item_id,
            user_id,
            filename,
            timestamp,
            total_clauses,
            json.dumps(summary),
            json.dumps(doc_info),
            json.dumps(full_analysis)
        ))
        conn.commit()


def get_user_history(user_id, limit=50):
    """Fetch history entries for a specific user."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, filename, timestamp, total_clauses, summary_json, document_info_json
            FROM history
            WHERE user_id = ?
            ORDER BY timestamp DESC
            LIMIT ?
        ''', (user_id, limit))
        rows = cursor.fetchall()
        
        results = []
        for r in rows:
            results.append({
                'id': r['id'],
                'filename': r['filename'],
                'timestamp': r['timestamp'],
                'total_clauses': r['total_clauses'],
                'summary': json.loads(r['summary_json']),
                'document_info': json.loads(r['document_info_json']),
            })
        return results


def delete_user_history_item(user_id, item_id):
    """Delete a single history entry for a user."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('DELETE FROM history WHERE id = ? AND user_id = ?', (item_id, user_id))
        conn.commit()


def clear_user_history(user_id):
    """Clear all history for a specific user."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('DELETE FROM history WHERE user_id = ?', (user_id,))
        conn.commit()
