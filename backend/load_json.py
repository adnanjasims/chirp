"""
Legacy loader: imports tweets from a JSON-lines file (one JSON object per line
with keys: user.username, content). The JSON files (10.json, 100.json) were
removed; use seed_dummy_data.py for dummy data instead.
To use this script, pass a path: python3 load_json.py path/to/file.json
"""
import sqlite3
import json
import os
import sys
import hashlib

DB_FILE = os.path.join(os.path.dirname(__file__), 'twitter.db')

def load_file(path):
    with open(path, 'r', encoding='utf-8') as f:
        lines = f.read().splitlines()
    conn = sqlite3.connect(DB_FILE)
    for line in lines:
        try:
            tweet = json.loads(line)
            username = tweet.get('user', {}).get('username', '').strip()
            content = (tweet.get('content') or '').strip()
            if not username or not content:
                continue
            user = conn.execute("SELECT id FROM users WHERE username = ?", (username,)).fetchone()
            if not user:
                hashed = hashlib.sha256("twitter_scraped".encode()).hexdigest()
                conn.execute("INSERT OR IGNORE INTO users (username, password) VALUES (?, ?)", (username, hashed))
                conn.commit()
                user = conn.execute("SELECT id FROM users WHERE username = ?", (username,)).fetchone()
            if user:
                try:
                    conn.execute("INSERT INTO posts (content, user_id) VALUES (?, ?)", (content, user[0]))
                except sqlite3.OperationalError:
                    conn.execute("INSERT INTO posts (content) VALUES (?)", (content,))
        except Exception as e:
            print(f"Skip line: {e}")
    conn.commit()
    conn.close()
    print(f"Loaded {path}")

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python3 load_json.py <path/to/file.json>")
        print("For dummy data, use: python3 seed_dummy_data.py")
        sys.exit(1)
    load_file(sys.argv[1])
