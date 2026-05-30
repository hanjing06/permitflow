import { useEffect, useState } from "react";
import { MapContainer, TileLayer, CircleMarker, Popup } from "react-leaflet";
import "leaflet/dist/leaflet.css";
import "./App.css";

const API = import.meta.env.VITE_API_URL || "http://localhost:8000";

function cleanText(text) {
  return String(text).replaceAll("&lt;br&gt;", " | ");
}

function App() {
  const [permits, setPermits] = useState([]);
  const [recommendations, setRecommendations] = useState([]);
  const [metrics, setMetrics] = useState(null);
  const [selectedExplanation, setSelectedExplanation] = useState("");
  const [loadingExplanation, setLoadingExplanation] = useState(false);

  useEffect(() => {
    fetch(`${API}/permits`)
      .then((res) => res.json())
      .then(setPermits)
      .catch(console.error);

    fetch(`${API}/recommendations`)
      .then((res) => res.json())
      .then((data) => setRecommendations(data.recommendations || []))
      .catch(console.error);

    fetch(`${API}/metrics`)
      .then((res) => res.json())
      .then(setMetrics)
      .catch(console.error);
  }, []);

  async function explainCluster(clusterId) {
    try {
      setLoadingExplanation(true);
      setSelectedExplanation("Generating explanation...");

      const response = await fetch(
        `${API}/explain?cluster_id=${clusterId}`
      );

      const data = await response.json();

      setSelectedExplanation(data.explanation);
    } catch (err) {
      console.error(err);
      setSelectedExplanation("Failed to generate explanation.");
    } finally {
      setLoadingExplanation(false);
    }
  }

  return (
    <div className="app">
      <div className="sidebar">
        <h1>PermitFlow</h1>
        <p>
          AI-assisted permit consolidation for Toronto infrastructure planning.
        </p>

        {metrics && (
          <>
            <h2>Metrics</h2>

            <div className="card">
              <p>
                <b>Total Projects:</b> {metrics.total_projects}
              </p>

              <p>
                <b>Opportunities:</b>{" "}
                {metrics.consolidation_opportunities}
              </p>

              <p>
                <b>Largest Cluster:</b>{" "}
                {metrics.largest_cluster}
              </p>

              <p>
                <b>Road Openings Saved:</b>{" "}
                {metrics.road_openings_saved}
              </p>

              <p>
                <b>Estimated Savings:</b> $
                {metrics.estimated_savings?.toLocaleString()}
              </p>
            </div>
          </>
        )}

        <h2>Recommendations</h2>

        {recommendations.slice(0, 10).map((rec) => (
          <div className="card" key={rec.cluster_id}>
            <h3>Cluster {rec.cluster_id}</h3>

            <p>
              <b>Projects:</b> {rec.permit_count}
            </p>

            <p>
              <b>Priority:</b> {rec.priority}
            </p>

            <p>
              <b>Road Openings Saved:</b>{" "}
              {rec.road_openings_saved}
            </p>

            <p>
              <b>Estimated Savings:</b> $
              {rec.estimated_savings?.toLocaleString()}
            </p>

            <button
              onClick={() =>
                explainCluster(rec.cluster_id)
              }
            >
              Explain Recommendation
            </button>
          </div>
        ))}

        {selectedExplanation && (
          <>
            <h2>AI Explanation</h2>

            <div className="card">
              <p>{selectedExplanation}</p>

              {loadingExplanation && (
                <p>Loading...</p>
              )}
            </div>
          </>
        )}
      </div>

      <MapContainer
        center={[43.6532, -79.3832]}
        zoom={11}
        className="map"
      >
        <TileLayer
          attribution="&copy; OpenStreetMap contributors"
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />

        {permits.map((permit) => {
          const clusterId = Number(
            permit.cluster_id
          );

          const clustered = clusterId !== -1;

          return (
            <CircleMarker
              key={permit.permit_id}
              center={[
                Number(permit.lat),
                Number(permit.lon),
              ]}
              radius={clustered ? 8 : 5}
              pathOptions={{
                color: clustered ? "red" : "gray",
                fillColor: clustered ? "red" : "gray",
                fillOpacity: 0.8,
              }}
            >
              <Popup>
                <b>
                  {cleanText(
                    permit.street_name
                  )}
                </b>

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
