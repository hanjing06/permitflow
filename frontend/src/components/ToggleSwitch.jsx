export default function ToggleSwitch({ view, onChange }) {
  return (
    <div className="toggle">
      <button
        className={view === "naive" ? "toggle-btn active" : "toggle-btn"}
        onClick={() => onChange("naive")}
      >Naive</button>
      <button
        className={view === "optimized" ? "toggle-btn active" : "toggle-btn"}
        onClick={() => onChange("optimized")}
      >Optimized</button>
    </div>
  );
}
