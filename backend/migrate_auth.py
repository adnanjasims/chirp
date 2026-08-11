"""session tokens so you cant just spoof a username"""
import sqlite3
import os

DB_FILE=os.path.join(os.path.dirname(__file__), 'twitter.db')


def main():
    conn=sqlite3.connect(DB_FILE)
    conn.execute('''
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            token_hash TEXT UNIQUE NOT NULL,
            user_id INTEGER NOT NULL,
            created_at TEXT DEFAULT (datetime('now')),
            expires_at TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_sessions_token ON sessions(token_hash)')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id)')
    conn.commit()
    conn.close()
    print('sessions table ready')


if __name__ == '__main__':
    main()
