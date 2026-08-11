import React from 'react';

//original Chirp letter-C mark
function ChirpMark({ size = 22, className = '', title = 'Chirp' }) {
  return (
    <svg
      className={className}
      width={size}
      height={size}
      viewBox="0 0 64 64"
      role="img"
      aria-label={title}
      focusable="false"
    >
      <rect width="64" height="64" rx="14" fill="#0071e3" />
      <path
        d="M45.5 18.2a19.5 19.5 0 1 0 0 27.6"
        fill="none"
        stroke="#ffffff"
        strokeWidth="9"
        strokeLinecap="round"
      />
    </svg>
  );
}

export default ChirpMark;
