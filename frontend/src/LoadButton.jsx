import React, { useRef } from "react";

export default function LoadButton({ onLoad }) {
  const inputRef = useRef(null);

  const openPicker = () => inputRef.current?.click();

  const onChange = (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = () => {
      try {
        const json = JSON.parse(reader.result);
        onLoad?.(json);
      } catch (err) {
        console.error("Invalid GeoJSON:", err);
        alert("Could not parse the selected file as JSON/GeoJSON.");
      }
    };
    reader.readAsText(file);

    e.target.value = ""; // allow re-upload same file
  };

  return (
    <>
      <button
        onClick={openPicker}
        style={{
          position: "absolute",
          top: 80,
          left: 10,
          zIndex: 1000,
          padding: "6px 10px",
          backgroundColor: "white",
          color: "black",
          border: "1px solid #000",
          borderRadius: 4,
          cursor: "pointer",
        }}
        title="Load a local .geojson file"
      >
        Load GeoJSON
      </button>

      <input
        ref={inputRef}
        type="file"
        accept=".geojson,application/geo+json,application/json"
        onChange={onChange}
        style={{ display: "none" }}
      />
    </>
  );
}
