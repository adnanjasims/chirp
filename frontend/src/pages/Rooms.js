import React, { useEffect, useState, useRef } from 'react';
import {apiFetch} from '../api';
import Avatar from '../components/Avatar';
import './FeaturePages.css';

function Rooms({ loggedInUser, roomId, setRoomId, showToast }) {
  const [rooms,setRooms]=useState([]);
  const [name,setName]=useState('');
  const [topic,setTopic]=useState('');
  const [room,setRoom]=useState(null);
  const [messages,setMessages]=useState([]);
  const [text,setText]=useState('');
  const bottomRef=useRef(null);

  const loadRooms=async ()=>{
    const res=await apiFetch(`/rooms`);
    setRooms(await res.json());
  };

  const loadRoom=async (id)=>{
    const [rRes, mRes]=await Promise.all([
      apiFetch(`/rooms/${id}`),
      apiFetch(`/rooms/${id}/messages`),
    ]);
    setRoom(await rRes.json());
    setMessages(await mRes.json());
  };

  useEffect(()=>{ loadRooms(); }, []);

  useEffect(() => {
    if (roomId) {
      loadRoom(roomId);
      apiFetch(`/rooms/${roomId}/join`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username: loggedInUser.username }),
      }).catch(() => {});
      const t = setInterval(() => loadRoom(roomId), 4000);
      return () => clearInterval(t);
    }
    setRoom(null);
    setMessages([]);
  }, [roomId, loggedInUser?.username]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const createRoom = async (e) => {
    e.preventDefault();
    const res = await apiFetch(`/rooms`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username: loggedInUser.username, name, topic }),
    });
    const data = await res.json();
    if (res.ok) {
      setName('');
      setTopic('');
      showToast?.('success', 'Room created.');
      await loadRooms();
      setRoomId(data.id);
    }
  };

  const sendMessage = async (e) => {
    e.preventDefault();
    if (!text.trim() || !roomId) return;
    const res = await apiFetch(`/rooms/${roomId}/messages`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username: loggedInUser.username, content: text.trim() }),
    });
    if (res.ok) {
      setText('');
      loadRoom(roomId);
    }
  };

  if (roomId && room) {
    return (
      <main className="feature-page">
        <div className="feature-container feature-container--wide">
          <div className="feature-header">
            <button type="button" className="btn btn--secondary btn--sm" onClick={() => setRoomId(null)}>← Rooms</button>
            <h1>{room.name}</h1>
            {room.host_id === loggedInUser?.id && (
              <button
                type="button"
                className="btn btn--secondary btn--sm"
                onClick={async () => {
                  await apiFetch(`/rooms/${roomId}/end`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ username: loggedInUser.username }),
                  });
                  setRoomId(null);
                  loadRooms();
                }}
              >
                End room
              </button>
            )}
          </div>
          {room.topic && <p className="feature-sub">{room.topic}</p>}
          <div className="room-layout">
            <div className="room-chat">
              {messages.map((m) => (
                <div key={m.id} className="room-msg">
                  <Avatar username={m.username} avatarUrl={m.avatar_url} size="sm" />
                  <div>
                    <strong>@{m.username}</strong>
                    <p>{m.content}</p>
                  </div>
                </div>
              ))}
              <div ref={bottomRef} />
            </div>
            <aside className="room-members">
              <h3>Here now</h3>
              {(room.members || []).map((m) => (
                <div key={m.id} className="room-member">@{m.username}</div>
              ))}
            </aside>
          </div>
          <form className="room-compose" onSubmit={sendMessage}>
            <input value={text} onChange={(e) => setText(e.target.value)} placeholder="Say something..." maxLength={500} />
            <button type="submit" className="btn btn--primary">Send</button>
          </form>
        </div>
      </main>
    );
  }

  return (
    <main className="feature-page">
      <div className="feature-container">
        <h1>Chirp Rooms</h1>
        <p className="feature-sub">Short lived live text spaces. pull up a chair.</p>
        <form className="feature-form" onSubmit={createRoom}>
          <input value={name} onChange={(e) => setName(e.target.value)} placeholder="Room name" required />
          <input value={topic} onChange={(e) => setTopic(e.target.value)} placeholder="Topic (optional)" />
          <button type="submit" className="btn btn--primary">Start room</button>
        </form>
        <div className="room-list">
          {rooms.length === 0 && <p className="feed-empty">No live rooms. Be the first.</p>}
          {rooms.map((r) => (
            <button key={r.id} type="button" className="room-card" onClick={() => setRoomId(r.id)}>
              <div className="room-card__title">{r.name}</div>
              <div className="room-card__meta">@{r.host} · {r.member_count} here</div>
              {r.topic && <div className="room-card__topic">{r.topic}</div>}
            </button>
          ))}
        </div>
      </div>
    </main>
  );
}

export default Rooms;
