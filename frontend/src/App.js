import React, { useState, useEffect, useCallback, useRef } from 'react';
import Navbar from './Navbar';
import Landing from './pages/Landing';
import Login from './pages/Login';
import Signup from './pages/Signup';
import Feed from './pages/Feed';
import Profile from './pages/Profile';
import Settings from './pages/Settings';
import TweetModal from './components/TweetModal';
import UserModal from './components/UserModal';
import './App.css';

const API = 'http://127.0.0.1:5000';
const LIVE_SEARCH_DEBOUNCE_MS = 300;
const LIVE_SEARCH_LIMIT = 5;

function App() {
  const [view, setView] = useState('landing'); // 'landing' | 'login' | 'signup' | 'feed' | 'profile' | 'settings'
  const [profileUsername, setProfileUsername] = useState(null);
  const [posts, setPosts] = useState([]);
  const [newPost, setNewPost] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState([]);
  const [userResults, setUserResults] = useState([]);
  const [liveSearchTweets, setLiveSearchTweets] = useState([]);
  const [liveSearchUsers, setLiveSearchUsers] = useState([]);
  const [selectedPost, setSelectedPost] = useState(null);
  const [selectedUser, setSelectedUser] = useState(null);
  const liveSearchRef = useRef(0);
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [loggedInUser, setLoggedInUser] = useState(null);
  const [darkMode, setDarkMode] = useState(false);
  const [postsError, setPostsError] = useState(null);
  const [postsLoading, setPostsLoading] = useState(true);
  const [toasts, setToasts] = useState([]);
  const [authMessage, setAuthMessage] = useState(null);

  const showToast = useCallback((type, text) => {
    const id = Date.now();
    setToasts((prev) => [...prev, { id, type, text }]);
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id));
    }, 4000);
  }, []);

  const fetchPosts = async () => {
    setPostsLoading(true);
    setPostsError(null);
    const viewer = loggedInUser?.username ? `?viewer=${encodeURIComponent(loggedInUser.username)}` : '';
    try {
      const res = await fetch(`${API}/posts${viewer}`);
      if (!res.ok) throw new Error(`Server returned ${res.status}`);
      const data = await res.json();
      setPosts(data);
    } catch (err) {
      setPostsError(err.message || 'Could not load posts. Is the backend running?');
      setPosts([]);
    } finally {
      setPostsLoading(false);
    }
  };

  // Restore session and credentials from localStorage
  useEffect(() => {
    try {
      const storedUser = localStorage.getItem('chirpUser');
      const storedCreds = localStorage.getItem('chirpCreds');
      if (storedUser) {
        const parsed = JSON.parse(storedUser);
        if (parsed && parsed.username) {
          setLoggedInUser(parsed);
          setView('feed');
        }
      }
      if (storedCreds) {
        const creds = JSON.parse(storedCreds);
        if (creds && creds.username) {
          setUsername(creds.username);
          setPassword(creds.password || '');
        }
      }
    } catch {
      // ignore corrupt localStorage
    }
  }, []);

  useEffect(() => {
    if (view === 'feed') fetchPosts();
  }, [view, loggedInUser?.username]);

  // Live search dropdown: debounced fetch as user types
  useEffect(() => {
    const q = (searchQuery || '').trim();
    if (!q) {
      setLiveSearchTweets([]);
      setLiveSearchUsers([]);
      return;
    }
    const id = ++liveSearchRef.current;
    const t = setTimeout(async () => {
      try {
        const [tweetsRes, usersRes] = await Promise.all([
          fetch(`${API}/search/tweets?q=${encodeURIComponent(q)}`),
          fetch(`${API}/search/users?q=${encodeURIComponent(q)}`),
        ]);
        const tweets = await tweetsRes.json();
        const users = await usersRes.json();
        if (id === liveSearchRef.current) {
          setLiveSearchTweets((tweets || []).slice(0, LIVE_SEARCH_LIMIT));
          setLiveSearchUsers((users || []).slice(0, LIVE_SEARCH_LIMIT));
        }
      } catch {
        if (id === liveSearchRef.current) {
          setLiveSearchTweets([]);
          setLiveSearchUsers([]);
        }
      }
    }, LIVE_SEARCH_DEBOUNCE_MS);
    return () => clearTimeout(t);
  }, [searchQuery]);

  const handleSignup = async (user, pass) => {
    setAuthMessage(null);
    let res;
    let data = {};
    try {
      res = await fetch(`${API}/signup`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username: user, password: pass }),
      });
      try {
        data = await res.json();
      } catch {
        data = {};
      }
    } catch {
      setAuthMessage({ type: 'error', text: 'Could not reach the server. Make sure the backend is running.' });
      return;
    }
    if (res.status === 201) {
      const userData = data.user || { username: user };
      const sessionUser = { id: userData.id, username: userData.username || user };
      setLoggedInUser(sessionUser);
      try {
        localStorage.setItem('chirpUser', JSON.stringify(sessionUser));
        localStorage.setItem('chirpCreds', JSON.stringify({ username: user, password: pass }));
      } catch {
        // ignore storage issues
      }
      setView('feed');
      showToast('success', 'Account created. You’re logged in.');
    } else if (res.status === 409) {
      setAuthMessage({ type: 'error', text: 'That username is taken. Try logging in.' });
    } else {
      setAuthMessage({ type: 'error', text: data.error || 'Signup failed.' });
    }
  };

  const handleLogin = async (user, pass) => {
    setAuthMessage(null);
    let res;
    let data = {};
    try {
      res = await fetch(`${API}/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username: user, password: pass }),
      });
      try {
        data = await res.json();
      } catch {
        data = {};
      }
    } catch {
      setAuthMessage({ type: 'error', text: 'Could not reach the server. Make sure the backend is running.' });
      return;
    }
    if (res.status === 200) {
      const userData = data.user || { username: user };
      const sessionUser = { id: userData.id, username: userData.username || user };
      setLoggedInUser(sessionUser);
      try {
        localStorage.setItem('chirpUser', JSON.stringify(sessionUser));
        localStorage.setItem('chirpCreds', JSON.stringify({ username: user, password: pass }));
      } catch {
        // ignore storage issues
      }
      setView('feed');
      showToast('success', 'Logged in.');
    } else {
      setAuthMessage({ type: 'error', text: data.error || 'Login failed.' });
    }
  };

  const handleLogout = () => {
    setLoggedInUser(null);
    setUsername('');
    setPassword('');
    setView('landing');
    showToast('success', 'Logged out.');
    try {
      localStorage.removeItem('chirpUser');
      localStorage.removeItem('chirpCreds');
    } catch {
      // ignore
    }
  };

  const handlePost = async (e) => {
    e.preventDefault();
    if (!newPost.trim() || !loggedInUser) {
      showToast('error', 'You must be logged in to post.');
      return;
    }
    const res = await fetch(`${API}/posts`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ content: newPost, username: loggedInUser.username }),
    });
    const data = await res.json();
    if (res.ok) {
      setNewPost('');
      fetchPosts();
      showToast('success', 'Posted.');
    } else {
      showToast('error', data.error || 'Failed to post.');
    }
  };

  const handleNavbarSearch = async (q) => {
    setSearchQuery(q);
    setLiveSearchTweets([]);
    setLiveSearchUsers([]);
    if (!q.trim()) {
      setSearchResults([]);
      setUserResults([]);
      return;
    }
    try {
      const [tweetsRes, usersRes] = await Promise.all([
        fetch(`${API}/search/tweets?q=${encodeURIComponent(q)}`),
        fetch(`${API}/search/users?q=${encodeURIComponent(q)}`),
      ]);
      const tweets = await tweetsRes.json();
      const users = await usersRes.json();
      setSearchResults(tweets || []);
      setUserResults(users || []);
    } catch {
      setSearchResults([]);
      setUserResults([]);
    }
  };

  const handleClearSearch = () => {
    setSearchQuery('');
    setSearchResults([]);
    setUserResults([]);
    setLiveSearchTweets([]);
    setLiveSearchUsers([]);
  };

  const handleSelectPost = (post) => {
    setLiveSearchTweets([]);
    setLiveSearchUsers([]);
    setSelectedPost(post);
  };

  const handleSelectUser = (user) => {
    setLiveSearchTweets([]);
    setLiveSearchUsers([]);
    setSelectedUser(user);
  };

  const handleGoToProfile = (username) => {
    setProfileUsername(username || loggedInUser?.username);
    setView('profile');
    setSelectedUser(null);
  };

  const handleCloseSearchDropdown = () => {
    setLiveSearchTweets([]);
    setLiveSearchUsers([]);
  };

  const handleFollow = async (targetId) => {
    if (!loggedInUser) {
      showToast('error', 'Log in to follow.');
      return;
    }
    let followerId = loggedInUser.id;
    // Fallback: look up the logged-in user by exact username if id is missing
    if (followerId == null) {
      const meRes = await fetch(`${API}/profile/${encodeURIComponent(loggedInUser.username)}`);
      if (!meRes.ok) {
        showToast('error', 'Could not resolve current user.');
        return;
      }
      const meData = await meRes.json();
      followerId = meData.id;
    }
    if (followerId == null || followerId === targetId) {
      showToast('error', "You can't follow yourself.");
      return;
    }
    const res = await fetch(`${API}/follow`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ follower_id: followerId, followee_id: targetId }),
    });
    const data = await res.json();
    if (res.ok) showToast('success', 'Following.');
    else showToast('error', data.error || 'Could not follow.');
  };

  const toggleDarkMode = () => setDarkMode((d) => !d);

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', darkMode ? 'dark' : 'light');
  }, [darkMode]);

  return (
    <div className="app-shell">
      <Navbar
        darkMode={darkMode}
        toggleDarkMode={toggleDarkMode}
        loggedInUser={loggedInUser}
        onLogout={handleLogout}
        onGoToLogin={() => { setAuthMessage(null); setView('login'); }}
        onGoToSignup={() => { setAuthMessage(null); setView('signup'); }}
        onGoToHome={() => { setProfileUsername(null); setView(loggedInUser ? 'feed' : 'landing'); }}
        onGoToProfile={handleGoToProfile}
        onGoToSettings={() => setView('settings')}
        searchQuery={searchQuery}
        setSearchQuery={setSearchQuery}
        onSearch={handleNavbarSearch}
        showSearch={view === 'feed' || view === 'profile'}
        liveSearchTweets={liveSearchTweets}
        liveSearchUsers={liveSearchUsers}
        onSelectPost={handleSelectPost}
        onSelectUser={handleSelectUser}
        onCloseSearchDropdown={handleCloseSearchDropdown}
      />

      <div className="toast-container">
        {toasts.map((t) => (
          <div key={t.id} className={`toast toast--${t.type}`}>
            {t.text}
          </div>
        ))}
      </div>

      {view === 'landing' && (
        <Landing onLogin={() => setView('login')} onSignup={() => setView('signup')} />
      )}
      {view === 'login' && (
        <Login
          onLogin={handleLogin}
          onSwitchToSignup={() => { setAuthMessage(null); setView('signup'); }}
          message={authMessage}
          setMessage={setAuthMessage}
        />
      )}
      {view === 'signup' && (
        <Signup
          onSignup={handleSignup}
          onSwitchToLogin={() => { setAuthMessage(null); setView('login'); }}
          message={authMessage}
          setMessage={setAuthMessage}
        />
      )}
      {view === 'feed' && (
        <Feed
          loggedInUser={loggedInUser}
          posts={posts}
          postsLoading={postsLoading}
          postsError={postsError}
          newPost={newPost}
          setNewPost={setNewPost}
          onPost={handlePost}
          onRefreshPosts={fetchPosts}
          searchQuery={searchQuery}
          searchResults={searchResults}
          userResults={userResults}
          onClearSearch={handleClearSearch}
          onFollow={handleFollow}
          onGoToProfile={handleGoToProfile}
          onSelectPost={handleSelectPost}
        />
      )}

      {view === 'profile' && (
        <Profile
          profileUsername={profileUsername || loggedInUser?.username}
          loggedInUser={loggedInUser}
          onBack={() => { setProfileUsername(null); setView('feed'); }}
          onGoToProfile={handleGoToProfile}
          onGoToSettings={() => setView('settings')}
          onSelectPost={handleSelectPost}
          showToast={showToast}
        />
      )}

      {view === 'settings' && (
        <Settings
          loggedInUser={loggedInUser}
          onBack={() => setView(loggedInUser ? 'feed' : 'landing')}
          showToast={showToast}
        />
      )}

      {selectedPost && (
        <TweetModal
          post={selectedPost}
          onClose={() => setSelectedPost(null)}
          loggedInUser={loggedInUser}
          onGoToProfile={handleGoToProfile}
          showToast={showToast}
        />
      )}
      {selectedUser && (
        <UserModal
          user={selectedUser}
          onClose={() => setSelectedUser(null)}
          onFollow={handleFollow}
          onGoToProfile={() => handleGoToProfile(selectedUser?.username)}
          loggedInUser={loggedInUser}
        />
      )}
    </div>
  );
}

export default App;
