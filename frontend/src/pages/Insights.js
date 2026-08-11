import React, { useEffect, useState } from 'react';
import TweetCard from '../components/TweetCard';
import {API, apiFetch} from '../api';
import './FeaturePages.css';

function Insights({ loggedInUser, onSelectPost, onGoToProfile, onHashtag, showToast }) {
  const [data,setData]=useState(null);

  useEffect(()=>{
    if (!loggedInUser) return;
    apiFetch('/insights')
      .then((r)=>r.json())
      .then(setData)
      .catch(()=>setData(null));
  }, [loggedInUser?.username]);

  if (!data) {
    return (
      <main className="feature-page">
        <div className="feature-container"><p>Loading...</p></div>
      </main>
    );
  }

  return (
    <main className="feature-page">
      <div className="feature-container">
        <h1>Your week</h1>
        <p className="feature-sub">Quick look at how your chirps are doing.</p>
        <div className="insights-grid">
          <div className="insight-stat">
            <span className="insight-stat__num">{data.impressions_7d}</span>
            <span>Impressions</span>
          </div>
          <div className="insight-stat">
            <span className="insight-stat__num">{data.likes_received}</span>
            <span>Likes received</span>
          </div>
          <div className="insight-stat">
            <span className="insight-stat__num">{data.posts_7d}</span>
            <span>Posts (7d)</span>
          </div>
          <div className="insight-stat">
            <span className="insight-stat__num">{data.followers}</span>
            <span>Followers</span>
          </div>
        </div>
        {data.top_post && (
          <section className="feature-card">
            <h2>Top post</h2>
            <TweetCard
              post={data.top_post}
              loggedInUser={loggedInUser}
              onSelectPost={onSelectPost}
              onGoToProfile={onGoToProfile}
              onHashtag={onHashtag}
              showToast={showToast}
            />
          </section>
        )}
      </div>
    </main>
  );
}

export default Insights;
