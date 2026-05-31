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

  // Naive view = no coordination = no savings. Permits-considered is the same
  // population in both views; excavations-avoided and cost-avoidance are zero.
  // Per gap closure G6-COUNTER (D-33/D-34): toggling the view must visibly retween
  // the tri-stat counter. The retween is achieved by handing TriStatCounter a
  // DIFFERENT object reference per view so useCountUp sees a new target.
  const naiveMetrics = metrics && {
    permits_considered: metrics.permits_considered,
    excavations_avoided: 0,
    cost_avoidance: 0,
  };
  const displayMetrics = view === "naive" ? naiveMetrics : metrics;

  return (
    <div className="app">
      <div className="topbar">
        <div className="brand">
          <h1>PermitFlow</h1>
          <span className="brand-sub">Toronto · Greektown corridor</span>
        </div>
        <ToggleSwitch view={view} onChange={setView} />
      </div>

      <TriStatCounter metrics={displayMetrics} />

      <div className="main">
        <HeroMap view={view} />
        <ChatPanel view={view} />
      </div>
    </div>
  );
}

export default App;
