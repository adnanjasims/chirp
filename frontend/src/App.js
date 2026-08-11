import React, { useState, useEffect, useCallback, useRef } from 'react';
import Navbar from './Navbar';
import Landing from './pages/Landing';
import Login from './pages/Login';
import Signup from './pages/Signup';
import Feed from './pages/Feed';
import Profile from './pages/Profile';
import Settings from './pages/Settings';
import Notifications from './pages/Notifications';
import Rooms from './pages/Rooms';
import Hashtag from './pages/Hashtag';
import Insights from './pages/Insights';
import Drafts from './pages/Drafts';
import Collections from './pages/Collections';
import TweetModal from './components/TweetModal';
import UserModal from './components/UserModal';
import { apiFetch, setToken, setStoredUser, getStoredUser, getToken, clearAuth, eventsUrl } from './api';
import './App.css';
import './pages/FeaturePages.css';

const LIVE_SEARCH_DEBOUNCE_MS=300;
const LIVE_SEARCH_LIMIT=5;
const THEME_KEY='chirpTheme';

function readStoredDarkMode() {
  try {
    const v=localStorage.getItem(THEME_KEY);
    if (v === 'dark') return true;
    if (v === 'light') return false;
  } catch { /* ignore */ }
  return false;
}

function App() {
  const [view,setView]=useState('landing');
  const [profileUsername,setProfileUsername]=useState(null);
  const [hashtag,setHashtag]=useState(null);
  const [roomId,setRoomId]=useState(null);
  const [posts,setPosts]=useState([]);
  const [newPost,setNewPost]=useState('');
  const [feedTab,setFeedTab]=useState('for_you');
  const [trending,setTrending]=useState([]);
  const [searchQuery,setSearchQuery]=useState('');
  const [searchResults,setSearchResults]=useState([]);
  const [userResults,setUserResults]=useState([]);
  const [liveSearchTweets,setLiveSearchTweets]=useState([]);
  const [liveSearchUsers,setLiveSearchUsers]=useState([]);
  const [selectedPost,setSelectedPost]=useState(null);
  const [selectedUser,setSelectedUser]=useState(null);
  const liveSearchRef=useRef(0);
  const [loggedInUser,setLoggedInUser]=useState(null);
  const [darkMode,setDarkMode]=useState(readStoredDarkMode);
  const [postsError,setPostsError]=useState(null);
  const [postsLoading,setPostsLoading]=useState(true);
  const [toasts,setToasts]=useState([]);
  const [authMessage,setAuthMessage]=useState(null);
  const [unreadCount,setUnreadCount]=useState(0);
  const [typingByPost,setTypingByPost]=useState({});

  const showToast=useCallback((type, text)=>{
    const id=Date.now()+Math.random();
    setToasts((prev)=>[...prev, { id, type, text }]);
    setTimeout(()=>{
      setToasts((prev)=>prev.filter((t)=>t.id !== id));
    }, 4000);
  }, []);

  const fetchPosts = useCallback(async () => {
    setPostsLoading(true);
    setPostsError(null);
    const params = new URLSearchParams();
    params.set('feed', feedTab);
    try {
      const res = await apiFetch(`/posts?${params}`);
      if (!res.ok) throw new Error(`Server returned ${res.status}`);
      setPosts(await res.json());
    } catch (err) {
      setPostsError(err.message || 'Could not load posts. Is the backend running?');
      setPosts([]);
    } finally {
      setPostsLoading(false);
    }
  }, [feedTab]);

  const fetchTrending = useCallback(async () => {
    try {
      const res = await apiFetch('/hashtags/trending');
      if (res.ok) setTrending(await res.json());
    } catch { /* ignore */ }
  }, []);

  const fetchUnread = useCallback(async () => {
    if (!loggedInUser?.username || !getToken()) {
      setUnreadCount(0);
      return;
    }
    try {
      const res = await apiFetch('/notifications');
      if (res.ok) {
        const data = await res.json();
        setUnreadCount(data.unread || 0);
      }
    } catch { /* ignore */ }
  }, [loggedInUser?.username]);

  //restore session from token, not stored passwords
  useEffect(() => {
    const boot = async () => {
      try { localStorage.removeItem('chirpCreds'); } catch { /* old insecure key */ }
      const token = getToken();
      const cached = getStoredUser();
      if (!token) {
        clearAuth();
        return;
      }
      try {
        const res = await apiFetch('/me');
        if (!res.ok) {
          clearAuth();
          return;
        }
        const data = await res.json();
        const sessionUser = data.user || cached;
        setStoredUser(sessionUser);
        setLoggedInUser(sessionUser);
        setView('feed');
      } catch {
        if (cached?.username) {
          setLoggedInUser(cached);
          setView('feed');
        }
      }
    };
    boot();
  }, []);

  useEffect(() => {
    if (view === 'feed') {
      fetchPosts();
      fetchTrending();
    }
  }, [view, fetchPosts, fetchTrending]);

  useEffect(() => {
    fetchUnread();
  }, [fetchUnread, view]);

  //sse keeps the feed/notifs warm
  useEffect(() => {
    if (!loggedInUser?.username || !getToken()) return undefined;
    const es = new EventSource(eventsUrl());
    es.onmessage = (ev) => {
      try {
        const data = JSON.parse(ev.data);
        if (data.event === 'notification') {
          setUnreadCount((c) => c + 1);
          showToast('success', data.message || `${data.actor || 'Someone'} · ${data.type}`);
        }
        if (data.event === 'feed' && view === 'feed') {
          fetchPosts();
        }
        if (data.event === 'typing' && data.post_id && data.username) {
          setTypingByPost((prev) => {
            const list = new Set(prev[data.post_id] || []);
            list.add(data.username);
            return { ...prev, [data.post_id]: Array.from(list) };
          });
          setTimeout(() => {
            setTypingByPost((prev) => {
              const list = (prev[data.post_id] || []).filter((u) => u !== data.username);
              return { ...prev, [data.post_id]: list };
            });
          }, 5000);
        }
      } catch { /* ignore */ }
    };
    return () => es.close();
  }, [loggedInUser?.username, view, fetchPosts, showToast]);

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
          apiFetch(`/search/tweets?q=${encodeURIComponent(q)}`),
          apiFetch(`/search/users?q=${encodeURIComponent(q)}`),
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
      res = await apiFetch('/signup', {
        method: 'POST',
        body: JSON.stringify({ username: user, password: pass }),
      });
      try { data = await res.json(); } catch { data = {}; }
    } catch {
      setAuthMessage({ type: 'error', text: 'Could not reach the server. Make sure the backend is running.' });
      return;
    }
    if (res.status === 201) {
      if (!data.token) {
        setAuthMessage({ type: 'error', text: 'Signup worked but no session token came back. Restart the backend.' });
        return;
      }
      const userData = data.user || { username: user };
      const sessionUser = { id: userData.id, username: userData.username || user };
      setToken(data.token);
      setStoredUser(sessionUser);
      setLoggedInUser(sessionUser);
      setView('feed');
      showToast('success', "Account created. You're logged in.");
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
      res = await apiFetch('/login', {
        method: 'POST',
        body: JSON.stringify({ username: user, password: pass }),
      });
      try { data = await res.json(); } catch { data = {}; }
    } catch {
      setAuthMessage({ type: 'error', text: 'Could not reach the server. Make sure the backend is running.' });
      return;
    }
    if (res.status === 200) {
      if (!data.token) {
        setAuthMessage({ type: 'error', text: 'Login worked but no session token came back. Restart the backend.' });
        return;
      }
      const userData = data.user || { username: user };
      const sessionUser = { id: userData.id, username: userData.username || user };
      setToken(data.token);
      setStoredUser(sessionUser);
      setLoggedInUser(sessionUser);
      setView('feed');
      showToast('success', 'Logged in.');
    } else {
      setAuthMessage({ type: 'error', text: data.error || 'Login failed.' });
    }
  };

  const handleLogout = async () => {
    try { await apiFetch('/logout', { method: 'POST', body: '{}' }); } catch { /* ignore */ }
    clearAuth();
    setLoggedInUser(null);
    setView('landing');
    showToast('success', 'Logged out.');
  };

  const handlePost = async (e, extras = {}) => {
    e.preventDefault();
    if ((!newPost.trim() && !extras.media_url) || !loggedInUser) {
      showToast('error', 'You must be logged in to post.');
      return;
    }
    const body = {
      content: newPost,
      ...extras,
    };
    const res = await apiFetch('/posts', {
      method: 'POST',
      body: JSON.stringify(body),
    });
    const data = await res.json();
    if (res.ok) {
      setNewPost('');
      if (extras.status === 'draft' || extras.status === 'scheduled') {
        showToast('success', extras.status === 'draft' ? 'Draft saved.' : 'Scheduled.');
      } else {
        fetchPosts();
        fetchTrending();
        showToast('success', 'Posted.');
      }
    } else {
      showToast('error', data.error || 'Failed to post.');
    }
  };

  const handleSaveDraft = async ({ content, media_url }) => {
    if (!loggedInUser) return;
    const res = await apiFetch('/posts', {
      method: 'POST',
      body: JSON.stringify({
        content: content || '',
        media_url,
        status: 'draft',
      }),
    });
    if (res.ok) {
      setNewPost('');
      showToast('success', 'Draft saved.');
    } else {
      const data = await res.json();
      showToast('error', data.error || 'Could not save draft.');
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
        apiFetch(`/search/tweets?q=${encodeURIComponent(q)}`),
        apiFetch(`/search/users?q=${encodeURIComponent(q)}`),
      ]);
      setSearchResults(await tweetsRes.json() || []);
      setUserResults(await usersRes.json() || []);
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

  const handleGoToProfile = (uname) => {
    setProfileUsername(uname || loggedInUser?.username);
    setView('profile');
    setSelectedUser(null);
  };

  const handleHashtag = (tag) => {
    setHashtag(tag);
    setView('hashtag');
  };

  const handleFollow = async (targetId) => {
    if (!loggedInUser) {
      showToast('error', 'Log in to follow.');
      return;
    }
    if (loggedInUser.id != null && loggedInUser.id === targetId) {
      showToast('error', "You can't follow yourself.");
      return;
    }
    const res = await apiFetch('/follow', {
      method: 'POST',
      body: JSON.stringify({ followee_id: targetId }),
    });
    const data = await res.json();
    if (res.ok) showToast('success', 'Following.');
    else showToast('error', data.error || 'Could not follow.');
  };

  const toggleDarkMode = () => setDarkMode((d) => !d);

  //apply theme to <html> and remember it for next visit
  useEffect(() => {
    const theme = darkMode ? 'dark' : 'light';
    document.documentElement.setAttribute('data-theme', theme);
    try { localStorage.setItem(THEME_KEY, theme); } catch { /* ignore */ }
  }, [darkMode]);

  const showSearch = ['feed', 'profile', 'hashtag', 'notifications', 'rooms', 'insights', 'drafts', 'collections'].includes(view);

  return (
    <div className="app-shell">
      <Navbar
        darkMode={darkMode}
        toggleDarkMode={toggleDarkMode}
        loggedInUser={loggedInUser}
        onLogout={handleLogout}
        onGoToLogin={() => { setAuthMessage(null); setView('login'); }}
        onGoToSignup={() => { setAuthMessage(null); setView('signup'); }}
        onGoToHome={() => { setProfileUsername(null); setRoomId(null); setView(loggedInUser ? 'feed' : 'landing'); }}
        onGoToProfile={handleGoToProfile}
        onGoToSettings={() => setView('settings')}
        onGoToNotifications={() => setView('notifications')}
        onGoToRooms={() => { setRoomId(null); setView('rooms'); }}
        onGoToInsights={() => setView('insights')}
        onGoToDrafts={() => setView('drafts')}
        onGoToCollections={() => setView('collections')}
        unreadCount={unreadCount}
        searchQuery={searchQuery}
        setSearchQuery={setSearchQuery}
        onSearch={handleNavbarSearch}
        showSearch={showSearch}
        liveSearchTweets={liveSearchTweets}
        liveSearchUsers={liveSearchUsers}
        onSelectPost={(p) => { setLiveSearchTweets([]); setLiveSearchUsers([]); setSelectedPost(p); }}
        onSelectUser={(u) => { setLiveSearchTweets([]); setLiveSearchUsers([]); setSelectedUser(u); }}
        onCloseSearchDropdown={() => { setLiveSearchTweets([]); setLiveSearchUsers([]); }}
      />

      <div className="toast-container">
        {toasts.map((t) => (
          <div key={t.id} className={`toast toast--${t.type}`}>{t.text}</div>
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
          onSaveDraft={handleSaveDraft}
          onRefreshPosts={fetchPosts}
          searchQuery={searchQuery}
          searchResults={searchResults}
          userResults={userResults}
          onClearSearch={handleClearSearch}
          onFollow={handleFollow}
          onGoToProfile={handleGoToProfile}
          onSelectPost={setSelectedPost}
          onHashtag={handleHashtag}
          feedTab={feedTab}
          setFeedTab={setFeedTab}
          trending={trending}
          showToast={showToast}
        />
      )}
      {view === 'profile' && (
        <Profile
          profileUsername={profileUsername || loggedInUser?.username}
          loggedInUser={loggedInUser}
          onBack={() => { setProfileUsername(null); setView('feed'); }}
          onGoToProfile={handleGoToProfile}
          onGoToSettings={() => setView('settings')}
          onGoToCollections={() => setView('collections')}
          onSelectPost={setSelectedPost}
          onHashtag={handleHashtag}
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
      {view === 'notifications' && loggedInUser && (
        <Notifications
          loggedInUser={loggedInUser}
          onGoToProfile={handleGoToProfile}
          onSelectPost={setSelectedPost}
          onGoToRoom={(id) => { setRoomId(id); setView('rooms'); }}
          showToast={showToast}
        />
      )}
      {view === 'rooms' && loggedInUser && (
        <Rooms
          loggedInUser={loggedInUser}
          roomId={roomId}
          setRoomId={setRoomId}
          showToast={showToast}
        />
      )}
      {view === 'hashtag' && (
        <Hashtag
          tag={hashtag}
          loggedInUser={loggedInUser}
          onBack={() => setView('feed')}
          onSelectPost={setSelectedPost}
          onGoToProfile={handleGoToProfile}
          onHashtag={handleHashtag}
          showToast={showToast}
        />
      )}
      {view === 'insights' && loggedInUser && (
        <Insights
          loggedInUser={loggedInUser}
          onSelectPost={setSelectedPost}
          onGoToProfile={handleGoToProfile}
          onHashtag={handleHashtag}
          showToast={showToast}
        />
      )}
      {view === 'drafts' && loggedInUser && (
        <Drafts loggedInUser={loggedInUser} showToast={showToast} onPublished={fetchPosts} />
      )}
      {view === 'collections' && loggedInUser && (
        <Collections
          loggedInUser={loggedInUser}
          onSelectPost={setSelectedPost}
          onGoToProfile={handleGoToProfile}
          onHashtag={handleHashtag}
          showToast={showToast}
        />
      )}

      {selectedPost && (
        <TweetModal
          post={selectedPost}
          onClose={() => setSelectedPost(null)}
          loggedInUser={loggedInUser}
          onGoToProfile={handleGoToProfile}
          onHashtag={handleHashtag}
          showToast={showToast}
          typingUsers={typingByPost[selectedPost.id] || []}
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
