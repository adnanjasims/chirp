"""
load demo users/tweets from seed_data.json (that file is committed; twitter.db is not)
run from backend: python3 seed_dummy_data.py
demo password is in the json (usually demo123)
"""
import sqlite3
import os
import json
import hashlib

DB_FILE=os.path.join(os.path.dirname(__file__), 'twitter.db')
SEED_FILE=os.path.join(os.path.dirname(__file__), 'seed_data.json')
AVATAR='https://api.dicebear.com/7.x/avataaars/svg?seed='


def hash_password(pw):
    return hashlib.sha256(pw.encode()).hexdigest()


def main():
    with open(SEED_FILE, 'r', encoding='utf-8') as f:
        data=json.load(f)

    password=data.get('password') or 'demo123'
    pw_hash=hash_password(password)
    conn=sqlite3.connect(DB_FILE)
    c=conn.cursor()

    #ensure basic profile cols
    for col, typedef in [('bio', 'TEXT'), ('avatar_url', 'TEXT')]:
        try:
            c.execute(f'SELECT {col} FROM users LIMIT 1')
        except sqlite3.OperationalError:
            try:
                c.execute(f'ALTER TABLE users ADD COLUMN {col} {typedef}')
            except sqlite3.OperationalError:
                pass
    try:
        c.execute('SELECT user_id FROM posts LIMIT 1')
    except sqlite3.OperationalError:
        try:
            c.execute('ALTER TABLE posts ADD COLUMN user_id INTEGER REFERENCES users(id)')
        except sqlite3.OperationalError:
            pass

    id_by_name={}
    for u in data.get('users') or []:
        name=u['username']
        bio=u.get('bio') or ''
        avatar=AVATAR + (u.get('avatar_seed') or name)
        row=c.execute('SELECT id FROM users WHERE username = ?', (name,)).fetchone()
        if row:
            uid=row[0]
            c.execute('UPDATE users SET bio = ?, avatar_url = ? WHERE id = ?', (bio, avatar, uid))
        else:
            c.execute(
                'INSERT INTO users (username, password, bio, avatar_url) VALUES (?, ?, ?, ?)',
                (name, pw_hash, bio, avatar)
            )
            uid=c.lastrowid
        id_by_name[name]=uid

    #follows
    for pair in data.get('follows') or []:
        if len(pair) != 2:
            continue
        a, b=pair[0], pair[1]
        if a not in id_by_name or b not in id_by_name:
            continue
        try:
            c.execute(
                'INSERT OR IGNORE INTO followers (follower_id, followee_id) VALUES (?, ?)',
                (id_by_name[a], id_by_name[b])
            )
        except sqlite3.OperationalError:
            try:
                c.execute(
                    'INSERT INTO followers (follower_id, followee_id) VALUES (?, ?)',
                    (id_by_name[a], id_by_name[b])
                )
            except sqlite3.IntegrityError:
                pass

    #tweets (skip exact dupes by content+user)
    for t in data.get('tweets') or []:
        name=t.get('username')
        content=(t.get('content') or '').strip()
        if not name or not content or name not in id_by_name:
            continue
        uid=id_by_name[name]
        exists=c.execute(
            'SELECT 1 FROM posts WHERE user_id = ? AND content = ? LIMIT 1',
            (uid, content)
        ).fetchone()
        if exists:
            continue
        try:
            c.execute(
                "INSERT INTO posts (content, user_id, parent_id, created_at, status) VALUES (?, ?, NULL, datetime('now'), 'published')",
                (content, uid)
            )
            pid=c.lastrowid
        except sqlite3.OperationalError:
            c.execute('INSERT INTO posts (content, user_id) VALUES (?, ?)', (content, uid))
            pid=c.lastrowid
        #cheap hashtag/mention link if helpers available
        try:
            import helpers as H
            H.link_mentions_hashtags(conn, pid, content, uid)
        except Exception:
            pass

    conn.commit()
    conn.close()
    print(f"seeded from {os.path.basename(SEED_FILE)} ({len(data.get('users') or [])} users, {len(data.get('tweets') or [])} tweets)")
    print(f"demo password: {password}")


if __name__ == '__main__':
    main()
