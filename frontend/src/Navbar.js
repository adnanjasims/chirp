import React, { useRef, useEffect, useState } from 'react';
import Avatar from './components/Avatar';
import ChirpMark from './components/ChirpMark';
import './Navbar.css';

const APP_NAME='Chirp';

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
  onGoToNotifications,
  onGoToRooms,
  onGoToInsights,
  onGoToDrafts,
  onGoToCollections,
  unreadCount=0,
  searchQuery='',
  setSearchQuery,
  onSearch,
  showSearch,
  liveSearchTweets=[],
  liveSearchUsers=[],
  onSelectPost,
  onSelectUser,
  onCloseSearchDropdown,
}) {
  const dropdownRef=useRef(null);
  const [searchOpen,setSearchOpen]=useState(false);
  const showDropdown=showSearch && searchOpen && (searchQuery||'').trim() && (liveSearchTweets.length>0||liveSearchUsers.length>0);

  const handleSubmit=(e)=>{
    e.preventDefault();
    const q=(searchQuery||'').trim();
    if(q && onSearch) onSearch(q);
  };

  useEffect(()=>{
    if(!showDropdown || !onCloseSearchDropdown) return;
    const onDocClick=(e)=>{
      if(dropdownRef.current && !dropdownRef.current.contains(e.target)){
        onCloseSearchDropdown();
      }
    };
    document.addEventListener('click',onDocClick,true);
    return ()=>document.removeEventListener('click',onDocClick,true);
  },[showDropdown,onCloseSearchDropdown]);

  //close expanded search when leaving pages that support it
  useEffect(()=>{
    if(!showSearch) setSearchOpen(false);
  },[showSearch]);

  return (
    <nav className="navbar">
      <div className="navbar__inner">
        <button type="button" className="navbar__logo" onClick={onGoToHome}>
          <ChirpMark size={22} className="navbar__logo-mark" />
          <span className="navbar__logo-text">{APP_NAME}</span>
        </button>

        {loggedInUser ? (
          <ul className="navbar__links">
            <li><button type="button" className="navbar__link" onClick={onGoToHome}>Home</button></li>
            <li>
              <button type="button" className="navbar__link" onClick={onGoToNotifications}>
                Alerts
                {unreadCount>0 && <span className="navbar__badge">{unreadCount>99?'99+':unreadCount}</span>}
              </button>
            </li>
            <li><button type="button" className="navbar__link" onClick={onGoToRooms}>Rooms</button></li>
            <li><button type="button" className="navbar__link" onClick={onGoToInsights}>Insights</button></li>
            <li><button type="button" className="navbar__link" onClick={onGoToDrafts}>Drafts</button></li>
            <li><button type="button" className="navbar__link" onClick={onGoToCollections}>Saved</button></li>
            <li className="navbar__links-hide-sm">
              <button type="button" className="navbar__link" onClick={()=>onGoToProfile?.(loggedInUser.username)}>Profile</button>
            </li>
          </ul>
        ) : (
          <ul className="navbar__links">
            <li><button type="button" className="navbar__link" onClick={onGoToHome}>Explore</button></li>
          </ul>
        )}

        <div className="navbar__right">
          {showSearch && (
            <div className={`navbar__search-wrap ${searchOpen?'navbar__search-wrap--open':''}`} ref={dropdownRef}>
              {!searchOpen ? (
                <button
                  type="button"
                  className="navbar__icon-btn"
                  aria-label="Search"
                  onClick={()=>setSearchOpen(true)}
                >
                  <svg width="15" height="15" viewBox="0 0 15 15" fill="none" aria-hidden="true">
                    <circle cx="6.5" cy="6.5" r="5.25" stroke="currentColor" strokeWidth="1.4"/>
                    <path d="M10.5 10.5L13.5 13.5" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round"/>
                  </svg>
                </button>
              ) : (
                <form onSubmit={handleSubmit} className="navbar__search-form">
                  <input
                    type="search"
                    name="search"
                    className="navbar__search-input"
                    placeholder="Search"
                    value={searchQuery}
                    onChange={(e)=>setSearchQuery(e.target.value)}
                    aria-label="Search"
                    autoComplete="off"
                    autoFocus
                  />
                  <button
                    type="button"
                    className="navbar__search-close"
                    onClick={()=>{
                      setSearchOpen(false);
                      setSearchQuery('');
                      onCloseSearchDropdown?.();
                    }}
                  >
                    Cancel
                  </button>
                </form>
              )}

              {showDropdown && (
                <div className="search-dropdown">
                  {liveSearchTweets.length>0 && (
                    <div className="search-dropdown__section">
                      <div className="search-dropdown__label">Posts</div>
                      {liveSearchTweets.map((post)=>(
                        <button
                          type="button"
                          key={post.id}
                          className="search-dropdown__item"
                          onClick={(e)=>{ e.stopPropagation(); onSelectPost && onSelectPost(post); }}
                        >
                          <Avatar username={post.username} avatarUrl={post.avatar_url} size="sm" />
                          <div className="search-dropdown__item-content">
                            <span className="search-dropdown__item-meta">@{post.username||'unknown'}</span>
                            <span className="search-dropdown__item-text">{post.content}</span>
                          </div>
                        </button>
                      ))}
                    </div>
                  )}
                  {liveSearchUsers.length>0 && (
                    <div className="search-dropdown__section">
                      <div className="search-dropdown__label">People</div>
                      {liveSearchUsers.map((user)=>(
                        <button
                          type="button"
                          key={user.id}
                          className="search-dropdown__item"
                          onClick={(e)=>{ e.stopPropagation(); onSelectUser && onSelectUser(user); }}
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

          <button
            type="button"
            className="navbar__icon-btn"
            onClick={toggleDarkMode}
            aria-label={darkMode?'Switch to light mode':'Switch to dark mode'}
            title={darkMode?'Light':'Dark'}
          >
            {darkMode?'Light':'Dark'}
          </button>

          {loggedInUser ? (
            <>
              <button type="button" className="navbar__link navbar__link--quiet" onClick={onGoToSettings}>Settings</button>
              <button type="button" className="navbar__cta navbar__cta--ghost" onClick={onLogout}>Log out</button>
            </>
          ) : (
            <>
              <button type="button" className="navbar__link" onClick={onGoToLogin}>Log in</button>
              <button type="button" className="navbar__cta" onClick={onGoToSignup}>Sign up</button>
            </>
          )}
        </div>
      </div>
    </nav>
  );
}

export default Navbar;
export { APP_NAME };
