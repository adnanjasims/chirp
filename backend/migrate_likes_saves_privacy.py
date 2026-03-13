"""Add likes, saved_tweets, and privacy columns. Safe to run on existing DB."""
import sqlite3
import os

DB_FILE = os.path.join(os.path.dirname(__file__), 'twitter.db')

def column_exists(cursor, table, col):
    cursor.execute(f"PRAGMA table_info({table})")
    return any(r[1] == col for r in cursor.fetchall())

def table_exists(cursor, name):
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (name,))
    return cursor.fetchone() is not None

def main():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    # Likes: user_id, post_id
    if not table_exists(c, 'likes'):
        c.execute('''
            CREATE TABLE likes (
                user_id INTEGER NOT NULL,
                post_id INTEGER NOT NULL,
                PRIMARY KEY (user_id, post_id),
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (post_id) REFERENCES posts(id)
            )
        ''')

    # Saved tweets (bookmarks)
    if not table_exists(c, 'saved_tweets'):
        c.execute('''
            CREATE TABLE saved_tweets (
                user_id INTEGER NOT NULL,
                post_id INTEGER NOT NULL,
                PRIMARY KEY (user_id, post_id),
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (post_id) REFERENCES posts(id)
            )
        ''')

    # Privacy columns on users (default: public)
    if not column_exists(c, 'users', 'who_can_see_tweets'):
        c.execute("ALTER TABLE users ADD COLUMN who_can_see_tweets TEXT DEFAULT 'public'")
    if not column_exists(c, 'users', 'who_can_see_followers'):
        c.execute("ALTER TABLE users ADD COLUMN who_can_see_followers TEXT DEFAULT 'public'")
    if not column_exists(c, 'users', 'who_can_see_following'):
        c.execute("ALTER TABLE users ADD COLUMN who_can_see_following TEXT DEFAULT 'public'")
    if not column_exists(c, 'users', 'show_likes_on_profile'):
        c.execute('ALTER TABLE users ADD COLUMN show_likes_on_profile INTEGER DEFAULT 1')

    # Unique constraint on followers (avoid duplicates)
    try:
        c.execute('CREATE UNIQUE INDEX IF NOT EXISTS idx_followers_pair ON followers(follower_id, followee_id)')
    except Exception:
        pass

    conn.commit()
    conn.close()
    print("Migration (likes, saved_tweets, privacy) done.")

if __name__ == '__main__':
    main()
