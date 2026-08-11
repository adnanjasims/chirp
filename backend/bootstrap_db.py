#one-shot schema + optional seed for fresh deploys
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def run(script):
    print(f'running {script}...')
    subprocess.check_call([sys.executable, os.path.join(HERE, script)], cwd=HERE)


def main():
    steps = [
        'init_db.py',
        'migrate_db.py',
        'migrate_likes_saves_privacy.py',
        'migrate_comments.py',
        'migrate_features.py',
        'migrate_auth.py',
    ]
    for s in steps:
        path = os.path.join(HERE, s)
        if os.path.isfile(path):
            run(s)

    #seed demo data only when empty / first boot
    if os.environ.get('SEED_ON_BOOT', '1') == '1':
        db = os.environ.get('DB_FILE') or os.path.join(HERE, 'twitter.db')
        need_seed = True
        if os.path.isfile(db):
            import sqlite3
            conn = sqlite3.connect(db)
            try:
                n = conn.execute('SELECT COUNT(*) FROM users').fetchone()[0]
                need_seed = n == 0
            except sqlite3.Error:
                need_seed = True
            conn.close()
        if need_seed:
            run('seed_dummy_data.py')
        else:
            print('users already present, skipping seed')


if __name__ == '__main__':
    main()
