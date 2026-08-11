"""helpers for mentions, feed ranking, notifs, sse, etc"""
import re
import sqlite3
import time
import json
import queue
import threading
from collections import defaultdict
from datetime import datetime, timedelta

MENTION_RE=re.compile(r'@([A-Za-z0-9_]+)')
HASHTAG_RE=re.compile(r'#([A-Za-z0-9_]+)')

#sse fans out to whoever is listening
_sse_subscribers=defaultdict(list)
_sse_lock=threading.Lock()

#who is typing on a post right now
_typing=defaultdict(dict)
_typing_lock=threading.Lock()


def can_see(conn, profile_user_id, viewer_id, setting):
    if viewer_id == profile_user_id:
        return True
    if setting == 'public':
        return True
    if setting == 'private':
        return False
    if setting == 'followers':
        row = conn.execute(
            'SELECT 1 FROM followers WHERE follower_id = ? AND followee_id = ?',
            (viewer_id, profile_user_id)
        ).fetchone()
        return row is not None
    return True


def get_user_id(conn, username):
    if not username:
        return None
    u = conn.execute('SELECT id FROM users WHERE username = ?', (username,)).fetchone()
    return u[0] if u else None


def get_blocked_ids(conn, viewer_id):
    #either direction so blocked people vanish from feeds
    if not viewer_id:
        return set()
    rows = conn.execute(
        '''SELECT blocked_id FROM blocks WHERE blocker_id = ?
           UNION SELECT blocker_id FROM blocks WHERE blocked_id = ?''',
        (viewer_id, viewer_id)
    ).fetchall()
    return {r[0] for r in rows}


def get_muted_ids(conn, viewer_id):
    if not viewer_id:
        return set()
    rows = conn.execute('SELECT muted_id FROM mutes WHERE muter_id = ?', (viewer_id,)).fetchall()
    return {r[0] for r in rows}


def get_muted_words(conn, viewer_id):
    if not viewer_id:
        return []
    try:
        rows = conn.execute('SELECT word FROM muted_words WHERE user_id = ?', (viewer_id,)).fetchall()
        return [r[0].lower() for r in rows]
    except sqlite3.OperationalError:
        return []


def should_filter_post(conn, post_row, viewer_id, blocked=None, muted=None, muted_words=None):
    #hide stuff from muted/blocked authors or muted words
    if blocked is None:
        blocked = get_blocked_ids(conn, viewer_id)
    if muted is None:
        muted = get_muted_ids(conn, viewer_id)
    if muted_words is None:
        muted_words = get_muted_words(conn, viewer_id)
    uid = post_row['user_id'] if isinstance(post_row, sqlite3.Row) else post_row.get('user_id')
    if uid and uid in blocked:
        return True
    if uid and uid in muted:
        return True
    content = (post_row['content'] if isinstance(post_row, sqlite3.Row) else post_row.get('content') or '').lower()
    for w in muted_words:
        if w and w in content:
            return True
    return False


def parse_mentions(content):
    return list(dict.fromkeys(m.lower() for m in MENTION_RE.findall(content or '')))


def parse_hashtags(content):
    return list(dict.fromkeys(t.lower() for t in HASHTAG_RE.findall(content or '')))


def link_mentions_hashtags(conn, post_id, content, author_id=None):
    #pull @users and #tags out of the text
    mentioned_ids = []
    for name in parse_mentions(content):
        u = conn.execute('SELECT id FROM users WHERE lower(username) = ?', (name,)).fetchone()
        if u and u[0] != author_id:
            try:
                conn.execute('INSERT OR IGNORE INTO mentions (post_id, user_id) VALUES (?, ?)', (post_id, u[0]))
                mentioned_ids.append(u[0])
            except sqlite3.OperationalError:
                pass
    tags = parse_hashtags(content)
    for tag in tags:
        try:
            conn.execute('INSERT OR IGNORE INTO hashtags (tag) VALUES (?)', (tag,))
            hid = conn.execute('SELECT id FROM hashtags WHERE tag = ?', (tag,)).fetchone()[0]
            conn.execute('INSERT OR IGNORE INTO post_hashtags (post_id, hashtag_id) VALUES (?, ?)', (post_id, hid))
        except sqlite3.OperationalError:
            pass
    return mentioned_ids, tags


def create_notification(conn, user_id, actor_id, ntype, post_id=None, room_id=None, message=None):
    if not user_id or user_id == actor_id:
        return
    try:
        conn.execute(
            '''INSERT INTO notifications (user_id, actor_id, type, post_id, room_id, message, read, created_at)
               VALUES (?, ?, ?, ?, ?, ?, 0, datetime('now'))''',
            (user_id, actor_id, ntype, post_id, room_id, message)
        )
    except sqlite3.OperationalError:
        return
        #figure out who did it for the sse payload
    actor = conn.execute('SELECT username FROM users WHERE id = ?', (actor_id,)).fetchone() if actor_id else None
    recipient = conn.execute('SELECT username FROM users WHERE id = ?', (user_id,)).fetchone()
    if recipient:
        broadcast(recipient[0], {
            'event': 'notification',
            'type': ntype,
            'actor': actor[0] if actor else None,
            'post_id': post_id,
            'room_id': room_id,
            'message': message,
        })


def publish_due_posts(conn):
    try:
        conn.execute(
            """UPDATE posts SET status = 'published', created_at = datetime('now')
               WHERE status = 'scheduled' AND scheduled_at IS NOT NULL
               AND scheduled_at <= datetime('now')"""
        )
        conn.commit()
    except sqlite3.OperationalError:
        pass


def build_tweet_list(conn, rows, viewer_id):
    out = []
    blocked = get_blocked_ids(conn, viewer_id)
    muted = get_muted_ids(conn, viewer_id)
    muted_words = get_muted_words(conn, viewer_id)

    for row in rows:
        if should_filter_post(conn, row, viewer_id, blocked, muted, muted_words):
            continue
        r = dict(row)
        #drafts/scheduled stay private to owner
        status = r.get('status') or 'published'
        if status != 'published':
            if not viewer_id or r.get('user_id') != viewer_id:
                continue
        uid = r.get('user_id')
        if uid:
            u = conn.execute('SELECT username, bio, avatar_url FROM users WHERE id = ?', (uid,)).fetchone()
            if u:
                r['username'] = u[0]
                r['bio'] = u[1] or ''
                r['avatar_url'] = u[2] or ''
        else:
            r.setdefault('username', '')
            r.setdefault('bio', '')
            r.setdefault('avatar_url', '')

        try:
            like_row = conn.execute('SELECT COUNT(*) FROM likes WHERE post_id = ?', (r['id'],)).fetchone()
            r['like_count'] = like_row[0] if like_row else 0
        except sqlite3.OperationalError:
            r['like_count'] = 0

        r['liked_by_me'] = r['saved_by_me'] = False
        if viewer_id:
            try:
                if conn.execute('SELECT 1 FROM likes WHERE user_id = ? AND post_id = ?', (viewer_id, r['id'])).fetchone():
                    r['liked_by_me'] = True
                if conn.execute('SELECT 1 FROM saved_tweets WHERE user_id = ? AND post_id = ?', (viewer_id, r['id'])).fetchone():
                    r['saved_by_me'] = True
            except sqlite3.OperationalError:
                pass

        r.setdefault('created_at', None)
        r.setdefault('parent_id', None)
        r.setdefault('media_url', None)
        r.setdefault('repost_of', None)
        r.setdefault('quote_content', None)
        r.setdefault('status', 'published')
        r.setdefault('scheduled_at', None)
        r.setdefault('impression_count', 0)

        try:
            cc = conn.execute('SELECT COUNT(*) FROM posts WHERE parent_id = ?', (r['id'],)).fetchone()
            r['comment_count'] = cc[0] if cc else 0
        except sqlite3.OperationalError:
            r['comment_count'] = 0

        #how many times this got bounced
        try:
            rc = conn.execute(
                "SELECT COUNT(*) FROM posts WHERE repost_of = ? AND (status = 'published' OR status IS NULL)",
                (r['id'],)
            ).fetchone()
            r['repost_count'] = rc[0] if rc else 0
        except sqlite3.OperationalError:
            r['repost_count'] = 0

        #stick the original under a quote/repost
        if r.get('repost_of'):
            try:
                orig = conn.execute(
                    '''SELECT id, content, user_id, created_at, media_url, parent_id
                       FROM posts WHERE id = ?''',
                    (r['repost_of'],)
                ).fetchone()
                if orig:
                    embedded = build_tweet_list(conn, [orig], viewer_id)
                    r['original'] = embedded[0] if embedded else None
                else:
                    r['original'] = None
            except sqlite3.OperationalError:
                r['original'] = None

        #tags on this post if we have the table
        try:
            tags = conn.execute(
                '''SELECT h.tag FROM hashtags h
                   JOIN post_hashtags ph ON ph.hashtag_id = h.id
                   WHERE ph.post_id = ?''',
                (r['id'],)
            ).fetchall()
            r['hashtags'] = [t[0] for t in tags]
        except sqlite3.OperationalError:
            r['hashtags'] = []

        out.append(r)
    return out


def bump_impressions(conn, post_ids):
    if not post_ids:
        return
    try:
        for pid in post_ids:
            conn.execute(
                'UPDATE posts SET impression_count = COALESCE(impression_count, 0) + 1 WHERE id = ?',
                (pid,)
            )
        conn.commit()
    except sqlite3.OperationalError:
        pass


def score_post(conn, row, viewer_id, followee_ids, viewer_tag_ids):
    #rough for-you score, nothing fancy
    now = datetime.utcnow()
    created = row['created_at'] if isinstance(row, sqlite3.Row) else row.get('created_at')
    age_hours = 72.0
    if created:
        try:
            #sqlite datetime is usually utc-ish text
            dt = datetime.strptime(str(created)[:19], '%Y-%m-%d %H:%M:%S')
            age_hours = max(0.1, (now - dt).total_seconds() / 3600.0)
        except (ValueError, TypeError):
            age_hours = 24.0

    pid = row['id'] if isinstance(row, sqlite3.Row) else row['id']
    try:
        likes = conn.execute('SELECT COUNT(*) FROM likes WHERE post_id = ?', (pid,)).fetchone()[0]
    except sqlite3.OperationalError:
        likes = 0
    try:
        comments = conn.execute('SELECT COUNT(*) FROM posts WHERE parent_id = ?', (pid,)).fetchone()[0]
    except sqlite3.OperationalError:
        comments = 0

    uid = row['user_id'] if isinstance(row, sqlite3.Row) else row.get('user_id')
    follow_boost = 8.0 if uid in followee_ids else 0.0

    tag_overlap = 0.0
    if viewer_tag_ids:
        try:
            rows = conn.execute(
                'SELECT hashtag_id FROM post_hashtags WHERE post_id = ?', (pid,)
            ).fetchall()
            post_tags = {r[0] for r in rows}
            tag_overlap = 3.0 * len(post_tags & viewer_tag_ids)
        except sqlite3.OperationalError:
            pass

    recency = 20.0 / (1.0 + age_hours / 6.0)
    return recency + likes * 2.0 + comments * 1.5 + follow_boost + tag_overlap


def rank_for_you(conn, rows, viewer_id):
    followee_ids = set()
    viewer_tag_ids = set()
    if viewer_id:
        followee_ids = {
            r[0] for r in conn.execute(
                'SELECT followee_id FROM followers WHERE follower_id = ?', (viewer_id,)
            ).fetchall()
        }
        #tags they liked recently get a little boost
        try:
            tag_rows = conn.execute(
                '''SELECT DISTINCT ph.hashtag_id FROM post_hashtags ph
                   JOIN likes l ON l.post_id = ph.post_id
                   WHERE l.user_id = ?''',
                (viewer_id,)
            ).fetchall()
            viewer_tag_ids = {r[0] for r in tag_rows}
        except sqlite3.OperationalError:
            pass

    scored = [(score_post(conn, row, viewer_id, followee_ids, viewer_tag_ids), row) for row in rows]
    scored.sort(key=lambda x: (-x[0], -(x[1]['id'] if isinstance(x[1], sqlite3.Row) else x[1].get('id', 0))))
    return [row for _, row in scored]


def ensure_default_collection(conn, user_id):
    row = conn.execute(
        'SELECT id FROM bookmark_collections WHERE user_id = ? AND name = ?',
        (user_id, 'Saved')
    ).fetchone()
    if row:
        return row[0]
    cur = conn.execute(
        "INSERT INTO bookmark_collections (user_id, name, created_at) VALUES (?, 'Saved', datetime('now'))",
        (user_id,)
    )
    cid = cur.lastrowid
    #move old saves into the default bucket
    try:
        saves = conn.execute('SELECT post_id FROM saved_tweets WHERE user_id = ?', (user_id,)).fetchall()
        for s in saves:
            conn.execute(
                'INSERT OR IGNORE INTO collection_items (collection_id, post_id) VALUES (?, ?)',
                (cid, s[0])
            )
    except sqlite3.OperationalError:
        pass
    conn.commit()
    return cid


#sse hub (in memory, fine for local)

def subscribe(username):
    q = queue.Queue(maxsize=64)
    with _sse_lock:
        _sse_subscribers[username].append(q)
    return q


def unsubscribe(username, q):
    with _sse_lock:
        subs = _sse_subscribers.get(username, [])
        if q in subs:
            subs.remove(q)
        if not subs and username in _sse_subscribers:
            del _sse_subscribers[username]


def broadcast(username, payload):
    data = json.dumps(payload)
    with _sse_lock:
        subs = list(_sse_subscribers.get(username, []))
        #feed events go to everyone listening
        if payload.get('event') == 'feed':
            all_subs = []
            for qs in _sse_subscribers.values():
                all_subs.extend(qs)
            subs = all_subs
    for q in subs:
        try:
            q.put_nowait(data)
        except queue.Full:
            pass


def broadcast_to_all(payload):
    data = json.dumps(payload)
    with _sse_lock:
        all_qs = []
        for qs in _sse_subscribers.values():
            all_qs.extend(qs)
    for q in all_qs:
        try:
            q.put_nowait(data)
        except queue.Full:
            pass


def set_typing(post_id, username):
    with _typing_lock:
        _typing[post_id][username] = time.time()
    broadcast_to_all({
        'event': 'typing',
        'post_id': post_id,
        'username': username,
    })


def get_typing(post_id, exclude=None, ttl=5.0):
    now = time.time()
    with _typing_lock:
        users = _typing.get(post_id, {})
        active = [u for u, ts in users.items() if now - ts < ttl and u != exclude]
    return active


def expire_rooms(conn):
    try:
        conn.execute(
            """UPDATE rooms SET is_live = 0
               WHERE is_live = 1 AND expires_at IS NOT NULL AND expires_at <= datetime('now')"""
        )
        conn.commit()
    except sqlite3.OperationalError:
        pass
