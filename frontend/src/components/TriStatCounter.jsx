import { useCountUp } from "../lib/useCountUp";

function fmtInt(v) { return Math.round(v).toLocaleString(); }
function fmtMoney(v) { return "$" + Math.round(v).toLocaleString(); }

export default function TriStatCounter({ metrics }) {
  // useCountUp must be called unconditionally at top level (rules of hooks).
  const considered    = useCountUp(metrics?.permits_considered ?? 0, 2000);
  const avoided       = useCountUp(metrics?.excavations_avoided ?? 0, 2000);
  const cost          = useCountUp(metrics?.cost_avoidance ?? 0, 2000);
  const coordination  = useCountUp(metrics?.coordination_opportunities ?? 0, 2000);

  if (!metrics) {
    return <div className="tristat tristat-loading">loading metrics…</div>;
  }

  return (
    <>
      <div className="tristat">
        <div className="tristat-cell">
          <div className="tristat-value">{fmtInt(considered)}</div>
          <div className="tristat-label">permits considered</div>
        </div>
        <div className="tristat-cell">
          <div className="tristat-value">{fmtInt(avoided)}</div>
          <div className="tristat-label">excavations avoided</div>
        </div>
        <div className="tristat-cell">
          <div className="tristat-value">{fmtMoney(cost)}</div>
          <div className="tristat-label">cost avoidance</div>
        </div>
      </div>
      {coordination > 0 && (
        <div className="tristat-subnote">
          + <b>{fmtInt(coordination)}</b> same-street clusters surfaced for the city to review
          <span className="tristat-subnote-hint">
            {" "}— possible coordination, not counted in savings above
          </span>
        </div>
      )}
    </>
  );
}
