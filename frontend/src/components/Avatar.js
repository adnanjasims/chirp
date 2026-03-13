import React from 'react';
import './Avatar.css';

function Avatar({ username, avatarUrl, size = 'md' }) {
  const initial = username ? username.charAt(0).toUpperCase() : '?';
  if (avatarUrl) {
    return (
      <img
        src={avatarUrl}
        alt={`@${username}`}
        className={`avatar avatar--${size}`}
      />
    );
  }
  return (
    <div className={`avatar avatar--${size} avatar--initial`}>
      {initial}
    </div>
  );
}

export default Avatar;
