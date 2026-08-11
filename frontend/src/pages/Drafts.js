import React, { useEffect, useState } from 'react';
import {API, apiFetch} from '../api';
import './FeaturePages.css';

function Drafts({ loggedInUser, showToast, onPublished }) {
  const [items,setItems]=useState([]);
  const [loading,setLoading]=useState(true);

  const load=async ()=>{
    if (!loggedInUser) return;
    setLoading(true);
    try {
      const res=await apiFetch('/drafts');
      setItems(await res.json());
    } finally {
      setLoading(false);
    }
  };

  useEffect(()=>{ load(); }, [loggedInUser?.username]);

  const publish=async (id)=>{
    const res=await apiFetch(`/posts/${id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username: loggedInUser.username, status: 'published' }),
    });
    if (res.ok) {
      showToast?.('success', 'Published.');
      load();
      onPublished?.();
    }
  };

  const remove=async (id)=>{
    if (!window.confirm('Delete this draft?')) return;
    await apiFetch(`/posts/${id}`, {
      method: 'DELETE',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username: loggedInUser.username }),
    });
    load();
  };

  return (
    <main className="feature-page">
      <div className="feature-container">
        <h1>Drafts & scheduled</h1>
        {loading && <p className="feed-loading">Loading...</p>}
        {!loading && items.length === 0 && <p className="feed-empty">No drafts or scheduled posts.</p>}
        <div className="draft-list">
          {items.map((d) => (
            <div key={d.id} className="draft-item">
              <div className="draft-item__meta">
                <span className="draft-badge">{d.status}</span>
                {d.scheduled_at && <span>at {d.scheduled_at}</span>}
              </div>
              <p>{d.content || '(media only)'}</p>
              <div className="draft-item__actions">
                {d.status !== 'published' && (
                  <button type="button" className="btn btn--primary btn--sm" onClick={() => publish(d.id)}>Publish now</button>
                )}
                <button type="button" className="btn btn--secondary btn--sm" onClick={() => remove(d.id)}>Delete</button>
              </div>
            </div>
          ))}
        </div>
      </div>
    </main>
  );
}

export default Drafts;
