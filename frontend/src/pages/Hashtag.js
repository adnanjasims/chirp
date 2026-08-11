import React, { useEffect, useState } from 'react';
import TweetCard from '../components/TweetCard';
import {apiFetch} from '../api';
import './FeaturePages.css';

function Hashtag({ tag, loggedInUser, onBack, onSelectPost, onGoToProfile, onHashtag, showToast }) {
  const [posts,setPosts]=useState([]);
  const [loading,setLoading]=useState(true);

  useEffect(()=>{
    if (!tag) return;
    setLoading(true);
    const viewer=loggedInUser?.username ? `?viewer=${encodeURIComponent(loggedInUser.username)}` : '';
    apiFetch(`/hashtags/${encodeURIComponent(tag)}${viewer}`)
      .then((r)=>r.json())
      .then((d)=>setPosts(d.posts || []))
      .finally(()=>setLoading(false));
  }, [tag, loggedInUser?.username]);

  return (
    <main className="feature-page">
      <div className="feature-container">
        <div className="feature-header">
          <button type="button" className="btn btn--secondary btn--sm" onClick={onBack}>← Back</button>
          <h1>#{tag}</h1>
        </div>
        {loading && <p className="feed-loading">Loading...</p>}
        {!loading && posts.length === 0 && <p className="feed-empty">No posts with this hashtag.</p>}
        <div className="feed-list">
          {posts.map((p) => (
            <TweetCard
              key={p.id}
              post={p}
              loggedInUser={loggedInUser}
              onSelectPost={onSelectPost}
              onGoToProfile={onGoToProfile}
              onHashtag={onHashtag}
              showToast={showToast}
            />
          ))}
        </div>
      </div>
    </main>
  );
}

export default Hashtag;
