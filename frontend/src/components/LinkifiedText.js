import React from 'react';

const TOKEN_RE=/(@[A-Za-z0-9_]+|#[A-Za-z0-9_]+)/g;

function LinkifiedText({ text, onMention, onHashtag }) {
  //split on mentions/hashtags so we can wire clicks
  if (!text) return null;
  const parts=String(text).split(TOKEN_RE);
  return (
    <>
      {parts.map((part, i) => {
        if (part.startsWith('@') && onMention) {
          const name = part.slice(1);
          return (
            <button
              key={i}
              type="button"
              className="linkified linkified--mention"
              onClick={(e) => { e.stopPropagation(); onMention(name); }}
            >
              {part}
            </button>
          );
        }
        if (part.startsWith('#') && onHashtag) {
          const tag = part.slice(1);
          return (
            <button
              key={i}
              type="button"
              className="linkified linkified--hashtag"
              onClick={(e) => { e.stopPropagation(); onHashtag(tag); }}
            >
              {part}
            </button>
          );
        }
        return <span key={i}>{part}</span>;
      })}
    </>
  );
}

export default LinkifiedText;
