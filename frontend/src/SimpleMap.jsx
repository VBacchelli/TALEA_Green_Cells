import React, { useRef, useState } from "react";
import { MapContainer, TileLayer, GeoJSON } from "react-leaflet";
import "leaflet/dist/leaflet.css";
import L from "leaflet";

import LoadButton from "./LoadButton";
import LayerSidebar from "./LayerSidebar";
import DatasetMenu from "./DatasetMenu"; // <-- NEW
import {
  reprojectIfNeeded,
  styleByGeomType,
  toFeatureCollection,
} from "./utils";

const DEFAULT_COLOR = "#3388ff";
const DEFAULT_OPACITY = 1.0;

/* -------------------- Color utilities -------------------- */

function hexToHsl(hex) {
  const m = hex.replace("#", "");
  const s = m.length === 3 ? m.split("").map((c) => c + c).join("") : m;
  const n = parseInt(s, 16);
  const r = (n >> 16) & 255,
    g = (n >> 8) & 255,
    b = n & 255;
  const r1 = r / 255,
    g1 = g / 255,
    b1 = b / 255;
  const max = Math.max(r1, g1, b1),
    min = Math.min(r1, g1, b1);
  let h, s1, l = (max + min) / 2;
  if (max === min) {
    h = s1 = 0;
  } else {
    const d = max - min;
    s1 = l > 0.5 ? d / (2 - max - min) : d / (max + min);
    switch (max) {
      case r1:
        h = (g1 - b1) / d + (g1 < b1 ? 6 : 0);
        break;
      case g1:
        h = (b1 - r1) / d + 2;
        break;
      case b1:
        h = (r1 - g1) / d + 4;
        break;
      default:
        h = 0;
    }
    h /= 6;
  }
  return { h, s: s1, l };
}

function hslToHex({ h, s, l }) {
  const hue2rgb = (p, q, t) => {
    if (t < 0) t += 1;
    if (t > 1) t -= 1;
    if (t < 1 / 6) return p + (q - p) * 6 * t;
    if (t < 1 / 2) return q;
    if (t < 2 / 3) return p + (q - p) * (2 / 3 - t) * 6;
    return p;
  };
  let r, g, b;
  if (s === 0) {
    r = g = b = l;
  } else {
    const q = l < 0.5 ? l * (1 + s) : l + s - l * s;
    const p = 2 * l - q;
    r = hue2rgb(p, q, h + 1 / 3);
    g = hue2rgb(p, q, h);
    b = hue2rgb(p, q, h - 1 / 3);
  }
  const toHex = (x) => ("0" + Math.round(x * 255).toString(16)).slice(-2);
  return `#${toHex(r)}${toHex(g)}${toHex(b)}`;
}

function clamp01(x) {
  return Math.max(0, Math.min(1, x));
}

// Given a base color, produce a lighter start and a darker end for ramp
function rampFromBaseColor(baseHex) {
  const hsl = hexToHsl(baseHex);
  const start = hslToHex({ h: hsl.h, s: hsl.s, l: clamp01(hsl.l + 0.25) });
  const end = hslToHex({ h: hsl.h, s: hsl.s, l: clamp01(hsl.l - 0.25) });
  return { start, end };
}

// Interpolate in HSL for smooth ramps
function lerpHsl(hex1, hex2, t) {
  const a = hexToHsl(hex1),
    b = hexToHsl(hex2);
  return hslToHex({
    h: a.h + (b.h - a.h) * t,
    s: a.s + (b.s - a.s) * t,
    l: a.l + (b.l - a.l) * t,
  });
}
function makeRamp(startHex, endHex, classes) {
  const arr = [];
  for (let i = 0; i < classes; i++) {
    const t = classes === 1 ? 0 : i / (classes - 1);
    arr.push(lerpHsl(startHex, endHex, t));
  }
  return arr;
}

/* --------------- Classification helpers ---------------- */

function getNumericFields(fc) {
  const fields = new Set();
  for (const f of fc.features || []) {
    const props = f?.properties || {};
    for (const [k, v] of Object.entries(props)) {
      if (typeof v === "number" && Number.isFinite(v)) fields.add(k);
    }
  }
  return Array.from(fields).sort();
}

function computeMinMax(fc, field) {
  let min = Infinity,
    max = -Infinity,
    count = 0;
  for (const f of fc.features || []) {
    const v = f?.properties?.[field];
    if (typeof v === "number" && Number.isFinite(v)) {
      min = Math.min(min, v);
      max = Math.max(max, v);
      count++;
    }
  }
  if (!count) return { min: 0, max: 0, count: 0 };
  if (min === max) max = min + 1e-9; // avoid zero range
  return { min, max, count };
}

function buildEqualIntervalClassifier(fc, field, classes, start, end) {
  const { min, max } = computeMinMax(fc, field);
  const colors = makeRamp(start, end, classes);
  const step = (max - min) / classes;

  function colorForValue(v) {
    if (typeof v !== "number" || !Number.isFinite(v)) return "#999999";
    let idx = Math.floor((v - min) / step);
    if (idx < 0) idx = 0;
    if (idx >= classes) idx = classes - 1;
    return colors[idx];
  }

  return { field, classes, colors, min, max, start, end, colorForValue };
}

/* -------------------- Utilities -------------------- */

const DEFAULT_CLASSIFY = {
  field: "",
  classes: 5,
  start: "#ffffcc",
  end: "#800026",
  colors: [],
  min: 0,
  max: 1,
  colorForValue: () => "#999999",
  autoFromBase: true,
};

function stripExt(name = "") {
  const i = name.lastIndexOf(".");
  return i > 0 ? name.slice(0, i) : name || "Layer";
}

function normalizeGroupName(g) {
  const name = (g || "").trim();
  return name.length ? name : "Ungrouped";
}

/* -------------------- Component -------------------- */

export default function SimpleMap() {
  const mapRef = useRef(null);
  const layerRefs = useRef(new Map()); // id -> Leaflet layer instance

  // layers: [{ id, name, data, visible, colorMode, color, opacity, classify, numericFields, group }]
  const [layers, setLayers] = useState([]);

  // Sidebar visibility
  const [sidebarVisible, setSidebarVisible] = useState(true);

  // Add a new layer from raw GeoJSON
  const addLayer = (raw, filename = "Layer") => {
    try {
      const fc = reprojectIfNeeded(toFeatureCollection(raw));
      const id = `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
      const numericFields = getNumericFields(fc);
      const defaultField = numericFields[0] || "";
      const baseColor = DEFAULT_COLOR;

      // Seed ramp from base color
      const { start, end } = rampFromBaseColor(baseColor);
      const seeded = buildEqualIntervalClassifier(
        fc,
        defaultField,
        DEFAULT_CLASSIFY.classes,
        start,
        end
      );

      setLayers((prev) => [
        ...prev,
        {
          id,
          name: stripExt(filename),
          data: fc,
          visible: true,
          colorMode: "single", // can switch to "classify"
          color: baseColor,
          opacity: DEFAULT_OPACITY,
          numericFields,
          classify: { ...seeded, autoFromBase: true },
          group: "Ungrouped", // default group
        },
      ]);
    } catch (err) {
      console.error("Error processing GeoJSON:", err);
      alert("Error processing the file.");
    }
  };

  // From LoadButton or DatasetMenu: (json, filename)
  const handleLoad = (json, filename) => addLayer(json, filename);

  // Sidebar actions
  const toggleVisible = (id) =>
    setLayers((prev) =>
      prev.map((l) => (l.id === id ? { ...l, visible: !l.visible } : l))
    );

  // explicitly set a single layer's visibility
  const setLayerVisible = (id, visible) =>
    setLayers((prev) => prev.map((l) => (l.id === id ? { ...l, visible } : l)));

  // set visibility for a whole group
  const setGroupVisible = (groupName, visible) =>
    setLayers((prev) =>
      prev.map((l) =>
        normalizeGroupName(l.group) === normalizeGroupName(groupName)
          ? { ...l, visible }
          : l
      )
    );

  const changeColorMode = (id, mode) =>
    setLayers((prev) =>
      prev.map((l) => {
        if (l.id !== id) return l;
        if (mode === "classify") {
          // (Re)seed ramp from current base color if still auto-managed
          const { start, end } = rampFromBaseColor(l.color);
          const field = l.classify?.field || l.numericFields[0] || "";
          const classes = l.classify?.classes || DEFAULT_CLASSIFY.classes;
          const seeded = buildEqualIntervalClassifier(
            l.data,
            field,
            classes,
            start,
            end
          );
          return {
            ...l,
            colorMode: mode,
            classify: {
              ...seeded,
              autoFromBase: l.classify?.autoFromBase ?? true,
            },
          };
        }
        return { ...l, colorMode: mode };
      })
    );

  const changeColor = (id, color) =>
    setLayers((prev) =>
      prev.map((l) => {
        if (l.id !== id) return l;
        if (l.classify?.autoFromBase) {
          // ramp auto-managed → reseed from new base color
          const { start, end } = rampFromBaseColor(color);
          const field = l.classify?.field || l.numericFields[0] || "";
          const classes = l.classify?.classes || DEFAULT_CLASSIFY.classes;
          const seeded = buildEqualIntervalClassifier(
            l.data,
            field,
            classes,
            start,
            end
          );
          return { ...l, color, classify: { ...seeded, autoFromBase: true } };
        }
        return { ...l, color };
      })
    );

  const changeOpacity = (id, opacity) =>
    setLayers((prev) =>
      prev.map((l) => (l.id === id ? { ...l, opacity } : l))
    );

  const renameLayer = (id, name) =>
    setLayers((prev) => prev.map((l) => (l.id === id ? { ...l, name } : l)));

  const changeGroup = (id, group) =>
    setLayers((prev) =>
      prev.map((l) => (l.id === id ? { ...l, group: normalizeGroupName(group) } : l))
    );

  const changeClassField = (id, field) =>
    setLayers((prev) =>
      prev.map((l) => {
        if (l.id !== id) return l;
        const cfg = buildEqualIntervalClassifier(
          l.data,
          field,
          l.classify.classes,
          l.classify.start,
          l.classify.end
        );
        return { ...l, classify: { ...cfg, autoFromBase: false } };
      })
    );

  const changeClassCount = (id, classes) =>
    setLayers((prev) =>
      prev.map((l) => {
        if (l.id !== id) return l;
        const field = l.classify.field || l.numericFields[0];
        const cfg = buildEqualIntervalClassifier(
          l.data,
          field,
          classes,
          l.classify.start,
          l.classify.end
        );
        return { ...l, classify: { ...cfg, autoFromBase: false } };
      })
    );

  const changeRamp = (id, start, end) =>
    setLayers((prev) =>
      prev.map((l) => {
        if (l.id !== id) return l;
        const field = l.classify.field || l.numericFields[0];
        const cfg = buildEqualIntervalClassifier(
          l.data,
          field,
          l.classify.classes,
          start,
          end
        );
        return { ...l, classify: { ...cfg, autoFromBase: false } };
      })
    );

  const removeLayer = (id) => {
    const map = mapRef.current;
    const ref = layerRefs.current.get(id);
    if (map && ref) {
      try {
        map.removeLayer(ref);
      } catch {}
      layerRefs.current.delete(id);
    }
    setLayers((prev) => prev.filter((l) => l.id !== id));
  };

  const clearAll = () => {
    const map = mapRef.current;
    if (map) {
      map.eachLayer((layer) => {
        if (!(layer instanceof L.TileLayer)) {
          try {
            map.removeLayer(layer);
          } catch {}
        }
      });
    }
    layerRefs.current.clear();
    setLayers([]);
  };

  const zoomToLayer = (id) => {
    const map = mapRef.current;
    const ref = layerRefs.current.get(id);
    if (!map || !ref) return;
    const bounds = ref.getBounds?.();
    if (bounds && bounds.isValid())
      map.fitBounds(bounds, { padding: [20, 20] });
  };

  // Scrollable popup content for all features
  const onEachFeature = (feature, layer) => {
    const props = feature?.properties || {};
    const title = props.name || props.id || feature?.geometry?.type || "Feature";

    const rows = Object.entries(props)
      .map(
        ([k, v]) =>
          `<div style="padding:4px 0;border-bottom:1px solid #eee;">
            <b>${k}:</b> <span>${String(v)}</span>
          </div>`
      )
      .join("");

    const html = `
      <div style="max-width:260px;">
        <div style="font-weight:700;margin-bottom:6px;">${title}</div>
        <div style="max-height:220px; overflow:auto; padding-right:6px;">
          ${rows || "<i>No properties</i>"}
        </div>
      </div>
    `;

    layer.bindPopup(html, { maxWidth: 300 });
  };

  const pointToLayer = (layerCfg) => (feature, latlng) => {
    const mode = layerCfg.colorMode;
    const opacity = layerCfg.opacity;
    let color = layerCfg.color;

    if (mode === "classify" && layerCfg.classify?.colorForValue) {
      const v = feature?.properties?.[layerCfg.classify.field];
      color = layerCfg.classify.colorForValue(v);
    }

    return L.circleMarker(latlng, {
      radius: 1,
      weight: 2,
      color,
      opacity,
      fillColor: color,
      fillOpacity: opacity,
    });
  };

  const makeStyleFn = (layerCfg) => (feature) => {
    const base = styleByGeomType(feature); // keep same behavior
    const mode = layerCfg.colorMode;
    const opacity = layerCfg.opacity;
    let color = layerCfg.color;

    if (mode === "classify" && layerCfg.classify?.colorForValue) {
      const v = feature?.properties?.[layerCfg.classify.field];
      color = layerCfg.classify.colorForValue(v);
    }

    return {
      ...base,
      color,
      opacity,
      fillColor: color,
      fillOpacity: feature.geometry?.type?.includes("Polygon")
        ? Math.min(opacity, 0.65)
        : 0,
    };
  };

  return (
    <div>
      <MapContainer
        center={[44.494981, 11.342641]}
        zoom={13}
        style={{ height: "100vh", width: "100vw" }}
        whenCreated={(map) => (mapRef.current = map)}
        zoomSnap={0.4}
        zoomDelta={0.4}
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />

        {layers.map((lyr) =>
          lyr.visible ? (
            <GeoJSON
              key={lyr.id}
              data={lyr.data}
              ref={(instance) => {
                if (instance) layerRefs.current.set(lyr.id, instance);
              }}
              style={makeStyleFn(lyr)}
              pointToLayer={pointToLayer(lyr)}
              onEachFeature={onEachFeature}
            />
          ) : null
        )}
      </MapContainer>

      {/* Controls */}
      <LoadButton onLoad={handleLoad} />
      <DatasetMenu
        onLoad={handleLoad}
        indexUrl="/datasets/index.json"   // public manifest path
        initialOpen={false}
      />

      <LayerSidebar
        layers={layers}
        visible={sidebarVisible}
        onClose={() => setSidebarVisible(false)}
        onToggleVisible={toggleVisible}
        onSetVisible={setLayerVisible}
        onSetGroupVisible={setGroupVisible}
        onChangeGroup={changeGroup}
        onZoomTo={zoomToLayer}
        onRemove={removeLayer}
        onClearAll={clearAll}
        onColorModeChange={changeColorMode}
        onColorChange={changeColor}
        onOpacityChange={changeOpacity}
        onRename={renameLayer}
        onClassFieldChange={changeClassField}
        onClassCountChange={changeClassCount}
        onRampChange={changeRamp}
      />

      {!sidebarVisible && (
        <button
          onClick={() => setSidebarVisible(true)}
          style={{
            position: "absolute",
            top: 20,
            right: 20,
            zIndex: 1200,
            padding: "8px 12px",
            background: "white",
            color: "black",
            border: "1px solid #ddd",
            borderRadius: 6,
            boxShadow: "0 2px 6px rgba(0,0,0,0.2)",
            cursor: "pointer",
            fontWeight: 600,
          }}
          title="Show sidebar"
        >
          Loaded layers
        </button>
      )}
    </div>
  );
}
