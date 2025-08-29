import React, { useEffect, useState } from "react";

export default function DatasetMenu({
  onLoad,                // (json, filename) => void
  indexUrl = "/public/index.json",
  initialOpen = false,
}) {
  const [open, setOpen] = useState(initialOpen);
  const [manifest, setManifest] = useState({ models: {} });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const [stage, setStage] = useState("model"); // "model" | "option"
  const [selectedModel, setSelectedModel] = useState(null);

  // Info panel state
  // For models: Set of model names with open descriptions.
  // For options: Set of "model|option" keys with open descriptions.
  const [openModelInfo, setOpenModelInfo] = useState(() => new Set());
  const [openOptionInfo, setOpenOptionInfo] = useState(() => new Set());

  // Fetch manifest once
  useEffect(() => {
    let abort = false;
    (async () => {
      try {
        setLoading(true);
        const res = await fetch(indexUrl, { cache: "no-cache" });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const json = await res.json();
        const models = json?.models && typeof json.models === "object" ? json.models : {};
        if (!abort) setManifest({ models });
      } catch (e) {
        if (!abort) setError(`Failed to load manifest: ${e.message}`);
      } finally {
        if (!abort) setLoading(false);
      }
    })();
    return () => { abort = true; };
  }, [indexUrl]);

  const modelNames = Object.keys(manifest.models || {}).sort();

  function getModelDescription(modelName) {
    const m = manifest.models?.[modelName];
    if (!m || typeof m !== "object") return "";
    // either "description" or "_description" supported
    return m.description || m._description || "";
  }

  function getOptionMeta(modelName, optionKey) {
    const m = manifest.models?.[modelName] || {};
    const raw = m?.[optionKey];
    if (!raw) return { path: null, description: "" };
    if (typeof raw === "string") return { path: raw, description: "" };
    // object form
    return { path: raw.path || null, description: raw.description || "" };
  }

  async function loadFromPath(path) {
    try {
      const res = await fetch(path, { cache: "no-cache" });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const json = await res.json();
      const filename = path.split("/").pop() || "dataset.geojson";
      onLoad?.(json, filename);
      // Close everything after load
      setOpen(false);
      setStage("model");
      setSelectedModel(null);
      setOpenModelInfo(new Set());
      setOpenOptionInfo(new Set());
    } catch (e) {
      alert(`Failed to load GeoJSON from "${path}": ${e.message}`);
      console.error(e);
    }
  }

  function onPickModel(name) {
    setSelectedModel(name);
    setStage("option");
    // Close all model info panels when moving forward
    setOpenModelInfo(new Set());
  }

  function onBackToModels() {
    setStage("model");
    setSelectedModel(null);
    setOpenOptionInfo(new Set());
  }

  // Styles
  const btnBase = {
    padding: "6px 10px",
    backgroundColor: "white",
    color: "black",
    border: "1px solid #000",
    borderRadius: 4,
    cursor: "pointer",
  };

  const menuBox = {
    position: "absolute",
    top: 120,
    left: 10,
    zIndex: 1000,
    display: "flex",
    flexDirection: "column",
    gap: 8,
  };

  const dropdown = {
    position: "absolute",
    top: 160,
    left: 10,
    zIndex: 1000,
    minWidth: 280,
    background: "white",
    color: "black",
    border: "1px solid #ddd",
    borderRadius: 10,
    boxShadow: "0 2px 10px rgba(0,0,0,0.1)",
    overflow: "hidden",
  };

  const header = {
    padding: 10,
    borderBottom: "1px solid #eee",
    fontWeight: 700,
  };

  const listItem = {
    display: "flex",
    alignItems: "center",
    justifyContent: "flex-start",
    gap: 12, // a touch more spacing between label and button
    width: "100%",
    padding: "8px 10px",
    border: "none",
    background: "white",
    color: "black",
    cursor: "pointer",
    textAlign: "left",
  };

  const listItemHover = (hover) => ({
    ...listItem,
    background: hover ? "#f5f5f5" : "white",
  });

  const infoButton = {
    flex: "0 0 auto",
    width: 24,
    height: 24,
    lineHeight: "24px",
    textAlign: "center",
    borderRadius: 12,
    border: "1px solid #ccc",
    background: "#fff",
    color: "black",
    cursor: "pointer",
    fontWeight: 700,
    padding: 0,
  };

  const infoPanel = {
    margin: "0 10px 8px 10px",
    padding: "8px 10px",
    border: "1px dashed #ddd",
    borderRadius: 8,
    background: "#fafafa",
    color: "#333",
    fontSize: 13,
  };

  return (
    <>
      <div style={menuBox}>
        <button
          onClick={() => {
            const next = !open;
            setOpen(next);
            if (next) {
              setStage("model");
              setSelectedModel(null);
              setOpenModelInfo(new Set());
              setOpenOptionInfo(new Set());
            }
          }}
          style={btnBase}
          title="Pick a dataset from predefined models/options"
        >
          {open ? "Hide Menu" : "Load Results"}
        </button>
      </div>

      {open && (
        <div style={dropdown}>
          <div style={header}>
            {stage === "model" ? "Choose a model" : `Model: ${selectedModel}`}
          </div>

          {loading && <div style={{ padding: 10, color: "#666" }}>Loading…</div>}
          {error && (
            <div style={{ padding: 10, color: "#b00020" }}>
              {error}
              <div style={{ fontSize: 12, color: "#555" }}>
                Check that <code>{indexUrl}</code> exists and is valid JSON.
              </div>
            </div>
          )}

          {!loading && !error && stage === "model" && (
            <ModelList
              models={modelNames}
              getModelDescription={getModelDescription}
              onPick={onPickModel}
              openModelInfo={openModelInfo}
              setOpenModelInfo={setOpenModelInfo}
              listItem={listItem}
              listItemHover={listItemHover}
              infoButton={infoButton}
              infoPanel={infoPanel}
            />
          )}

          {!loading && !error && stage === "option" && selectedModel && (
            <OptionList
              modelName={selectedModel}
              optionsObj={manifest.models[selectedModel] || {}}
              getOptionMeta={getOptionMeta}
              onPick={(optKey) => {
                const { path } = getOptionMeta(selectedModel, optKey);
                if (!path) {
                  alert("No path configured for this option.");
                  return;
                }
                loadFromPath(path);
              }}
              onBack={onBackToModels}
              openOptionInfo={openOptionInfo}
              setOpenOptionInfo={setOpenOptionInfo}
              listItem={listItem}
              listItemHover={listItemHover}
              infoButton={infoButton}
              infoPanel={infoPanel}
            />
          )}
        </div>
      )}
    </>
  );
}

function ModelList({
  models,
  getModelDescription,
  onPick,
  openModelInfo,
  setOpenModelInfo,
  listItem,
  listItemHover,
  infoButton,
  infoPanel,
}) {
  const [hover, setHover] = useState(null);

  if (!models.length) {
    return <div style={{ padding: 10, color: "#666" }}>No models found.</div>;
  }

  return (
    <div>
      {models.map((m) => {
        const isOpen = openModelInfo.has(m);
        const desc = getModelDescription(m);
        return (
          <div key={m} style={{ borderBottom: "1px solid #f0f0f0" }}>
            <div
              style={listItemHover(hover === m)}
              onMouseEnter={() => setHover(m)}
              onMouseLeave={() => setHover(null)}
            >
              {/* Clicking the label picks the model */}
              <button
                onClick={() => onPick(m)}
                style={{
                  border: "none",
                  background: "transparent",
                  color: "black",
                  padding: 0,
                  margin: 0,
                  cursor: "pointer",
                  // removed flex grow so the description button sits closer
                  textAlign: "left",
                  fontSize: 14,
                }}
                title={`Select ${m}`}
              >
                {m}
              </button>
              {/* Info toggle with text */}
              {desc ? (
                <button
                  style={{
                    ...infoButton,
                    width: "auto",
                    height: "auto",
                    lineHeight: "normal",
                    padding: "2px 8px",
                    borderRadius: 6,
                    display: "flex",
                    alignItems: "center",
                    gap: 6,
                    fontWeight: 600,
                    fontSize: 12,
                  }}
                  title={isOpen ? "Hide description" : "Show description"}
                  onClick={(e) => {
                    e.stopPropagation();
                    const next = new Set(openModelInfo);
                    if (next.has(m)) next.delete(m);
                    else next.add(m);
                    setOpenModelInfo(next);
                  }}
                >
                  {isOpen ? "–" : "＋"} <span>description</span>
                </button>
              ) : (
                <span style={{ width: 24, height: 24 }} />
              )}
            </div>
            {isOpen && desc && <div style={infoPanel}>{desc}</div>}
          </div>
        );
      })}
    </div>
  );
}

function OptionList({
  modelName,
  optionsObj,
  getOptionMeta,
  onPick,
  onBack,
  openOptionInfo,
  setOpenOptionInfo,
  listItem,
  listItemHover,
  infoButton,
  infoPanel,
}) {
  const [hover, setHover] = useState(null);
  // Filter out the model-level "description" field
  const optionKeys = Object.keys(optionsObj || {})
    .filter((k) => k !== "description" && k !== "_description")
    .sort();

  return (
    <div>
      <div style={{ display: "flex", gap: 8, padding: 8, borderBottom: "1px solid #eee" }}>
        <button
          onClick={onBack}
          style={{
            padding: "4px 8px",
            background: "#f5f5f5",
            color: "black",
            border: "1px solid #ddd",
            borderRadius: 6,
            cursor: "pointer",
            fontSize: 13,
          }}
          title="Back to models"
        >
          ← Back
        </button>
      </div>

      {!optionKeys.length && (
        <div style={{ padding: 10, color: "#666" }}>
          This model has no options configured.
        </div>
      )}

      {optionKeys.map((k) => {
        const meta = getOptionMeta(modelName, k);
        const key = `${modelName}|${k}`;
        const isOpen = openOptionInfo.has(key);
        return (
          <div key={k} style={{ borderBottom: "1px solid #f0f0f0" }}>
            <div
              style={listItemHover(hover === k)}
              onMouseEnter={() => setHover(k)}
              onMouseLeave={() => setHover(null)}
            >
              {/* Clicking the label picks the option */}
              <button
                onClick={() => onPick(k)}
                style={{
                  border: "none",
                  background: "transparent",
                  color: "black",
                  padding: 0,
                  margin: 0,
                  cursor: "pointer",
                  // removed flex grow so the description button sits closer
                  textAlign: "left",
                  fontSize: 14,
                }}
                title={`Load ${k}`}
              >
                {k}
              </button>
              {/* Info toggle with text */}
              {meta.description ? (
                <button
                  style={{
                    ...infoButton,
                    width: "auto",
                    height: "auto",
                    lineHeight: "normal",
                    padding: "2px 8px",
                    borderRadius: 6,
                    display: "flex",
                    alignItems: "center",
                    gap: 6,
                    fontWeight: 600,
                    fontSize: 12,
                  }}
                  title={isOpen ? "Hide description" : "Show description"}
                  onClick={(e) => {
                    e.stopPropagation();
                    const next = new Set(openOptionInfo);
                    if (next.has(key)) next.delete(key);
                    else next.add(key);
                    setOpenOptionInfo(next);
                  }}
                >
                  {isOpen ? "–" : "＋"} <span>description</span>
                </button>
              ) : (
                <span style={{ width: 24, height: 24 }} />
              )}
            </div>
            {isOpen && meta.description && <div style={infoPanel}>{meta.description}</div>}
          </div>
        );
      })}
    </div>
  );
}
