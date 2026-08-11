from flask import Flask, request, jsonify, send_from_directory, Response, stream_with_context
from flask_cors import CORS
import sqlite3
import os
import hashlib
import uuid
import time

import helpers as H
import auth as Auth

app=Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}}, supports_credentials=True)

#DB_FILE / UPLOAD_DIR can point at a Render disk (e.g. /var/data/...)
_BASE=os.path.dirname(__file__)
DB_FILE=os.environ.get('DB_FILE') or os.path.join(_BASE, 'twitter.db')
UPLOAD_DIR=os.environ.get('UPLOAD_DIR') or os.path.join(_BASE, 'uploads')
os.makedirs(UPLOAD_DIR, exist_ok=True)
_db_dir=os.path.dirname(DB_FILE)
if _db_dir:
    os.makedirs(_db_dir, exist_ok=True)
ALLOWED_EXT={'png', 'jpg', 'jpeg', 'gif', 'webp'}


def get_db_connection():
    conn=sqlite3.connect(DB_FILE)
    conn.row_factory=sqlite3.Row
    return conn


def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()


def _user_by_username(conn, username):
    return conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()


def _select_posts_cols(alias=None):
    #qualify with alias when joining other tables that also have id/etc
    cols = [
        'id', 'content', 'user_id', 'created_at', 'parent_id', 'media_url',
        'repost_of', 'quote_content', 'status', 'scheduled_at', 'impression_count',
    ]
    if alias:
        return ', '.join(f'{alias}.{c}' for c in cols)
    return ', '.join(cols)


def current_user(conn):
    #who is logged in via bearer token (or None)
    return Auth.user_from_token(conn, Auth.bearer_from_request(request))


def require_user(conn):
    user=current_user(conn)
    if not user:
        return None
    return user


#auth
@app.route('/signup', methods=['POST'])
def signup():
    data = request.get_json() or {}
    username = data.get('username', '').strip()
    password = data.get('password', '').strip()
    if not username or not password:
        return jsonify({'error': 'Username and password required'}), 400
    if len(password) < 6:
        return jsonify({'error': 'Password must be at least 6 characters'}), 400
    password_hash = hash_password(password)
    conn = get_db_connection()
    if conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone():
        conn.close()
        return jsonify({'error': 'Username already exists'}), 409
    conn.execute('INSERT INTO users (username, password) VALUES (?, ?)', (username, password_hash))
    conn.commit()
    user_id = conn.execute('SELECT id FROM users WHERE username = ?', (username,)).fetchone()[0]
    H.ensure_default_collection(conn, user_id)
    try:
        token = Auth.create_session(conn, user_id)
        conn.commit()
    except sqlite3.OperationalError:
        token = None
    conn.close()
    return jsonify({
        'message': 'User created',
        'token': token,
        'user': {'id': user_id, 'username': username},
    }), 201


@app.route('/login', methods=['POST'])
def login():
    data = request.get_json() or {}
    username = data.get('username', '').strip()
    password = data.get('password', '').strip()
    if not username or not password:
        return jsonify({'error': 'Username and password required'}), 400
    password_hash = hash_password(password)
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
    if not user or user['password'] != password_hash:
        conn.close()
        if user:
            return jsonify({'error': 'Incorrect password'}), 401
        return jsonify({'error': 'User not found'}), 404
    try:
        token = Auth.create_session(conn, user['id'])
        conn.commit()
    except sqlite3.OperationalError:
        token = None
    conn.close()
    return jsonify({
        'message': 'Login successful',
        'token': token,
        'user': {'id': user['id'], 'username': user['username']},
    }), 200


@app.route('/logout', methods=['POST'])
def logout():
    conn = get_db_connection()
    Auth.revoke_session(conn, Auth.bearer_from_request(request))
    conn.commit()
    conn.close()
    return jsonify({'message': 'Logged out'}), 200


@app.route('/me', methods=['GET'])
def me():
    conn = get_db_connection()
    user = require_user(conn)
    if not user:
        conn.close()
        return jsonify({'error': 'Unauthorized'}), 401
    out = {'id': user['id'], 'username': user['username'], 'bio': user['bio'] if 'bio' in user.keys() else '', 'avatar_url': user['avatar_url'] if 'avatar_url' in user.keys() else ''}
    conn.close()
    return jsonify({'user': out}), 200


#upload
@app.route('/upload', methods=['POST'])
def upload_file():
    conn = get_db_connection()
    user = require_user(conn)
    conn.close()
    if not user:
        return jsonify({'error': 'Unauthorized'}), 401
    if 'file' not in request.files:
        return jsonify({'error': 'No file'}), 400
    f = request.files['file']
    if not f or not f.filename:
        return jsonify({'error': 'Empty file'}), 400
    ext = f.filename.rsplit('.', 1)[-1].lower() if '.' in f.filename else ''
    if ext not in ALLOWED_EXT:
        return jsonify({'error': 'Invalid file type'}), 400
    name = f'{uuid.uuid4().hex}.{ext}'
    path = os.path.join(UPLOAD_DIR, name)
    f.save(path)
    url = f'/uploads/{name}'
    return jsonify({'url': url, 'media_url': url}), 201


@app.route('/uploads/<path:filename>')
def serve_upload(filename):
    return send_from_directory(UPLOAD_DIR, filename)


#create post (draft/schedule/reply/media)
@app.route('/posts', methods=['POST'])
def create_post():
    data = request.get_json() or {}
    content = (data.get('content') or '').strip()
    parent_id = data.get('parent_id')
    media_url = data.get('media_url')
    status = data.get('status') or 'published'
    scheduled_at = data.get('scheduled_at')
    if status not in ('published', 'draft', 'scheduled'):
        status = 'published'
    if status == 'scheduled' and not scheduled_at:
        return jsonify({'error': 'scheduled_at required for scheduled posts'}), 400
    if status == 'published' and not content and not media_url:
        return jsonify({'error': 'Post content is required'}), 400
    if status == 'draft' and not content and not media_url:
        return jsonify({'error': 'Draft needs content or media'}), 400

    conn = get_db_connection()
    user = require_user(conn)
    if not user:
        conn.close()
        return jsonify({'error': 'Unauthorized'}), 401
    H.publish_due_posts(conn)
    user_id = user['id']

    try:
        cur = conn.execute(
            f'''INSERT INTO posts (content, user_id, parent_id, created_at, media_url, status, scheduled_at)
                VALUES (?, ?, ?, datetime('now'), ?, ?, ?)''',
            (content or '', user_id, parent_id, media_url, status, scheduled_at)
        )
    except sqlite3.OperationalError:
        cur = conn.execute(
            "INSERT INTO posts (content, user_id, parent_id, created_at) VALUES (?, ?, ?, datetime('now'))",
            (content or '', user_id, parent_id)
        )
    new_id = cur.lastrowid

    if status == 'published' and content:
        mentioned_ids, _ = H.link_mentions_hashtags(conn, new_id, content, user_id)
        for mid in mentioned_ids:
            H.create_notification(conn, mid, user_id, 'mention', post_id=new_id,
                                  message='mentioned you')
        if parent_id:
            parent = conn.execute('SELECT user_id FROM posts WHERE id = ?', (parent_id,)).fetchone()
            if parent and parent[0]:
                H.create_notification(conn, parent[0], user_id, 'reply', post_id=new_id,
                                      message='replied to your chirp')

    conn.commit()
    if status == 'published':
        H.broadcast_to_all({'event': 'feed', 'post_id': new_id})
    conn.close()
    return jsonify({'message': 'Post created', 'id': new_id, 'status': status}), 201


#edit draft or publish
@app.route('/posts/<int:post_id>', methods=['PUT'])
def update_post(post_id):
    data = request.get_json() or {}
    conn = get_db_connection()
    user = require_user(conn)
    if not user:
        conn.close()
        return jsonify({'error': 'Unauthorized'}), 401
    user_id = user['id']
    post = conn.execute('SELECT * FROM posts WHERE id = ?', (post_id,)).fetchone()
    if not post:
        conn.close()
        return jsonify({'error': 'Post not found'}), 404
    if post['user_id'] != user_id:
        conn.close()
        return jsonify({'error': 'Forbidden'}), 403

    content = data.get('content')
    media_url = data.get('media_url')
    status = data.get('status')
    scheduled_at = data.get('scheduled_at')
    updates, params = [], []
    if content is not None:
        updates.append('content = ?')
        params.append(content)
    if media_url is not None:
        updates.append('media_url = ?')
        params.append(media_url)
    if status in ('published', 'draft', 'scheduled'):
        updates.append('status = ?')
        params.append(status)
        if status == 'published':
            updates.append("created_at = datetime('now')")
    if 'scheduled_at' in data:
        updates.append('scheduled_at = ?')
        params.append(scheduled_at)
    if not updates:
        conn.close()
        return jsonify({'message': 'No changes'}), 200
    params.append(post_id)
    conn.execute('UPDATE posts SET ' + ', '.join(updates) + ' WHERE id = ?', params)

    final_status = status or post['status']
    final_content = content if content is not None else post['content']
    if final_status == 'published' and final_content:
        conn.execute('DELETE FROM mentions WHERE post_id = ?', (post_id,))
        conn.execute('DELETE FROM post_hashtags WHERE post_id = ?', (post_id,))
        mentioned_ids, _ = H.link_mentions_hashtags(conn, post_id, final_content, user_id)
        for mid in mentioned_ids:
            H.create_notification(conn, mid, user_id, 'mention', post_id=post_id, message='mentioned you')
        H.broadcast_to_all({'event': 'feed', 'post_id': post_id})

    conn.commit()
    conn.close()
    return jsonify({'message': 'Post updated'}), 200


@app.route('/posts', methods=['GET'])
def get_posts():
    feed = (request.args.get('feed') or 'for_you').strip().lower()
    conn = get_db_connection()
    H.publish_due_posts(conn)
    user = current_user(conn)
    viewer_id = user['id'] if user else H.get_user_id(conn, (request.args.get('viewer') or '').strip())

    try:
        if feed == 'following' and viewer_id:
            rows = conn.execute(f'''
                SELECT {_select_posts_cols()}
                FROM posts p
                WHERE p.parent_id IS NULL
                  AND (p.status = 'published' OR p.status IS NULL)
                  AND p.user_id IN (SELECT followee_id FROM followers WHERE follower_id = ?)
                ORDER BY p.id DESC
            ''', (viewer_id,)).fetchall()
        else:
            rows = conn.execute(f'''
                SELECT {_select_posts_cols()}
                FROM posts p
                WHERE p.parent_id IS NULL
                  AND (p.status = 'published' OR p.status IS NULL)
                ORDER BY p.id DESC
            ''').fetchall()
    except sqlite3.OperationalError:
        rows = conn.execute(
            'SELECT id, content, user_id, created_at, parent_id FROM posts WHERE parent_id IS NULL ORDER BY id DESC'
        ).fetchall()

    if feed == 'for_you':
        rows = H.rank_for_you(conn, rows, viewer_id)

    out = H.build_tweet_list(conn, rows, viewer_id)
    H.bump_impressions(conn, [p['id'] for p in out])
    conn.close()
    return jsonify(out)


@app.route('/posts/<int:post_id>', methods=['GET'])
def get_post_detail(post_id):
    conn = get_db_connection()
    H.publish_due_posts(conn)
    user = current_user(conn)
    viewer_id = user['id'] if user else H.get_user_id(conn, (request.args.get('viewer') or '').strip())
    try:
        row = conn.execute(f'SELECT {_select_posts_cols()} FROM posts WHERE id = ?', (post_id,)).fetchone()
    except sqlite3.OperationalError:
        row = conn.execute(
            'SELECT id, content, user_id, created_at, parent_id FROM posts WHERE id = ?', (post_id,)
        ).fetchone()
    if not row:
        conn.close()
        return jsonify({'error': 'Post not found'}), 404
    items = H.build_tweet_list(conn, [row], viewer_id)
    if not items:
        conn.close()
        return jsonify({'error': 'Post not found'}), 404
    H.bump_impressions(conn, [post_id])
    conn.close()
    return jsonify(items[0])


@app.route('/posts/<int:post_id>/comments', methods=['GET'])
def get_post_comments(post_id):
    conn = get_db_connection()
    user = current_user(conn)
    viewer_id = user['id'] if user else H.get_user_id(conn, (request.args.get('viewer') or '').strip())
    try:
        rows = conn.execute(
            f'SELECT {_select_posts_cols()} FROM posts WHERE parent_id = ? ORDER BY id ASC',
            (post_id,)
        ).fetchall()
    except sqlite3.OperationalError:
        rows = conn.execute(
            'SELECT id, content, user_id, created_at, parent_id FROM posts WHERE parent_id = ? ORDER BY id ASC',
            (post_id,)
        ).fetchall()
    out = H.build_tweet_list(conn, rows, viewer_id)
    conn.close()
    return jsonify(out)


#repost / quote
@app.route('/posts/<int:post_id>/repost', methods=['POST'])
def repost(post_id):
    data = request.get_json() or {}
    quote = (data.get('quote') or data.get('quote_content') or '').strip() or None
    conn = get_db_connection()
    user = require_user(conn)
    if not user:
        conn.close()
        return jsonify({'error': 'Unauthorized'}), 401
    user_id = user['id']
    original = conn.execute('SELECT * FROM posts WHERE id = ?', (post_id,)).fetchone()
    if not original:
        conn.close()
        return jsonify({'error': 'Post not found'}), 404
    content = quote or ''
    cur = conn.execute(
        """INSERT INTO posts (content, user_id, parent_id, created_at, repost_of, quote_content, status)
            VALUES (?, ?, NULL, datetime('now'), ?, ?, 'published')""",
        (content, user_id, post_id, quote)
    )
    new_id = cur.lastrowid
    if quote:
        H.link_mentions_hashtags(conn, new_id, quote, user_id)
    if original['user_id']:
        H.create_notification(conn, original['user_id'], user_id, 'repost', post_id=post_id,
                              message='reposted your chirp')
    conn.commit()
    H.broadcast_to_all({'event': 'feed', 'post_id': new_id})
    conn.close()
    return jsonify({'message': 'Reposted', 'id': new_id}), 201


@app.route('/posts/<int:post_id>/typing', methods=['POST'])
def post_typing(post_id):
    conn = get_db_connection()
    user = require_user(conn)
    conn.close()
    if not user:
        return jsonify({'error': 'Unauthorized'}), 401
    H.set_typing(post_id, user['username'])
    return jsonify({'ok': True, 'typing': H.get_typing(post_id, exclude=user['username'])}), 200


@app.route('/posts/<int:post_id>/typing', methods=['GET'])
def get_typing(post_id):
    exclude = (request.args.get('exclude') or '').strip() or None
    return jsonify({'typing': H.get_typing(post_id, exclude=exclude)})


#drafts
@app.route('/drafts', methods=['GET'])
def get_drafts():
    conn = get_db_connection()
    H.publish_due_posts(conn)
    user = require_user(conn)
    if not user:
        conn.close()
        return jsonify({'error': 'Unauthorized'}), 401
    user_id = user['id']
    try:
        rows = conn.execute(
            'SELECT ' + _select_posts_cols() + """ FROM posts
                WHERE user_id = ? AND status IN ('draft', 'scheduled')
                ORDER BY id DESC""",
            (user_id,)
        ).fetchall()
    except sqlite3.OperationalError:
        rows = []
    out = H.build_tweet_list(conn, rows, user_id)
    conn.close()
    return jsonify(out)


@app.route('/search/tweets')
def search_tweets():
    q = request.args.get('q', '')
    viewer_username = (request.args.get('viewer') or '').strip()
    conn = get_db_connection()
    viewer_id = H.get_user_id(conn, viewer_username)
    try:
        rows = conn.execute(
            f'''SELECT {_select_posts_cols()} FROM posts
                WHERE content LIKE ? AND (status = 'published' OR status IS NULL)
                ORDER BY id DESC''',
            ('%' + q + '%',)
        ).fetchall()
    except sqlite3.OperationalError:
        rows = conn.execute(
            "SELECT id, content, user_id FROM posts WHERE content LIKE ? ORDER BY id DESC",
            ('%' + q + '%',)
        ).fetchall()
    out = H.build_tweet_list(conn, rows, viewer_id)
    conn.close()
    return jsonify(out)


@app.route('/search/users')
def search_users():
    q = request.args.get('q', '')
    conn = get_db_connection()
    try:
        rows = conn.execute(
            "SELECT id, username, bio, avatar_url FROM users WHERE username LIKE ?",
            ('%' + q + '%',)
        ).fetchall()
    except sqlite3.OperationalError:
        rows = conn.execute(
            "SELECT id, username FROM users WHERE username LIKE ?", ('%' + q + '%',)
        ).fetchall()
    out = []
    for row in rows:
        r = dict(row)
        r.setdefault('bio', '')
        r.setdefault('avatar_url', '')
        out.append(r)
    conn.close()
    return jsonify(out)


#hashtags
@app.route('/hashtags/trending')
def trending_hashtags():
    conn = get_db_connection()
    try:
        rows = conn.execute('''
            SELECT h.tag, COUNT(*) as cnt
            FROM hashtags h
            JOIN post_hashtags ph ON ph.hashtag_id = h.id
            JOIN posts p ON p.id = ph.post_id
            WHERE (p.status = 'published' OR p.status IS NULL)
              AND p.created_at >= datetime('now', '-7 days')
            GROUP BY h.id
            ORDER BY cnt DESC
            LIMIT 20
        ''').fetchall()
    except sqlite3.OperationalError:
        rows = []
    conn.close()
    return jsonify([{'tag': r[0], 'count': r[1]} for r in rows])


@app.route('/hashtags/<tag>')
def hashtag_posts(tag):
    tag = (tag or '').lstrip('#').lower()
    viewer_username = (request.args.get('viewer') or '').strip()
    conn = get_db_connection()
    viewer_id = H.get_user_id(conn, viewer_username)
    try:
        rows = conn.execute(f'''
            SELECT {_select_posts_cols('p')}
            FROM posts p
            JOIN post_hashtags ph ON ph.post_id = p.id
            JOIN hashtags h ON h.id = ph.hashtag_id
            WHERE h.tag = ? AND (p.status = 'published' OR p.status IS NULL)
            ORDER BY p.id DESC
        ''', (tag,)).fetchall()
    except sqlite3.OperationalError:
        rows = []
    out = H.build_tweet_list(conn, rows, viewer_id)
    conn.close()
    return jsonify({'tag': tag, 'posts': out})


#profile
@app.route('/profile/<username>')
def get_profile(username):
    conn = get_db_connection()
    try:
        row = conn.execute(
            '''SELECT id, username, bio, avatar_url, who_can_see_tweets, who_can_see_followers,
                      who_can_see_following, show_likes_on_profile FROM users WHERE username = ?''',
            (username,)
        ).fetchone()
    except sqlite3.OperationalError:
        row = conn.execute(
            'SELECT id, username, bio, avatar_url FROM users WHERE username = ?', (username,)
        ).fetchone()
    if not row:
        conn.close()
        return jsonify({'error': 'User not found'}), 404
    d = dict(row)
    d.setdefault('bio', '')
    d.setdefault('avatar_url', '')
    d.setdefault('who_can_see_tweets', 'public')
    d.setdefault('who_can_see_followers', 'public')
    d.setdefault('who_can_see_following', 'public')
    d.setdefault('show_likes_on_profile', 1)
    conn.close()
    return jsonify(d)


@app.route('/follow', methods=['POST'])
def follow():
    data = request.get_json() or {}
    followee_id = data.get('followee_id')
    conn = get_db_connection()
    user = require_user(conn)
    if not user:
        conn.close()
        return jsonify({'error': 'Unauthorized'}), 401
    follower_id = user['id']
    if not followee_id or int(followee_id) == follower_id:
        conn.close()
        return jsonify({'error': 'Invalid follow target'}), 400
    try:
        conn.execute('INSERT INTO followers (follower_id, followee_id) VALUES (?, ?)', (follower_id, followee_id))
        H.create_notification(conn, followee_id, follower_id, 'follow', message='followed you')
        conn.commit()
        return jsonify({'message': 'Followed'}), 201
    except Exception:
        return jsonify({'error': 'Already following or invalid'}), 400
    finally:
        conn.close()


@app.route('/followers/<int:user_id>')
def get_followers(user_id):
    conn = get_db_connection()
    rows = conn.execute('''
        SELECT u.id, u.username FROM users u
        JOIN followers f ON u.id = f.follower_id WHERE f.followee_id = ?
    ''', (user_id,)).fetchall()
    conn.close()
    return jsonify([dict(row) for row in rows])


# legacy aliases used by older code paths
def _can_see(conn, profile_user_id, viewer_id, setting):
    return H.can_see(conn, profile_user_id, viewer_id, setting)


def _build_tweet_list_full(conn, rows, viewer_id):
    return H.build_tweet_list(conn, rows, viewer_id)


@app.route('/users/<int:user_id>/tweets')
def get_user_tweets(user_id):
    viewer_username = (request.args.get('viewer') or '').strip()
    conn = get_db_connection()
    H.publish_due_posts(conn)
    viewer_id = H.get_user_id(conn, viewer_username)
    try:
        rows = conn.execute(
            f'''SELECT {_select_posts_cols()} FROM posts
                WHERE user_id = ? AND parent_id IS NULL
                  AND (status = 'published' OR status IS NULL)
                ORDER BY id DESC''',
            (int(user_id),)
        ).fetchall()
    except sqlite3.OperationalError:
        rows = []
    out = H.build_tweet_list(conn, rows, viewer_id)
    conn.close()
    return jsonify(out)


@app.route('/profile/<username>/tweets')
def get_profile_tweets(username):
    username = (username or '').strip()
    if not username:
        return jsonify({'error': 'Username required'}), 400
    viewer_username = (request.args.get('viewer') or '').strip()
    conn = get_db_connection()
    H.publish_due_posts(conn)
    try:
        user = conn.execute('SELECT id, who_can_see_tweets FROM users WHERE username = ?', (username,)).fetchone()
        who = (user[1] if user and len(user) > 1 else None) or 'public'
    except sqlite3.OperationalError:
        user = conn.execute('SELECT id FROM users WHERE username = ?', (username,)).fetchone()
        who = 'public'
    if not user:
        conn.close()
        return jsonify({'error': 'User not found'}), 404
    profile_id = int(user[0])
    viewer_id = H.get_user_id(conn, viewer_username)
    if not H.can_see(conn, profile_id, viewer_id, who):
        conn.close()
        return jsonify([])
    try:
        rows = conn.execute(
            f'''SELECT {_select_posts_cols()} FROM posts
                WHERE user_id = ? AND parent_id IS NULL
                  AND (status = 'published' OR status IS NULL)
                ORDER BY id DESC''',
            (profile_id,)
        ).fetchall()
    except sqlite3.OperationalError:
        rows = []
    out = H.build_tweet_list(conn, rows, viewer_id)
    conn.close()
    return jsonify(out)


@app.route('/profile/<username>', methods=['PUT'])
def update_profile(username):
    data = request.get_json() or {}
    conn = get_db_connection()
    user = require_user(conn)
    if not user or user['username'] != username:
        conn.close()
        return jsonify({'error': 'Unauthorized'}), 403
    bio = data.get('bio')
    avatar_url = data.get('avatar_url')
    updates, params = [], []
    if bio is not None:
        updates.append('bio = ?')
        params.append(bio)
    if avatar_url is not None:
        updates.append('avatar_url = ?')
        params.append(avatar_url)
    if not updates:
        conn.close()
        return jsonify({'message': 'No changes'}), 200
    params.append(username)
    conn.execute('UPDATE users SET ' + ', '.join(updates) + ' WHERE username = ?', params)
    conn.commit()
    conn.close()
    return jsonify({'message': 'Profile updated'}), 200


@app.route('/posts/<int:post_id>', methods=['DELETE'])
def delete_post(post_id):
    conn = get_db_connection()
    user = require_user(conn)
    if not user:
        conn.close()
        return jsonify({'error': 'Unauthorized'}), 401
    post = conn.execute('SELECT user_id FROM posts WHERE id = ?', (post_id,)).fetchone()
    if not post or post[0] != user['id']:
        conn.close()
        return jsonify({'error': 'Forbidden'}), 403
    conn.execute('DELETE FROM posts WHERE id = ?', (post_id,))
    conn.execute('DELETE FROM likes WHERE post_id = ?', (post_id,))
    conn.execute('DELETE FROM saved_tweets WHERE post_id = ?', (post_id,))
    try:
        conn.execute('DELETE FROM mentions WHERE post_id = ?', (post_id,))
        conn.execute('DELETE FROM post_hashtags WHERE post_id = ?', (post_id,))
        conn.execute('DELETE FROM collection_items WHERE post_id = ?', (post_id,))
    except sqlite3.OperationalError:
        pass
    conn.commit()
    conn.close()
    return jsonify({'message': 'Post deleted'}), 200


@app.route('/posts/<int:post_id>/like', methods=['POST'])
def like_post(post_id):
    conn = get_db_connection()
    user = require_user(conn)
    if not user:
        conn.close()
        return jsonify({'error': 'Unauthorized'}), 401
    try:
        conn.execute('INSERT INTO likes (user_id, post_id) VALUES (?, ?)', (user['id'], post_id))
        post = conn.execute('SELECT user_id FROM posts WHERE id = ?', (post_id,)).fetchone()
        if post and post[0]:
            H.create_notification(conn, post[0], user['id'], 'like', post_id=post_id, message='liked your chirp')
        conn.commit()
        conn.close()
        return jsonify({'message': 'Liked'}), 201
    except sqlite3.IntegrityError:
        conn.close()
        return jsonify({'message': 'Already liked'}), 200


@app.route('/posts/<int:post_id>/like', methods=['DELETE'])
def unlike_post(post_id):
    conn = get_db_connection()
    user = require_user(conn)
    if not user:
        conn.close()
        return jsonify({'error': 'Unauthorized'}), 401
    conn.execute('DELETE FROM likes WHERE user_id = ? AND post_id = ?', (user['id'], post_id))
    conn.commit()
    conn.close()
    return jsonify({'message': 'Unliked'}), 200


@app.route('/posts/<int:post_id>/save', methods=['POST'])
def save_post(post_id):
    data = request.get_json() or {}
    collection_id = data.get('collection_id')
    conn = get_db_connection()
    user = require_user(conn)
    if not user:
        conn.close()
        return jsonify({'error': 'Unauthorized'}), 401
    try:
        conn.execute('INSERT OR IGNORE INTO saved_tweets (user_id, post_id) VALUES (?, ?)', (user['id'], post_id))
        cid = collection_id or H.ensure_default_collection(conn, user['id'])
        conn.execute('INSERT OR IGNORE INTO collection_items (collection_id, post_id) VALUES (?, ?)', (cid, post_id))
        conn.commit()
        conn.close()
        return jsonify({'message': 'Saved', 'collection_id': cid}), 201
    except sqlite3.OperationalError:
        try:
            conn.execute('INSERT INTO saved_tweets (user_id, post_id) VALUES (?, ?)', (user['id'], post_id))
            conn.commit()
        except sqlite3.IntegrityError:
            pass
        conn.close()
        return jsonify({'message': 'Saved'}), 201


@app.route('/posts/<int:post_id>/save', methods=['DELETE'])
def unsave_post(post_id):
    conn = get_db_connection()
    user = require_user(conn)
    if not user:
        conn.close()
        return jsonify({'error': 'Unauthorized'}), 401
    conn.execute('DELETE FROM saved_tweets WHERE user_id = ? AND post_id = ?', (user['id'], post_id))
    try:
        cols = conn.execute(
            'SELECT id FROM bookmark_collections WHERE user_id = ?', (user['id'],)
        ).fetchall()
        for c in cols:
            conn.execute('DELETE FROM collection_items WHERE collection_id = ? AND post_id = ?', (c[0], post_id))
    except sqlite3.OperationalError:
        pass
    conn.commit()
    conn.close()
    return jsonify({'message': 'Unsaved'}), 200


@app.route('/profile/<username>/likes')
def get_profile_likes(username):
    viewer_username = (request.args.get('viewer') or '').strip()
    conn = get_db_connection()
    try:
        user = conn.execute(
            'SELECT id, show_likes_on_profile, who_can_see_tweets FROM users WHERE username = ?',
            (username,)
        ).fetchone()
        if not user:
            conn.close()
            return jsonify({'error': 'User not found'}), 404
        profile_id = user[0]
        show_likes = (user[1] if len(user) > 1 else 1) != 0
        who = (user[2] if len(user) > 2 else 'public') or 'public'
    except sqlite3.OperationalError:
        user = conn.execute('SELECT id FROM users WHERE username = ?', (username,)).fetchone()
        if not user:
            conn.close()
            return jsonify({'error': 'User not found'}), 404
        profile_id = user[0]
        show_likes = True
        who = 'public'
    viewer_id = H.get_user_id(conn, viewer_username)
    if profile_id != viewer_id and (not show_likes or not H.can_see(conn, profile_id, viewer_id, who)):
        conn.close()
        return jsonify([])
    try:
        rows = conn.execute(f'''
            SELECT {_select_posts_cols('p')}
            FROM posts p JOIN likes l ON l.post_id = p.id
            WHERE l.user_id = ? ORDER BY p.id DESC
        ''', (profile_id,)).fetchall()
    except sqlite3.OperationalError:
        rows = []
    out = H.build_tweet_list(conn, rows, viewer_id)
    conn.close()
    return jsonify(out)


@app.route('/profile/<username>/saved')
def get_profile_saved(username):
    conn = get_db_connection()
    user = require_user(conn)
    if not user or user['username'] != username:
        conn.close()
        return jsonify({'error': 'Forbidden'}), 403
    try:
        rows = conn.execute(
            'SELECT ' + _select_posts_cols('p') + '''
            FROM posts p JOIN saved_tweets s ON s.post_id = p.id
            WHERE s.user_id = ? ORDER BY p.id DESC''',
            (user['id'],)
        ).fetchall()
    except sqlite3.OperationalError:
        rows = []
    out = H.build_tweet_list(conn, rows, user['id'])
    for r in out:
        r['saved_by_me'] = True
    conn.close()
    return jsonify(out)


@app.route('/profile/<username>/followers')
def get_profile_followers(username):
    viewer_username = (request.args.get('viewer') or '').strip()
    conn = get_db_connection()
    try:
        user = conn.execute('SELECT id, who_can_see_followers FROM users WHERE username = ?', (username,)).fetchone()
        if not user:
            conn.close()
            return jsonify({'error': 'User not found'}), 404
        profile_id = user[0]
        who = (user[1] if len(user) > 1 else None) or 'public'
    except sqlite3.OperationalError:
        user = conn.execute('SELECT id FROM users WHERE username = ?', (username,)).fetchone()
        if not user:
            conn.close()
            return jsonify({'error': 'User not found'}), 404
        profile_id = user[0]
        who = 'public'
    viewer_id = H.get_user_id(conn, viewer_username)
    if not H.can_see(conn, profile_id, viewer_id, who):
        conn.close()
        return jsonify([])
    blocked = H.get_blocked_ids(conn, viewer_id)
    rows = conn.execute('''
        SELECT u.id, u.username, u.bio, u.avatar_url
        FROM users u JOIN followers f ON u.id = f.follower_id
        WHERE f.followee_id = ?
    ''', (profile_id,)).fetchall()
    out = []
    for row in rows:
        if row['id'] in blocked:
            continue
        r = dict(row)
        r.setdefault('bio', '')
        r.setdefault('avatar_url', '')
        out.append(r)
    conn.close()
    return jsonify(out)


@app.route('/profile/<username>/following')
def get_profile_following(username):
    viewer_username = (request.args.get('viewer') or '').strip()
    conn = get_db_connection()
    try:
        user = conn.execute('SELECT id, who_can_see_following FROM users WHERE username = ?', (username,)).fetchone()
        if not user:
            conn.close()
            return jsonify({'error': 'User not found'}), 404
        profile_id = user[0]
        who = (user[1] if len(user) > 1 else None) or 'public'
    except sqlite3.OperationalError:
        user = conn.execute('SELECT id FROM users WHERE username = ?', (username,)).fetchone()
        if not user:
            conn.close()
            return jsonify({'error': 'User not found'}), 404
        profile_id = user[0]
        who = 'public'
    viewer_id = H.get_user_id(conn, viewer_username)
    if not H.can_see(conn, profile_id, viewer_id, who):
        conn.close()
        return jsonify([])
    blocked = H.get_blocked_ids(conn, viewer_id)
    rows = conn.execute('''
        SELECT u.id, u.username, u.bio, u.avatar_url
        FROM users u JOIN followers f ON u.id = f.followee_id
        WHERE f.follower_id = ?
    ''', (profile_id,)).fetchall()
    out = []
    for row in rows:
        if row['id'] in blocked:
            continue
        r = dict(row)
        r.setdefault('bio', '')
        r.setdefault('avatar_url', '')
        out.append(r)
    conn.close()
    return jsonify(out)


@app.route('/follow', methods=['DELETE'])
def unfollow():
    data = request.get_json() or {}
    followee_id = data.get('followee_id')
    conn = get_db_connection()
    user = require_user(conn)
    if not user:
        conn.close()
        return jsonify({'error': 'Unauthorized'}), 401
    if followee_id is None:
        conn.close()
        return jsonify({'error': 'followee_id required'}), 400
    conn.execute('DELETE FROM followers WHERE follower_id = ? AND followee_id = ?', (user['id'], followee_id))
    conn.commit()
    conn.close()
    return jsonify({'message': 'Unfollowed'}), 200


@app.route('/follow/check')
def check_follow():
    follower_id = request.args.get('follower_id', type=int)
    followee_id = request.args.get('followee_id', type=int)
    if follower_id is None or followee_id is None:
        return jsonify({'following': False})
    conn = get_db_connection()
    row = conn.execute(
        'SELECT 1 FROM followers WHERE follower_id = ? AND followee_id = ?',
        (follower_id, followee_id)
    ).fetchone()
    conn.close()
    return jsonify({'following': row is not None})


@app.route('/profile/<username>/settings')
def get_profile_settings(username):
    conn = get_db_connection()
    user = require_user(conn)
    if not user or user['username'] != username:
        conn.close()
        return jsonify({'error': 'Forbidden'}), 403
    row = conn.execute(
        '''SELECT who_can_see_tweets, who_can_see_followers, who_can_see_following, show_likes_on_profile
           FROM users WHERE username = ?''',
        (username,)
    ).fetchone()
    conn.close()
    if not row:
        return jsonify({'error': 'User not found'}), 404
    return jsonify({
        'who_can_see_tweets': row[0] or 'public',
        'who_can_see_followers': row[1] or 'public',
        'who_can_see_following': row[2] or 'public',
        'show_likes_on_profile': bool(row[3]) if row[3] is not None else True,
    })


@app.route('/profile/<username>/settings', methods=['PUT'])
def update_profile_settings(username):
    data = request.get_json() or {}
    conn = get_db_connection()
    user = require_user(conn)
    if not user or user['username'] != username:
        conn.close()
        return jsonify({'error': 'Unauthorized'}), 403
    updates, params = [], []
    for key in ('who_can_see_tweets', 'who_can_see_followers', 'who_can_see_following'):
        val = data.get(key)
        if val in ('public', 'followers', 'private'):
            updates.append(f'{key} = ?')
            params.append(val)
    if data.get('show_likes_on_profile') is not None:
        updates.append('show_likes_on_profile = ?')
        params.append(1 if data.get('show_likes_on_profile') else 0)
    if not updates:
        conn.close()
        return jsonify({'message': 'No changes'}), 200
    params.append(username)
    conn.execute('UPDATE users SET ' + ', '.join(updates) + ' WHERE username = ?', params)
    conn.commit()
    conn.close()
    return jsonify({'message': 'Settings updated'}), 200


@app.route('/notifications', methods=['GET'])
def get_notifications():
    conn = get_db_connection()
    user = require_user(conn)
    if not user:
        conn.close()
        return jsonify({'error': 'Unauthorized'}), 401
    rows = conn.execute('''
        SELECT n.id, n.type, n.post_id, n.room_id, n.message, n.read, n.created_at,
               u.username as actor, u.avatar_url as actor_avatar
        FROM notifications n
        LEFT JOIN users u ON u.id = n.actor_id
        WHERE n.user_id = ?
        ORDER BY n.id DESC
        LIMIT 100
    ''', (user['id'],)).fetchall()
    unread = conn.execute(
        'SELECT COUNT(*) FROM notifications WHERE user_id = ? AND read = 0', (user['id'],)
    ).fetchone()[0]
    conn.close()
    return jsonify({'notifications': [dict(r) for r in rows], 'unread': unread})


@app.route('/notifications/read', methods=['POST'])
def mark_notifications_read():
    data = request.get_json() or {}
    ids = data.get('ids')
    conn = get_db_connection()
    user = require_user(conn)
    if not user:
        conn.close()
        return jsonify({'error': 'Unauthorized'}), 401
    if ids:
        for nid in ids:
            conn.execute(
                'UPDATE notifications SET read = 1 WHERE id = ? AND user_id = ?',
                (nid, user['id'])
            )
    else:
        conn.execute('UPDATE notifications SET read = 1 WHERE user_id = ?', (user['id'],))
    conn.commit()
    conn.close()
    return jsonify({'message': 'Marked read'}), 200


@app.route('/block', methods=['POST'])
def block_user():
    data = request.get_json() or {}
    target = data.get('target_id') or data.get('blocked_id')
    target_name = (data.get('target_username') or '').strip()
    conn = get_db_connection()
    user = require_user(conn)
    if not user:
        conn.close()
        return jsonify({'error': 'Unauthorized'}), 401
    if target_name and not target:
        target = H.get_user_id(conn, target_name)
    if not target or int(target) == user['id']:
        conn.close()
        return jsonify({'error': 'Invalid target'}), 400
    conn.execute('INSERT OR IGNORE INTO blocks (blocker_id, blocked_id) VALUES (?, ?)', (user['id'], target))
    conn.execute('DELETE FROM followers WHERE (follower_id = ? AND followee_id = ?) OR (follower_id = ? AND followee_id = ?)',
                 (user['id'], target, target, user['id']))
    conn.commit()
    conn.close()
    return jsonify({'message': 'Blocked'}), 201


@app.route('/block', methods=['DELETE'])
def unblock_user():
    data = request.get_json() or {}
    target = data.get('target_id') or data.get('blocked_id')
    target_name = (data.get('target_username') or '').strip()
    conn = get_db_connection()
    user = require_user(conn)
    if target_name and not target:
        target = H.get_user_id(conn, target_name)
    if not user or not target:
        conn.close()
        return jsonify({'error': 'Unauthorized'}), 401
    conn.execute('DELETE FROM blocks WHERE blocker_id = ? AND blocked_id = ?', (user['id'], target))
    conn.commit()
    conn.close()
    return jsonify({'message': 'Unblocked'}), 200


@app.route('/block/list')
def list_blocks():
    conn = get_db_connection()
    user = require_user(conn)
    if not user:
        conn.close()
        return jsonify({'error': 'Unauthorized'}), 401
    rows = conn.execute('''
        SELECT u.id, u.username, u.bio, u.avatar_url
        FROM blocks b JOIN users u ON u.id = b.blocked_id
        WHERE b.blocker_id = ?
    ''', (user['id'],)).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@app.route('/mute', methods=['POST'])
def mute_user():
    data = request.get_json() or {}
    target = data.get('target_id') or data.get('muted_id')
    target_name = (data.get('target_username') or '').strip()
    conn = get_db_connection()
    user = require_user(conn)
    if target_name and not target:
        target = H.get_user_id(conn, target_name)
    if not user or not target or int(target) == user['id']:
        conn.close()
        return jsonify({'error': 'Unauthorized'}), 401
    conn.execute('INSERT OR IGNORE INTO mutes (muter_id, muted_id) VALUES (?, ?)', (user['id'], target))
    conn.commit()
    conn.close()
    return jsonify({'message': 'Muted'}), 201


@app.route('/mute', methods=['DELETE'])
def unmute_user():
    data = request.get_json() or {}
    target = data.get('target_id') or data.get('muted_id')
    target_name = (data.get('target_username') or '').strip()
    conn = get_db_connection()
    user = require_user(conn)
    if target_name and not target:
        target = H.get_user_id(conn, target_name)
    if not user or not target:
        conn.close()
        return jsonify({'error': 'Unauthorized'}), 401
    conn.execute('DELETE FROM mutes WHERE muter_id = ? AND muted_id = ?', (user['id'], target))
    conn.commit()
    conn.close()
    return jsonify({'message': 'Unmuted'}), 200


@app.route('/mute/list')
def list_mutes():
    conn = get_db_connection()
    user = require_user(conn)
    if not user:
        conn.close()
        return jsonify({'error': 'Unauthorized'}), 401
    rows = conn.execute('''
        SELECT u.id, u.username, u.bio, u.avatar_url
        FROM mutes m JOIN users u ON u.id = m.muted_id
        WHERE m.muter_id = ?
    ''', (user['id'],)).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@app.route('/muted-words', methods=['GET'])
def get_muted_words():
    conn = get_db_connection()
    user = require_user(conn)
    if not user:
        conn.close()
        return jsonify({'error': 'Unauthorized'}), 401
    rows = conn.execute('SELECT word FROM muted_words WHERE user_id = ?', (user['id'],)).fetchall()
    conn.close()
    return jsonify([r[0] for r in rows])


@app.route('/muted-words', methods=['POST'])
def add_muted_word():
    data = request.get_json() or {}
    word = (data.get('word') or '').strip().lower()
    if not word:
        return jsonify({'error': 'Word required'}), 400
    conn = get_db_connection()
    user = require_user(conn)
    if not user:
        conn.close()
        return jsonify({'error': 'Unauthorized'}), 401
    conn.execute('INSERT OR IGNORE INTO muted_words (user_id, word) VALUES (?, ?)', (user['id'], word))
    conn.commit()
    conn.close()
    return jsonify({'message': 'Added'}), 201


@app.route('/muted-words', methods=['DELETE'])
def remove_muted_word():
    data = request.get_json() or {}
    word = (data.get('word') or '').strip().lower()
    conn = get_db_connection()
    user = require_user(conn)
    if not user:
        conn.close()
        return jsonify({'error': 'Unauthorized'}), 401
    conn.execute('DELETE FROM muted_words WHERE user_id = ? AND word = ?', (user['id'], word))
    conn.commit()
    conn.close()
    return jsonify({'message': 'Removed'}), 200


@app.route('/reports', methods=['POST'])
def report_post():
    data = request.get_json() or {}
    post_id = data.get('post_id')
    reason = (data.get('reason') or '').strip()
    conn = get_db_connection()
    user = require_user(conn)
    if not user or not post_id:
        conn.close()
        return jsonify({'error': 'Unauthorized'}), 401
    conn.execute(
        "INSERT INTO reports (reporter_id, post_id, reason, created_at) VALUES (?, ?, ?, datetime('now'))",
        (user['id'], post_id, reason)
    )
    conn.commit()
    conn.close()
    return jsonify({'message': 'Reported'}), 201


@app.route('/block/check')
def check_block():
    target = request.args.get('target_id', type=int)
    target_name = (request.args.get('target_username') or '').strip()
    conn = get_db_connection()
    user = require_user(conn)
    if target_name and not target:
        target = H.get_user_id(conn, target_name)
    blocked = muted = False
    if user and target:
        blocked = conn.execute(
            'SELECT 1 FROM blocks WHERE blocker_id = ? AND blocked_id = ?', (user['id'], target)
        ).fetchone() is not None
        muted = conn.execute(
            'SELECT 1 FROM mutes WHERE muter_id = ? AND muted_id = ?', (user['id'], target)
        ).fetchone() is not None
    conn.close()
    return jsonify({'blocked': blocked, 'muted': muted})


@app.route('/collections', methods=['GET'])
def list_collections():
    conn = get_db_connection()
    user = require_user(conn)
    if not user:
        conn.close()
        return jsonify({'error': 'Unauthorized'}), 401
    H.ensure_default_collection(conn, user['id'])
    rows = conn.execute('''
        SELECT c.id, c.name, c.created_at, COUNT(ci.post_id) as item_count
        FROM bookmark_collections c
        LEFT JOIN collection_items ci ON ci.collection_id = c.id
        WHERE c.user_id = ?
        GROUP BY c.id
        ORDER BY c.id ASC
    ''', (user['id'],)).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@app.route('/collections', methods=['POST'])
def create_collection():
    data = request.get_json() or {}
    name = (data.get('name') or '').strip()
    if not name:
        return jsonify({'error': 'Name required'}), 400
    conn = get_db_connection()
    user = require_user(conn)
    if not user:
        conn.close()
        return jsonify({'error': 'Unauthorized'}), 401
    cur = conn.execute(
        "INSERT INTO bookmark_collections (user_id, name, created_at) VALUES (?, ?, datetime('now'))",
        (user['id'], name)
    )
    conn.commit()
    cid = cur.lastrowid
    conn.close()
    return jsonify({'id': cid, 'name': name}), 201


@app.route('/collections/<int:collection_id>', methods=['DELETE'])
def delete_collection(collection_id):
    conn = get_db_connection()
    user = require_user(conn)
    if not user:
        conn.close()
        return jsonify({'error': 'Unauthorized'}), 401
    col = conn.execute('SELECT user_id, name FROM bookmark_collections WHERE id = ?', (collection_id,)).fetchone()
    if not col or col[0] != user['id']:
        conn.close()
        return jsonify({'error': 'Forbidden'}), 403
    if col[1] == 'Saved':
        conn.close()
        return jsonify({'error': 'Cannot delete default Saved collection'}), 400
    conn.execute('DELETE FROM collection_items WHERE collection_id = ?', (collection_id,))
    conn.execute('DELETE FROM bookmark_collections WHERE id = ?', (collection_id,))
    conn.commit()
    conn.close()
    return jsonify({'message': 'Deleted'}), 200


@app.route('/collections/<int:collection_id>/items')
def collection_items(collection_id):
    conn = get_db_connection()
    user = require_user(conn)
    if not user:
        conn.close()
        return jsonify({'error': 'Unauthorized'}), 401
    col = conn.execute('SELECT user_id FROM bookmark_collections WHERE id = ?', (collection_id,)).fetchone()
    if not col or col[0] != user['id']:
        conn.close()
        return jsonify({'error': 'Forbidden'}), 403
    try:
        rows = conn.execute(
            'SELECT ' + _select_posts_cols('p') + '''
            FROM posts p
            JOIN collection_items ci ON ci.post_id = p.id
            WHERE ci.collection_id = ?
            ORDER BY p.id DESC''',
            (collection_id,)
        ).fetchall()
    except sqlite3.OperationalError:
        rows = []
    out = H.build_tweet_list(conn, rows, user['id'])
    for r in out:
        r['saved_by_me'] = True
    conn.close()
    return jsonify(out)


@app.route('/collections/<int:collection_id>/items', methods=['POST'])
def add_collection_item(collection_id):
    data = request.get_json() or {}
    post_id = data.get('post_id')
    conn = get_db_connection()
    user = require_user(conn)
    col = conn.execute('SELECT user_id FROM bookmark_collections WHERE id = ?', (collection_id,)).fetchone()
    if not user or not col or col[0] != user['id'] or not post_id:
        conn.close()
        return jsonify({'error': 'Forbidden'}), 403
    conn.execute('INSERT OR IGNORE INTO collection_items (collection_id, post_id) VALUES (?, ?)', (collection_id, post_id))
    conn.execute('INSERT OR IGNORE INTO saved_tweets (user_id, post_id) VALUES (?, ?)', (user['id'], post_id))
    conn.commit()
    conn.close()
    return jsonify({'message': 'Added'}), 201


@app.route('/collections/<int:collection_id>/items', methods=['DELETE'])
def remove_collection_item(collection_id):
    data = request.get_json() or {}
    post_id = data.get('post_id')
    conn = get_db_connection()
    user = require_user(conn)
    col = conn.execute('SELECT user_id FROM bookmark_collections WHERE id = ?', (collection_id,)).fetchone()
    if not user or not col or col[0] != user['id'] or not post_id:
        conn.close()
        return jsonify({'error': 'Forbidden'}), 403
    conn.execute('DELETE FROM collection_items WHERE collection_id = ? AND post_id = ?', (collection_id, post_id))
    conn.commit()
    conn.close()
    return jsonify({'message': 'Removed'}), 200


@app.route('/rooms', methods=['GET'])
def list_rooms():
    conn = get_db_connection()
    H.expire_rooms(conn)
    rows = conn.execute('''
        SELECT r.id, r.name, r.topic, r.host_id, r.is_live, r.created_at, r.expires_at,
               u.username as host, u.avatar_url as host_avatar,
               (SELECT COUNT(*) FROM room_members rm WHERE rm.room_id = r.id) as member_count
        FROM rooms r
        JOIN users u ON u.id = r.host_id
        WHERE r.is_live = 1
        ORDER BY r.id DESC
    ''').fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@app.route('/rooms', methods=['POST'])
def create_room():
    data = request.get_json() or {}
    name = (data.get('name') or '').strip()
    topic = (data.get('topic') or '').strip()
    hours = int(data.get('hours') or 4)
    if not name:
        return jsonify({'error': 'Name required'}), 400
    conn = get_db_connection()
    user = require_user(conn)
    if not user:
        conn.close()
        return jsonify({'error': 'Unauthorized'}), 401
    cur = conn.execute(
        "INSERT INTO rooms (name, topic, host_id, is_live, created_at, expires_at) "
        "VALUES (?, ?, ?, 1, datetime('now'), datetime('now', '+' || ? || ' hours'))",
        (name, topic, user['id'], hours)
    )
    rid = cur.lastrowid
    conn.execute(
        "INSERT INTO room_members (room_id, user_id, last_seen_at) VALUES (?, ?, datetime('now'))",
        (rid, user['id'])
    )
    conn.commit()
    conn.close()
    return jsonify({'id': rid, 'name': name}), 201


@app.route('/rooms/<int:room_id>')
def get_room(room_id):
    conn = get_db_connection()
    H.expire_rooms(conn)
    row = conn.execute('''
        SELECT r.*, u.username as host, u.avatar_url as host_avatar
        FROM rooms r JOIN users u ON u.id = r.host_id WHERE r.id = ?
    ''', (room_id,)).fetchone()
    if not row:
        conn.close()
        return jsonify({'error': 'Not found'}), 404
    members = conn.execute('''
        SELECT u.id, u.username, u.avatar_url, rm.last_seen_at
        FROM room_members rm JOIN users u ON u.id = rm.user_id
        WHERE rm.room_id = ?
    ''', (room_id,)).fetchall()
    d = dict(row)
    d['members'] = [dict(m) for m in members]
    conn.close()
    return jsonify(d)


@app.route('/rooms/<int:room_id>/join', methods=['POST'])
def join_room(room_id):
    conn = get_db_connection()
    user = require_user(conn)
    room = conn.execute('SELECT host_id, is_live FROM rooms WHERE id = ?', (room_id,)).fetchone()
    if not user or not room or not room['is_live']:
        conn.close()
        return jsonify({'error': 'Cannot join'}), 400
    conn.execute(
        '''INSERT INTO room_members (room_id, user_id, last_seen_at) VALUES (?, ?, datetime('now'))
           ON CONFLICT(room_id, user_id) DO UPDATE SET last_seen_at = datetime('now')''',
        (room_id, user['id'])
    )
    conn.commit()
    conn.close()
    return jsonify({'message': 'Joined'}), 200


@app.route('/rooms/<int:room_id>/leave', methods=['POST'])
def leave_room(room_id):
    conn = get_db_connection()
    user = require_user(conn)
    if user:
        conn.execute('DELETE FROM room_members WHERE room_id = ? AND user_id = ?', (room_id, user['id']))
        conn.commit()
    conn.close()
    return jsonify({'message': 'Left'}), 200


@app.route('/rooms/<int:room_id>/messages')
def room_messages(room_id):
    conn = get_db_connection()
    rows = conn.execute('''
        SELECT m.id, m.content, m.created_at, m.user_id, u.username, u.avatar_url
        FROM room_messages m JOIN users u ON u.id = m.user_id
        WHERE m.room_id = ?
        ORDER BY m.id ASC
        LIMIT 200
    ''', (room_id,)).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@app.route('/rooms/<int:room_id>/messages', methods=['POST'])
def post_room_message(room_id):
    data = request.get_json() or {}
    content = (data.get('content') or '').strip()
    if not content:
        return jsonify({'error': 'Content required'}), 400
    conn = get_db_connection()
    user = require_user(conn)
    room = conn.execute('SELECT is_live, host_id FROM rooms WHERE id = ?', (room_id,)).fetchone()
    if not user or not room or not room['is_live']:
        conn.close()
        return jsonify({'error': 'Cannot post'}), 400
    conn.execute(
        '''INSERT INTO room_members (room_id, user_id, last_seen_at) VALUES (?, ?, datetime('now'))
           ON CONFLICT(room_id, user_id) DO UPDATE SET last_seen_at = datetime('now')''',
        (room_id, user['id'])
    )
    cur = conn.execute(
        "INSERT INTO room_messages (room_id, user_id, content, created_at) VALUES (?, ?, ?, datetime('now'))",
        (room_id, user['id'], content)
    )
    mid = cur.lastrowid
    members = conn.execute(
        'SELECT user_id FROM room_members WHERE room_id = ? AND user_id != ?', (room_id, user['id'])
    ).fetchall()
    for m in members:
        H.create_notification(conn, m[0], user['id'], 'room', room_id=room_id, message='message in room')
    conn.commit()
    H.broadcast_to_all({
        'event': 'room_message',
        'room_id': room_id,
        'id': mid,
        'username': user['username'],
        'content': content,
    })
    conn.close()
    return jsonify({'id': mid}), 201


@app.route('/rooms/<int:room_id>/end', methods=['POST'])
def end_room(room_id):
    conn = get_db_connection()
    user = require_user(conn)
    room = conn.execute('SELECT host_id FROM rooms WHERE id = ?', (room_id,)).fetchone()
    if not user or not room or room[0] != user['id']:
        conn.close()
        return jsonify({'error': 'Forbidden'}), 403
    conn.execute('UPDATE rooms SET is_live = 0 WHERE id = ?', (room_id,))
    conn.commit()
    conn.close()
    return jsonify({'message': 'Ended'}), 200


@app.route('/insights')
def insights():
    conn = get_db_connection()
    user = require_user(conn)
    if not user:
        conn.close()
        return jsonify({'error': 'Unauthorized'}), 401
    uid = user['id']
    try:
        impressions = conn.execute(
            '''SELECT COALESCE(SUM(impression_count), 0) FROM posts
               WHERE user_id = ? AND created_at >= datetime('now', '-7 days')''',
            (uid,)
        ).fetchone()[0]
        likes_received = conn.execute(
            '''SELECT COUNT(*) FROM likes l
               JOIN posts p ON p.id = l.post_id
               WHERE p.user_id = ?''',
            (uid,)
        ).fetchone()[0]
        top = conn.execute(
            'SELECT ' + _select_posts_cols() + ''' FROM posts
                WHERE user_id = ? AND (status = 'published' OR status IS NULL) AND parent_id IS NULL
                ORDER BY COALESCE(impression_count, 0) DESC, id DESC LIMIT 1''',
            (uid,)
        ).fetchone()
        new_followers = conn.execute(
            '''SELECT COUNT(*) FROM followers WHERE followee_id = ?''',
            (uid,)
        ).fetchone()[0]
        post_count = conn.execute(
            '''SELECT COUNT(*) FROM posts WHERE user_id = ? AND parent_id IS NULL
               AND (status = 'published' OR status IS NULL)
               AND created_at >= datetime('now', '-7 days')''',
            (uid,)
        ).fetchone()[0]
    except sqlite3.OperationalError:
        impressions = likes_received = new_followers = post_count = 0
        top = None
    top_post = H.build_tweet_list(conn, [top], uid)[0] if top else None
    conn.close()
    return jsonify({
        'impressions_7d': impressions,
        'likes_received': likes_received,
        'followers': new_followers,
        'posts_7d': post_count,
        'top_post': top_post,
    })


@app.route('/events')
def sse_events():
    conn = get_db_connection()
    user = require_user(conn)
    conn.close()
    if not user:
        return jsonify({'error': 'Unauthorized'}), 401
    username = user['username']

    def generate():
        q = H.subscribe(username)
        try:
            yield 'data: {"event":"connected"}\n\n'
            while True:
                try:
                    msg = q.get(timeout=25)
                    yield f'data: {msg}\n\n'
                except Exception:
                    yield ': ping\n\n'
        finally:
            H.unsubscribe(username, q)

    return Response(
        stream_with_context(generate()),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no',
            'Connection': 'keep-alive',
        }
    )


if __name__ == '__main__':
    #run migrations on boot if needed
    try:
        from migrate_features import main as migrate_main
        migrate_main()
    except Exception as e:
        print('Migration note:', e)
    try:
        from migrate_auth import main as migrate_auth_main
        migrate_auth_main()
    except Exception as e:
        print('Auth migrate note:', e)
    app.run(debug=True, threaded=True)
