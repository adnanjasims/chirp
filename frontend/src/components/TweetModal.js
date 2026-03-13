import React, { useState, useEffect, useCallback } from 'react';
import Avatar from './Avatar';
import './TweetModal.css';

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

function TweetModal({ post, onClose, loggedInUser, onGoToProfile, showToast }) {
  const [detail, setDetail] = useState(null);
  const [comments, setComments] = useState([]);
  const [commentText, setCommentText] = useState('');
  const [posting, setPosting] = useState(false);
  const [liked, setLiked] = useState(false);
  const [saved, setSaved] = useState(false);
  const [likeCount, setLikeCount] = useState(0);
  const [busy, setBusy] = useState(false);

  const viewer = loggedInUser?.username || '';

  const fetchDetail = useCallback(async () => {
    if (!post?.id) return;
    try {
      const res = await fetch(`${API}/posts/${post.id}?viewer=${encodeURIComponent(viewer)}`);
      if (!res.ok) return;
      const data = await res.json();
      setDetail(data);
      setLiked(!!data.liked_by_me);
      setSaved(!!data.saved_by_me);
      setLikeCount(data.like_count ?? 0);
    } catch { /* ignore */ }
  }, [post?.id, viewer]);

  const fetchComments = useCallback(async () => {
    if (!post?.id) return;
    try {
      const res = await fetch(`${API}/posts/${post.id}/comments?viewer=${encodeURIComponent(viewer)}`);
      if (!res.ok) return;
      const data = await res.json();
      setComments(Array.isArray(data) ? data : []);
    } catch { /* ignore */ }
  }, [post?.id, viewer]);

  useEffect(() => {
    fetchDetail();
    fetchComments();
  }, [fetchDetail, fetchComments]);

  if (!post) return null;

  const d = detail || post;
  const username = d.username || '';

  const handleAuthorClick = () => {
    if (onGoToProfile && username) {
      onClose();
      onGoToProfile(username);
    }
  };

  const handleLike = async () => {
    if (!loggedInUser || busy) return;
    setBusy(true);
    const method = liked ? 'DELETE' : 'POST';
    try {
      const res = await fetch(`${API}/posts/${d.id}/like`, {
        method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username: loggedInUser.username }),
      });
      if (res.ok) {
        setLiked(!liked);
        setLikeCount((c) => c + (liked ? -1 : 1));
      }
    } finally {
      setBusy(false);
    }
  };

  const handleSave = async () => {
    if (!loggedInUser || busy) return;
    setBusy(true);
    const method = saved ? 'DELETE' : 'POST';
    try {
      const res = await fetch(`${API}/posts/${d.id}/save`, {
        method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username: loggedInUser.username }),
      });
      if (res.ok) setSaved(!saved);
    } finally {
      setBusy(false);
    }
  };

  const handlePostComment = async (e) => {
    e.preventDefault();
    if (!commentText.trim() || !loggedInUser || posting) return;
    setPosting(true);
    try {
      const res = await fetch(`${API}/posts`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          content: commentText.trim(),
          username: loggedInUser.username,
          parent_id: d.id,
        }),
      });
      if (res.ok) {
        setCommentText('');
        fetchComments();
        fetchDetail();
        showToast?.('success', 'Reply posted.');
      }
    } finally {
      setPosting(false);
    }
  };

  const handleCommentAuthorClick = (uname) => {
    if (onGoToProfile && uname) {
      onClose();
      onGoToProfile(uname);
    }
  };

  return (
    <div className="tweet-modal-backdrop" onClick={onClose}>
      <div className="tweet-modal tweet-modal--rich" onClick={(e) => e.stopPropagation()}>
        <button type="button" className="tweet-modal__close" onClick={onClose} aria-label="Close">
          &times;
        </button>

        <div className="tweet-modal__main">
          <button type="button" className="tweet-modal__author tweet-modal__author--clickable" onClick={handleAuthorClick}>
            <Avatar username={username} avatarUrl={d.avatar_url} size="lg" />
            <div className="tweet-modal__author-info">
              <span className="tweet-modal__username">@{username || 'unknown'}</span>
              {d.bio && <p className="tweet-modal__bio">{d.bio}</p>}
            </div>
          </button>

          <div className="tweet-modal__content">{d.content}</div>

          <div className="tweet-modal__meta">
            {d.created_at && <span className="tweet-modal__time">{formatTime(d.created_at)}</span>}
            <span className="tweet-modal__stat">{likeCount} {likeCount === 1 ? 'like' : 'likes'}</span>
            <span className="tweet-modal__stat">{d.comment_count ?? comments.length} {(d.comment_count ?? comments.length) === 1 ? 'reply' : 'replies'}</span>
          </div>

          <div className="tweet-modal__actions">
            <button
              type="button"
              className={`tweet-modal__action ${liked ? 'tweet-modal__action--liked' : ''}`}
              onClick={handleLike}
              disabled={!loggedInUser || busy}
            >
              <span className="tweet-modal__action-icon">&#9829;</span> {liked ? 'Liked' : 'Like'}
            </button>
            <button
              type="button"
              className={`tweet-modal__action ${saved ? 'tweet-modal__action--saved' : ''}`}
              onClick={handleSave}
              disabled={!loggedInUser || busy}
            >
              &#128278; {saved ? 'Saved' : 'Save'}
            </button>
          </div>
        </div>

        <div className="tweet-modal__comments">
          <h3 className="tweet-modal__comments-heading">
            Replies {comments.length > 0 && `(${comments.length})`}
          </h3>

          {loggedInUser && (
            <form className="tweet-modal__comment-form" onSubmit={handlePostComment}>
              <Avatar username={loggedInUser.username} size="sm" />
              <input
                type="text"
                className="tweet-modal__comment-input"
                placeholder="Write a reply..."
                value={commentText}
                onChange={(e) => setCommentText(e.target.value)}
                maxLength={280}
              />
              <button
                type="submit"
                className="btn btn--primary btn--sm"
                disabled={!commentText.trim() || posting}
              >
                {posting ? '...' : 'Reply'}
              </button>
            </form>
          )}

          {comments.length === 0 ? (
            <p className="tweet-modal__no-comments">No replies yet.</p>
          ) : (
            <div className="tweet-modal__comment-list">
              {comments.map((c) => (
                <div key={c.id} className="tweet-modal__comment">
                  <button
                    type="button"
                    className="tweet-modal__comment-author"
                    onClick={() => handleCommentAuthorClick(c.username)}
                  >
                    <Avatar username={c.username} avatarUrl={c.avatar_url} size="sm" />
                    <span className="tweet-modal__comment-username">@{c.username || 'unknown'}</span>
                  </button>
                  <p className="tweet-modal__comment-text">{c.content}</p>
                  {c.created_at && <span className="tweet-modal__comment-time">{formatTime(c.created_at)}</span>}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default TweetModal;
