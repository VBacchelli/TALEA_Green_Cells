from pathlib import Path

import geopandas as gpd
import numpy as np
import osmnx as ox
import pandas as pd
from shapely import make_valid
from tqdm import tqdm


# ---------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------

PROCESSED_DIR = Path("dataset/processed_data/330300")

STAT_AREAS = PROCESSED_DIR / "stat_areas.gpkg"
PARKS = PROCESSED_DIR / "parks.gpkg"

BUILDINGS_OUT = PROCESSED_DIR / "buildings_300.gpkg"
STAT_AREAS_OUT = PROCESSED_DIR / "stat_areas_300.csv"

CRS_METRIC = "EPSG:32632"

R_PARK = 300


def expand_bounds(geom, distance):
    minx, miny, maxx, maxy = geom.bounds

    return (
        minx - distance,
        miny - distance,
        maxx + distance,
        maxy + distance,
    )


def main():

    # -----------------------------------------------------------------
    # 1. Load prepared layers
    # -----------------------------------------------------------------

    print("Lettura layer preprocessati...")

    stat_areas = gpd.read_file(
        STAT_AREAS,
        layer="stat_areas",
    ).to_crs(CRS_METRIC)

    parks = gpd.read_file(
        PARKS,
        layer="parks",
    ).to_crs(CRS_METRIC)

    print(f"Aree statistiche: {len(stat_areas)}")
    print(f"Geometrie parco: {len(parks)}")


    # -----------------------------------------------------------------
    # 2. Download residential buildings from OpenStreetMap
    # -----------------------------------------------------------------

    print("Download edifici OSM...")

    bounding_polygon = (
        stat_areas
        .to_crs(epsg=4326)
        .geometry
        .unary_union
        .convex_hull
        .buffer(0.01)
    )

    buildings = ox.features_from_polygon(
        bounding_polygon,
        tags={"building": True},
    )

    buildings = buildings[
        buildings["building"].isin(
            [
                "residential",
                "apartments",
                "house",
                "detached",
                "yes",
            ]
        )
    ]

    buildings = (
        buildings[["geometry"]]
        .explode(index_parts=False)
        .reset_index(drop=True)
        .to_crs(CRS_METRIC)
    )

    buildings["geometry"] = (
        buildings["geometry"]
        .apply(make_valid)
    )

    print(
        f"Edifici residenziali scaricati: "
        f"{len(buildings)}"
    )


    # -----------------------------------------------------------------
    # 3. Assign each building to a statistical area
    # -----------------------------------------------------------------

    print("Assegnazione edifici alle aree statistiche...")

    buildings = buildings.reset_index(drop=True)

    buildings["building_id"] = np.arange(
        len(buildings)
    )

    buildings["centroid"] = (
        buildings.geometry.centroid
    )

    centroids = gpd.GeoDataFrame(
        {
            "building_id": buildings["building_id"],
        },
        geometry=buildings["centroid"],
        crs=CRS_METRIC,
    )

    centroids = gpd.sjoin(
        centroids,
        stat_areas[
            [
                "codice_area_statistica",
                "geometry",
            ]
        ],
        how="left",
        predicate="within",
    )

    centroids = (
        centroids[
            [
                "building_id",
                "codice_area_statistica",
            ]
        ]
        .drop_duplicates("building_id")
    )

    buildings = buildings.merge(
        centroids,
        on="building_id",
        how="left",
    )

    buildings = buildings[
        buildings[
            "codice_area_statistica"
        ].notna()
    ].reset_index(drop=True)

    print(
        "Edifici assegnati a un'area statistica: "
        f"{len(buildings)}"
    )


    # -----------------------------------------------------------------
    # 4. Rule 300 per building
    # -----------------------------------------------------------------

    print("Calcolo criterio 300...")

    parks_geom = parks.geometry
    parks_sindex = parks.sindex

    near_park_flags = np.zeros(
        len(buildings),
        dtype=bool,
    )

    geometries = buildings.geometry.values

    for i in tqdm(
        range(len(buildings)),
        desc="Buildings",
    ):

        geom = geometries[i]

        candidate_idx = list(
            parks_sindex.intersection(
                expand_bounds(
                    geom,
                    R_PARK,
                )
            )
        )

        if candidate_idx:

            distances = (
                parks_geom
                .iloc[candidate_idx]
                .distance(geom)
            )

            near_park_flags[i] = bool(
                (distances <= R_PARK).any()
            )

    buildings["near_park"] = near_park_flags

    buildings["meet_300"] = (
        buildings["near_park"]
    )


    # -----------------------------------------------------------------
    # 5. Aggregate per statistical area
    # -----------------------------------------------------------------

    print("Aggregazione per area statistica...")

    aggregation = (
        buildings
        .groupby("codice_area_statistica")
        .agg(
            num_buildings=(
                "building_id",
                "count",
            ),
            num_buildings_within_300m_park=(
                "meet_300",
                "sum",
            ),
        )
        .reset_index()
    )

    aggregation[
        "perc_buildings_within_300m_park"
    ] = (
        aggregation[
            "num_buildings_within_300m_park"
        ]
        / aggregation["num_buildings"]
        * 100
    )

    aggregation["meet_300"] = (
        aggregation[
            "perc_buildings_within_300m_park"
        ]
        >= 100
    )


    # -----------------------------------------------------------------
    # 6. Save outputs
    # -----------------------------------------------------------------

    buildings_out = buildings.drop(
        columns=["centroid"]
    )

    buildings_out.to_file(
        BUILDINGS_OUT,
        layer="buildings_300",
        driver="GPKG",
    )

    stat_output = stat_areas[
        [
            "codice_area_statistica",
            "area_statistica",
        ]
    ].drop_duplicates()

    stat_output = stat_output.merge(
        aggregation,
        on="codice_area_statistica",
        how="left",
    )

    stat_output.to_csv(
        STAT_AREAS_OUT,
        index=False,
    )

    print()
    print("Calcolo completato.")
    print(
        f"Edifici salvati in: "
        f"{BUILDINGS_OUT}"
    )
    print(
        f"Aree statistiche salvate in: "
        f"{STAT_AREAS_OUT}"
    )

    print()
    print(
        "Edifici che soddisfano il criterio 300: "
        f"{buildings['meet_300'].sum()} / "
        f"{len(buildings)}"
    )

    print(
        "Aree statistiche che soddisfano il criterio 300: "
        f"{aggregation['meet_300'].sum()} / "
        f"{len(aggregation)}"
    )


if __name__ == "__main__":
    main()