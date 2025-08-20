import React, { useRef } from "react";

export default function LoadButton({ onLoad }) {
  const inputRef = useRef(null);

  const openPicker = () => inputRef.current?.click();

  const onChange = (e) => {
    const files = Array.from(e.target.files || []);
    if (!files.length) return;

    files.forEach((file) => {
      const reader = new FileReader();
      reader.onload = () => {
        try {
          const json = JSON.parse(reader.result);
          onLoad?.(json, file.name);
        } catch (err) {
          console.error("Invalid GeoJSON:", err);
          alert(`Could not parse "${file.name}" as JSON/GeoJSON.`);
        }
      };
      reader.readAsText(file);
    });

    // allow re-selecting the same files again later
    e.target.value = "";
  };

  return (
    <>
      {/* Floating control group under Leaflet zoom controls */}
      <div
        style={{
          position: "absolute",
          top: 80,
          left: 10,
          zIndex: 1000,
          display: "flex",
          flexDirection: "column",
          gap: 8,
        }}
      >
        <button
          onClick={openPicker}
          style={{
            padding: "6px 10px",
            backgroundColor: "white",
            color: "black",
            border: "1px solid #000",
            borderRadius: 4,
            cursor: "pointer",
          }}
          title="Load one or more local .geojson files"
        >
          Load GeoJSON
        </button>
      </div>

      <input
        ref={inputRef}
        type="file"
        multiple
        accept=".geojson,application/geo+json,application/json"
        onChange={onChange}
        style={{ display: "none" }}
      />
    </>
  );
}
