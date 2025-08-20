import React, { useRef, useState, useEffect } from "react";
import { MapContainer, TileLayer, GeoJSON } from "react-leaflet";
import "leaflet/dist/leaflet.css";
import LoadButton from "./LoadButton";
import { reprojectIfNeeded, styleByGeomType, toFeatureCollection } from "./utils";
import L from "leaflet";

export default function SimpleMap() {
  const mapRef = useRef(null);
  const layerRef = useRef(null);
  const [geoJsonData, setGeoJsonData] = useState(null);

  // Fit bounds whenever new data is loaded
  useEffect(() => {
    const map = mapRef.current;
    const layer = layerRef.current;
    if (!map || !layer || !geoJsonData) return;

    const bounds = layer.getBounds?.();
    if (bounds && bounds.isValid()) {
      map.fitBounds(bounds, { padding: [20, 20] });
    }
  }, [geoJsonData]);

  // Handle uploaded file
  const onUpload = (raw) => {
    try {
      const fc = reprojectIfNeeded(toFeatureCollection(raw));
      setGeoJsonData(fc);
    } catch (err) {
      console.error("Error processing GeoJSON:", err);
      alert("Error processing the file.");
    }
  };

  // Render points as circle markers
  const pointToLayer = (feature, latlng) =>
    L.circleMarker(latlng, {
      radius: 6,
      weight: 2,
      color: "#e31a1c",
      fillColor: "#fb9a99",
      fillOpacity: 0.8,
    });

  // Bind popups with feature properties
  const onEachFeature = (feature, layer) => {
    const props = feature?.properties || {};
    const title = props.name || props.id || feature?.geometry?.type;
    const lines = Object.entries(props)
      .slice(0, 10)
      .map(([k, v]) => `<div><b>${k}:</b> ${String(v)}</div>`)
      .join("");
    layer.bindPopup(`<div><b>${title}</b>${lines ? "<hr/>" + lines : ""}</div>`);
  };

  return (
    <div>
      <MapContainer
        center={[44.494981, 11.342641]}
        zoom={13}
        style={{ height: "100vh", width: "100vw" }}
        whenCreated={(map) => (mapRef.current = map)}
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />

        {geoJsonData && (
          <GeoJSON
            data={geoJsonData}
            ref={layerRef}
            style={styleByGeomType}
            pointToLayer={pointToLayer}
            onEachFeature={onEachFeature}
          />
        )}
      </MapContainer>

      <LoadButton onLoad={onUpload} />
    </div>
  );
}
