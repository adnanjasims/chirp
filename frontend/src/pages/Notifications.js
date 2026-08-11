import React, { useEffect, useState } from 'react';
import {API, apiFetch} from '../api';
import Avatar from '../components/Avatar';
import './FeaturePages.css';

function Notifications({ loggedInUser, onGoToProfile, onSelectPost, onGoToRoom, showToast }) {
  const [items,setItems]=useState([]);
  const [loading,setLoading]=useState(true);

  const load=async ()=>{
    if (!loggedInUser) return;
    setLoading(true);
    try {
      const res=await apiFetch('/notifications');
      const data=await res.json();
      setItems(data.notifications || []);
    } finally {
      setLoading(false);
    }
  };

  useEffect(()=>{ load(); }, [loggedInUser?.username]);

  const markAllRead=async ()=>{
    await apiFetch(`/notifications/read`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: '{}',
    });
    showToast?.('success', 'Marked all as read.');
    load();
  };

  const label=(n)=>{
    const actor=n.actor ? `@${n.actor}` : 'Someone';
    if (n.type === 'like') return `${actor} liked your chirp`;
    if (n.type === 'reply') return `${actor} replied`;
    if (n.type === 'follow') return `${actor} followed you`;
    if (n.type === 'mention') return `${actor} mentioned you`;
    if (n.type === 'repost') return `${actor} reposted you`;
    if (n.type === 'room') return `${actor} posted in a room`;
    return n.message || `${actor} notified you`;
  };

  return (
    <main className="feature-page">
      <div className="feature-container">
        <div className="feature-header">
          <h1>Notifications</h1>
          <button type="button" className="btn btn--secondary btn--sm" onClick={markAllRead}>Mark all read</button>
        </div>
        {loading && <p className="feed-loading">Loading...</p>}
        {!loading && items.length === 0 && <p className="feed-empty">No notifications yet.</p>}
        <div className="notif-list">
          {items.map((n) => (
            <button
              key={n.id}
              type="button"
              className={`notif-item ${n.read ? '' : 'notif-item--unread'}`}
              onClick={() => {
                if (n.post_id) onSelectPost?.({ id: n.post_id });
                else if (n.room_id) onGoToRoom?.(n.room_id);
                else if (n.actor) onGoToProfile?.(n.actor);
              }}
            >
              <Avatar username={n.actor} avatarUrl={n.actor_avatar} size="sm" />
              <div className="notif-item__body">
                <span>{label(n)}</span>
                {n.created_at && <span className="notif-item__time">{n.created_at}</span>}
              </div>
            </button>
          ))}
        </div>
      </div>
    </main>
  );
}

export default Notifications;
