import { useEffect, useState } from "react";
import { MapContainer, TileLayer, Polygon, Popup } from "react-leaflet";
import "leaflet/dist/leaflet.css";
import { colorFor, fillOpacityFor } from "../lib/permitColors";

const API = import.meta.env.VITE_API_URL || "http://localhost:8000";

const DEFAULT_CENTER = [43.6532, -79.3832];
const DEFAULT_ZOOM = 11;

// Convert GeoJSON Polygon coordinates ([lon,lat] rings) to Leaflet ([lat,lon] rings).
function geomToLatLngs(geometry) {
  if (!geometry || geometry.type !== "Polygon") return [];
  return geometry.coordinates.map(ring => ring.map(([lon, lat]) => [lat, lon]));
}

export default function HeroMap({ view }) {
  const [permits, setPermits] = useState([]);

  useEffect(() => {
    fetch(`${API}/${view}`).then(r => r.json()).then(setPermits).catch(console.error);
  }, [view]);

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
              <b>{p.street_name}</b><br/>
              {p.work_type} ({p.status})<br/>
              {p.start_date} → {p.end_date}<br/>
              lane-days: {p.lane_days}<br/>
              status: {status}<br/>
              cluster: {p.cluster_id ?? "—"}
            </Popup>
          </Polygon>
        );
      })}
    </MapContainer>
  );
}
