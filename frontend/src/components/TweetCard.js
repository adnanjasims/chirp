import React, { useState } from 'react';
import Avatar from './Avatar';
import './TweetCard.css';

const API = 'http://127.0.0.1:5000';

function formatTime(iso) {
  if (!iso) return '';
  const d = new Date(iso + 'Z');
  const now = new Date();
  const diffMs = now - d;
  const diffMin = Math.floor(diffMs / 60000);
  if (diffMin < 1) return 'just now';
  if (diffMin < 60) return `${diffMin}m`;
  const diffHr = Math.floor(diffMin / 60);
  if (diffHr < 24) return `${diffHr}h`;
  const diffDay = Math.floor(diffHr / 24);
  if (diffDay < 7) return `${diffDay}d`;
  return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: d.getFullYear() !== now.getFullYear() ? 'numeric' : undefined });
}

function TweetCard({
  post,
  loggedInUser,
  onSelectPost,
  onLikeChange,
  onSaveChange,
  onDelete,
  onGoToProfile,
}) {
  const [liked, setLiked] = useState(!!post.liked_by_me);
  const [saved, setSaved] = useState(!!post.saved_by_me);
  const [likeCount, setLikeCount] = useState(post.like_count ?? 0);
  const [busy, setBusy] = useState(false);

  const handleLike = async (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (!loggedInUser || busy) return;
    setBusy(true);
    const method = liked ? 'DELETE' : 'POST';
    try {
      const res = await fetch(`${API}/posts/${post.id}/like`, {
        method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username: loggedInUser.username }),
      });
      if (res.ok) {
        setLiked(!liked);
        setLikeCount((c) => c + (liked ? -1 : 1));
        onLikeChange?.();
      }
    } finally {
      setBusy(false);
    }
  };

  const handleSave = async (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (!loggedInUser || busy) return;
    setBusy(true);
    const method = saved ? 'DELETE' : 'POST';
    try {
      const res = await fetch(`${API}/posts/${post.id}/save`, {
        method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username: loggedInUser.username }),
      });
      if (res.ok) {
        setSaved(!saved);
        onSaveChange?.();
      }
    } finally {
      setBusy(false);
    }
  };

  const handleDelete = async (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (!onDelete || busy) return;
    if (!window.confirm('Delete this tweet?')) return;
    setBusy(true);
    try {
      await onDelete(post.id);
    } finally {
      setBusy(false);
    }
  };

  const handleAuthorClick = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (onGoToProfile && post.username) onGoToProfile(post.username);
  };

  const handleCardClick = () => {
    if (onSelectPost) onSelectPost(post);
  };

  const username = post.username || 'unknown';
  const canDelete = !!onDelete && loggedInUser && post.username === loggedInUser.username;
  const commentCount = post.comment_count ?? 0;
  const timeStr = formatTime(post.created_at);

  return (
    <div
      className="tweet-card tweet-card--with-actions"
      onClick={handleCardClick}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); handleCardClick(); } }}
    >
      <div className="tweet-card__top">
        <button
          type="button"
          className="tweet-card__author tweet-card__author--clickable"
          onClick={handleAuthorClick}
          aria-label={`Go to @${username} profile`}
        >
          <Avatar username={username} avatarUrl={post.avatar_url} size="sm" />
          <span className="tweet-card__username">@{username}</span>
        </button>
        <div className="tweet-card__top-right">
          {timeStr && <span className="tweet-card__time">{timeStr}</span>}
          {canDelete && (
            <button
              type="button"
              className="tweet-card__delete"
              onClick={handleDelete}
              disabled={busy}
              aria-label="Delete tweet"
            >
              Delete
            </button>
          )}
        </div>
      </div>
      <div className="tweet-card__content">{post.content}</div>
      <div className="tweet-card__actions">
        <button
          type="button"
          className={`tweet-card__action tweet-card__action--like ${liked ? 'tweet-card__action--active' : ''}`}
          onClick={handleLike}
          disabled={!loggedInUser || busy}
          aria-label={liked ? 'Unlike' : 'Like'}
          title={liked ? 'Unlike' : 'Like'}
        >
          <span className="tweet-card__action-icon">&#9829;</span>
          {likeCount > 0 && <span className="tweet-card__action-count">{likeCount}</span>}
        </button>
        <button
          type="button"
          className={`tweet-card__action tweet-card__action--comment`}
          onClick={handleCardClick}
          aria-label="Replies"
          title="Replies"
        >
          <span className="tweet-card__action-icon">&#128172;</span>
          {commentCount > 0 && <span className="tweet-card__action-count">{commentCount}</span>}
        </button>
        <button
          type="button"
          className={`tweet-card__action tweet-card__action--save ${saved ? 'tweet-card__action--active' : ''}`}
          onClick={handleSave}
          disabled={!loggedInUser || busy}
          aria-label={saved ? 'Unsave' : 'Save'}
          title={saved ? 'Unsave' : 'Save tweet'}
        >
          <span className="tweet-card__action-icon">&#128278;</span>
        </button>
      </div>
    </div>
  );
}

export default TweetCard;
