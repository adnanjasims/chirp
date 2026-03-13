import React, { useState, useEffect, useCallback } from 'react';
import Avatar from '../components/Avatar';
import TweetCard from '../components/TweetCard';
import './Profile.css';

const API = 'http://127.0.0.1:5000';

function Profile({
  profileUsername,
  loggedInUser,
  onBack,
  onGoToProfile,
  onGoToSettings,
  onSelectPost,
  showToast,
}) {
  const [profile, setProfile] = useState(null);
  const [tweets, setTweets] = useState([]);
  const [likes, setLikes] = useState([]);
  const [saved, setSaved] = useState([]);
  const [followers, setFollowers] = useState([]);
  const [following, setFollowing] = useState([]);
  const [followersLoading, setFollowersLoading] = useState(false);
  const [followingLoading, setFollowingLoading] = useState(false);
  const [followersError, setFollowersError] = useState(null);
  const [followingError, setFollowingError] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [tab, setTab] = useState('tweets');
  const [followingThisUser, setFollowingThisUser] = useState(false);
  const [editMode, setEditMode] = useState(false);
  const [editBio, setEditBio] = useState('');
  const [editAvatarUrl, setEditAvatarUrl] = useState('');
  const [savingProfile, setSavingProfile] = useState(false);
  const [showLikesTab, setShowLikesTab] = useState(true);

  const isOwnProfile = loggedInUser && profileUsername === loggedInUser.username;
  const viewer = loggedInUser ? loggedInUser.username : '';

  const fetchProfile = useCallback(async () => {
    if (!profileUsername) return;
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API}/profile/${encodeURIComponent(profileUsername)}`);
      if (!res.ok) {
        if (res.status === 404) setError('User not found');
        else setError('Could not load profile');
        setProfile(null);
        return;
      }
      const data = await res.json();
      setProfile(data);
      setEditBio(data.bio || '');
      setEditAvatarUrl(data.avatar_url || '');
      setShowLikesTab(!!data.show_likes_on_profile || isOwnProfile);
    } catch {
      setError('Could not load profile');
      setProfile(null);
    } finally {
      setLoading(false);
    }
  }, [profileUsername, isOwnProfile]);

  const fetchTweets = useCallback(async () => {
    if (!profileUsername && !profile?.username) return;
    try {
      const viewerParam = `viewer=${encodeURIComponent(viewer)}`;
      const res = await fetch(`${API}/posts?${viewerParam}`);
      const data = await (res.ok ? res.json() : []);
      const usernameToUse = (profile?.username || profileUsername || '').trim();
      const filtered = Array.isArray(data)
        ? data.filter((p) => p && p.username === usernameToUse)
        : [];
      setTweets(filtered);
    } catch {
      setTweets([]);
    }
  }, [profileUsername, profile, viewer]);

  const fetchLikes = useCallback(async () => {
    if (!profileUsername) return;
    try {
      const res = await fetch(`${API}/profile/${encodeURIComponent(profileUsername)}/likes?viewer=${encodeURIComponent(viewer)}`);
      if (!res.ok) { setLikes([]); return; }
      const data = await res.json();
      setLikes(Array.isArray(data) ? data : []);
    } catch {
      setLikes([]);
    }
  }, [profileUsername, viewer]);

  const fetchSaved = useCallback(async () => {
    if (!profileUsername || !isOwnProfile) return;
    try {
      const res = await fetch(`${API}/profile/${encodeURIComponent(profileUsername)}/saved?viewer=${encodeURIComponent(viewer)}`);
      if (!res.ok) return;
      const data = await res.json();
      setSaved(Array.isArray(data) ? data : []);
    } catch {
      setSaved([]);
    }
  }, [profileUsername, viewer, isOwnProfile]);

  const fetchFollowers = useCallback(async () => {
    const target = (profile?.username || profileUsername || '').trim();
    if (!target) return;
    setFollowersLoading(true);
    setFollowersError(null);
    try {
      const res = await fetch(`${API}/profile/${encodeURIComponent(target)}/followers?viewer=${encodeURIComponent(viewer)}`);
      if (!res.ok) { setFollowers([]); return; }
      const data = await res.json();
      setFollowers(Array.isArray(data) ? data : []);
    } catch {
      setFollowers([]);
      setFollowersError('Could not load followers.');
    } finally {
      setFollowersLoading(false);
    }
  }, [profileUsername, profile, viewer]);

  const fetchFollowing = useCallback(async () => {
    const target = (profile?.username || profileUsername || '').trim();
    if (!target) return;
    setFollowingLoading(true);
    setFollowingError(null);
    try {
      const res = await fetch(`${API}/profile/${encodeURIComponent(target)}/following?viewer=${encodeURIComponent(viewer)}`);
      if (!res.ok) { setFollowing([]); return; }
      const data = await res.json();
      setFollowing(Array.isArray(data) ? data : []);
    } catch {
      setFollowing([]);
      setFollowingError('Could not load following.');
    } finally {
      setFollowingLoading(false);
    }
  }, [profileUsername, profile, viewer]);

  useEffect(() => {
    fetchProfile();
  }, [fetchProfile]);

  useEffect(() => {
    if (!profile) return;
    fetchTweets();
    if (tab === 'likes') fetchLikes();
    if (tab === 'saved' && isOwnProfile) fetchSaved();
    if (tab === 'followers') fetchFollowers();
    if (tab === 'following') fetchFollowing();
  }, [profile, profileUsername, tab, fetchTweets, fetchLikes, fetchSaved, fetchFollowers, fetchFollowing, isOwnProfile]);

  // Check if current user follows this profile
  useEffect(() => {
    if (!profile || !loggedInUser || isOwnProfile) {
      setFollowingThisUser(false);
      return;
    }
    let cancelled = false;
    (async () => {
      try {
        let myId = loggedInUser.id;
        if (myId == null) {
          const meRes = await fetch(`${API}/profile/${encodeURIComponent(loggedInUser.username)}`);
          if (!meRes.ok) return;
          const meData = await meRes.json();
          myId = meData.id;
        }
        if (myId == null || cancelled) return;
        const res = await fetch(`${API}/follow/check?follower_id=${myId}&followee_id=${profile.id}`);
        const data = await res.json();
        if (!cancelled) setFollowingThisUser(!!data.following);
      } catch {
        if (!cancelled) setFollowingThisUser(false);
      }
    })();
    return () => { cancelled = true; };
  }, [profile, loggedInUser, isOwnProfile]);

  const handleFollow = async () => {
    if (!loggedInUser || !profile || isOwnProfile) return;
    let myId = loggedInUser.id;
    if (myId == null) {
      const meRes = await fetch(`${API}/profile/${encodeURIComponent(loggedInUser.username)}`);
      if (!meRes.ok) return;
      const meData = await meRes.json();
      myId = meData.id;
    }
    if (myId == null) return;
    const res = await fetch(`${API}/follow`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ follower_id: myId, followee_id: profile.id }),
    });
    if (res.ok) {
      setFollowingThisUser(true);
      showToast?.('success', 'Following');
      fetchFollowers();
    } else {
      const data = await res.json();
      showToast?.('error', data.error || 'Could not follow');
    }
  };

  const handleUnfollow = async () => {
    if (!loggedInUser || !profile || isOwnProfile) return;
    let myId = loggedInUser.id;
    if (myId == null) {
      const meRes = await fetch(`${API}/profile/${encodeURIComponent(loggedInUser.username)}`);
      if (!meRes.ok) return;
      const meData = await meRes.json();
      myId = meData.id;
    }
    if (myId == null) return;
    const res = await fetch(`${API}/follow`, {
      method: 'DELETE',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ follower_id: myId, followee_id: profile.id }),
    });
    if (res.ok) {
      setFollowingThisUser(false);
      showToast?.('success', 'Unfollowed');
      fetchFollowers();
    }
  };

  const handleSaveProfile = async () => {
    if (!loggedInUser || !isOwnProfile) return;
    setSavingProfile(true);
    try {
      const res = await fetch(`${API}/profile/${encodeURIComponent(profileUsername)}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          username: loggedInUser.username,
          bio: editBio,
          avatar_url: editAvatarUrl || undefined,
        }),
      });
      if (res.ok) {
        setEditMode(false);
        fetchProfile();
        showToast?.('success', 'Profile updated');
      } else {
        const data = await res.json();
        showToast?.('error', data.error || 'Failed to update');
      }
    } finally {
      setSavingProfile(false);
    }
  };

  const handleDeleteTweet = async (postId) => {
    if (!loggedInUser || !isOwnProfile) return;
    const res = await fetch(`${API}/posts/${postId}`, {
      method: 'DELETE',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username: loggedInUser.username }),
    });
    if (res.ok) {
      setTweets((prev) => prev.filter((p) => p.id !== postId));
      showToast?.('success', 'Tweet deleted');
    } else {
      showToast?.('error', 'Could not delete');
    }
  };

  const refreshTweets = () => {
    fetchTweets();
    fetchLikes();
    if (isOwnProfile) fetchSaved();
  };

  if (loading && !profile) {
    return (
      <main className="profile-page">
        <div className="profile-container">
          <p className="profile-loading">Loading profile…</p>
        </div>
      </main>
    );
  }

  if (error || !profile) {
    return (
      <main className="profile-page">
        <div className="profile-container">
          <button type="button" className="btn btn--secondary btn--sm" onClick={onBack}>
            Back
          </button>
          <p className="profile-error">{error || 'User not found'}</p>
        </div>
      </main>
    );
  }

  const list =
    tab === 'tweets' ? tweets :
    tab === 'likes' ? likes :
    tab === 'saved' ? saved :
    tab === 'followers' ? followers :
    tab === 'following' ? following : [];

  const isListUsers = tab === 'followers' || tab === 'following';
  const listLoading = tab === 'followers' ? followersLoading : tab === 'following' ? followingLoading : false;
  const listError = tab === 'followers' ? followersError : tab === 'following' ? followingError : null;

  return (
    <main className="profile-page">
      <div className="profile-container">
        <div className="profile-header-card">
          <button type="button" className="profile-back btn btn--secondary btn--sm" onClick={onBack}>
            Back
          </button>
          <div className="profile-cover" />
          <div className="profile-info">
            <Avatar
              username={profile.username}
              avatarUrl={editMode ? editAvatarUrl : profile.avatar_url}
              size="xl"
            />
            <h1 className="profile-username">@{profile.username}</h1>
            {!editMode ? (
              <>
                {profile.bio && <p className="profile-bio">{profile.bio}</p>}
                {isOwnProfile && (
                  <div className="profile-actions">
                    <button type="button" className="btn btn--secondary btn--sm" onClick={() => setEditMode(true)}>
                      Edit profile
                    </button>
                    <button type="button" className="btn btn--secondary btn--sm" onClick={onGoToSettings}>
                      Settings
                    </button>
                  </div>
                )}
                {!isOwnProfile && loggedInUser && (
                  <div className="profile-actions">
                    {followingThisUser ? (
                      <button type="button" className="btn btn--secondary btn--sm" onClick={handleUnfollow}>
                        Unfollow
                      </button>
                    ) : (
                      <button type="button" className="btn btn--primary btn--sm" onClick={handleFollow}>
                        Follow
                      </button>
                    )}
                  </div>
                )}
              </>
            ) : (
              <div className="profile-edit">
                <label className="profile-edit__label">Bio</label>
                <textarea
                  className="profile-edit__input"
                  value={editBio}
                  onChange={(e) => setEditBio(e.target.value)}
                  rows={3}
                  placeholder="Bio"
                />
                <label className="profile-edit__label">Avatar URL</label>
                <input
                  type="url"
                  className="profile-edit__input"
                  value={editAvatarUrl}
                  onChange={(e) => setEditAvatarUrl(e.target.value)}
                  placeholder="https://..."
                />
                <div className="profile-edit__actions">
                  <button type="button" className="btn btn--secondary btn--sm" onClick={() => setEditMode(false)}>
                    Cancel
                  </button>
                  <button type="button" className="btn btn--primary btn--sm" onClick={handleSaveProfile} disabled={savingProfile}>
                    {savingProfile ? 'Saving…' : 'Save'}
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>

        <div className="profile-tabs">
          <button type="button" className={`profile-tab ${tab === 'tweets' ? 'profile-tab--active' : ''}`} onClick={() => setTab('tweets')}>
            Tweets
          </button>
          {(showLikesTab || isOwnProfile) && (
            <button type="button" className={`profile-tab ${tab === 'likes' ? 'profile-tab--active' : ''}`} onClick={() => setTab('likes')}>
              Likes
            </button>
          )}
          {isOwnProfile && (
            <button type="button" className={`profile-tab ${tab === 'saved' ? 'profile-tab--active' : ''}`} onClick={() => setTab('saved')}>
              Saved
            </button>
          )}
          <button
            type="button"
            className={`profile-tab ${tab === 'followers' ? 'profile-tab--active' : ''}`}
            onClick={() => { setTab('followers'); fetchFollowers(); }}
          >
            Followers {followers.length > 0 ? `(${followers.length})` : ''}
          </button>
          <button
            type="button"
            className={`profile-tab ${tab === 'following' ? 'profile-tab--active' : ''}`}
            onClick={() => { setTab('following'); fetchFollowing(); }}
          >
            Following {following.length > 0 ? `(${following.length})` : ''}
          </button>
        </div>

        <div className="profile-content">
          {isListUsers ? (
            <div className="profile-list profile-list--users">
              {listLoading ? (
                <p className="profile-empty">Loading…</p>
              ) : listError ? (
                <div className="profile-error-box">
                  <p className="profile-error-box__text">{listError}</p>
                  <button
                    type="button"
                    className="btn btn--secondary btn--sm"
                    onClick={() => (tab === 'followers' ? fetchFollowers() : fetchFollowing())}
                  >
                    Retry
                  </button>
                </div>
              ) : list.length === 0 ? (
                <p className="profile-empty">No one here yet.</p>
              ) : (
                list.map((u) => (
                  <button
                    key={u.id}
                    type="button"
                    className="profile-user-row profile-user-row--clickable"
                    onClick={() => onGoToProfile?.(u.username)}
                  >
                    <Avatar username={u.username} avatarUrl={u.avatar_url} size="md" />
                    <div className="profile-user-row__info">
                      <span className="profile-user-row__name">@{u.username}</span>
                      {u.bio && <p className="profile-user-row__bio">{u.bio}</p>}
                    </div>
                  </button>
                ))
              )}
            </div>
          ) : (
            <div className="profile-list profile-list--tweets">
              {list.length === 0 ? (
                <p className="profile-empty">No tweets here.</p>
              ) : (
                list.map((post) => (
                  <TweetCard
                    key={post.id}
                    post={post}
                    loggedInUser={loggedInUser}
                    onSelectPost={onSelectPost}
                    onLikeChange={refreshTweets}
                    onSaveChange={refreshTweets}
                    onDelete={isOwnProfile ? handleDeleteTweet : null}
                    onGoToProfile={onGoToProfile}
                  />
                ))
              )}
            </div>
          )}
        </div>
      </div>
    </main>
  );
}

export default Profile;
