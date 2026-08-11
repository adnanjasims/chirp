//base url + authed fetch
export const API = process.env.REACT_APP_API_URL || 'http://127.0.0.1:5000';

const TOKEN_KEY='chirpToken';
const USER_KEY='chirpUser';

export function getToken() {
  try { return localStorage.getItem(TOKEN_KEY) || ''; } catch { return ''; }
}

export function setToken(token) {
  try {
    if (token) localStorage.setItem(TOKEN_KEY, token);
    else localStorage.removeItem(TOKEN_KEY);
  } catch { /* ignore */ }
}

export function getStoredUser() {
  try {
    const raw=localStorage.getItem(USER_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch { return null; }
}

export function setStoredUser(user) {
  try {
    if (user) localStorage.setItem(USER_KEY, JSON.stringify(user));
    else localStorage.removeItem(USER_KEY);
  } catch { /* ignore */ }
}

export function clearAuth() {
  setToken('');
  setStoredUser(null);
  try { localStorage.removeItem('chirpCreds'); } catch { /* old key */ }
}

export function mediaUrl(path) {
  if (!path) return '';
  if (path.startsWith('http://') || path.startsWith('https://')) return path;
  return `${API}${path.startsWith('/') ? path : `/${path}`}`;
}

export async function apiFetch(path, opts={}) {
  const headers={ ...(opts.headers || {}) };
  const token=getToken();
  if (token) headers.Authorization=`Bearer ${token}`;
  const isForm=typeof FormData !== 'undefined' && opts.body instanceof FormData;
  if (opts.body && !isForm && !headers['Content-Type']) {
    headers['Content-Type']='application/json';
  }
  return fetch(`${API}${path}`, { ...opts, headers });
}

export function eventsUrl() {
  const token=getToken();
  const q=token ? `?token=${encodeURIComponent(token)}` : '';
  return `${API}/events${q}`;
}
