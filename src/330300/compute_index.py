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
TREE_PIXELS = PROCESSED_DIR / "tree_pixels.gpkg"
PARKS = PROCESSED_DIR / "parks.gpkg"

BUILDINGS_OUT = PROCESSED_DIR / "buildings_330300.gpkg"
STAT_AREAS_OUT = (PROCESSED_DIR / "bologna_3_30_300_stat_areas.csv")

GRID = Path("dataset/processed_data/full/final_grid.geojson")

CELL_300_BENEFIT_OUT = (PROCESSED_DIR / "cell_300_benefit.csv")

CELL_300_COVERAGE_OUT = (PROCESSED_DIR / "cell_300_coverage.csv")

# ---------------------------------------------------------------------
# Parameters
# ---------------------------------------------------------------------

CRS_METRIC = "EPSG:32632"

R_TREE = 50
R_PARK = 300

# ---------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------

def expand_bounds(geom, distance):
    minx, miny, maxx, maxy = geom.bounds

    return (
        minx - distance,
        miny - distance,
        maxx + distance,
        maxy + distance,
    )

# ---------------------------------------------------------------------
# Load prepared layers
# ---------------------------------------------------------------------

def load_layers():
    print("Lettura layer preprocessati...")

    stat_areas = gpd.read_file(STAT_AREAS, layer="stat_areas").to_crs(CRS_METRIC)
    tree_pixels = gpd.read_file(TREE_PIXELS, layer="tree_pixels").to_crs(CRS_METRIC)
    parks = gpd.read_file(PARKS, layer="parks").to_crs(CRS_METRIC)
    grid = gpd.read_file(GRID).to_crs(CRS_METRIC)

    print(f"Grid cells:        {len(grid)}")
    print(f"Aree statistiche: {len(stat_areas)}")
    print(f"Tree pixels:       {len(tree_pixels)}")
    print(f"Park polygons:     {len(parks)}")

    return stat_areas, tree_pixels, parks, grid

# ---------------------------------------------------------------------
# Download residential buildings
# ---------------------------------------------------------------------

def download_buildings(stat_areas):
    print("Download edifici OSM...")

    bounding_polygon = stat_areas.to_crs(4326).geometry.union_all().convex_hull.buffer(0.01)

    buildings = ox.features_from_polygon(
        bounding_polygon,
        tags={"building": True},
    )

    buildings = buildings[
        buildings["building"].isin([
            "residential",
            "apartments",
            "house",
            "detached",
            "yes",
        ])
    ]

    buildings = buildings[["geometry"]].explode(index_parts=False)
    buildings = buildings.reset_index(drop=True).to_crs(CRS_METRIC)
    buildings["geometry"] = buildings.geometry.apply(make_valid)
    print(f"Edifici residenziali scaricati: "f"{len(buildings)}")

    return buildings

# ---------------------------------------------------------------------
# Assign buildings to statistical areas
# ---------------------------------------------------------------------

def assign_buildings_to_statistical_areas(buildings, stat_areas):
    print("Assegnazione edifici alle aree statistiche...")

    buildings = buildings.reset_index(drop=True)
    buildings["building_id"] = np.arange(len(buildings))
    buildings["centroid"] = buildings.geometry.centroid

    centroids = gpd.GeoDataFrame(
        buildings[["building_id", "centroid"]],
        geometry="centroid",
        crs=CRS_METRIC,
    )

    centroids = gpd.sjoin(
        centroids,
        stat_areas[["codice_area_statistica", "geometry"]],
        how="left",
        predicate="within",
    )[["building_id", "codice_area_statistica"]].drop_duplicates("building_id")

    buildings = buildings.merge(
        centroids,
        on="building_id",
        how="left",
    )

    buildings = buildings[
        buildings["codice_area_statistica"].notna()
    ].reset_index(drop=True)

    print(f"Edifici assegnati a un'area statistica: {len(buildings)}")

    return buildings


# ---------------------------------------------------------------------
# Rule 300
# ---------------------------------------------------------------------

def compute_rule_300(buildings, parks):
    parks = parks[["geometry"]].reset_index(drop=True)

    parks_geom = parks.geometry
    parks_sindex = parks.sindex

    flags = np.zeros(
        len(buildings),
        dtype=bool,
    )

    geometries = buildings.geometry.values

    for i in tqdm(
        range(len(buildings)),
        desc="Rule 300",
    ):
        geom = geometries[i]

        candidate_idx = list(
            parks_sindex.intersection(expand_bounds(geom,R_PARK,))
        )

        if not candidate_idx:
            continue

        distances = (
            parks_geom
            .iloc[candidate_idx]
            .distance(geom)
        )
        flags[i] = bool((distances <= R_PARK).any())

    return flags

# ---------------------------------------------------------------------
# Counterfactual Rule 300
# ---------------------------------------------------------------------

def compute_counterfactual_300(buildings, grid):
    print("Calcolo beneficio controfattuale criterio 300...")

    uncovered = buildings.loc[
        ~buildings["meet_300"],
        ["building_id", "geometry"]
    ]

    green_cells = grid[["id", "geometry"]].rename(columns={"id": "cell_id"}).copy()
    green_cells["geometry"] = green_cells.geometry.buffer(R_PARK)

    coverage = gpd.sjoin(
        uncovered,
        green_cells,
        how="inner",
        predicate="intersects",
    )[["cell_id", "building_id"]].drop_duplicates()

    benefit = (
        coverage.groupby("cell_id")["building_id"]
        .nunique()
        .rename("benefit_300_count")
    )

    cell_benefit = (
        grid[["id"]]
        .rename(columns={"id": "cell_id"})
        .merge(benefit, on="cell_id", how="left")
    )

    cell_benefit["benefit_300_count"] = (
        cell_benefit["benefit_300_count"].fillna(0).astype(int)
    )

    cell_benefit["benefit_300_share"] = (
        cell_benefit["benefit_300_count"] / len(uncovered)
    )

    return cell_benefit, coverage

# ---------------------------------------------------------------------
# Rule 3
# ---------------------------------------------------------------------

def compute_rule_3(
    buildings,
    tree_pixels,
    near_park_flags,
):
    trees = (
        tree_pixels[["geometry"]]
        .reset_index(drop=True)
    )

    trees_geom = trees.geometry
    trees_sindex = trees.sindex

    has_3_trees_flags = np.zeros(
        len(buildings),
        dtype=bool,
    )

    centroids = buildings["centroid"].values

    for i in tqdm(
        range(len(buildings)),
        desc="Rule 3",
    ):
        centroid = centroids[i]

        candidate_idx = list(
            trees_sindex.intersection(
                expand_bounds(centroid, R_TREE)
            )
        )

        if not candidate_idx:
            continue

        distances = (
            trees_geom
            .iloc[candidate_idx]
            .distance(centroid)
        )

        has_3_trees_flags[i] = (
            int(np.sum(distances <= R_TREE)) >= 3
        )

    # Approximation: >= 3 tree pixels within 50 m OR park within 300 m.
    meet_3_flags = (has_3_trees_flags | near_park_flags)

    return has_3_trees_flags, meet_3_flags

# ---------------------------------------------------------------------
# Aggregate per statistical area
# ---------------------------------------------------------------------

def aggregate_results(
    buildings,
    stat_areas,
):
    print("Aggregazione per area statistica...")

    aggregation = (
        buildings
        .groupby("codice_area_statistica")
        .agg(
            num_buildings=("building_id", "count"),
            num_buildings_meet_3=("meet_3","sum"),
            num_buildings_meet_300=("meet_300","sum"),
        )
        .reset_index()
    )

    aggregation["perc_buildings_near_3_trees"] = (
        aggregation["num_buildings_meet_3"]
        / aggregation["num_buildings"] 
        * 100
    )

    aggregation["perc_buildings_within_300m_park"] = (
        aggregation["num_buildings_meet_300"]
        / aggregation["num_buildings"] 
        * 100
    )

    result = stat_areas[[
        "codice_area_statistica",
        "area_statistica",
        "perc_canopy_cover_30",
        "geometry",
    ]].copy()

    result = result.merge(
        aggregation,
        on="codice_area_statistica",
        how="left",
    )

    result["meet_3"] = (result["perc_buildings_near_3_trees"] >= 100)
    result["meet_30"] = (result["perc_canopy_cover_30"] >= 30)
    result["meet_300"] = (result["perc_buildings_within_300m_park"] >= 100)

    result["num_conditions_met"] = (
        result[[
            "meet_3",
            "meet_30",
            "meet_300",
        ]]
        .astype(int)
        .sum(axis=1)
    )

    return result

# ---------------------------------------------------------------------
# Save results
# ---------------------------------------------------------------------

def save_results(buildings, result):
    buildings_out = buildings.drop(columns=["centroid"])

    buildings_out.to_file(
        BUILDINGS_OUT,
        layer="buildings_330300",
        driver="GPKG",
    )

    result = result.rename(
        columns={
            "codice_area_statistica": "stat_area_id",
            "area_statistica": "stat_area_name",
        }
    )

    # Convert geometry explicitly after leaving GeoDataFrame semantics.
    result_df = pd.DataFrame(result.copy())

    result_df["geometry"] = (result.geometry.to_wkt())

    result_df = result_df[[
        "stat_area_id",
        "stat_area_name",
        "geometry",
        "perc_buildings_near_3_trees",
        "perc_canopy_cover_30",
        "perc_buildings_within_300m_park",
        "num_conditions_met",
        "meet_3",
        "meet_30",
        "meet_300",
    ]]

    result_df.to_csv(
        STAT_AREAS_OUT,
        index=False,
    )

    return result_df

# ---------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------

def main():
    stat_areas, tree_pixels, parks, grid = (load_layers())
    buildings = download_buildings(stat_areas)

    buildings = (
        assign_buildings_to_statistical_areas(buildings,stat_areas)
    )

    print("Calcolo criterio 300...")
    near_park_flags = compute_rule_300(
        buildings,
        parks,
    )
    buildings["near_park"] = (near_park_flags)
    buildings["meet_300"] = (near_park_flags)

    # counterfactual benefit
    cell_benefit_300, coverage_300 = (
        compute_counterfactual_300(
            buildings,
            grid,
        )
    )

    cell_benefit_300.to_csv(
        CELL_300_BENEFIT_OUT,
        index=False,
    )

    coverage_300.to_csv(
        CELL_300_COVERAGE_OUT,
        index=False,
    )

    print(
        "Celle con beneficio 300 > 0: "
        f"{(cell_benefit_300['benefit_300_count'] > 0).sum()} "
        f"/ {len(cell_benefit_300)}"
    )

    print(
        "Massimo numero di nuovi edifici coperti "
        "da una singola cella: "
        f"{cell_benefit_300['benefit_300_count'].max()}"
    )

    print("Calcolo criterio 3...")

    (has_3_trees_flags,meet_3_flags,) = compute_rule_3(
        buildings,
        tree_pixels,
        near_park_flags,
    )

    buildings["has_3_trees"] = (has_3_trees_flags)
    buildings["meet_3"] = (meet_3_flags)

    result = aggregate_results(
        buildings,
        stat_areas,
    )

    result_df = save_results(
        buildings,
        result,
    )

    print()
    print("=" * 80)
    print("CALCOLO 3-30-300 COMPLETATO")
    print("=" * 80)

    print(
        "Edifici che soddisfano il criterio 3:   "
        f"{buildings['meet_3'].sum()} / "
        f"{len(buildings)}"
    )

    print(
        "Edifici che soddisfano il criterio 300: "
        f"{buildings['meet_300'].sum()} / "
        f"{len(buildings)}"
    )

    print()

    print(
        "Aree che soddisfano il criterio 3:   "
        f"{result_df['meet_3'].sum()} / "
        f"{len(result_df)}"
    )

    print(
        "Aree che soddisfano il criterio 30:  "
        f"{result_df['meet_30'].sum()} / "
        f"{len(result_df)}"
    )

    print(
        "Aree che soddisfano il criterio 300: "
        f"{result_df['meet_300'].sum()} / "
        f"{len(result_df)}"
    )

    print()
    print(f"Edifici salvati in: {BUILDINGS_OUT}")
    print(f"Indice salvato in:  {STAT_AREAS_OUT}")

if __name__ == "__main__":
    main()