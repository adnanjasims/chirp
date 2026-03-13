Chirp - fullstack social media app
====================================

A Twitter-style social media clone built with a React frontend and a Flask plus SQLite backend. Designed as a learning project that covers authentication, timelines, social features, comments and privacy controls.

Main features
-------------

1. Accounts and authentication

- Sign up with a username and password.
- Passwords are stored as SHA-256 hashes in SQLite.
- Login and logout endpoints on the backend.
- The frontend persists the session in local storage so you stay signed in across page refreshes.

2. Tweets and timeline

- Post short text updates (up to 280 characters).
- Home feed shows top-level tweets in reverse chronological order.
- Each tweet card shows the author avatar, username, content, timestamp, like count and reply count.
- Like, unlike and save tweets directly from the feed.
- Clicking the author name navigates to their profile.

3. Comments and replies

- Click any tweet to open a detailed modal view.
- The modal shows full tweet info: author (clickable), bio, content, timestamp, like and reply counts, and like/save actions.
- Reply to any tweet from the modal. Replies are stored as posts with a `parent_id` linking them to the parent tweet.
- Each reply shows author (clickable), content and timestamp.
- Reply counts are visible on every tweet card in the feed.

4. Search

- Search tweets by text content.
- Search people by username.
- Live dropdown under the top search bar shows matching posts and users as you type.
- Pressing Enter opens full search results in the feed area.

5. Profiles

- Dedicated profile page per user with avatar, bio and tabbed content.
- Tabs: Tweets, Likes, Saved, Followers, Following.
- Followers and Following tabs show user lists with avatars and bios. Click any user to visit their profile.
- Profile editing for your own account: update bio and avatar URL.
- Privacy settings control who can see your tweets, followers, following and liked tweets.

6. Followers and following

- Follow and unfollow other accounts from their profile page or from search results.
- Backend stores relationships in a followers table keyed by numeric user ids.
- Follower and following counts are shown on profile tab labels.

7. Likes and saved tweets

- Backend tracks likes and saved tweets in separate tables.
- Profile Likes tab shows tweets a user has liked (respects the show-likes privacy setting).
- Profile Saved tab is visible only to the account owner.

Technology stack
----------------

- Frontend
  - React (Create React App).
  - CSS variables with light and dark theme support.
  - Responsive layout with toast notifications, modals and live search.
  - Local state and local storage for session persistence.

- Backend
  - Python 3 and Flask with debug auto-reload.
  - SQLite database (`twitter.db`) in the backend folder.
  - Flask-CORS for local development (`localhost:3000` to `127.0.0.1:5000`).

Running the project
-------------------

1. Backend

```bash
cd backend
python3 -m venv venv
source venv/bin/activate   # or venv\Scripts\activate on Windows
pip install -r requirements.txt

# First time: create schema and run migrations
python3 init_db.py
python3 migrate_db.py
python3 migrate_likes_saves_privacy.py
python3 migrate_comments.py

# Seed demo data
python3 seed_dummy_data.py

# Start the server
python3 main.py    # serves on http://127.0.0.1:5000
```

2. Frontend

```bash
cd frontend
npm install
npm start    # serves on http://localhost:3000
```

Run both servers in separate terminals. The React app talks to the Flask backend at `http://127.0.0.1:5000`.

Seeding and resetting data
--------------------------

- `seed_dummy_data.py` adds several demo users with short bios and a set of human-sounding tweets. All demo accounts use the password `demo123`.
- `reset_and_seed.py` clears users, posts and followers and re-seeds from scratch:

```bash
cd backend
python3 reset_and_seed.py
python3 migrate_comments.py   # re-add columns after reset if needed
```

After resetting, restart `python3 main.py` so the backend picks up the refreshed database.

API overview
------------

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/signup` | Create account |
| POST | `/login` | Log in |
| GET | `/posts` | List top-level tweets (excludes replies) |
| POST | `/posts` | Create a tweet or reply (`parent_id` for replies) |
| GET | `/posts/<id>` | Single tweet detail with comment count |
| DELETE | `/posts/<id>` | Delete own tweet |
| GET | `/posts/<id>/comments` | List replies for a tweet |
| POST | `/posts/<id>/like` | Like a tweet |
| DELETE | `/posts/<id>/like` | Unlike |
| POST | `/posts/<id>/save` | Save a tweet |
| DELETE | `/posts/<id>/save` | Unsave |
| GET | `/search/tweets?q=` | Search tweets |
| GET | `/search/users?q=` | Search users |
| GET | `/profile/<username>` | User profile |
| PUT | `/profile/<username>` | Update bio / avatar |
| GET | `/profile/<username>/tweets` | User tweets (privacy-aware) |
| GET | `/profile/<username>/likes` | Liked tweets |
| GET | `/profile/<username>/saved` | Saved tweets (owner only) |
| GET | `/profile/<username>/followers` | Follower list |
| GET | `/profile/<username>/following` | Following list |
| GET | `/profile/<username>/settings` | Privacy settings (owner only) |
| PUT | `/profile/<username>/settings` | Update privacy settings |
| POST | `/follow` | Follow a user |
| DELETE | `/follow` | Unfollow |
| GET | `/follow/check` | Check if following |

