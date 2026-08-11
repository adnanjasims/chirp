import React, { useState, useRef } from 'react';
import Avatar from '../components/Avatar';
import TweetCard from '../components/TweetCard';
import {API, mediaUrl, apiFetch} from '../api';
import './Feed.css';

function Feed({
  loggedInUser,
  posts,
  postsLoading,
  postsError,
  newPost,
  setNewPost,
  onPost,
  onSaveDraft,
  onRefreshPosts,
  searchQuery,
  searchResults,
  userResults,
  onClearSearch,
  onFollow,
  onGoToProfile,
  onSelectPost,
  onHashtag,
  feedTab,
  setFeedTab,
  trending=[],
  showToast,
}) {
  const showSearchBlock=(searchQuery||'').trim();
  const [mediaUrlLocal,setMediaUrlLocal]=useState('');
  const [schedule,setSchedule]=useState(false);
  const [scheduledAt,setScheduledAt]=useState('');
  const [uploading,setUploading]=useState(false);
  const fileRef=useRef(null);

  const handleUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    try {
      const fd = new FormData();
      fd.append('file', file);
      const res = await apiFetch(`/upload`, { method: 'POST', body: fd });
      const data = await res.json();
      if (res.ok) {
        setMediaUrlLocal(data.url);
        showToast?.('success', 'Image uploaded.');
      } else {
        showToast?.('error', data.error || 'Upload failed.');
      }
    } finally {
      setUploading(false);
    }
  };

  const submitPost = (e) => {
    e.preventDefault();
    onPost(e, {
      media_url: mediaUrlLocal || undefined,
      status: schedule ? 'scheduled' : 'published',
      scheduled_at: schedule && scheduledAt ? scheduledAt.replace('T', ' ') + ':00' : undefined,
    });
    setMediaUrlLocal('');
    setSchedule(false);
    setScheduledAt('');
  };

  const saveDraft = () => {
    onSaveDraft?.({
      content: newPost,
      media_url: mediaUrlLocal || undefined,
    });
    setMediaUrlLocal('');
  };

  return (
    <main className="feed-page">
      <div className="feed-container">
        {loggedInUser && (
          <section className="feed-card feed-compose">
            <p className="feed-compose__user">@{loggedInUser.username}</p>
            <form onSubmit={submitPost} className="compose-form">
              <textarea
                className="compose-input"
                placeholder="What's happening? Use @mentions and #hashtags"
                value={newPost}
                onChange={(e) => setNewPost(e.target.value)}
                rows={3}
                maxLength={280}
              />
              {mediaUrlLocal && (
                <div className="compose-media-preview">
                  <img src={mediaUrl(mediaUrlLocal)} alt="upload" />
                  <button type="button" className="btn btn--secondary btn--sm" onClick={() => setMediaUrlLocal('')}>Remove</button>
                </div>
              )}
              <div className="compose-extras">
                <input ref={fileRef} type="file" accept="image/*" hidden onChange={handleUpload} />
                <button type="button" className="btn btn--secondary btn--sm" onClick={() => fileRef.current?.click()} disabled={uploading}>
                  {uploading ? 'Uploading...' : 'Image'}
                </button>
                <label className="compose-schedule">
                  <input type="checkbox" checked={schedule} onChange={(e) => setSchedule(e.target.checked)} />
                  Schedule
                </label>
                {schedule && (
                  <input
                    type="datetime-local"
                    value={scheduledAt}
                    onChange={(e) => setScheduledAt(e.target.value)}
                    className="compose-datetime"
                  />
                )}
              </div>
              <div className="compose-actions">
                <button type="button" className="btn btn--secondary" onClick={saveDraft} disabled={!newPost.trim() && !mediaUrlLocal}>
                  Save draft
                </button>
                <button type="submit" className="btn btn--primary" disabled={!newPost.trim() && !mediaUrlLocal}>
                  {schedule ? 'Schedule' : 'Post'}
                </button>
              </div>
            </form>
          </section>
        )}

        {trending.length > 0 && !showSearchBlock && (
          <section className="feed-card feed-trending">
            <h2 className="feed-card__title">Trending</h2>
            <div className="trending-tags">
              {trending.map((t) => (
                <button key={t.tag} type="button" className="trending-tag" onClick={() => onHashtag?.(t.tag)}>
                  #{t.tag} <span className="trending-tag__count">{t.count}</span>
                </button>
              ))}
            </div>
          </section>
        )}

        {showSearchBlock && (
          <section className="feed-card feed-search-results">
            <div className="feed-search-results__header">
              <h2 className="feed-card__title">Search results</h2>
              <button type="button" className="link-btn btn--sm" onClick={onClearSearch}>Clear</button>
            </div>
            <div className="feed-list">
              <h3 className="feed-list__title">Posts</h3>
              {searchResults.length === 0 ? (
                <p className="feed-empty">No posts found.</p>
              ) : (
                searchResults.map((post) => (
                  <TweetCard
                    key={post.id}
                    post={post}
                    loggedInUser={loggedInUser}
                    onSelectPost={onSelectPost}
                    onLikeChange={onRefreshPosts}
                    onSaveChange={onRefreshPosts}
                    onGoToProfile={onGoToProfile}
                    onHashtag={onHashtag}
                    onRepost={onRefreshPosts}
                    showToast={showToast}
                  />
                ))
              )}
            </div>
            <div className="feed-list">
              <h3 className="feed-list__title">People</h3>
              {userResults.length === 0 ? (
                <p className="feed-empty">No people found.</p>
              ) : (
                userResults.map((user) => (
                  <div key={user.id} className="user-row">
                    <button type="button" className="user-row__link" onClick={() => onGoToProfile?.(user.username)}>
                      <Avatar username={user.username} avatarUrl={user.avatar_url} size="md" />
                      <div className="user-row__info">
                        <span className="user-row__name">@{user.username}</span>
                        {user.bio && <p className="user-row__bio">{user.bio}</p>}
                      </div>
                    </button>
                    {loggedInUser && loggedInUser.username !== user.username && (
                      <button type="button" className="btn btn--secondary btn--sm" onClick={() => onFollow(user.id)}>Follow</button>
                    )}
                  </div>
                ))
              )}
            </div>
          </section>
        )}

        <section className="feed-card">
          <div className="feed-tabs">
            <button type="button" className={`feed-tab ${feedTab === 'for_you' ? 'feed-tab--active' : ''}`} onClick={() => setFeedTab('for_you')}>
              For You
            </button>
            <button type="button" className={`feed-tab ${feedTab === 'following' ? 'feed-tab--active' : ''}`} onClick={() => setFeedTab('following')}>
              Following
            </button>
          </div>
          {postsError && <div className="feed-error">{postsError}</div>}
          {postsLoading && !postsError && <p className="feed-loading">Loading...</p>}
          {!postsLoading && !postsError && posts.length === 0 && <p className="feed-empty">No posts yet.</p>}
          {!postsLoading && !postsError && posts.length > 0 && (
            <div className="feed-list">
              {posts.map((post) => (
                <TweetCard
                  key={post.id}
                  post={post}
                  loggedInUser={loggedInUser}
                  onSelectPost={onSelectPost}
                  onGoToProfile={onGoToProfile}
                  onHashtag={onHashtag}
                  onRepost={onRefreshPosts}
                  showToast={showToast}
                />
              ))}
            </div>
          )}
        </section>
      </div>
    </main>
  );
}

export default Feed;
