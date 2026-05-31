import { useEffect, useState } from "react";
import HeroMap from "./components/HeroMap";
import ToggleSwitch from "./components/ToggleSwitch";
import TriStatCounter from "./components/TriStatCounter";
import ChatPanel from "./components/ChatPanel";
import "./App.css";

const API = import.meta.env.VITE_API_URL || "http://localhost:8000";

function App() {
  const [view, setView] = useState("optimized");
  const [metrics, setMetrics] = useState(null);

  useEffect(() => {
    fetch(`${API}/metrics`).then(r => r.json()).then(setMetrics).catch(console.error);
  }, []);

  return (
    <div className="app">
      <div className="topbar">
        <div className="brand">
          <h1>PermitFlow</h1>
          <span className="brand-sub">Toronto · Greektown corridor</span>
        </div>
        <ToggleSwitch view={view} onChange={setView} />
      </div>

      <TriStatCounter metrics={metrics} />

      <div className="main">
        <HeroMap view={view} />
        <ChatPanel view={view} />
      </div>
    </div>
  );
}

export default App;
