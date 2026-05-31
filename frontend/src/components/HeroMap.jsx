import { useEffect, useState } from "react";
import { MapContainer, TileLayer, Polygon, Popup, useMap } from "react-leaflet";
import "leaflet/dist/leaflet.css";
import { colorFor, fillOpacityFor } from "../lib/permitColors";

const API = import.meta.env.VITE_API_URL || "http://localhost:8000";

function FitToHeroBlock({ bbox }) {
  const map = useMap();
  useEffect(() => {
    if (!bbox) return;
    // /hero-block bbox is [min_lon, min_lat, max_lon, max_lat].
    // Leaflet fitBounds wants [[min_lat,min_lon],[max_lat,max_lon]].
    const [minLon, minLat, maxLon, maxLat] = bbox;
    map.fitBounds([[minLat, minLon], [maxLat, maxLon]], { padding: [20, 20] });
  }, [bbox, map]);
  return null;
}

// Convert GeoJSON Polygon coordinates ([lon,lat] rings) to Leaflet ([lat,lon] rings).
function geomToLatLngs(geometry) {
  if (!geometry || geometry.type !== "Polygon") return [];
  return geometry.coordinates.map(ring => ring.map(([lon, lat]) => [lat, lon]));
}

export default function HeroMap({ view }) {
  const [hero, setHero] = useState(null);
  const [permits, setPermits] = useState([]);

  useEffect(() => {
    fetch(`${API}/hero-block`).then(r => r.json()).then(setHero).catch(console.error);
  }, []);

  useEffect(() => {
    fetch(`${API}/${view}`).then(r => r.json()).then(setPermits).catch(console.error);
  }, [view]);

  const fallbackCenter = hero?.center || [43.6657, -79.3642];

  return (
    <MapContainer center={fallbackCenter} zoom={15} className="map">
      <TileLayer
        attribution="&copy; OpenStreetMap contributors"
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      <FitToHeroBlock bbox={hero?.bbox} />
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
