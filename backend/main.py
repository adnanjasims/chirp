from flask import Flask, request, jsonify
from flask_cors import CORS
import sqlite3
import os
import hashlib

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

DB_FILE = os.path.join(os.path.dirname(__file__), 'twitter.db')

def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# -- sign up user --
@app.route('/signup', methods=['POST'])
def signup():
    data = request.get_json()
    username = data.get('username', '').strip()
    password = data.get('password', '').strip()
    if not username or not password:
        return jsonify({'error': 'Username and password required'}), 400

    password_hash = hash_password(password)
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
    if user:
        return jsonify({'error': 'Username already exists'}), 409

    conn.execute('INSERT INTO users (username, password) VALUES (?, ?)', (username, password_hash))
    conn.commit()
    user_id = conn.execute('SELECT id FROM users WHERE username = ?', (username,)).fetchone()[0]
    conn.close()
    return jsonify({'message': 'User created', 'user': {'id': user_id, 'username': username}}), 201

# -- log in user --
@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username', '').strip()
    password = data.get('password', '').strip()
    if not username or not password:
        return jsonify({'error': 'Username and password required'}), 400

    password_hash = hash_password(password)
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
    conn.close()
    if user and user['password'] == password_hash:
        return jsonify({
            'message': 'Login successful',
            'user': {'id': user['id'], 'username': user['username']}
        }), 200
    elif user:
        return jsonify({'error': 'Incorrect password'}), 401
    else:
        return jsonify({'error': 'User not found'}), 404

# -- post a tweet (optional: username to attach post to user, parent_id for replies) --
@app.route('/posts', methods=['POST'])
def create_post():
    data = request.get_json()
    content = data.get('content', '')
    username = (data.get('username') or '').strip()
    parent_id = data.get('parent_id')
    if not content:
        return jsonify({'error': 'Post content is required'}), 400
    conn = get_db_connection()
    user_id = None
    if username:
        u = conn.execute('SELECT id FROM users WHERE username = ?', (username,)).fetchone()
        if u:
            user_id = u[0]
    try:
        cur = conn.execute(
            "INSERT INTO posts (content, user_id, parent_id, created_at) VALUES (?, ?, ?, datetime('now'))",
            (content, user_id, parent_id)
        )
    except sqlite3.OperationalError:
        try:
            cur = conn.execute('INSERT INTO posts (content, user_id, parent_id) VALUES (?, ?, ?)', (content, user_id, parent_id))
        except sqlite3.OperationalError:
            cur = conn.execute('INSERT INTO posts (content, user_id) VALUES (?, ?)', (content, user_id))
    conn.commit()
    new_id = cur.lastrowid
    conn.close()
    return jsonify({'message': 'Post created', 'id': new_id}), 201

# -- get all posts (with author info, like_count, liked_by_me, saved_by_me if viewer given) --
@app.route('/posts', methods=['GET'])
def get_posts():
    viewer_username = (request.args.get('viewer') or '').strip()
    conn = get_db_connection()
    try:
        rows = conn.execute('''
            SELECT p.id, p.content, p.user_id, p.created_at, p.parent_id
            FROM posts p
            WHERE p.parent_id IS NULL
            ORDER BY p.id DESC
        ''').fetchall()
    except sqlite3.OperationalError:
        try:
            rows = conn.execute('''
                SELECT p.id, p.content, p.user_id
                FROM posts p
                ORDER BY p.id DESC
            ''').fetchall()
        except sqlite3.OperationalError:
            rows = conn.execute('SELECT id, content FROM posts ORDER BY id DESC').fetchall()
    viewer_id = None
    if viewer_username:
        u = conn.execute('SELECT id FROM users WHERE username = ?', (viewer_username,)).fetchone()
        if u:
            viewer_id = u[0]
    out = _build_tweet_list_full(conn, rows, viewer_id)
    conn.close()
    return jsonify(out)

# -- get single post detail --
@app.route('/posts/<int:post_id>', methods=['GET'])
def get_post_detail(post_id):
    viewer_username = (request.args.get('viewer') or '').strip()
    conn = get_db_connection()
    viewer_id = None
    if viewer_username:
        u = conn.execute('SELECT id FROM users WHERE username = ?', (viewer_username,)).fetchone()
        if u:
            viewer_id = u[0]
    try:
        row = conn.execute(
            'SELECT id, content, user_id, created_at, parent_id FROM posts WHERE id = ?',
            (post_id,)
        ).fetchone()
    except sqlite3.OperationalError:
        row = conn.execute('SELECT id, content, user_id FROM posts WHERE id = ?', (post_id,)).fetchone()
    if not row:
        conn.close()
        return jsonify({'error': 'Post not found'}), 404
    items = _build_tweet_list_full(conn, [row], viewer_id)
    conn.close()
    return jsonify(items[0])

# -- get comments (replies) for a post --
@app.route('/posts/<int:post_id>/comments', methods=['GET'])
def get_post_comments(post_id):
    viewer_username = (request.args.get('viewer') or '').strip()
    conn = get_db_connection()
    viewer_id = None
    if viewer_username:
        u = conn.execute('SELECT id FROM users WHERE username = ?', (viewer_username,)).fetchone()
        if u:
            viewer_id = u[0]
    try:
        rows = conn.execute(
            'SELECT id, content, user_id, created_at, parent_id FROM posts WHERE parent_id = ? ORDER BY id ASC',
            (post_id,)
        ).fetchall()
    except sqlite3.OperationalError:
        rows = []
    out = _build_tweet_list_full(conn, rows, viewer_id)
    conn.close()
    return jsonify(out)

# -- search tweets (with author info) --
@app.route('/search/tweets')
def search_tweets():
    q = request.args.get('q', '')
    conn = get_db_connection()
    try:
        rows = conn.execute(
            "SELECT id, content, user_id FROM posts WHERE content LIKE ? ORDER BY id DESC",
            ('%' + q + '%',)
        ).fetchall()
    except sqlite3.OperationalError:
        rows = conn.execute(
            "SELECT id, content FROM posts WHERE content LIKE ? ORDER BY id DESC",
            ('%' + q + '%',)
        ).fetchall()
    out = []
    for row in rows:
        r = dict(row)
        if r.get('user_id'):
            u = conn.execute(
                'SELECT username, bio, avatar_url FROM users WHERE id = ?',
                (r['user_id'],)
            ).fetchone()
            if u:
                r['username'] = u[0]
                r['bio'] = u[1] or ''
                r['avatar_url'] = u[2] or ''
        else:
            r['username'] = ''
            r['bio'] = ''
            r['avatar_url'] = ''
        out.append(r)
    conn.close()
    return jsonify(out)

# -- search users (with bio, avatar_url) --
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
            "SELECT id, username FROM users WHERE username LIKE ?",
            ('%' + q + '%',)
        ).fetchall()
    out = []
    for row in rows:
        r = dict(row)
        r.setdefault('bio', '')
        r.setdefault('avatar_url', '')
        out.append(r)
    conn.close()
    return jsonify(out)

# -- get profile by username (includes privacy fields for owner) --
@app.route('/profile/<username>')
def get_profile(username):
    conn = get_db_connection()
    try:
        row = conn.execute(
            'SELECT id, username, bio, avatar_url, who_can_see_tweets, who_can_see_followers, who_can_see_following, show_likes_on_profile FROM users WHERE username = ?',
            (username,)
        ).fetchone()
    except sqlite3.OperationalError:
        row = conn.execute(
            'SELECT id, username, bio, avatar_url FROM users WHERE username = ?',
            (username,)
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

# -- follow user --
@app.route('/follow', methods=['POST'])
def follow():
    data = request.get_json()
    follower_id = data.get('follower_id')
    followee_id = data.get('followee_id')
    conn = get_db_connection()
    try:
        conn.execute('INSERT INTO followers (follower_id, followee_id) VALUES (?, ?)', (follower_id, followee_id))
        conn.commit()
        return jsonify({'message': 'Followed'}), 201
    except:
        return jsonify({'error': 'Already following or invalid'}), 400
    finally:
        conn.close()

# -- get followers for a user (legacy) --
@app.route('/followers/<int:user_id>')
def get_followers(user_id):
    conn = get_db_connection()
    rows = conn.execute('''
        SELECT u.id, u.username
        FROM users u
        JOIN followers f ON u.id = f.follower_id
        WHERE f.followee_id = ?
    ''', (user_id,)).fetchall()
    conn.close()
    return jsonify([dict(row) for row in rows])

def _can_see(conn, profile_user_id, viewer_id, setting):
    """Check if viewer can see (tweets/followers/following) for profile. setting = who_can_see_* value."""
    if viewer_id == profile_user_id:
        return True
    if setting == 'public':
        return True
    if setting == 'private':
        return False
    if setting == 'followers':
        row = conn.execute('SELECT 1 FROM followers WHERE follower_id = ? AND followee_id = ?', (viewer_id, profile_user_id)).fetchone()
        return row is not None
    return True

def _build_tweet_list(conn, rows, viewer_id):
    """Build list of tweet dicts with author info, like_count, liked_by_me, saved_by_me."""
    out = []
    for row in rows:
        r = dict(row)
        uid = r.get('user_id')
        if uid:
            u = conn.execute('SELECT username, bio, avatar_url FROM users WHERE id = ?', (uid,)).fetchone()
            if u:
                r['username'] = u[0]
                r['bio'] = u[1] or ''
                r['avatar_url'] = u[2] or ''
        else:
            r['username'] = r.get('username', '')
            r['bio'] = r.get('bio', '')
            r['avatar_url'] = r.get('avatar_url', '')
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
        out.append(r)
    return out

def _build_tweet_list_full(conn, rows, viewer_id):
    """Like _build_tweet_list but also adds created_at, parent_id, comment_count."""
    out = _build_tweet_list(conn, rows, viewer_id)
    for r in out:
        r.setdefault('created_at', None)
        r.setdefault('parent_id', None)
        try:
            cc = conn.execute('SELECT COUNT(*) FROM posts WHERE parent_id = ?', (r['id'],)).fetchone()
            r['comment_count'] = cc[0] if cc else 0
        except sqlite3.OperationalError:
            r['comment_count'] = 0
    return out

# -- get tweets by user id (for profile page; no privacy check, use after profile loaded) --
@app.route('/users/<int:user_id>/tweets')
def get_user_tweets(user_id):
    viewer_username = (request.args.get('viewer') or '').strip()
    conn = get_db_connection()
    viewer_id = None
    if viewer_username:
        u = conn.execute('SELECT id FROM users WHERE username = ?', (viewer_username,)).fetchone()
        if u:
            viewer_id = u[0]
    try:
        rows = conn.execute(
            'SELECT id, content, user_id, created_at, parent_id FROM posts WHERE user_id = ? AND parent_id IS NULL ORDER BY id DESC',
            (int(user_id),)
        ).fetchall()
    except sqlite3.OperationalError:
        try:
            rows = conn.execute(
                'SELECT id, content, user_id FROM posts WHERE user_id = ? ORDER BY id DESC',
                (int(user_id),)
            ).fetchall()
        except sqlite3.OperationalError:
            rows = []
    out = _build_tweet_list_full(conn, rows, viewer_id)
    conn.close()
    return jsonify(out)

# -- get tweets by profile user (respects who_can_see_tweets) --
@app.route('/profile/<username>/tweets')
def get_profile_tweets(username):
    username = (username or '').strip()
    if not username:
        return jsonify({'error': 'Username required'}), 400
    viewer_username = (request.args.get('viewer') or '').strip()
    conn = get_db_connection()
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
    viewer_id = None
    if viewer_username:
        u = conn.execute('SELECT id FROM users WHERE username = ?', (viewer_username,)).fetchone()
        if u:
            viewer_id = u[0]
    if not _can_see(conn, profile_id, viewer_id, who):
        conn.close()
        return jsonify([])
    try:
        rows = conn.execute(
            'SELECT id, content, user_id, created_at, parent_id FROM posts WHERE user_id = ? AND parent_id IS NULL ORDER BY id DESC',
            (profile_id,)
        ).fetchall()
    except sqlite3.OperationalError:
        try:
            rows = conn.execute(
                'SELECT id, content, user_id FROM posts WHERE user_id = ? ORDER BY id DESC',
                (profile_id,)
            ).fetchall()
        except sqlite3.OperationalError:
            rows = []
    out = _build_tweet_list_full(conn, rows, viewer_id)
    conn.close()
    return jsonify(out)

# -- update profile (bio, avatar_url) - actor must be profile owner --
@app.route('/profile/<username>', methods=['PUT'])
def update_profile(username):
    data = request.get_json() or {}
    actor = (data.get('username') or '').strip()
    if actor != username:
        return jsonify({'error': 'Unauthorized'}), 403
    conn = get_db_connection()
    user = conn.execute('SELECT id FROM users WHERE username = ?', (username,)).fetchone()
    if not user:
        conn.close()
        return jsonify({'error': 'User not found'}), 404
    bio = data.get('bio')
    avatar_url = data.get('avatar_url')
    updates = []
    params = []
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

# -- delete own post --
@app.route('/posts/<int:post_id>', methods=['DELETE'])
def delete_post(post_id):
    data = request.get_json() or {}
    username = (data.get('username') or '').strip()
    if not username:
        return jsonify({'error': 'Username required'}), 400
    conn = get_db_connection()
    user = conn.execute('SELECT id FROM users WHERE username = ?', (username,)).fetchone()
    if not user:
        conn.close()
        return jsonify({'error': 'User not found'}), 404
    post = conn.execute('SELECT user_id FROM posts WHERE id = ?', (post_id,)).fetchone()
    if not post or post[0] != user[0]:
        conn.close()
        return jsonify({'error': 'Forbidden'}), 403
    conn.execute('DELETE FROM posts WHERE id = ?', (post_id,))
    conn.execute('DELETE FROM likes WHERE post_id = ?', (post_id,))
    conn.execute('DELETE FROM saved_tweets WHERE post_id = ?', (post_id,))
    conn.commit()
    conn.close()
    return jsonify({'message': 'Post deleted'}), 200

# -- like a post --
@app.route('/posts/<int:post_id>/like', methods=['POST'])
def like_post(post_id):
    data = request.get_json() or {}
    username = (data.get('username') or '').strip()
    if not username:
        return jsonify({'error': 'Username required'}), 400
    conn = get_db_connection()
    user = conn.execute('SELECT id FROM users WHERE username = ?', (username,)).fetchone()
    if not user:
        conn.close()
        return jsonify({'error': 'User not found'}), 404
    try:
        conn.execute('INSERT INTO likes (user_id, post_id) VALUES (?, ?)', (user[0], post_id))
        conn.commit()
        conn.close()
        return jsonify({'message': 'Liked'}), 201
    except sqlite3.IntegrityError:
        conn.close()
        return jsonify({'message': 'Already liked'}), 200

# -- unlike --
@app.route('/posts/<int:post_id>/like', methods=['DELETE'])
def unlike_post(post_id):
    data = request.get_json() or {}
    username = (data.get('username') or '').strip()
    if not username:
        return jsonify({'error': 'Username required'}), 400
    conn = get_db_connection()
    user = conn.execute('SELECT id FROM users WHERE username = ?', (username,)).fetchone()
    if not user:
        conn.close()
        return jsonify({'error': 'User not found'}), 404
    conn.execute('DELETE FROM likes WHERE user_id = ? AND post_id = ?', (user[0], post_id))
    conn.commit()
    conn.close()
    return jsonify({'message': 'Unliked'}), 200

# -- save a post --
@app.route('/posts/<int:post_id>/save', methods=['POST'])
def save_post(post_id):
    data = request.get_json() or {}
    username = (data.get('username') or '').strip()
    if not username:
        return jsonify({'error': 'Username required'}), 400
    conn = get_db_connection()
    user = conn.execute('SELECT id FROM users WHERE username = ?', (username,)).fetchone()
    if not user:
        conn.close()
        return jsonify({'error': 'User not found'}), 404
    try:
        conn.execute('INSERT INTO saved_tweets (user_id, post_id) VALUES (?, ?)', (user[0], post_id))
        conn.commit()
        conn.close()
        return jsonify({'message': 'Saved'}), 201
    except sqlite3.IntegrityError:
        conn.close()
        return jsonify({'message': 'Already saved'}), 200

# -- unsave --
@app.route('/posts/<int:post_id>/save', methods=['DELETE'])
def unsave_post(post_id):
    data = request.get_json() or {}
    username = (data.get('username') or '').strip()
    if not username:
        return jsonify({'error': 'Username required'}), 400
    conn = get_db_connection()
    user = conn.execute('SELECT id FROM users WHERE username = ?', (username,)).fetchone()
    if not user:
        conn.close()
        return jsonify({'error': 'User not found'}), 404
    conn.execute('DELETE FROM saved_tweets WHERE user_id = ? AND post_id = ?', (user[0], post_id))
    conn.commit()
    conn.close()
    return jsonify({'message': 'Unsaved'}), 200

# -- get liked tweets for profile (respects show_likes_on_profile and who_can_see) --
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
        # Fallback when privacy columns don't exist yet
        user = conn.execute('SELECT id FROM users WHERE username = ?', (username,)).fetchone()
        if not user:
            conn.close()
            return jsonify({'error': 'User not found'}), 404
        profile_id = user[0]
        show_likes = True
        who = 'public'
    viewer_id = None
    if viewer_username:
        u = conn.execute('SELECT id FROM users WHERE username = ?', (viewer_username,)).fetchone()
        if u:
            viewer_id = u[0]
    if profile_id != viewer_id and (not show_likes or not _can_see(conn, profile_id, viewer_id, who)):
        conn.close()
        return jsonify([])
    try:
        rows = conn.execute('''
            SELECT p.id, p.content, p.user_id
            FROM posts p
            JOIN likes l ON l.post_id = p.id
            WHERE l.user_id = ?
            ORDER BY p.id DESC
        ''', (profile_id,)).fetchall()
    except sqlite3.OperationalError:
        conn.close()
        return jsonify([])
    out = []
    for row in rows:
        r = dict(row)
        u = conn.execute('SELECT username, bio, avatar_url FROM users WHERE id = ?', (r['user_id'],)).fetchone()
        if u:
            r['username'] = u[0]
            r['bio'] = u[1] or ''
            r['avatar_url'] = u[2] or ''
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
        out.append(r)
    conn.close()
    return jsonify(out)

# -- get saved tweets (only for own profile) --
@app.route('/profile/<username>/saved')
def get_profile_saved(username):
    viewer_username = (request.args.get('viewer') or '').strip()
    if viewer_username != username:
        return jsonify({'error': 'Forbidden'}), 403
    conn = get_db_connection()
    user = conn.execute('SELECT id FROM users WHERE username = ?', (username,)).fetchone()
    if not user:
        conn.close()
        return jsonify({'error': 'User not found'}), 404
    try:
        rows = conn.execute('''
            SELECT p.id, p.content, p.user_id
            FROM posts p
            JOIN saved_tweets s ON s.post_id = p.id
            WHERE s.user_id = ?
            ORDER BY p.id DESC
        ''', (user[0],)).fetchall()
    except sqlite3.OperationalError:
        conn.close()
        return jsonify([])
    out = []
    for row in rows:
        r = dict(row)
        u = conn.execute('SELECT username, bio, avatar_url FROM users WHERE id = ?', (r['user_id'],)).fetchone()
        if u:
            r['username'] = u[0]
            r['bio'] = u[1] or ''
            r['avatar_url'] = u[2] or ''
        try:
            like_row = conn.execute('SELECT COUNT(*) FROM likes WHERE post_id = ?', (r['id'],)).fetchone()
            r['like_count'] = like_row[0] if like_row else 0
        except sqlite3.OperationalError:
            r['like_count'] = 0
        r['liked_by_me'] = r['saved_by_me'] = True
        out.append(r)
    conn.close()
    return jsonify(out)

# -- get followers for profile (respects who_can_see_followers) --
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
        # Fallback when privacy column is missing
        user = conn.execute('SELECT id FROM users WHERE username = ?', (username,)).fetchone()
        if not user:
            conn.close()
            return jsonify({'error': 'User not found'}), 404
        profile_id = user[0]
        who = 'public'
    viewer_id = None
    if viewer_username:
        u = conn.execute('SELECT id FROM users WHERE username = ?', (viewer_username,)).fetchone()
        if u:
            viewer_id = u[0]
    if not _can_see(conn, profile_id, viewer_id, who):
        conn.close()
        return jsonify([])
    rows = conn.execute('''
        SELECT u.id, u.username, u.bio, u.avatar_url
        FROM users u
        JOIN followers f ON u.id = f.follower_id
        WHERE f.followee_id = ?
    ''', (profile_id,)).fetchall()
    out = []
    for row in rows:
        r = dict(row)
        r.setdefault('bio', '')
        r.setdefault('avatar_url', '')
        out.append(r)
    conn.close()
    return jsonify(out)

# -- get following for profile (respects who_can_see_following) --
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
        # Fallback when privacy column is missing
        user = conn.execute('SELECT id FROM users WHERE username = ?', (username,)).fetchone()
        if not user:
            conn.close()
            return jsonify({'error': 'User not found'}), 404
        profile_id = user[0]
        who = 'public'
    viewer_id = None
    if viewer_username:
        u = conn.execute('SELECT id FROM users WHERE username = ?', (viewer_username,)).fetchone()
        if u:
            viewer_id = u[0]
    if not _can_see(conn, profile_id, viewer_id, who):
        conn.close()
        return jsonify([])
    rows = conn.execute('''
        SELECT u.id, u.username, u.bio, u.avatar_url
        FROM users u
        JOIN followers f ON u.id = f.followee_id
        WHERE f.follower_id = ?
    ''', (profile_id,)).fetchall()
    out = []
    for row in rows:
        r = dict(row)
        r.setdefault('bio', '')
        r.setdefault('avatar_url', '')
        out.append(r)
    conn.close()
    return jsonify(out)

# -- unfollow --
@app.route('/follow', methods=['DELETE'])
def unfollow():
    data = request.get_json() or {}
    follower_id = data.get('follower_id')
    followee_id = data.get('followee_id')
    if follower_id is None or followee_id is None:
        return jsonify({'error': 'follower_id and followee_id required'}), 400
    conn = get_db_connection()
    conn.execute('DELETE FROM followers WHERE follower_id = ? AND followee_id = ?', (follower_id, followee_id))
    conn.commit()
    conn.close()
    return jsonify({'message': 'Unfollowed'}), 200

# -- check if following --
@app.route('/follow/check')
def check_follow():
    follower_id = request.args.get('follower_id', type=int)
    followee_id = request.args.get('followee_id', type=int)
    if follower_id is None or followee_id is None:
        return jsonify({'following': False})
    conn = get_db_connection()
    row = conn.execute('SELECT 1 FROM followers WHERE follower_id = ? AND followee_id = ?', (follower_id, followee_id)).fetchone()
    conn.close()
    return jsonify({'following': row is not None})

# -- get privacy settings (own profile only) --
@app.route('/profile/<username>/settings')
def get_profile_settings(username):
    viewer_username = (request.args.get('viewer') or '').strip()
    if viewer_username != username:
        return jsonify({'error': 'Forbidden'}), 403
    conn = get_db_connection()
    row = conn.execute(
        'SELECT who_can_see_tweets, who_can_see_followers, who_can_see_following, show_likes_on_profile FROM users WHERE username = ?',
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

# -- update privacy settings (own profile only) --
@app.route('/profile/<username>/settings', methods=['PUT'])
def update_profile_settings(username):
    data = request.get_json() or {}
    actor = (data.get('username') or '').strip()
    if actor != username:
        return jsonify({'error': 'Unauthorized'}), 403
    conn = get_db_connection()
    user = conn.execute('SELECT id FROM users WHERE username = ?', (username,)).fetchone()
    if not user:
        conn.close()
        return jsonify({'error': 'User not found'}), 404
    who_tweets = data.get('who_can_see_tweets')
    who_followers = data.get('who_can_see_followers')
    who_following = data.get('who_can_see_following')
    show_likes = data.get('show_likes_on_profile')
    updates = []
    params = []
    if who_tweets in ('public', 'followers', 'private'):
        updates.append('who_can_see_tweets = ?')
        params.append(who_tweets)
    if who_followers in ('public', 'followers', 'private'):
        updates.append('who_can_see_followers = ?')
        params.append(who_followers)
    if who_following in ('public', 'followers', 'private'):
        updates.append('who_can_see_following = ?')
        params.append(who_following)
    if show_likes is not None:
        updates.append('show_likes_on_profile = ?')
        params.append(1 if show_likes else 0)
    if not updates:
        conn.close()
        return jsonify({'message': 'No changes'}), 200
    params.append(username)
    conn.execute('UPDATE users SET ' + ', '.join(updates) + ' WHERE username = ?', params)
    conn.commit()
    conn.close()
    return jsonify({'message': 'Settings updated'}), 200

if __name__ == '__main__':
    app.run(debug=True)