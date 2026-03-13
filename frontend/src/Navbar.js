import React, { useRef, useEffect } from 'react';
import Avatar from './components/Avatar';
import './Navbar.css';

const APP_NAME = 'Chirp';

function Navbar({
  darkMode,
  toggleDarkMode,
  loggedInUser,
  onLogout,
  onGoToLogin,
  onGoToSignup,
  onGoToHome,
  onGoToProfile,
  onGoToSettings,
  searchQuery = '',
  setSearchQuery,
  onSearch,
  showSearch,
  liveSearchTweets = [],
  liveSearchUsers = [],
  onSelectPost,
  onSelectUser,
  onCloseSearchDropdown,
}) {
  const dropdownRef = useRef(null);
  const showDropdown = showSearch && (searchQuery || '').trim() && (liveSearchTweets.length > 0 || liveSearchUsers.length > 0);

  const handleSubmit = (e) => {
    e.preventDefault();
    const q = (searchQuery || '').trim();
    if (q && onSearch) onSearch(q);
  };

  useEffect(() => {
    if (!showDropdown || !onCloseSearchDropdown) return;
    const onDocClick = (e) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target)) {
        onCloseSearchDropdown();
      }
    };
    document.addEventListener('click', onDocClick, true);
    return () => document.removeEventListener('click', onDocClick, true);
  }, [showDropdown, onCloseSearchDropdown]);

  return (
    <nav className="navbar">
      <button type="button" className="navbar__logo" onClick={onGoToHome}>
        {APP_NAME}
      </button>

      {showSearch && (
        <div className="navbar__search-wrap" ref={dropdownRef}>
          <form onSubmit={handleSubmit} className="navbar__search-form">
            <input
              type="search"
              name="search"
              className="navbar__search-input"
              placeholder="Search posts and people…"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              aria-label="Search"
              aria-expanded={showDropdown}
              autoComplete="off"
            />
            <button type="submit" className="btn btn--secondary btn--sm">Search</button>
          </form>

          {showDropdown && (
            <div className="search-dropdown">
              {liveSearchTweets.length > 0 && (
                <div className="search-dropdown__section">
                  <div className="search-dropdown__label">Posts</div>
                  {liveSearchTweets.map((post) => (
                    <button
                      type="button"
                      key={post.id}
                      className="search-dropdown__item"
                      onClick={(e) => { e.stopPropagation(); onSelectPost && onSelectPost(post); }}
                    >
                      <Avatar username={post.username} avatarUrl={post.avatar_url} size="sm" />
                      <div className="search-dropdown__item-content">
                        <span className="search-dropdown__item-meta">@{post.username || 'unknown'}</span>
                        <span className="search-dropdown__item-text">{post.content}</span>
                      </div>
                    </button>
                  ))}
                </div>
              )}
              {liveSearchUsers.length > 0 && (
                <div className="search-dropdown__section">
                  <div className="search-dropdown__label">People</div>
                  {liveSearchUsers.map((user) => (
                    <button
                      type="button"
                      key={user.id}
                      className="search-dropdown__item"
                      onClick={(e) => { e.stopPropagation(); onSelectUser && onSelectUser(user); }}
                    >
                      <Avatar username={user.username} avatarUrl={user.avatar_url} size="sm" />
                      <div className="search-dropdown__item-content">
                        <span className="search-dropdown__item-meta">@{user.username}</span>
                        {user.bio && <span className="search-dropdown__item-bio">{user.bio}</span>}
                      </div>
                    </button>
                  ))}
                </div>
              )}
              <div className="search-dropdown__hint">Press Enter for full results</div>
            </div>
          )}
        </div>
      )}

      <div className="navbar__actions">
        <button
          type="button"
          className="navbar__theme-btn"
          onClick={toggleDarkMode}
          aria-label={darkMode ? 'Switch to light mode' : 'Switch to dark mode'}
        >
          {darkMode ? 'Light' : 'Dark'}
        </button>
        {loggedInUser ? (
          <>
            <button type="button" className="btn btn--secondary btn--sm" onClick={() => onGoToProfile?.(loggedInUser.username)}>
              Profile
            </button>
            <button type="button" className="btn btn--secondary btn--sm" onClick={onGoToSettings}>
              Settings
            </button>
            <button type="button" className="btn btn--secondary btn--sm" onClick={onLogout}>
              Log out
            </button>
          </>
        ) : (
          <>
            <button type="button" className="btn btn--secondary btn--sm" onClick={onGoToLogin}>
              Log in
            </button>
            <button type="button" className="btn btn--primary btn--sm" onClick={onGoToSignup}>
              Sign up
            </button>
          </>
        )}
      </div>
    </nav>
  );
}

export default Navbar;
export { APP_NAME };
