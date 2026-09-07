from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import rasterio

from shapely import make_valid, force_2d
from shapely.geometry import Point, Polygon, MultiPolygon
from tqdm import tqdm

# ---------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------

RAW_DIR = Path("dataset/raw_data")
PROCESSED_DIR = Path("dataset/processed_data/330300")

STAT_AREAS = RAW_DIR / "aree-statistiche.geojson"
TREE_CANOPY = RAW_DIR / "TreeCanopy_ExportV2.tif"
DBSN = RAW_DIR / "Bologna_dbsn.gdb"

STAT_AREAS_OUT = PROCESSED_DIR / "stat_areas.gpkg"
PARKS_OUT = PROCESSED_DIR / "parks.gpkg"

# ---------------------------------------------------------------------
# Geometry utilities
# ---------------------------------------------------------------------

def remove_z(geom):
    """Drop Z coordinate from Polygon / MultiPolygon geometries."""
    return force_2d(geom)


def main():

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    # =================================================================
    # 1. Administrative boundaries
    # =================================================================

    print("Lettura aree statistiche...")
    stat_areas = (gpd.read_file(STAT_AREAS).to_crs(epsg=4326))
    print(f"Aree statistiche: {len(stat_areas)}")

    # =================================================================
    # 2. Tree canopy raster
    #
    # Rule 30:
    #     percentage of canopy pixels inside each statistical area
    #
    # Rule 3:
    #     canopy pixels == 1 become "tree" reference points
    # =================================================================

    print("Lettura raster canopy...")

    with rasterio.open(TREE_CANOPY) as src:
        data = src.read(1)
        transform = src.transform
        raster_crs = src.crs

        rows, cols = np.where(data != src.nodata)

        points = [Point(transform * (c, r)) for r, c in zip(rows, cols)]

        values = [data[r, c] for r, c in zip(rows, cols)]

        canopy = gpd.GeoDataFrame(
            {
                "geometry": points,
                "canopy_value": values,
            },
            geometry="geometry",
            crs=raster_crs,
        )

    print(f"Pixel raster validi: {len(canopy)}")

    # The spatial join requires both layers in the same CRS.
    stat_areas_for_canopy = (stat_areas.to_crs(canopy.crs))

    # Spatial join: canopy pixels -> statistical areas
    canopy_by_area = gpd.sjoin(
        canopy,
        stat_areas_for_canopy,
        how="inner",
        predicate="within",
    )

    canopy_by_area_valid = canopy_by_area[
        canopy_by_area["canopy_value"].isin([0, 1])
    ].copy()

    print("Pixel canopy assegnati alle aree statistiche: "f"{len(canopy_by_area_valid)}")

    # -----------------------------------------------------------------
    # Rule 30 - canopy percentage per statistical area
    # -----------------------------------------------------------------

    print("Calcolo percentuale canopy per area statistica...")

    canopy_pct = (
        canopy_by_area_valid
        .groupby("codice_area_statistica")
        .apply(lambda g: (g["canopy_value"].sum() / len(g)) * 100, include_groups=False)
        .reset_index(name="perc_canopy_cover_30")
    )

    stat_areas = stat_areas.merge(
        canopy_pct,
        on="codice_area_statistica",
        how="left",
    )

    # =================================================================
    # Parks and gardens
    #
    # Used by rules 3 and 300
    # =================================================================

    print("Lettura parchi e giardini...")
    parks = gpd.read_file(DBSN, layer="pe_uins")

    parks = parks[
        parks["pe_uins_ty"].isin(["11","1101","1102","1103"])
    ].copy()

    print(f"Parchi selezionati prima del clipping: "f"{len(parks)}")
    parks["geometry"] = (parks["geometry"].apply(remove_z))
    parks["tipo"] = "park or garden"
    parks = (gpd.GeoDataFrame(parks, geometry="geometry", crs=parks.crs).to_crs(epsg=4326))

    # -----------------------------------------------------------------
    # Fix invalid geometries before overlay
    # -----------------------------------------------------------------

    stat_areas["geometry"] = (
        stat_areas["geometry"]
        .apply(make_valid)
    )

    parks["geometry"] = (
        parks["geometry"]
        .apply(make_valid)
    )

    # -----------------------------------------------------------------
    # Clip parks to statistical areas
    # -----------------------------------------------------------------

    print("Clipping parchi sulle aree statistiche...")

    parks_sindex = parks.sindex
    results = []

    for _, area_row in tqdm(
        stat_areas.iterrows(),
        total=len(stat_areas),
        desc="Statistical areas",
    ):
        area_geom = area_row.geometry
        area_code = area_row["codice_area_statistica"]

        candidate_idx = list(
            parks_sindex.intersection(area_geom.bounds)
        )

        parks_in_area = parks.iloc[candidate_idx]
        parks_in_area = parks_in_area[parks_in_area.intersects(area_geom)]

        if parks_in_area.empty:
            continue

        try:
            overlay = gpd.overlay(
                parks_in_area,
                gpd.GeoDataFrame([area_row], crs=stat_areas.crs),
                how="intersection",
                keep_geom_type=False,
            )

            results.append(overlay)

        except Exception as exc:
            print(f"Overlay error for area "f"{area_code}: {exc}")

    clipped_parks = gpd.GeoDataFrame(
        pd.concat(results, ignore_index=True),
        crs=stat_areas.crs,
    )

    clipped_parks = clipped_parks[[
        "geometry",
        "quartiere",
        "zona",
        "area_statistica",
        "codice_area_statistica",
        "tipo",
    ]]

    # =================================================================
    # 4. Save prepared layers
    # =================================================================

    print("Salvataggio layer preprocessati...")

    stat_areas.to_file(
        STAT_AREAS_OUT,
        layer="stat_areas",
        driver="GPKG",
    )

    clipped_parks.to_file(
        PARKS_OUT,
        layer="parks",
        driver="GPKG",
    )

    # =================================================================
    # Summary
    # =================================================================

    print()
    print("=" * 80)
    print("PREPARAZIONE 3-30-300 COMPLETATA")
    print("=" * 80)

    print(f"Aree statistiche: "f"{len(stat_areas)}")

    print(f"Park polygons:     "f"{len(clipped_parks)}")

    print()
    print(f"Output directory: "f"{PROCESSED_DIR}")


if __name__ == "__main__":
    main()
