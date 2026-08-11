import React, { useEffect, useState } from 'react';
import TweetCard from '../components/TweetCard';
import {apiFetch} from '../api';
import './FeaturePages.css';

function Collections({ loggedInUser, onSelectPost, onGoToProfile, onHashtag, showToast }) {
  const [collections,setCollections]=useState([]);
  const [active,setActive]=useState(null);
  const [posts,setPosts]=useState([]);
  const [newName,setNewName]=useState('');

  const loadCollections=async ()=>{
    const res=await apiFetch('/collections');
    const data=await res.json();
    setCollections(Array.isArray(data) ? data : []);
    if (!active && data?.[0]) setActive(data[0].id);
  };

  const loadItems=async (cid)=>{
    if (!cid) return;
    const res=await apiFetch(`/collections/${cid}/items`);
    setPosts(await res.json());
  };

  useEffect(()=>{ loadCollections(); }, [loggedInUser?.username]);
  useEffect(()=>{ loadItems(active); }, [active]);

  const create=async (e)=>{
    e.preventDefault();
    if (!newName.trim()) return;
    const res=await apiFetch(`/collections`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name: newName.trim() }),
    });
    const data=await res.json();
    if (res.ok) {
      setNewName('');
      await loadCollections();
      setActive(data.id);
    }
  };

  const removeCollection=async (cid)=>{
    if (!window.confirm('Delete this collection?')) return;
    await apiFetch(`/collections/${cid}`, {
      method: 'DELETE',
      headers: { 'Content-Type': 'application/json' },
      body: '{}',
    });
    setActive(null);
    loadCollections();
  };

  return (
    <main className="feature-page">
      <div className="feature-container">
        <h1>Bookmark collections</h1>
        <form className="feature-form" onSubmit={create}>
          <input value={newName} onChange={(e) => setNewName(e.target.value)} placeholder="New collection name" />
          <button type="submit" className="btn btn--primary">Create</button>
        </form>
        <div className="collection-tabs">
          {collections.map((c) => (
            <button
              key={c.id}
              type="button"
              className={`feed-tab ${active === c.id ? 'feed-tab--active' : ''}`}
              onClick={() => setActive(c.id)}
            >
              {c.name} ({c.item_count})
            </button>
          ))}
        </div>
        {active && collections.find((c) => c.id === active)?.name !== 'Saved' && (
          <button type="button" className="btn btn--secondary btn--sm" onClick={() => removeCollection(active)}>
            Delete collection
          </button>
        )}
        <div className="feed-list" style={{ marginTop: '1rem' }}>
          {posts.length === 0 && <p className="feed-empty">No bookmarks here.</p>}
          {posts.map((p) => (
            <TweetCard
              key={p.id}
              post={p}
              loggedInUser={loggedInUser}
              onSelectPost={onSelectPost}
              onGoToProfile={onGoToProfile}
              onHashtag={onHashtag}
              showToast={showToast}
              onSaveChange={() => loadItems(active)}
            />
          ))}
        </div>
      </div>
    </main>
  );
}

export default Collections;
