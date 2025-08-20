// Inverse Web Mercator (EPSG:3857) -> WGS84 (EPSG:4326)
function from3857To4326([x, y]) {
  const R = 6378137;
  const lon = (x / R) * (180 / Math.PI);
  const lat = (2 * Math.atan(Math.exp(y / R)) - Math.PI / 2) * (180 / Math.PI);
  return [lon, lat];
}

// Detect if coordinates look like EPSG:3857 meters (big numbers)
function looksLike3857(firstCoord) {
  if (!Array.isArray(firstCoord) || firstCoord.length < 2) return false;
  const [x, y] = firstCoord;
  return Math.abs(x) > 180 || Math.abs(y) > 90;
}

// Walk any coordinates array and transform with fn([x,y])
function mapCoords(coords, fn) {
  if (typeof coords[0] === "number") {
    return fn(coords);
  }
  return coords.map((c) => mapCoords(c, fn));
}

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
    t === "Point" ||
    t === "MultiPoint" ||
    t === "LineString" ||
    t === "MultiLineString" ||
    t === "Polygon" ||
    t === "MultiPolygon" ||
    t === "GeometryCollection"
  ) {
    return {
      type: "FeatureCollection",
      features: [{ type: "Feature", geometry: geojson, properties: {} }],
    };
  }

  throw new Error(`Unsupported GeoJSON type: ${t}`);
}

// Reproject if needed
export function reprojectIfNeeded(geojson) {
  const fc = toFeatureCollection(geojson);

  // If declared EPSG:3857 or looks like meters, convert to 4326
  const declared3857 =
    fc.crs &&
    (fc.crs.properties?.name?.includes("EPSG::3857") ||
      fc.crs.properties?.name?.includes("EPSG:3857"));

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
    return c;
  }

  let seems3857 = false;
  for (const f of fc.features) {
    const c = firstCoordOfGeom(f.geometry);
    if (c && looksLike3857(c)) {
      seems3857 = true;
      break;
    }
  }

  if (!(declared3857 || seems3857)) return fc; // assume already 4326

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
            geometries: g.geometries.map((gg) => ({
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
