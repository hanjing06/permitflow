import { useEffect, useMemo, useState } from "react";
import { MapContainer, TileLayer, Polygon, Popup } from "react-leaflet";
import "leaflet/dist/leaflet.css";
import { colorFor, fillOpacityFor } from "../lib/permitColors";

const API = import.meta.env.VITE_API_URL || "http://localhost:8000";

const DEFAULT_CENTER = [43.6532, -79.3832];
const DEFAULT_ZOOM = 11;

function geomToLatLngs(geometry) {
  if (!geometry || geometry.type !== "Polygon") return [];
  return geometry.coordinates.map(ring => ring.map(([lon, lat]) => [lat, lon]));
}

function daysBetween(a, b) {
  const ms = new Date(b).getTime() - new Date(a).getTime();
  return Math.round(ms / (1000 * 60 * 60 * 24));
}

function shortId(id) {
  // "road_resurfacing:1234" → "road_resurfacing #1234"
  const [src, num] = String(id).split(":");
  return num ? `${src} #${num}` : id;
}

export default function HeroMap({ view }) {
  const [permits, setPermits] = useState([]);
  const [naivePermits, setNaivePermits] = useState([]);
  const [clusters, setClusters] = useState([]);
  const [conflictGraph, setConflictGraph] = useState([]);

  useEffect(() => {
    fetch(`${API}/${view}`).then(r => r.json()).then(setPermits).catch(console.error);
  }, [view]);

  useEffect(() => {
    fetch(`${API}/naive`).then(r => r.json()).then(setNaivePermits).catch(console.error);
    fetch(`${API}/clusters`).then(r => r.json()).then(setClusters).catch(console.error);
    fetch(`${API}/conflict-graph`).then(r => r.json()).then(setConflictGraph).catch(console.error);
  }, []);

  const clusterById = useMemo(
    () => Object.fromEntries(clusters.map(c => [String(c.cluster_id), c])),
    [clusters]
  );

  const naiveById = useMemo(
    () => Object.fromEntries(naivePermits.map(p => [p.permit_id, p])),
    [naivePermits]
  );

  const conflictsForPermit = useMemo(() => {
    const map = {};
    for (const edge of conflictGraph) {
      (map[edge.permit_a] ??= []).push({
        other: edge.permit_b,
        score: edge.conflict_score,
        streets: edge.shared_streets,
      });
      (map[edge.permit_b] ??= []).push({
        other: edge.permit_a,
        score: edge.conflict_score,
        streets: edge.shared_streets,
      });
    }
    // Sort each list strongest-first so the popup shows the most relevant conflict.
    for (const k of Object.keys(map)) {
      map[k].sort((a, b) => b.score - a.score);
    }
    return map;
  }, [conflictGraph]);

  return (
    <MapContainer center={DEFAULT_CENTER} zoom={DEFAULT_ZOOM} className="map">
      <TileLayer
        attribution="&copy; OpenStreetMap contributors"
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      {permits.map(p => {
        const positions = geomToLatLngs(p.geometry);
        const status = p.optimization_status || "naive";
        if (positions.length === 0) return null;

        const cluster = p.cluster_id != null ? clusterById[String(p.cluster_id)] : null;
        const partners = cluster?.member_permit_ids?.filter(id => id !== p.permit_id) ?? [];
        const naiveTwin = naiveById[p.permit_id];
        const shiftedDays = naiveTwin ? daysBetween(naiveTwin.start_date, p.start_date) : 0;
        const conflicts = (conflictsForPermit[p.permit_id] ?? []).slice(0, 3);

        return (
          <Polygon
            key={p.permit_id}
            positions={positions}
            pathOptions={{
              color: colorFor(status),
              fillColor: colorFor(status),
              fillOpacity: fillOpacityFor(status),
              weight: 2,
            }}
          >
            <Popup>
              <div style={{ minWidth: 220 }}>
                <b>{p.street_name}</b><br/>
                {p.work_type} ({p.status})<br/>
                <span style={{ color: "#555" }}>{shortId(p.permit_id)}</span><br/>
                {p.start_date} → {p.end_date} ({p.lane_days} lane-days)<br/>
                <span style={{ display: "inline-block", marginTop: 4, padding: "1px 6px", background: colorFor(status), color: "#fff", borderRadius: 3, fontSize: 11 }}>
                  {status}
                </span>

                {status === "coordinated" && cluster && (
                  <>
                    <hr style={{ margin: "8px 0", border: 0, borderTop: "1px solid #ddd" }}/>
                    <b>Coordinated ({cluster.type})</b><br/>
                    {partners.length > 0 ? (
                      <>
                        Merged with {partners.length} other{partners.length === 1 ? "" : "s"}:<br/>
                        {partners.slice(0, 4).map(id => (
                          <div key={id} style={{ fontSize: 11, color: "#444" }}>• {shortId(id)}</div>
                        ))}
                        {partners.length > 4 && <div style={{ fontSize: 11, color: "#777" }}>+ {partners.length - 4} more</div>}
                      </>
                    ) : (
                      <span style={{ fontSize: 11 }}>Single-permit cluster</span>
                    )}
                    {cluster.savings_lane_days != null && (
                      <div style={{ fontSize: 11, marginTop: 4, color: "#444" }}>
                        Saves ~{cluster.savings_lane_days} lane-days vs running independently
                      </div>
                    )}
                  </>
                )}

                {status === "conflict_deferred" && (
                  <>
                    <hr style={{ margin: "8px 0", border: 0, borderTop: "1px solid #ddd" }}/>
                    <b>Pushed +{shiftedDays} days</b> to avoid concurrent closure<br/>
                    {conflicts.length > 0 ? (
                      <>
                        <div style={{ fontSize: 11, marginTop: 4 }}>Top conflict{conflicts.length === 1 ? "" : "s"}:</div>
                        {conflicts.map(c => (
                          <div key={c.other} style={{ fontSize: 11, color: "#444" }}>
                            • vs {shortId(c.other)} on {c.streets.join(" / ")} <span style={{ color: "#999" }}>(score {c.score.toFixed(2)})</span>
                          </div>
                        ))}
                      </>
                    ) : (
                      <div style={{ fontSize: 11, color: "#777" }}>Conflict edge not in cached graph</div>
                    )}
                  </>
                )}

                {status === "singleton" && (
                  <>
                    <hr style={{ margin: "8px 0", border: 0, borderTop: "1px solid #ddd" }}/>
                    <span style={{ fontSize: 11, color: "#666" }}>No coordination opportunity found within tolerance.</span>
                  </>
                )}

                {status === "naive" && (
                  <>
                    <hr style={{ margin: "8px 0", border: 0, borderTop: "1px solid #ddd" }}/>
                    <span style={{ fontSize: 11, color: "#666" }}>As-applied schedule — no optimizer run.</span>
                  </>
                )}
              </div>
            </Popup>
          </Polygon>
        );
      })}
    </MapContainer>
  );
}
