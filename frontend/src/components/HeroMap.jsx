import { useEffect, useMemo, useState } from "react";
import { MapContainer, TileLayer, Polygon, Circle, Popup } from "react-leaflet";
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
  const [src, num] = String(id).split(":");
  return num ? `${src} #${num}` : id;
}

// Approx meters between two [lat, lon] points — fine at hero-block scales.
function distM([lat1, lon1], [lat2, lon2]) {
  const dLat = (lat2 - lat1) * 111320;
  const dLon = (lon2 - lon1) * 111320 * Math.cos((lat1 * Math.PI) / 180);
  return Math.sqrt(dLat * dLat + dLon * dLon);
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

  const permitById = useMemo(
    () => Object.fromEntries(permits.map(p => [p.permit_id, p])),
    [permits]
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
    for (const k of Object.keys(map)) map[k].sort((a, b) => b.score - a.score);
    return map;
  }, [conflictGraph]);

  // In optimized view: collapse multi-member clusters into a single Circle so the
  // user sees "one decision per cluster" instead of N overlapping polygons.
  // In naive view: clusters don't apply — render every permit independently.
  const { clusterRenders, clusteredPermitIds } = useMemo(() => {
    if (view !== "optimized" || clusters.length === 0 || permits.length === 0) {
      return { clusterRenders: [], clusteredPermitIds: new Set() };
    }
    const renders = [];
    const ids = new Set();
    for (const cluster of clusters) {
      const members = (cluster.member_permit_ids || [])
        .map(id => permitById[id])
        .filter(Boolean);
      if (members.length < 2) continue;

      const centroid = [
        members.reduce((s, m) => s + m.lat, 0) / members.length,
        members.reduce((s, m) => s + m.lon, 0) / members.length,
      ];
      const radius = Math.max(80, ...members.map(m => distM(centroid, [m.lat, m.lon]))) + 40;

      // Chronology: sort members by start_date ascending.
      const chronology = [...members].sort(
        (a, b) => new Date(a.start_date) - new Date(b.start_date)
      );

      members.forEach(m => ids.add(m.permit_id));
      renders.push({ cluster, members, chronology, centroid, radius });
    }
    return { clusterRenders: renders, clusteredPermitIds: ids };
  }, [view, clusters, permits, permitById]);

  return (
    <MapContainer center={DEFAULT_CENTER} zoom={DEFAULT_ZOOM} className="map">
      <TileLayer
        attribution="&copy; OpenStreetMap contributors"
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />

      {/* Cluster circles (optimized view only) — one shape per coordinated decision.
          Blue = anchor_program (review-only). Amber = confirmed trench-share. */}
      {clusterRenders.map(({ cluster, chronology, centroid, radius }) => {
        const start = chronology[0]?.start_date;
        const end = chronology.reduce(
          (max, m) => (new Date(m.end_date) > new Date(max) ? m.end_date : max),
          chronology[0]?.end_date,
        );
        const clusterColorKey = cluster.review_only ? "review_cluster" : "coordinated";
        return (
          <Circle
            key={`cluster-${cluster.cluster_id}`}
            center={centroid}
            radius={radius}
            pathOptions={{
              color: colorFor(clusterColorKey),
              fillColor: colorFor(clusterColorKey),
              fillOpacity: 0.35,
              weight: 3,
            }}
          >
            <Popup>
              <div style={{ minWidth: 260 }}>
                <b>{cluster.type === "piggyback" ? "Piggyback" : "Merged cluster"}</b>
                {" "}<span style={{ color: "#666", fontSize: 11 }}>({cluster.cluster_id})</span>
                <br/>
                <span style={{ fontSize: 12, color: "#444" }}>
                  {chronology.length} permits · {start} → {end}
                </span>
                {cluster.match_type && (
                  <div style={{ fontSize: 11, color: "#888", marginTop: 2 }}>
                    match: {String(cluster.match_type).replace(/_/g, " ")}
                  </div>
                )}
                {cluster.savings_lane_days != null && (
                  <div style={{ fontSize: 12, marginTop: 4, color: "#444" }}>
                    Saves <b>{cluster.savings_lane_days} lane-days</b> vs running independently
                  </div>
                )}
                <hr style={{ margin: "8px 0", border: 0, borderTop: "1px solid #ddd" }}/>
                <div style={{ fontSize: 11, fontWeight: 600, marginBottom: 4 }}>Chronology</div>
                {chronology.map((m, i) => (
                  <div key={m.permit_id} style={{ fontSize: 11, color: "#333", marginBottom: 2 }}>
                    <span style={{ display: "inline-block", width: 14, color: "#999" }}>{i + 1}.</span>
                    <b>{m.start_date}</b> → {m.end_date} · {shortId(m.permit_id)}
                    <div style={{ marginLeft: 14, color: "#666" }}>
                      {m.street_name} <span style={{ color: "#999" }}>· {m.work_type}</span>
                    </div>
                  </div>
                ))}
                {cluster.action && (
                  <div style={{ fontSize: 11, marginTop: 6, color: "#555", fontStyle: "italic" }}>
                    {cluster.action}
                  </div>
                )}
              </div>
            </Popup>
          </Circle>
        );
      })}

      {/* Individual permit polygons — skip the ones already represented by a cluster circle. */}
      {permits.map(p => {
        if (clusteredPermitIds.has(p.permit_id)) return null;
        const positions = geomToLatLngs(p.geometry);
        const status = p.optimization_status || "naive";
        if (positions.length === 0) return null;

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
                <span style={{ color: "#555", fontSize: 11 }}>{shortId(p.permit_id)}</span><br/>
                {p.start_date} → {p.end_date} ({p.lane_days} lane-days)<br/>
                <span style={{ display: "inline-block", marginTop: 4, padding: "1px 6px", background: colorFor(status), color: "#fff", borderRadius: 3, fontSize: 11 }}>
                  {status}
                </span>

                {status === "conflict_deferred" && (
                  <>
                    <hr style={{ margin: "8px 0", border: 0, borderTop: "1px solid #ddd" }}/>
                    <b>Pushed +{shiftedDays} days</b> to avoid concurrent closure<br/>
                    {conflicts.length > 0 ? (
                      <>
                        <div style={{ fontSize: 11, marginTop: 4 }}>Conflicts with:</div>
                        {conflicts.map(c => (
                          <div key={c.other} style={{ fontSize: 11, color: "#444" }}>
                            • {shortId(c.other)} on {c.streets.join(" / ")} <span style={{ color: "#999" }}>(score {c.score.toFixed(2)})</span>
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
