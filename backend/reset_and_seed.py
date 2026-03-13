"""
Reset the database to only the seeded dummy data (no old posts or users).
Run from backend dir: python3 reset_and_seed.py
"""
import sqlite3
import os

DB_FILE = os.path.join(os.path.dirname(__file__), 'twitter.db')

def main():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('DELETE FROM followers')
    c.execute('DELETE FROM posts')
    c.execute('DELETE FROM users')
    conn.commit()
    conn.close()
    print("Cleared posts, users, and followers.")

    # Re-run seed
    import seed_dummy_data
    seed_dummy_data.main()
    print("Done. DB now has only seeded users and tweets.")

if __name__ == '__main__':
    main()
