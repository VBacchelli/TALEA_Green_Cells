from pathlib import Path

import geopandas as gpd
import pandas as pd
from shapely import make_valid
from shapely.geometry import Polygon, MultiPolygon
from tqdm import tqdm


# ---------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------

STAT_AREAS = Path("dataset/raw_data/aree-statistiche.geojson")
DBSN = Path("dataset/raw_data/Bologna_dbsn.gdb")

OUTPUT_DIR = Path("dataset/processed_data/330300")

STAT_AREAS_OUT = OUTPUT_DIR / "stat_areas.gpkg"
PARKS_OUT = OUTPUT_DIR / "parks.gpkg"


def remove_z(geom):
    """Remove Z coordinate from Polygon / MultiPolygon geometries."""

    if geom.geom_type == "MultiPolygon":
        return MultiPolygon(
            [
                Polygon(
                    [(x, y) for x, y, *_ in poly.exterior.coords]
                )
                for poly in geom.geoms
            ]
        )

    if geom.geom_type == "Polygon":
        return Polygon(
            [(x, y) for x, y, *_ in geom.exterior.coords]
        )

    return geom


def main():

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    # -----------------------------------------------------------------
    # 1. Administrative boundaries
    # -----------------------------------------------------------------

    print("Lettura aree statistiche...")

    stat_areas = (
        gpd.read_file(STAT_AREAS)
        .to_crs(epsg=4326)
    )

    stat_areas["geometry"] = (
        stat_areas["geometry"]
        .apply(make_valid)
    )

    print(
        f"Aree statistiche: {len(stat_areas)}"
    )


    # -----------------------------------------------------------------
    # 2. Parks and gardens
    # -----------------------------------------------------------------

    print("Lettura parchi e giardini...")

    parks = gpd.read_file(
        DBSN,
        layer="pe_uins",
    )

    parks = parks[
        parks["pe_uins_ty"].isin(
            ["11", "1101", "1102", "1103"]
        )
    ].copy()

    parks["geometry"] = (
        parks["geometry"]
        .apply(remove_z)
        .apply(make_valid)
    )

    parks["tipo"] = "park or garden"

    parks = parks.to_crs(epsg=4326)

    print(
        f"Parchi selezionati: {len(parks)}"
    )


    # -----------------------------------------------------------------
    # 3. Clip parks to statistical areas
    # -----------------------------------------------------------------

    print(
        "Clipping parchi sulle aree statistiche..."
    )

    sindex = parks.sindex

    results = []

    for _, area_row in tqdm(
        stat_areas.iterrows(),
        total=len(stat_areas),
        desc="Statistical areas",
    ):

        area_geom = area_row.geometry

        candidate_idx = list(
            sindex.intersection(
                area_geom.bounds
            )
        )

        parks_in_area = (
            parks.iloc[candidate_idx]
        )

        parks_in_area = parks_in_area[
            parks_in_area.intersects(
                area_geom
            )
        ]

        if parks_in_area.empty:
            continue

        try:

            overlay = gpd.overlay(
                parks_in_area,
                gpd.GeoDataFrame(
                    [area_row],
                    crs=stat_areas.crs,
                ),
                how="intersection",
                keep_geom_type=False,
            )

            results.append(
                overlay
            )

        except Exception as exc:

            area_code = area_row[
                "codice_area_statistica"
            ]

            print(
                f"Errore overlay area "
                f"{area_code}: {exc}"
            )

    clipped_parks = gpd.GeoDataFrame(
        pd.concat(
            results,
            ignore_index=True,
        ),
        crs=stat_areas.crs,
    )

    # Keep the same relevant fields used by the original pipeline.
    clipped_parks = clipped_parks[
        [
            "geometry",
            "quartiere",
            "zona",
            "area_statistica",
            "codice_area_statistica",
            "tipo",
        ]
    ]


    # -----------------------------------------------------------------
    # 4. Save processed layers
    # -----------------------------------------------------------------

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

    print()
    print("Preparazione completata.")
    print(
        f"Aree statistiche salvate: "
        f"{len(stat_areas)}"
    )
    print(
        f"Geometrie parco salvate: "
        f"{len(clipped_parks)}"
    )
    print(
        f"Output directory: "
        f"{OUTPUT_DIR}"
    )


if __name__ == "__main__":
    main()