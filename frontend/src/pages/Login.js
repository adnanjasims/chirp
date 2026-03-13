import React, { useState } from 'react';
import './Auth.css';

function Login({ onLogin, onSwitchToSignup, message, setMessage }) {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setMessage(null);
    if (!username.trim() || !password) {
      setMessage({ type: 'error', text: 'Enter your username and password.' });
      return;
    }
    setLoading(true);
    try {
      await onLogin(username.trim(), password);
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="auth-page">
      <div className="auth-card">
        <h1 className="auth-card__title">Log in</h1>
        {message && (
          <div className={`auth-message auth-message--${message.type}`}>
            {message.text}
          </div>
        )}
        <form onSubmit={handleSubmit} className="auth-form">
          <label className="auth-label">Username</label>
          <input
            type="text"
            className="auth-input"
            placeholder="Username"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            autoComplete="username"
            disabled={loading}
          />
          <label className="auth-label">Password</label>
          <input
            type="password"
            className="auth-input"
            placeholder="Password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete="current-password"
            disabled={loading}
          />
          <button type="submit" className="btn btn--primary btn--block" disabled={loading}>
            {loading ? 'Logging in…' : 'Log in'}
          </button>
        </form>
        <p className="auth-switch">
          Don’t have an account?{' '}
          <button type="button" className="link-btn" onClick={onSwitchToSignup}>
            Sign up
          </button>
        </p>
      </div>
    </main>
  );
}

export default Login;
