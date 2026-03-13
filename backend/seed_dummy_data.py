"""
Seed the database with dummy users (bio, avatar) and human-sounding tweets.
Run from backend dir: python3 migrate_db.py  then  python3 seed_dummy_data.py
Safe to run multiple times (adds more data). Dummy login: any username from
USERS list below, password: demo123
"""
import sqlite3
import os
import hashlib

DB_FILE = os.path.join(os.path.dirname(__file__), 'twitter.db')

# Placeholder avatar (neutral silhouette); in production you'd use real URLs or uploads
DEFAULT_AVATAR = 'https://api.dicebear.com/7.x/avataaars/svg?seed='

USERS = [
    ('alex_r', 'Coffee addict. Sometimes I tweet.', DEFAULT_AVATAR + 'alex'),
    ('jordan_lee', 'Designer. Dog dad. Bad at mornings.', DEFAULT_AVATAR + 'jordan'),
    ('sam_writes', 'Writing a book maybe. Mostly procrastinating.', DEFAULT_AVATAR + 'sam'),
    ('morgan_', 'just here for the memes tbh', DEFAULT_AVATAR + 'morgan'),
    ('casey', 'engineer. they/them. hot takes are cold takes by now', DEFAULT_AVATAR + 'casey'),
    ('riley', 'music and cats. that’s the whole personality', DEFAULT_AVATAR + 'riley'),
    ('quinn', 'idk what to put here', DEFAULT_AVATAR + 'quinn'),
]

TWEETS = [
    ("wait did anyone else's power just flicker or is it just me", 'alex_r'),
    ("need coffee. like. now. it's not even 9am and I've given up", 'alex_r'),
    ("that meeting could have been a slack message", 'jordan_lee'),
    ("my dog looked at me and sighed. I feel judged", 'jordan_lee'),
    ("finally figured out that bug. only took 4 hours and 3 coffees", 'sam_writes'),
    ("writing is hard. why do words", 'sam_writes'),
    ("ok but why is the wifi always slow when you actually need it", 'morgan_'),
    ("saw a really good meme earlier and now I cant find it. pain", 'morgan_'),
    ("hot take: most hot takes are lukewarm at best", 'casey'),
    ("spent 20 mins debugging and it was a typo. never speaking of this again", 'casey'),
    ("this song has been stuck in my head for 3 days send help", 'riley'),
    ("cat just knocked my water over. again. I'm not even mad anymore", 'riley'),
    ("forgot what I was gonna say", 'quinn'),
    ("why is there so much to do. when did I sign up for this", 'quinn'),
    ("the amount of times I've refreshed this app today... not great", 'alex_r'),
    ("someone tell me its gonna be ok (it's monday)", 'jordan_lee'),
    ("i have so many tabs open my browser is judging me", 'sam_writes'),
    ("no thoughts. head empty. just vibes", 'morgan_'),
    ("tried to be productive. failed. tomorrow maybe", 'casey'),
    ("my plants are still alive so thats a win", 'riley'),
    ("sometimes you just need to step away from the screen ya know", 'quinn'),
    ("cant believe its already wednesday where did the week go", 'alex_r'),
    ("that feeling when you fix something and have no idea why it worked", 'jordan_lee'),
    ("re-reading my old messages and cringing. normal tuesday", 'sam_writes'),
    ("why do we say 'reply to this tweet' when we could say 'reply to this'... anyway", 'morgan_'),
    ("the bar for 'doing fine' is so low and I'm still tripping over it", 'casey'),
    ("listening to the same 5 songs on repeat. no I will not elaborate", 'riley'),
    ("forgot to reply to someone 2 days ago. its too late now right", 'quinn'),
    ("anyone else just stare at the ceiling sometimes. just me ok", 'alex_r'),
    ("my sleep schedule is a suggestion at this point", 'jordan_lee'),
]

def hash_password(pw):
    return hashlib.sha256(pw.encode()).hexdigest()

def main():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    # Ensure columns exist (in case migrate wasn't run)
    try:
        c.execute("SELECT bio FROM users LIMIT 1")
    except sqlite3.OperationalError:
        try:
            c.execute('ALTER TABLE users ADD COLUMN bio TEXT')
            c.execute('ALTER TABLE users ADD COLUMN avatar_url TEXT')
        except sqlite3.OperationalError:
            pass
    try:
        c.execute("SELECT user_id FROM posts LIMIT 1")
    except sqlite3.OperationalError:
        try:
            c.execute('ALTER TABLE posts ADD COLUMN user_id INTEGER REFERENCES users(id)')
        except sqlite3.OperationalError:
            pass

    username_to_id = {}
    for username, bio, avatar_url in USERS:
        existing = c.execute('SELECT id, bio FROM users WHERE username = ?', (username,)).fetchone()
        if existing:
            uid = existing[0]
            if len(existing) > 1 and (existing[1] is None or existing[1] == ''):
                c.execute('UPDATE users SET bio = ?, avatar_url = ? WHERE id = ?', (bio, avatar_url, uid))
        else:
            c.execute(
                'INSERT INTO users (username, password, bio, avatar_url) VALUES (?, ?, ?, ?)',
                (username, hash_password('demo123'), bio, avatar_url)
            )
            uid = c.execute('SELECT last_insert_rowid()').fetchone()[0]
        username_to_id[username] = uid

    for content, username in TWEETS:
        uid = username_to_id.get(username)
        if uid is None:
            continue
        try:
            c.execute('INSERT INTO posts (content, user_id) VALUES (?, ?)', (content, uid))
        except sqlite3.OperationalError:
            c.execute('INSERT INTO posts (content) VALUES (?)', (content,))

    conn.commit()
    conn.close()
    print("Dummy users and tweets seeded. Log in as any user above with password: demo123")

if __name__ == '__main__':
    main()
