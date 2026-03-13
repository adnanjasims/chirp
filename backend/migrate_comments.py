"""
Migration: add created_at and parent_id columns to posts table.
parent_id allows tweets to be replies to other tweets (comments).
Run once:  python3 migrate_comments.py
"""
import sqlite3, os

DB = os.path.join(os.path.dirname(__file__), 'twitter.db')

def migrate():
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    cols = [row[1] for row in c.execute("PRAGMA table_info(posts)").fetchall()]

    if 'created_at' not in cols:
        c.execute("ALTER TABLE posts ADD COLUMN created_at TEXT")
        c.execute("UPDATE posts SET created_at = datetime('now') WHERE created_at IS NULL")
        print("Added created_at to posts.")
    else:
        print("created_at already exists.")

    if 'parent_id' not in cols:
        c.execute("ALTER TABLE posts ADD COLUMN parent_id INTEGER REFERENCES posts(id)")
        print("Added parent_id to posts.")
    else:
        print("parent_id already exists.")

    conn.commit()
    conn.close()
    print("Done.")

if __name__ == '__main__':
    migrate()
