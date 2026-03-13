import React from 'react';
import Avatar from '../components/Avatar';
import TweetCard from '../components/TweetCard';
import './Feed.css';

function Feed({
  loggedInUser,
  posts,
  postsLoading,
  postsError,
  newPost,
  setNewPost,
  onPost,
  onRefreshPosts,
  searchQuery,
  searchResults,
  userResults,
  onClearSearch,
  onFollow,
  onGoToProfile,
  onSelectPost,
}) {
  const showSearchBlock = (searchQuery || '').trim();

  return (
    <main className="feed-page">
      <div className="feed-container">
        {/* Compose */}
        {loggedInUser && (
          <section className="feed-card feed-compose">
            <p className="feed-compose__user">@{loggedInUser.username}</p>
            <form onSubmit={onPost} className="compose-form">
              <textarea
                className="compose-input"
                placeholder="What's happening?"
                value={newPost}
                onChange={(e) => setNewPost(e.target.value)}
                rows={3}
              />
              <button type="submit" className="btn btn--primary">
                Post
              </button>
            </form>
          </section>
        )}

        {/* Search results (from navbar) */}
        {showSearchBlock && (
          <section className="feed-card feed-search-results">
            <div className="feed-search-results__header">
              <h2 className="feed-card__title">Search results</h2>
              <button type="button" className="link-btn btn--sm" onClick={onClearSearch}>
                Clear
              </button>
            </div>
            <div className="feed-list">
              <h3 className="feed-list__title">Posts</h3>
              {searchResults.length === 0 ? (
                <p className="feed-empty">No posts found.</p>
              ) : (
                searchResults.map((post) => (
                  <TweetCard
                    key={post.id}
                    post={{ ...post, like_count: post.like_count ?? 0, liked_by_me: !!post.liked_by_me, saved_by_me: !!post.saved_by_me }}
                    loggedInUser={loggedInUser}
                    onSelectPost={onSelectPost}
                    onLikeChange={onRefreshPosts}
                    onSaveChange={onRefreshPosts}
                    onGoToProfile={onGoToProfile}
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
                    <button
                      type="button"
                      className="user-row__link"
                      onClick={() => onGoToProfile?.(user.username)}
                    >
                      <Avatar username={user.username} avatarUrl={user.avatar_url} size="md" />
                      <div className="user-row__info">
                        <span className="user-row__name">@{user.username}</span>
                        {user.bio && <p className="user-row__bio">{user.bio}</p>}
                      </div>
                    </button>
                    {loggedInUser && loggedInUser.username !== user.username && (
                      <button
                        type="button"
                        className="btn btn--secondary btn--sm"
                        onClick={() => onFollow(user.id)}
                      >
                        Follow
                      </button>
                    )}
                  </div>
                ))
              )}
            </div>
          </section>
        )}

        {/* All posts */}
        <section className="feed-card">
          <h2 className="feed-card__title">All posts</h2>
          {postsError && (
            <div className="feed-error">{postsError}</div>
          )}
          {postsLoading && !postsError && (
            <p className="feed-loading">Loading…</p>
          )}
          {!postsLoading && !postsError && posts.length === 0 && (
            <p className="feed-empty">No posts yet.</p>
          )}
          {!postsLoading && !postsError && posts.length > 0 && (
            <div className="feed-list">
              {posts.map((post) => (
                <TweetCard
                  key={post.id}
                  post={post}
                  loggedInUser={loggedInUser}
                  onSelectPost={onSelectPost}
                  // For smoother UX, keep like/save local and avoid refetch scroll jump
                  onLikeChange={null}
                  onSaveChange={null}
                  onDelete={null}
                  onGoToProfile={onGoToProfile}
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
