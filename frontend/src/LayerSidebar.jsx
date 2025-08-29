import React, { useEffect, useMemo, useState } from "react";

/**
 * Sidebar with collapsible rows and GROUP support.
 * - Group headers show a Visible checkbox that sets visibility for all members.
 * - Each layer has the existing controls + a Group input.
 * - Group changes are COMMITTED ONLY when the user presses Enter.
 */
export default function LayerSidebar({
  layers,
  onToggleVisible,     // existing: toggle a single layer
  onSetVisible,         // set a single layer's visible state
  onSetGroupVisible,    // set visible for all layers in a group
  onChangeGroup,        // assign/rename a layer's group (called on Enter)
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

  const normalizeGroupName = (g) => {
    const n = (g || "").trim();
    return n.length ? n : "Ungrouped";
  };

  // Local draft state for group inputs (only committed on Enter)
  // keyed by layer.id -> string
  const [groupDrafts, setGroupDrafts] = useState({});

  // Keep drafts in sync when layers list changes (e.g., new layers)
  useEffect(() => {
    setGroupDrafts((prev) => {
      const next = { ...prev };
      for (const l of layers) {
        if (next[l.id] == null) next[l.id] = normalizeGroupName(l.group);
      }
      // remove drafts for layers that no longer exist
      for (const k of Object.keys(next)) {
        if (!layers.some((l) => l.id === k)) delete next[k];
      }
      return next;
    });
  }, [layers]);

  // Build groups: { [groupName]: Layer[] }
  const groups = useMemo(() => {
    const acc = {};
    for (const lyr of layers) {
      const g = normalizeGroupName(lyr.group);
      if (!acc[g]) acc[g] = [];
      acc[g].push(lyr);
    }
    Object.values(acc).forEach((arr) =>
      arr.sort((a, b) => a.name.localeCompare(b.name))
    );
    return acc;
  }, [layers]);

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
              color: "black",
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

        {Object.entries(groups).map(([groupName, groupLayers]) => {
          const allVisible = groupLayers.every((l) => l.visible);
          const anyVisible = groupLayers.some((l) => l.visible);
          const groupCheckboxState = allVisible ? true : anyVisible ? "mixed" : false;

          return (
            <div key={groupName} style={{ marginBottom: 16 }}>
              {/* GROUP HEADER */}
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  padding: "6px 8px",
                  background: "#fafafa",
                  color: "black",
                  border: "1px solid #eee",
                  borderRadius: 8,
                  marginBottom: 8,
                }}
              >
                <div style={{ fontWeight: 700 }}>{groupName}</div>

                {/* Indeterminate/mixed-state checkbox */}
                <label
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: 6,
                    fontSize: 12,
                    color: "#444",
                    whiteSpace: "nowrap",
                  }}
                  title="Toggle visibility for all layers in this group"
                >
                  <input
                    type="checkbox"
                    checked={!!allVisible}
                    onChange={(e) => {
                      const target = e.target.checked; // true → all on, false → all off
                      onSetGroupVisible?.(groupName, target);
                    }}
                    ref={(el) => {
                      if (el) el.indeterminate = groupCheckboxState === "mixed";
                    }}
                  />
                  Visible
                </label>
              </div>

              {/* LAYERS IN GROUP */}
              {groupLayers.map((lyr) => {
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

                const draftValue =
                  groupDrafts[lyr.id] ?? normalizeGroupName(lyr.group);

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
                          color: "black",
                          textOverflow: "ellipsis",
                          whiteSpace: "nowrap",
                          cursor: "pointer",
                        }}
                        title={lyr.name}
                        onDoubleClick={() => onZoomTo?.(lyr.id)}
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
                          onChange={() =>
                            onSetVisible
                              ? onSetVisible(lyr.id, !lyr.visible)
                              : onToggleVisible(lyr.id)
                          }
                        />
                        Visible
                      </label>

                      {/* + / − button */}
                      <button
                        onClick={() => toggleExpand(lyr.id)}
                        style={{
                          padding: "2px 8px",
                          background: "#f5f5f5",
                          color: "black",
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
                          <span style={{ fontSize: 12, color: "#555" }}>
                            Rename layer
                          </span>
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

                        {/* Group (commit on Enter) */}
                        <label style={{ display: "grid", gap: 6 }}>
                          <span style={{ fontSize: 12, color: "#555" }}>
                            Group (press Enter to apply)
                          </span>
                          <input
                            type="text"
                            value={draftValue}
                            onChange={(e) =>
                              setGroupDrafts((prev) => ({
                                ...prev,
                                [lyr.id]: e.target.value,
                              }))
                            }
                            onKeyDown={(e) => {
                              if (e.key === "Enter") {
                                const finalName = normalizeGroupName(
                                  groupDrafts[lyr.id]
                                );
                                onChangeGroup?.(lyr.id, finalName);
                                // ensure draft reflects committed value
                                setGroupDrafts((prev) => ({
                                  ...prev,
                                  [lyr.id]: finalName,
                                }));
                              } else if (e.key === "Escape") {
                                // revert draft to current layer group name
                                setGroupDrafts((prev) => ({
                                  ...prev,
                                  [lyr.id]: normalizeGroupName(lyr.group),
                                }));
                                e.currentTarget.blur();
                              }
                            }}
                            style={{
                              padding: "6px 8px",
                              border: "1px solid #ccc",
                              borderRadius: 6,
                            }}
                            placeholder="Group name"
                          />
                        </label>

                        {/* Color mode */}
                        <label style={{ display: "grid", gap: 6 }}>
                          <span style={{ fontSize: 12, color: "#555" }}>
                            Color mode
                          </span>
                          <select
                            value={lyr.colorMode}
                            onChange={(e) =>
                              onColorModeChange(lyr.id, e.target.value)
                            }
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
                            <span style={{ fontSize: 12, color: "#555" }}>
                              Color
                            </span>
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
                                onChange={(e) =>
                                  onClassFieldChange(lyr.id, e.target.value)
                                }
                                style={{
                                  padding: "6px 8px",
                                  border: "1px solid",
                                  background: "#ccc",
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
                            onClick={() => onZoomTo?.(lyr.id)}
                            style={{
                              padding: "4px 8px",
                              background: "white",
                              color: "#333",
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
          );
        })}
      </div>
    </div>
  );
}
