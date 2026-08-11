import React, { useState } from 'react';
import Avatar from './Avatar';
import LinkifiedText from './LinkifiedText';
import {API, mediaUrl, apiFetch} from '../api';
import './TweetCard.css';

function formatTime(iso) {
  if (!iso) return '';
  const d=new Date(iso.endsWith('Z') ? iso : iso + 'Z');
  const now=new Date();
  const diffMs=now - d;
  const diffMin=Math.floor(diffMs / 60000);
  if (diffMin < 1) return 'just now';
  if (diffMin < 60) return `${diffMin}m`;
  const diffHr=Math.floor(diffMin / 60);
  if (diffHr < 24) return `${diffHr}h`;
  const diffDay=Math.floor(diffHr / 24);
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
  onHashtag,
  onRepost,
  showToast,
}) {
  const [liked,setLiked]=useState(!!post.liked_by_me);
  const [saved,setSaved]=useState(!!post.saved_by_me);
  const [likeCount,setLikeCount]=useState(post.like_count ?? 0);
  const [repostCount,setRepostCount]=useState(post.repost_count ?? 0);
  const [busy,setBusy]=useState(false);
  const [quoteOpen,setQuoteOpen]=useState(false);
  const [quoteText,setQuoteText]=useState('');

  const handleLike = async (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (!loggedInUser || busy) return;
    setBusy(true);
    const method = liked ? 'DELETE' : 'POST';
    try {
      const res = await apiFetch(`/posts/${post.id}/like`, {
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
      const res = await apiFetch(`/posts/${post.id}/save`, {
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

  const handleRepost = async (e, withQuote = false) => {
    e.preventDefault();
    e.stopPropagation();
    if (!loggedInUser || busy) return;
    if (withQuote) {
      setQuoteOpen(true);
      return;
    }
    setBusy(true);
    try {
      const res = await apiFetch(`/posts/${post.id}/repost`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username: loggedInUser.username }),
      });
      if (res.ok) {
        setRepostCount((c) => c + 1);
        showToast?.('success', 'Reposted.');
        onRepost?.();
      }
    } finally {
      setBusy(false);
    }
  };

  const submitQuote = async (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (!loggedInUser || busy) return;
    setBusy(true);
    try {
      const res = await apiFetch(`/posts/${post.id}/repost`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username: loggedInUser.username, quote: quoteText.trim() }),
      });
      if (res.ok) {
        setRepostCount((c) => c + 1);
        setQuoteOpen(false);
        setQuoteText('');
        showToast?.('success', 'Quote chirped.');
        onRepost?.();
      }
    } finally {
      setBusy(false);
    }
  };

  const handleReport = async (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (!loggedInUser) return;
    const reason = window.prompt('Why are you reporting this post?') || '';
    const res = await apiFetch(`/reports`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username: loggedInUser.username, post_id: post.id, reason }),
    });
    if (res.ok) showToast?.('success', 'Reported. Thanks.');
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
  const isRepost = !!post.repost_of;
  const displayContent = isRepost && post.quote_content ? post.quote_content : post.content;
  const original = post.original;

  return (
    <div
      className="tweet-card tweet-card--with-actions"
      onClick={handleCardClick}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); handleCardClick(); } }}
    >
      {isRepost && !post.quote_content && (
        <div className="tweet-card__repost-label">@{username} reposted</div>
      )}
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
            <button type="button" className="tweet-card__delete" onClick={handleDelete} disabled={busy}>
              Delete
            </button>
          )}
        </div>
      </div>

      {displayContent && (
        <div className="tweet-card__content">
          <LinkifiedText
            text={displayContent}
            onMention={(n) => onGoToProfile?.(n)}
            onHashtag={(t) => onHashtag?.(t)}
          />
        </div>
      )}

      {post.media_url && (
        <img
          className="tweet-card__media"
          src={mediaUrl(post.media_url)}
          alt=""
          onClick={(e) => e.stopPropagation()}
        />
      )}

      {original && (
        <div
          className="tweet-card__embed"
          onClick={(e) => { e.stopPropagation(); onSelectPost?.(original); }}
        >
          <div className="tweet-card__embed-author">@{original.username}</div>
          <div className="tweet-card__embed-content">
            <LinkifiedText
              text={original.content}
              onMention={(n) => onGoToProfile?.(n)}
              onHashtag={(t) => onHashtag?.(t)}
            />
          </div>
          {original.media_url && (
            <img className="tweet-card__media tweet-card__media--sm" src={mediaUrl(original.media_url)} alt="" />
          )}
        </div>
      )}

      {quoteOpen && (
        <form className="tweet-card__quote-form" onClick={(e) => e.stopPropagation()} onSubmit={submitQuote}>
          <textarea
            value={quoteText}
            onChange={(e) => setQuoteText(e.target.value)}
            placeholder="Add a comment..."
            rows={2}
            maxLength={280}
          />
          <div className="tweet-card__quote-actions">
            <button type="button" className="btn btn--secondary btn--sm" onClick={() => setQuoteOpen(false)}>Cancel</button>
            <button type="submit" className="btn btn--primary btn--sm" disabled={busy}>Quote</button>
          </div>
        </form>
      )}

      <div className="tweet-card__actions">
        <button
          type="button"
          className={`tweet-card__action tweet-card__action--like ${liked ? 'tweet-card__action--active' : ''}`}
          onClick={handleLike}
          disabled={!loggedInUser || busy}
        >
          <span className="tweet-card__action-icon">&#9829;</span>
          {likeCount > 0 && <span className="tweet-card__action-count">{likeCount}</span>}
        </button>
        <button type="button" className="tweet-card__action" onClick={handleCardClick}>
          <span className="tweet-card__action-icon">&#128172;</span>
          {commentCount > 0 && <span className="tweet-card__action-count">{commentCount}</span>}
        </button>
        <button
          type="button"
          className="tweet-card__action"
          onClick={(e) => handleRepost(e, false)}
          disabled={!loggedInUser || busy}
          title="Repost"
        >
          <span className="tweet-card__action-icon">↻</span>
          {repostCount > 0 && <span className="tweet-card__action-count">{repostCount}</span>}
        </button>
        <button
          type="button"
          className="tweet-card__action"
          onClick={(e) => handleRepost(e, true)}
          disabled={!loggedInUser || busy}
          title="Quote"
        >
          <span className="tweet-card__action-icon">❝</span>
        </button>
        <button
          type="button"
          className={`tweet-card__action tweet-card__action--save ${saved ? 'tweet-card__action--active' : ''}`}
          onClick={handleSave}
          disabled={!loggedInUser || busy}
        >
          <span className="tweet-card__action-icon">&#128278;</span>
        </button>
        {loggedInUser && loggedInUser.username !== post.username && (
          <button type="button" className="tweet-card__action" onClick={handleReport} title="Report">
            !
          </button>
        )}
      </div>
    </div>
  );
}

export default TweetCard;
