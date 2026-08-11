# Chirp

Twitter-ish social app. React on the front and Flask + SQLite on the back.

Built as a learning project for SQL and front-end development. Includes a ranked feed, notifications, rooms, drafts, moderation.

## Stack

- Frontend: React (Create React App), plain CSS with light/dark themes
- Backend: Python 3, Flask, flask-cors, SQLite (`backend/twitter.db`)
- Media: files land in `backend/uploads/` and get served at `/uploads/...`
- Realtime: Server-Sent Events on `/events?username=`

## What it does

**Accounts**
Signup + login. Passwords are SHA-256 hashed. Session sticks in localStorage (`chirpUser` / `chirpCreds`) so a refresh doesn't kick you out.

**Feed**
Two tabs: For You (scored by recency, likes, replies, who you follow, hashtag overlap) and Following. Compose supports images, drafts, and scheduled posts. Scheduled ones flip to published when the feed is fetched and the time is due.

**Posts**
Likes, saves, replies, delete your own. Repost or quote. `@mentions` and `#hashtags` get parsed, linked, and searchable. Trending hashtags show up on the home feed.

**Social**
Follow/unfollow, profiles with tweets/likes/saved/followers/following, privacy knobs (who can see tweets, followers, following, likes).

**Notifications**
Likes, replies, follows, mentions, reposts, room pings. Unread badge in the nav. Live toasts when you're connected to SSE.

**Rooms**
Short-lived text rooms. Create one, jump in, chat. Host can end it. Rooms expire after a few hours.

**Moderation** Mute people, block people, mute words, report a post. Blocked/muted posts gets filtered out of feeds.

**Bookmarks**
Saves can live in collections (default "Saved" plus whatever you create).

**Insights**
Rough "your week" view: impressions, likes received, posts, followers, top post.

**Live bits**
SSE for feed bumps + notifications. Typing indicator in the reply modal.

## Project layout

```
twitterfullstack/
  backend/
    main.py              # Flask app + routes
    helpers.py           # feed scoring, notifs, SSE hub, filters
    migrate_*.py         # schema migrations
    seed_dummy_data.py
    uploads/             # uploaded images (gitignored)
    twitter.db
  frontend/
    src/
      App.js             # view state machine (no react-router)
      Navbar.js
      api.js             # API base URL
      pages/             # Feed, Profile, Settings, Rooms, etc
      components/        # TweetCard, TweetModal, ...
  README.md
```

## Run it locally

You need two terminals.

### 1) Backend

```bash
cd backend
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

# first time only (or after a wipe)
python3 init_db.py
python3 migrate_db.py
python3 migrate_likes_saves_privacy.py
python3 migrate_comments.py
python3 migrate_features.py

# optional demo users/tweets (password for demos: demo123)
python3 seed_dummy_data.py

python3 main.py                 # http://127.0.0.1:5000
```

`main.py` will try to run `migrate_features.py` on boot too

### 2) Frontend

```bash
cd frontend
npm install
npm start                       # http://localhost:3000
```

Frontend talks to `http://127.0.0.1:5000`. CORS is open for local use.

## Seeding / reset

```bash
cd backend
source venv/bin/activate
python3 reset_and_seed.py
# if columns look missing after a hard reset, re-run the migrate_*.py scripts
python3 migrate_comments.py
python3 migrate_features.py
```

Then restart `python3 main.py`.

### Auth + media


|                       |                                    |
| --------------------- | ---------------------------------- |
| `POST /signup`        | Create account                     |
| `POST /login`         | Log in                             |
| `POST /upload`        | Multipart image, returns `{ url }` |
| `GET /uploads/<file>` | Serve an upload                    |


### Posts + feed


|                                             |                                                                            |
| ------------------------------------------- | -------------------------------------------------------------------------- |
| `GET /posts?feed=for_you|following&viewer=` | Home feed                                                                  |
| `POST /posts`                               | Create (content, username, parent_id?, media_url?, status?, scheduled_at?) |
| `PUT /posts/<id>`                           | Edit / publish a draft                                                     |
| `GET /posts/<id>`                           | One post                                                                   |
| `DELETE /posts/<id>`                        | Delete yours                                                               |
| `GET /posts/<id>/comments`                  | Replies                                                                    |
| `POST /posts/<id>/repost`                   | Repost or quote (`quote`)                                                  |
| `POST/GET /posts/<id>/typing`               | Typing ping                                                                |
| `POST/DELETE /posts/<id>/like`              | Like / unlike                                                              |
| `POST/DELETE /posts/<id>/save`              | Save / unsave                                                              |
| `GET /drafts?username=`                     | Drafts + scheduled                                                         |


### Search + tags


|                          |                 |
| ------------------------ | --------------- |
| `GET /search/tweets?q=`  | Search posts    |
| `GET /search/users?q=`   | Search people   |
| `GET /hashtags/trending` | Hot tags        |
| `GET /hashtags/<tag>`    | Posts for a tag |


### People + privacy


|                                        |                    |
| -------------------------------------- | ------------------ |
| `GET/PUT /profile/<username>`          | Profile            |
| `GET /profile/<username>/tweets`       | Their tweets       |
| `GET /profile/<username>/likes`        | Likes              |
| `GET /profile/<username>/saved`        | Saves (owner only) |
| `GET /profile/<username>/followers`    | Followers          |
| `GET /profile/<username>/following`    | Following          |
| `GET/PUT /profile/<username>/settings` | Privacy settings   |
| `POST/DELETE /follow`                  | Follow / unfollow  |
| `GET /follow/check`                    | Are they following |


### Notifications + moderation


|                                |                      |
| ------------------------------ | -------------------- |
| `GET /notifications?username=` | Inbox + unread count |
| `POST /notifications/read`     | Mark read            |
| `POST/DELETE /block`           | Block / unblock      |
| `GET /block/list`              | Blocked list         |
| `POST/DELETE /mute`            | Mute / unmute        |
| `GET /mute/list`               | Muted list           |
| `GET/POST/DELETE /muted-words` | Muted words          |
| `POST /reports`                | Report a post        |


### Collections + rooms + extras


|                                           |                                    |
| ----------------------------------------- | ---------------------------------- |
| `GET/POST /collections`                   | List / create                      |
| `DELETE /collections/<id>`                | Delete (not the default Saved one) |
| `GET/POST/DELETE /collections/<id>/items` | Items in a collection              |
| `GET/POST /rooms`                         | List / create live rooms           |
| `GET /rooms/<id>`                         | Room + members                     |
| `POST /rooms/<id>/join` `leave` `end`     | Membership                         |
| `GET/POST /rooms/<id>/messages`           | Chat                               |
| `GET /insights?username=`                 | Your week stats                    |
| `GET /events?username=`                   | SSE stream                         |


## Notes

- Frontend can still be static-hosted later; just point `frontend/src/api.js` at wherever the API lives.
- If feed looks empty after a reset, you probably need migrations + seed again.

With the backend running:

```bash
curl -s -X POST http://127.0.0.1:5000/signup \
  -H 'Content-Type: application/json' \
  -d '{"username":"smoke","password":"demo123"}'

curl -s -X POST http://127.0.0.1:5000/posts \
  -H 'Content-Type: application/json' \
  -d '{"username":"smoke","content":"hello #chirp"}'

curl -s 'http://127.0.0.1:5000/posts?feed=for_you&viewer=smoke' | head
```

Then open `http://localhost:3000`, log in, and poke around: For You tab, Alerts, Rooms, Drafts, Saved, Insights.