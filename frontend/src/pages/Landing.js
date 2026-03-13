import React from 'react';
import './Landing.css';

function Landing({ onLogin, onSignup }) {
  return (
    <main className="landing">
      <div className="landing__content">
        <h1 className="landing__title">See what’s happening.</h1>
        <p className="landing__subtitle">
          Join the conversation. Share updates. Connect with others.
        </p>
        <div className="landing__actions">
          <button type="button" className="btn btn--primary btn--lg" onClick={onSignup}>
            Create account
          </button>
          <p className="landing__login-prompt">
            Already have an account?{' '}
            <button type="button" className="link-btn" onClick={onLogin}>
              Log in
            </button>
          </p>
        </div>
      </div>
    </main>
  );
}

export default Landing;
