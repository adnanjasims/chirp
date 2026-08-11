"""auth helpers: issue / check / revoke bearer tokens"""
import hashlib
import secrets
import sqlite3


def hash_token(raw):
    return hashlib.sha256(raw.encode()).hexdigest()


def create_session(conn, user_id, days=30):
    raw=secrets.token_urlsafe(32)
    th=hash_token(raw)
    conn.execute(
        f'''INSERT INTO sessions (token_hash, user_id, created_at, expires_at)
            VALUES (?, ?, datetime('now'), datetime('now', '+{int(days)} days'))''',
        (th, user_id)
    )
    return raw


def revoke_session(conn, raw_token):
    if not raw_token:
        return
    conn.execute('DELETE FROM sessions WHERE token_hash = ?', (hash_token(raw_token),))


def revoke_all_sessions(conn, user_id):
    conn.execute('DELETE FROM sessions WHERE user_id = ?', (user_id,))


def cleanup_expired(conn):
    try:
        conn.execute("DELETE FROM sessions WHERE expires_at <= datetime('now')")
    except sqlite3.OperationalError:
        pass


def user_from_token(conn, raw_token):
    """return user row or None"""
    if not raw_token:
        return None
    cleanup_expired(conn)
    try:
        row=conn.execute(
            '''SELECT u.id, u.username, u.bio, u.avatar_url
               FROM sessions s
               JOIN users u ON u.id = s.user_id
               WHERE s.token_hash = ?
                 AND s.expires_at > datetime('now')''',
            (hash_token(raw_token),)
        ).fetchone()
    except sqlite3.OperationalError:
        return None
    return row


def bearer_from_request(request):
    auth=request.headers.get('Authorization') or ''
    if auth.lower().startswith('bearer '):
        return auth[7:].strip() or None
    #sse cant set headers, so allow ?token=
    q=(request.args.get('token') or '').strip()
    if q:
        return q
    return (request.headers.get('X-Auth-Token') or '').strip() or None
