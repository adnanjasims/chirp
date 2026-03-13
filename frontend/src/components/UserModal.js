import React from 'react';
import Avatar from './Avatar';
import './UserModal.css';

function UserModal({ user, onClose, onFollow, onGoToProfile, loggedInUser }) {
  if (!user) return null;
  const handleViewProfile = () => {
    onGoToProfile?.(user.username);
    onClose();
  };
  return (
    <div className="user-modal-backdrop" onClick={onClose}>
      <div className="user-modal" onClick={(e) => e.stopPropagation()}>
        <button type="button" className="user-modal__close" onClick={onClose} aria-label="Close">
          ×
        </button>
        <div className="user-modal__header">
          <Avatar username={user.username} avatarUrl={user.avatar_url} size="lg" />
          <span className="user-modal__username">@{user.username}</span>
          {user.bio && <p className="user-modal__bio">{user.bio}</p>}
        </div>
        <div className="user-modal__actions">
          <button type="button" className="btn btn--primary" onClick={handleViewProfile}>
            View profile
          </button>
          {loggedInUser && loggedInUser.username !== user.username && (
            <button
              type="button"
              className="btn btn--secondary"
              onClick={() => { onFollow(user.id); onClose(); }}
            >
              Follow
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

export default UserModal;
