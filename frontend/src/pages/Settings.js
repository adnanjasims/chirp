import React, { useState, useEffect } from 'react';
import {API, apiFetch} from '../api';
import './Settings.css';
import './FeaturePages.css';

function Settings({ loggedInUser, onBack, showToast }) {
  const [loading,setLoading]=useState(true);
  const [saving,setSaving]=useState(false);
  const [whoCanSeeTweets,setWhoCanSeeTweets]=useState('public');
  const [whoCanSeeFollowers,setWhoCanSeeFollowers]=useState('public');
  const [whoCanSeeFollowing,setWhoCanSeeFollowing]=useState('public');
  const [showLikesOnProfile,setShowLikesOnProfile]=useState(true);
  const [mutedWords,setMutedWords]=useState([]);
  const [newWord,setNewWord]=useState('');
  const [blocked,setBlocked]=useState([]);
  const [muted,setMuted]=useState([]);

  const loadModeration=async ()=>{
    if (!loggedInUser) return;
    const [w, b, m]=await Promise.all([
      apiFetch('/muted-words').then((r)=>r.json()),
      apiFetch('/block/list').then((r)=>r.json()),
      apiFetch('/mute/list').then((r)=>r.json()),
    ]);
    setMutedWords(Array.isArray(w) ? w : []);
    setBlocked(Array.isArray(b) ? b : []);
    setMuted(Array.isArray(m) ? m : []);
  };

  useEffect(() => {
    if (!loggedInUser) return;
    let cancelled = false;
    (async () => {
      try {
        const res = await apiFetch(
          `/profile/${encodeURIComponent(loggedInUser.username)}/settings`
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
        await loadModeration();
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
      const res = await apiFetch(
        `/profile/${encodeURIComponent(loggedInUser.username)}/settings`,
        {
          method: 'PUT',
          body: JSON.stringify({
            who_can_see_tweets: whoCanSeeTweets,
            who_can_see_followers: whoCanSeeFollowers,
            who_can_see_following: whoCanSeeFollowing,
            show_likes_on_profile: showLikesOnProfile,
          }),
        }
      );
      if (res.ok) showToast?.('success', 'Settings saved');
      else {
        const data = await res.json();
        showToast?.('error', data.error || 'Failed to save');
      }
    } finally {
      setSaving(false);
    }
  };

  const addWord = async (e) => {
    e.preventDefault();
    if (!newWord.trim()) return;
    await apiFetch(`/muted-words`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ word: newWord.trim() }),
    });
    setNewWord('');
    loadModeration();
  };

  const removeWord = async (word) => {
    await apiFetch(`/muted-words`, {
      method: 'DELETE',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ word }),
    });
    loadModeration();
  };

  const unblock = async (target_username) => {
    await apiFetch(`/block`, {
      method: 'DELETE',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ target_username }),
    });
    loadModeration();
  };

  const unmute = async (target_username) => {
    await apiFetch(`/mute`, {
      method: 'DELETE',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ target_username }),
    });
    loadModeration();
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
          <button type="button" className="btn btn--secondary btn--sm" onClick={onBack}>Back</button>
          <h1 className="settings-title">Settings</h1>
        </div>

        {loading ? (
          <p className="settings-loading">Loading...</p>
        ) : (
          <>
            <div className="settings-card">
              <h2 className="settings-card__title">Privacy</h2>
              <p className="settings-card__desc">Control who can see your content.</p>

              <div className="settings-field">
                <label className="settings-field__label">Who can see your tweets</label>
                <select className="settings-field__select" value={whoCanSeeTweets} onChange={(e) => setWhoCanSeeTweets(e.target.value)}>
                  <option value="public">Everyone</option>
                  <option value="followers">Only followers</option>
                  <option value="private">Only you</option>
                </select>
              </div>

              <div className="settings-field">
                <label className="settings-field__label">Who can see your followers list</label>
                <select className="settings-field__select" value={whoCanSeeFollowers} onChange={(e) => setWhoCanSeeFollowers(e.target.value)}>
                  <option value="public">Everyone</option>
                  <option value="followers">Only followers</option>
                  <option value="private">Only you</option>
                </select>
              </div>

              <div className="settings-field">
                <label className="settings-field__label">Who can see who you follow</label>
                <select className="settings-field__select" value={whoCanSeeFollowing} onChange={(e) => setWhoCanSeeFollowing(e.target.value)}>
                  <option value="public">Everyone</option>
                  <option value="followers">Only followers</option>
                  <option value="private">Only you</option>
                </select>
              </div>

              <div className="settings-field settings-field--row">
                <label className="settings-field__label settings-field__label--flex">
                  <input type="checkbox" checked={showLikesOnProfile} onChange={(e) => setShowLikesOnProfile(e.target.checked)} />
                  <span>Show liked tweets on my profile</span>
                </label>
              </div>

              <button type="button" className="btn btn--primary" onClick={handleSave} disabled={saving}>
                {saving ? 'Saving...' : 'Save privacy settings'}
              </button>
            </div>

            <div className="settings-card moderation-section">
              <h2 className="settings-card__title">Muted words</h2>
              <form className="feature-form" onSubmit={addWord}>
                <input value={newWord} onChange={(e) => setNewWord(e.target.value)} placeholder="Add a word to hide" />
                <button type="submit" className="btn btn--secondary">Add</button>
              </form>
              <div className="moderation-list">
                {mutedWords.map((w) => (
                  <div key={w} className="moderation-row">
                    <span>{w}</span>
                    <button type="button" className="btn btn--secondary btn--sm" onClick={() => removeWord(w)}>Remove</button>
                  </div>
                ))}
              </div>
            </div>

            <div className="settings-card moderation-section">
              <h2 className="settings-card__title">Blocked accounts</h2>
              <div className="moderation-list">
                {blocked.length === 0 && <p className="feed-empty">None</p>}
                {blocked.map((u) => (
                  <div key={u.id} className="moderation-row">
                    <span>@{u.username}</span>
                    <button type="button" className="btn btn--secondary btn--sm" onClick={() => unblock(u.username)}>Unblock</button>
                  </div>
                ))}
              </div>
            </div>

            <div className="settings-card moderation-section">
              <h2 className="settings-card__title">Muted accounts</h2>
              <div className="moderation-list">
                {muted.length === 0 && <p className="feed-empty">None</p>}
                {muted.map((u) => (
                  <div key={u.id} className="moderation-row">
                    <span>@{u.username}</span>
                    <button type="button" className="btn btn--secondary btn--sm" onClick={() => unmute(u.username)}>Unmute</button>
                  </div>
                ))}
              </div>
            </div>
          </>
        )}
      </div>
    </main>
  );
}

export default Settings;
