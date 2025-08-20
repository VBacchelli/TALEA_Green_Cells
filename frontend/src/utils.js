// geojson-utils.js

// --- Internal helpers ---

// Inverse Web Mercator (EPSG:3857) -> WGS84 (EPSG:4326)
function from3857To4326([x, y]) {
  const R = 6378137;
  const lon = (x / R) * (180 / Math.PI);
  const lat = (2 * Math.atan(Math.exp(y / R)) - Math.PI / 2) * (180 / Math.PI);
  return [lon, lat];
}

// Walk arbitrary coordinate depth, applying fn([x,y]) -> [lon,lat]
function mapCoords(coords, fn) {
  if (typeof coords?.[0] === "number") return fn(coords);
  return coords.map((c) => mapCoords(c, fn));
}

// Pull the first coordinate pair we can find (for heuristics)
function firstCoordOfGeom(geom) {
  if (!geom) return null;
  const { type, coordinates, geometries } = geom;
  if (type === "GeometryCollection") {
    for (const g of geometries || []) {
      const c = firstCoordOfGeom(g);
      if (c) return c;
    }
    return null;
  }
  let c = coordinates;
  while (Array.isArray(c) && Array.isArray(c[0])) c = c[0];
  return c; // should be [x,y] or null
}

// Simple bbox-based hint (FC-level or Feature-level)
function bboxSuggests3857(bbox) {
  if (!Array.isArray(bbox) || bbox.length < 4) return false;
  const [minX, minY, maxX, maxY] = bbox;
  return (
    Math.abs(minX) > 180 || Math.abs(maxX) > 180 ||
    Math.abs(minY) > 90  || Math.abs(maxY) > 90
  );
}

// Magnitude heuristic: lon/lat are small; 3857 meters are large
function coordSuggests3857(coord) {
  if (!Array.isArray(coord) || coord.length < 2) return false;
  const [x, y] = coord;
  return Math.abs(x) > 180 || Math.abs(y) > 90;
}

// --- Public API ---

// Normalize any GeoJSON input to a FeatureCollection
export function toFeatureCollection(geojson) {
  if (!geojson) throw new Error("Empty GeoJSON");
  const t = geojson.type;

  if (t === "FeatureCollection") return geojson;

  if (t === "Feature") {
    return { type: "FeatureCollection", features: [geojson] };
  }

  // Bare Geometry
  if (
    t === "Point" || t === "MultiPoint" ||
    t === "LineString" || t === "MultiLineString" ||
    t === "Polygon" || t === "MultiPolygon" ||
    t === "GeometryCollection"
  ) {
    return {
      type: "FeatureCollection",
      features: [{ type: "Feature", geometry: geojson, properties: {} }],
    };
  }

  throw new Error(`Unsupported GeoJSON type: ${t}`);
}

/**
 * Detect the CRS of the given GeoJSON.
 * Returns one of: "EPSG:4326", "EPSG:3857", or "unknown".
 * Uses (1) declared crs, (2) bbox hints, (3) coordinate magnitude heuristics.
 */
export function detectCrs(geojson) {
  const fc = toFeatureCollection(geojson);

  // 1) Declared CRS, if any
  const name = fc?.crs?.properties?.name || fc?.crs?.name || "";
  const nameUC = String(name).toUpperCase();

  if (nameUC.includes("EPSG:4326") || nameUC.includes("WGS84")) {
    return "EPSG:4326";
  }
  if (
    nameUC.includes("EPSG:3857") ||
    nameUC.includes("EPSG::3857") ||
    nameUC.includes("900913") // old alias used by some tools
  ) {
    return "EPSG:3857";
  }

  // 2) BBox hints (on FC or first Feature with bbox)
  if (bboxSuggests3857(fc.bbox)) return "EPSG:3857";
  for (const f of fc.features) {
    if (bboxSuggests3857(f.bbox)) return "EPSG:3857";
  }

  // 3) Coordinate magnitude heuristic
  for (const f of fc.features) {
    const c = firstCoordOfGeom(f.geometry);
    if (!c) continue;
    if (coordSuggests3857(c)) return "EPSG:3857";

    // Optional positive hint for 4326
    const [x, y] = c;
    if (Math.abs(x) <= 180 && Math.abs(y) <= 90) return "EPSG:4326";
  }

  return "unknown";
}

/**
 * Reproject to EPSG:4326 ONLY if detection says EPSG:3857.
 * Otherwise, returns the input (normalized to FeatureCollection) unchanged.
 */
export function reprojectIfNeeded(geojson) {
  const fc = toFeatureCollection(geojson);
  const crs = detectCrs(fc);

  if (crs !== "EPSG:3857") {
    // Already 4326 or unknown → assume safe as-is
    return fc;
  }

  // Convert every geometry coordinate pair from 3857 → 4326
  return {
    ...fc,
    crs: { type: "name", properties: { name: "EPSG:4326" } },
    features: fc.features.map((feat) => {
      const g = feat.geometry;
      if (!g) return feat;

      if (g.type === "GeometryCollection") {
        return {
          ...feat,
          geometry: {
            ...g,
            geometries: (g.geometries || []).map((gg) => ({
              ...gg,
              coordinates: mapCoords(gg.coordinates, from3857To4326),
            })),
          },
        };
      }

      return {
        ...feat,
        geometry: {
          ...g,
          coordinates: mapCoords(g.coordinates, from3857To4326),
        },
      };
    }),
  };
}

// Simple style by geometry type
export function styleByGeomType(feature) {
  const t = feature?.geometry?.type;
  const base = { weight: 2, opacity: 1, fillOpacity: 0.2 };

  switch (t) {
    case "LineString":
    case "MultiLineString":
      return { ...base, color: "#1f78b4", fillOpacity: 0 };
    case "Polygon":
    case "MultiPolygon":
      return { ...base, color: "#33a02c", fillColor: "#33a02c" };
    case "GeometryCollection":
      return { ...base, color: "#6a3d9a", fillColor: "#6a3d9a" };
    default:
      return { ...base, color: "#555", fillColor: "#999" };
  }
}
