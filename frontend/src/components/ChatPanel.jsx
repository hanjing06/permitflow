import { useState } from "react";

const API = import.meta.env.VITE_API_URL || "http://localhost:8000";

// Placeholder canned set per D-37 (pitch lead replaces content in Phase 6).
// The *plumbing* must exist now per D-38.
const CANNED = [
  "What's the biggest coordination opportunity on the hero block?",
  "Show me a conflict near Danforth & Pape.",
  "Why isn't this utility cut piggybacking on the resurfacing?",
];

export default function ChatPanel({ view }) {
  const [query, setQuery] = useState("");
  const [response, setResponse] = useState("");
  const [streaming, setStreaming] = useState(false);

  async function send(q) {
    const text = (q ?? query).trim();
    if (!text || streaming) return;
    setStreaming(true);
    setResponse("");

    try {
      const res = await fetch(`${API}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: text, view }),
      });
      if (!res.ok || !res.body) {
        setResponse(`[chat error: HTTP ${res.status}]`);
        return;
      }
      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buf = "";
      let acc = "";
      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        buf += decoder.decode(value, { stream: true });
        // SSE frames terminated by blank line ("\n\n").
        let idx;
        while ((idx = buf.indexOf("\n\n")) >= 0) {
          const frame = buf.slice(0, idx);
          buf = buf.slice(idx + 2);
          for (const line of frame.split("\n")) {
            if (!line.startsWith("data: ")) continue;
            const payload = line.slice(6);
            if (payload === "[DONE]") { setStreaming(false); return; }
            // Backend escapes literal newlines as "\n" — unescape for display.
            acc += payload.replace(/\\n/g, "\n");
            setResponse(acc);
          }
        }
      }
    } catch (err) {
      console.error(err);
      setResponse(`[chat error: ${err.message}]`);
    } finally {
      setStreaming(false);
    }
  }

  return (
    <div className="chat-panel">
      <div className="chat-header">
        <h2>Ask PermitFlow</h2>
        <span className="chat-badge">running on GX10</span>
      </div>

      <div className="chat-canned">
        {CANNED.map((q, i) => (
          <button key={i} className="canned-btn" disabled={streaming} onClick={() => send(q)}>
            {q}
          </button>
        ))}
      </div>

      <div className="chat-response">
        {response || (streaming ? "streaming…" : "Ask a question or pick a scenario above.")}
      </div>

      <div className="chat-input-row">
        <input
          className="chat-input"
          value={query}
          onChange={e => setQuery(e.target.value)}
          onKeyDown={e => { if (e.key === "Enter") send(); }}
          placeholder="Ask about a permit, street, or conflict…"
          disabled={streaming}
        />
        <button className="chat-send" onClick={() => send()} disabled={streaming}>
          {streaming ? "…" : "Send"}
        </button>
      </div>
    </div>
  );
}
