import React, { useState, useEffect } from 'react';
import './Settings.css';

const API = 'http://127.0.0.1:5000';

function Settings({ loggedInUser, onBack, showToast }) {
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [whoCanSeeTweets, setWhoCanSeeTweets] = useState('public');
  const [whoCanSeeFollowers, setWhoCanSeeFollowers] = useState('public');
  const [whoCanSeeFollowing, setWhoCanSeeFollowing] = useState('public');
  const [showLikesOnProfile, setShowLikesOnProfile] = useState(true);

  useEffect(() => {
    if (!loggedInUser) return;
    let cancelled = false;
    (async () => {
      try {
        const res = await fetch(
          `${API}/profile/${encodeURIComponent(loggedInUser.username)}/settings?viewer=${encodeURIComponent(loggedInUser.username)}`
        );
        if (res.ok) {
          const data = await res.json();
          if (!cancelled) {
            setWhoCanSeeTweets(data.who_can_see_tweets || 'public');
            setWhoCanSeeFollowers(data.who_can_see_followers || 'public');
            setWhoCanSeeFollowing(data.who_can_see_following || 'public');
            setShowLikesOnProfile(data.show_likes_on_profile !== false);
          }
        }
      } catch {
        if (!cancelled) showToast?.('error', 'Could not load settings');
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => { cancelled = true; };
  }, [loggedInUser, showToast]);

  const handleSave = async () => {
    if (!loggedInUser || saving) return;
    setSaving(true);
    try {
      const res = await fetch(
        `${API}/profile/${encodeURIComponent(loggedInUser.username)}/settings`,
        {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            username: loggedInUser.username,
            who_can_see_tweets: whoCanSeeTweets,
            who_can_see_followers: whoCanSeeFollowers,
            who_can_see_following: whoCanSeeFollowing,
            show_likes_on_profile: showLikesOnProfile,
          }),
        }
      );
      if (res.ok) {
        showToast?.('success', 'Settings saved');
      } else {
        const data = await res.json();
        showToast?.('error', data.error || 'Failed to save');
      }
    } finally {
      setSaving(false);
    }
  };

  if (!loggedInUser) {
    return (
      <main className="settings-page">
        <div className="settings-container">
          <p className="settings-message">Log in to change settings.</p>
          <button type="button" className="btn btn--secondary" onClick={onBack}>Back</button>
        </div>
      </main>
    );
  }

  return (
    <main className="settings-page">
      <div className="settings-container">
        <div className="settings-header">
          <button type="button" className="btn btn--secondary btn--sm" onClick={onBack}>
            Back
          </button>
          <h1 className="settings-title">Settings</h1>
        </div>

        {loading ? (
          <p className="settings-loading">Loading…</p>
        ) : (
          <div className="settings-card">
            <h2 className="settings-card__title">Privacy</h2>
            <p className="settings-card__desc">Control who can see your content.</p>

            <div className="settings-field">
              <label className="settings-field__label">Who can see your tweets</label>
              <select
                className="settings-field__select"
                value={whoCanSeeTweets}
                onChange={(e) => setWhoCanSeeTweets(e.target.value)}
              >
                <option value="public">Everyone</option>
                <option value="followers">Only followers</option>
                <option value="private">Only you</option>
              </select>
            </div>

            <div className="settings-field">
              <label className="settings-field__label">Who can see your followers list</label>
              <select
                className="settings-field__select"
                value={whoCanSeeFollowers}
                onChange={(e) => setWhoCanSeeFollowers(e.target.value)}
              >
                <option value="public">Everyone</option>
                <option value="followers">Only followers</option>
                <option value="private">Only you</option>
              </select>
            </div>

            <div className="settings-field">
              <label className="settings-field__label">Who can see who you follow</label>
              <select
                className="settings-field__select"
                value={whoCanSeeFollowing}
                onChange={(e) => setWhoCanSeeFollowing(e.target.value)}
              >
                <option value="public">Everyone</option>
                <option value="followers">Only followers</option>
                <option value="private">Only you</option>
              </select>
            </div>

            <div className="settings-field settings-field--row">
              <label className="settings-field__label settings-field__label--flex">
                <input
                  type="checkbox"
                  checked={showLikesOnProfile}
                  onChange={(e) => setShowLikesOnProfile(e.target.checked)}
                />
                <span>Show liked tweets on my profile</span>
              </label>
              <p className="settings-field__hint">When off, only you can see your likes tab.</p>
            </div>

            <button
              type="button"
              className="btn btn--primary"
              onClick={handleSave}
              disabled={saving}
            >
              {saving ? 'Saving…' : 'Save privacy settings'}
            </button>
          </div>
        )}
      </div>
    </main>
  );
}

export default Settings;
