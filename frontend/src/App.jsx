import { useEffect, useState } from "react";
import { MapContainer, TileLayer, CircleMarker, Popup } from "react-leaflet";
import "leaflet/dist/leaflet.css";
import "./App.css";

const API = "http://100.81.34.28:8000";

function cleanText(text) {
  return String(text).replaceAll("&lt;br&gt;", " | ");
}

function App() {
  const [permits, setPermits] = useState([]);
  const [recommendations, setRecommendations] = useState([]);

  useEffect(() => {
    fetch(`${API}/permits`)
      .then((res) => res.json())
      .then((data) => {
        console.log("permits", data);
        setPermits(data);
      });

    fetch(`${API}/recommendations`)
      .then((res) => res.json())
      .then((data) => {
        console.log("recommendations", data);
        setRecommendations(data.recommendations || []);
      });
  }, []);

  return (
    <div className="app">
      <div className="sidebar">
        <h1>PermitFlow</h1>
        <p>AI-assisted permit consolidation for Toronto road work.</p>

        <div className="stat">
          <b>{permits.length}</b>
          <span>projects loaded</span>
        </div>

        <div className="stat">
          <b>{recommendations.length}</b>
          <span>clusters found</span>
        </div>

        <h2>Recommendations</h2>

        {recommendations.slice(0, 12).map((rec) => (
          <div className="card" key={rec.cluster_id}>
            <h3>Cluster {rec.cluster_id}</h3>
            <p><b>Projects:</b> {rec.permit_count}</p>
            <p><b>Action:</b> {rec.action}</p>
            <p><b>Reason:</b> {rec.reason}</p>
          </div>
        ))}
      </div>

      <MapContainer center={[43.6532, -79.3832]} zoom={12} className="map">
        <TileLayer
          attribution="&copy; OpenStreetMap contributors"
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />

        {permits.map((permit) => {
          const clusterId = Number(permit.cluster_id);
          const clustered = clusterId !== -1;

          return (
            <CircleMarker
              key={permit.permit_id}
              center={[Number(permit.lat), Number(permit.lon)]}
              radius={clustered ? 8 : 5}
              pathOptions={{
                color: clustered ? "red" : "gray",
                fillColor: clustered ? "red" : "gray",
                fillOpacity: 0.75,
              }}
            >
              <Popup>
                <b>{cleanText(permit.street_name)}</b>
                <br />
                Project: {permit.work_type}
                <br />
                Status: {permit.status}
                <br />
                Cluster: {permit.cluster_id}
              </Popup>
            </CircleMarker>
          );
        })}
      </MapContainer>
    </div>
  );
}

export default App;
