"""adds the newer product feature columns/tables. safe to re-run."""
import sqlite3
import os

DB_FILE=os.path.join(os.path.dirname(__file__), 'twitter.db')


def column_exists(conn, table, column):
    cols=[r[1] for r in conn.execute(f'PRAGMA table_info({table})').fetchall()]
    return column in cols


def add_column(conn, table, column, typedef):
    if not column_exists(conn, table, column):
        conn.execute(f'ALTER TABLE {table} ADD COLUMN {column} {typedef}')
        print(f'  + {table}.{column}')


def main():
    conn=sqlite3.connect(DB_FILE)
    print('Migrating features schema...')

    #posts got a bunch of new fields
    add_column(conn, 'posts', 'media_url', 'TEXT')
    add_column(conn, 'posts', 'repost_of', 'INTEGER')
    add_column(conn, 'posts', 'quote_content', 'TEXT')
    add_column(conn, 'posts', 'status', "TEXT DEFAULT 'published'")
    add_column(conn, 'posts', 'scheduled_at', 'TEXT')
    add_column(conn, 'posts', 'impression_count', 'INTEGER DEFAULT 0')

    #old rows should look published
    try:
        conn.execute("UPDATE posts SET status = 'published' WHERE status IS NULL")
    except sqlite3.OperationalError:
        pass

    conn.execute('''
        CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            actor_id INTEGER,
            type TEXT NOT NULL,
            post_id INTEGER,
            room_id INTEGER,
            message TEXT,
            read INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (actor_id) REFERENCES users(id)
        )
    ''')

    conn.execute('''
        CREATE TABLE IF NOT EXISTS hashtags (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tag TEXT UNIQUE NOT NULL
        )
    ''')

    conn.execute('''
        CREATE TABLE IF NOT EXISTS post_hashtags (
            post_id INTEGER NOT NULL,
            hashtag_id INTEGER NOT NULL,
            PRIMARY KEY (post_id, hashtag_id),
            FOREIGN KEY (post_id) REFERENCES posts(id),
            FOREIGN KEY (hashtag_id) REFERENCES hashtags(id)
        )
    ''')

    conn.execute('''
        CREATE TABLE IF NOT EXISTS mentions (
            post_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            PRIMARY KEY (post_id, user_id),
            FOREIGN KEY (post_id) REFERENCES posts(id),
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')

    conn.execute('''
        CREATE TABLE IF NOT EXISTS blocks (
            blocker_id INTEGER NOT NULL,
            blocked_id INTEGER NOT NULL,
            PRIMARY KEY (blocker_id, blocked_id),
            FOREIGN KEY (blocker_id) REFERENCES users(id),
            FOREIGN KEY (blocked_id) REFERENCES users(id)
        )
    ''')

    conn.execute('''
        CREATE TABLE IF NOT EXISTS mutes (
            muter_id INTEGER NOT NULL,
            muted_id INTEGER NOT NULL,
            PRIMARY KEY (muter_id, muted_id),
            FOREIGN KEY (muter_id) REFERENCES users(id),
            FOREIGN KEY (muted_id) REFERENCES users(id)
        )
    ''')

    conn.execute('''
        CREATE TABLE IF NOT EXISTS muted_words (
            user_id INTEGER NOT NULL,
            word TEXT NOT NULL,
            PRIMARY KEY (user_id, word),
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')

    conn.execute('''
        CREATE TABLE IF NOT EXISTS reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            reporter_id INTEGER NOT NULL,
            post_id INTEGER NOT NULL,
            reason TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (reporter_id) REFERENCES users(id),
            FOREIGN KEY (post_id) REFERENCES posts(id)
        )
    ''')

    conn.execute('''
        CREATE TABLE IF NOT EXISTS bookmark_collections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')

    conn.execute('''
        CREATE TABLE IF NOT EXISTS collection_items (
            collection_id INTEGER NOT NULL,
            post_id INTEGER NOT NULL,
            PRIMARY KEY (collection_id, post_id),
            FOREIGN KEY (collection_id) REFERENCES bookmark_collections(id),
            FOREIGN KEY (post_id) REFERENCES posts(id)
        )
    ''')

    conn.execute('''
        CREATE TABLE IF NOT EXISTS rooms (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            topic TEXT,
            host_id INTEGER NOT NULL,
            is_live INTEGER DEFAULT 1,
            created_at TEXT DEFAULT (datetime('now')),
            expires_at TEXT,
            FOREIGN KEY (host_id) REFERENCES users(id)
        )
    ''')

    conn.execute('''
        CREATE TABLE IF NOT EXISTS room_members (
            room_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            last_seen_at TEXT DEFAULT (datetime('now')),
            PRIMARY KEY (room_id, user_id),
            FOREIGN KEY (room_id) REFERENCES rooms(id),
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')

    conn.execute('''
        CREATE TABLE IF NOT EXISTS room_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            room_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            content TEXT NOT NULL,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (room_id) REFERENCES rooms(id),
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')

    conn.commit()
    conn.close()
    print('Features migration complete.')


if __name__ == '__main__':
    main()
