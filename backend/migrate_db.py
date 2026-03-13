"""Add profile (bio, avatar_url) to users and user_id to posts. Safe to run on existing DB."""
import sqlite3
import os

DB_FILE = os.path.join(os.path.dirname(__file__), 'twitter.db')

def column_exists(cursor, table, col):
    cursor.execute(f"PRAGMA table_info({table})")
    return any(r[1] == col for r in cursor.fetchall())

def main():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    # Users: add bio, avatar_url
    if not column_exists(c, 'users', 'bio'):
        c.execute('ALTER TABLE users ADD COLUMN bio TEXT')
    if not column_exists(c, 'users', 'avatar_url'):
        c.execute('ALTER TABLE users ADD COLUMN avatar_url TEXT')
    # Posts: add user_id if missing
    if not column_exists(c, 'posts', 'user_id'):
        c.execute('ALTER TABLE posts ADD COLUMN user_id INTEGER REFERENCES users(id)')
    conn.commit()
    conn.close()
    print("Migration done.")

if __name__ == '__main__':
    main()
