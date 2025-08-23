import React, { useState } from "react";

/**
 * Sidebar with collapsible rows.
 * Header shows Clear All and ✕ (hide).
 * Collapsed row shows: color swatch, NAME (always), Visible checkbox, [+] expand.
 * Expanded shows: Rename, Color mode (single/choropleth), Single color picker,
 *                 Attribute, Classes, Ramp start/end (with gradient preview), Opacity,
 *                 Zoom, Remove.
 */
export default function LayerSidebar({
  layers,
  onToggleVisible,
  onZoomTo,
  onRemove,
  onClearAll,
  onColorChange,
  onOpacityChange,
  onRename,
  onColorModeChange,
  onClassFieldChange,
  onClassCountChange,
  onRampChange,
  visible,
  onClose,
}) {
  const [expanded, setExpanded] = useState({});
  const toggleExpand = (id) =>
    setExpanded((prev) => ({ ...prev, [id]: !prev[id] }));

  if (!visible) return null;

  return (
    <div
      style={{
        position: "absolute",
        top: 10,
        right: 10,
        bottom: 10,
        width: 340,
        zIndex: 1000,
        background: "white",
        border: "1px solid #ddd",
        borderRadius: 8,
        boxShadow: "0 2px 10px rgba(0,0,0,0.08)",
        display: "flex",
        flexDirection: "column",
        overflow: "hidden",
      }}
    >
      <div
        style={{
          padding: "10px 12px",
          borderBottom: "1px solid #eee",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          fontWeight: 600,
        }}
      >
        Layers
        <div style={{ display: "flex", gap: 8 }}>
          <button
            onClick={onClearAll}
            disabled={layers.length === 0}
            style={{
              padding: "4px 8px",
              background: layers.length === 0 ? "#fafafa" : "#f5f5f5",
              color: layers.length === 0 ? "#bbb" : "inherit",
              border: "1px solid #ddd",
              borderRadius: 6,
              cursor: layers.length === 0 ? "not-allowed" : "pointer",
            }}
            title="Remove all layers"
          >
            Clear All
          </button>
          <button
            onClick={onClose}
            style={{
              padding: "4px 8px",
              background: "#f5f5f5",
              color: "black",
              border: "1px solid #ddd",
              borderRadius: 6,
              cursor: "pointer",
            }}
            title="Hide sidebar"
          >
            ✕
          </button>
        </div>
      </div>

      <div style={{ padding: 10, overflowY: "auto" }}>
        {layers.length === 0 && (
          <div style={{ padding: 8, color: "#666" }}>
            No layers loaded yet. Use “Load GeoJSON”.
          </div>
        )}

        {layers.map((lyr) => {
          const isOpen = !!expanded[lyr.id];
          const isChoro = lyr.colorMode === "classify";
          const numericFields = lyr.numericFields || [];

          const swatchStyle =
            isChoro && lyr.classify?.colors?.length
              ? {
                  background: `linear-gradient(90deg, ${lyr.classify.colors.join(
                    ","
                  )})`,
                }
              : { background: lyr.color };

          return (
            <div
              key={lyr.id}
              style={{
                border: "1px solid #eee",
                borderRadius: 8,
                padding: 10,
                marginBottom: 10,
                background: "#fff",
              }}
            >
              {/* HEADER ROW (always visible) */}
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "16px 1fr auto auto",
                  gap: 10,
                  alignItems: "center",
                }}
              >
                {/* color swatch */}
                <span
                  title="Layer color"
                  style={{
                    width: 16,
                    height: 16,
                    borderRadius: 3,
                    border: "1px solid #ccc",
                    display: "inline-block",
                    ...swatchStyle,
                  }}
                />

                {/* NAME — always visible */}
                <div
                  style={{
                    fontWeight: 600,
                    overflow: "hidden",
                    textOverflow: "ellipsis",
                    whiteSpace: "nowrap",
                  }}
                  title={lyr.name}
                >
                  {lyr.name}
                </div>

                {/* Visible checkbox */}
                <label
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: 6,
                    fontSize: 12,
                    color: "#444",
                    whiteSpace: "nowrap",
                  }}
                  title="Toggle layer visibility"
                >
                  <input
                    type="checkbox"
                    checked={lyr.visible}
                    onChange={() => onToggleVisible(lyr.id)}
                  />
                  Visible
                </label>

                {/* + / − button */}
                <button
                  onClick={() => toggleExpand(lyr.id)}
                  style={{
                    padding: "2px 8px",
                    background: "#f5f5f5",
                    border: "1px solid #ddd",
                    borderRadius: 6,
                    cursor: "pointer",
                    fontWeight: 700,
                  }}
                  aria-expanded={isOpen}
                  title={isOpen ? "Hide settings" : "Show settings"}
                >
                  {isOpen ? "−" : "+"}
                </button>
              </div>

              {/* BODY (expanded settings) */}
              {isOpen && (
                <div style={{ marginTop: 10, display: "grid", gap: 10 }}>
                  {/* Rename */}
                  <label style={{ display: "grid", gap: 6 }}>
                    <span style={{ fontSize: 12, color: "#555" }}>Rename layer</span>
                    <input
                      type="text"
                      value={lyr.name}
                      onChange={(e) => onRename(lyr.id, e.target.value)}
                      style={{
                        padding: "6px 8px",
                        border: "1px solid #ccc",
                        borderRadius: 6,
                      }}
                      placeholder="Layer name"
                    />
                  </label>

                  {/* Color mode */}
                  <label style={{ display: "grid", gap: 6 }}>
                    <span style={{ fontSize: 12, color: "#555" }}>Color mode</span>
                    <select
                      value={lyr.colorMode}
                      onChange={(e) => onColorModeChange(lyr.id, e.target.value)}
                      style={{
                        padding: "6px 8px",
                        border: "1px solid #ccc",
                        borderRadius: 6,
                      }}
                    >
                      <option value="single">Single color</option>
                      <option value="classify">By attribute (choropleth)</option>
                    </select>
                  </label>

                  {/* Single color controls */}
                  {lyr.colorMode === "single" && (
                    <label style={{ display: "grid", gap: 6 }}>
                      <span style={{ fontSize: 12, color: "#555" }}>Color</span>
                      <input
                        type="color"
                        value={lyr.color}
                        onChange={(e) => onColorChange(lyr.id, e.target.value)}
                        style={{
                          width: 52,
                          height: 32,
                          padding: 0,
                          border: "1px solid #ccc",
                          borderRadius: 6,
                          cursor: "pointer",
                        }}
                      />
                    </label>
                  )}

                  {/* Choropleth controls */}
                  {lyr.colorMode === "classify" && (
                    <>
                      <label style={{ display: "grid", gap: 6 }}>
                        <span style={{ fontSize: 12, color: "#555" }}>
                          Attribute (numeric)
                        </span>
                        <select
                          value={lyr.classify?.field || ""}
                          onChange={(e) => onClassFieldChange(lyr.id, e.target.value)}
                          style={{
                            padding: "6px 8px",
                            border: "1px solid #ccc",
                            borderRadius: 6,
                          }}
                        >
                          <option value="" disabled>
                            Select field
                          </option>
                          {numericFields.map((f) => (
                            <option key={f} value={f}>
                              {f}
                            </option>
                          ))}
                        </select>
                      </label>

                      <label style={{ display: "grid", gap: 6 }}>
                        <span style={{ fontSize: 12, color: "#555" }}>
                          Classes: {lyr.classify?.classes || 5}
                        </span>
                        <input
                          type="range"
                          min={2}
                          max={100}
                          step={1}
                          value={lyr.classify?.classes || 5}
                          onChange={(e) =>
                            onClassCountChange(lyr.id, Number(e.target.value))
                          }
                        />
                      </label>

                      <div
                        style={{
                          display: "grid",
                          gridTemplateColumns: "1fr 1fr",
                          gap: 10,
                        }}
                      >
                        <label style={{ display: "grid", gap: 6 }}>
                          <span style={{ fontSize: 12, color: "#555" }}>
                            Ramp start
                          </span>
                          <input
                            type="color"
                            value={lyr.classify?.start || "#ffffcc"}
                            onChange={(e) =>
                              onRampChange(
                                lyr.id,
                                e.target.value,
                                lyr.classify?.end || "#800026"
                              )
                            }
                            style={{
                              width: 52,
                              height: 32,
                              padding: 0,
                              border: "1px solid #ccc",
                              borderRadius: 6,
                              cursor: "pointer",
                            }}
                          />
                        </label>
                        <label style={{ display: "grid", gap: 6 }}>
                          <span style={{ fontSize: 12, color: "#555" }}>
                            Ramp end
                          </span>
                          <input
                            type="color"
                            value={lyr.classify?.end || "#800026"}
                            onChange={(e) =>
                              onRampChange(
                                lyr.id,
                                lyr.classify?.start || "#ffffcc",
                                e.target.value
                              )
                            }
                            style={{
                              width: 52,
                              height: 32,
                              padding: 0,
                              border: "1px solid #ccc",
                              borderRadius: 6,
                              cursor: "pointer",
                            }}
                          />
                        </label>
                      </div>

                      {/* Legend preview */}
                      {lyr.classify?.colors?.length > 1 && (
                        <div
                          style={{
                            height: 14,
                            borderRadius: 6,
                            border: "1px solid #ddd",
                            background: `linear-gradient(90deg, ${lyr.classify.colors.join(
                              ","
                            )})`,
                          }}
                          title={`min ${lyr.classify.min} → max ${lyr.classify.max}`}
                        />
                      )}
                    </>
                  )}

                  {/* Opacity */}
                  <label style={{ display: "grid", gap: 6 }}>
                    <span style={{ fontSize: 12, color: "#555" }}>
                      Opacity: {(lyr.opacity ?? 1).toFixed(2)}
                    </span>
                    <input
                      type="range"
                      min={0}
                      max={1}
                      step={0.05}
                      value={lyr.opacity ?? 1}
                      onChange={(e) =>
                        onOpacityChange(lyr.id, Number(e.target.value))
                      }
                    />
                  </label>

                  <div style={{ display: "flex", gap: 8 }}>
                    <button
                      onClick={() => onZoomTo(lyr.id)}
                      style={{
                        padding: "4px 8px",
                        background: "#f5f5f5",
                        border: "1px solid #ddd",
                        borderRadius: 6,
                        cursor: "pointer",
                      }}
                      title="Zoom to layer"
                    >
                      Zoom
                    </button>

                    <button
                      onClick={() => onRemove(lyr.id)}
                      style={{
                        padding: "4px 8px",
                        background: "white",
                        color: "#b00020",
                        border: "1px solid #f2c4c4",
                        borderRadius: 6,
                        cursor: "pointer",
                        marginLeft: "auto",
                      }}
                      title="Remove layer"
                    >
                      Remove
                    </button>
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
