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
RAW_DIR = Path("dataset/raw_data")

STAT_AREAS = PROCESSED_DIR / "stat_areas.gpkg"
PARKS = PROCESSED_DIR / "parks.gpkg"
GRID = PROCESSED_DIR.parent / "full/final_grid.geojson"
STAT_GRID = PROCESSED_DIR.parent / "full/aree_statistiche_grid.geojson"

BUILDINGS_OUT = PROCESSED_DIR / "buildings_330300.gpkg"
STAT_AREAS_OUT = PROCESSED_DIR / "bologna_3_30_300_stat_areas.csv"
CELL_300_BENEFIT_OUT = PROCESSED_DIR / "cell_300_benefit.csv"
CELL_300_COVERAGE_OUT = PROCESSED_DIR / "cell_300_coverage.csv"
CELL_3_COVERAGE_OUT = PROCESSED_DIR / "cell_3_coverage.csv"

# ---------------------------------------------------------------------
# Parameters
# ---------------------------------------------------------------------

CRS_METRIC = "EPSG:32632"

R_TREE = 50
R_PARK = 300
TREE_DENSITY = 0.01

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
    parks = gpd.read_file(PARKS, layer="parks").to_crs(CRS_METRIC)
    grid = gpd.read_file(GRID).to_crs(CRS_METRIC)

    print(f"Grid cells:        {len(grid)}")
    print(f"Aree statistiche: {len(stat_areas)}")
    print(f"Park polygons:     {len(parks)}")

    return stat_areas, parks, grid

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
        buildings[["building_id"]],
        geometry=buildings["centroid"],
        crs=buildings.crs,
    )

    area_ids = gpd.sjoin(
        centroids,
        stat_areas[["codice_area_statistica", "geometry"]],
        how="left",
        predicate="within",
    )[["building_id", "codice_area_statistica"]].drop_duplicates("building_id")

    buildings = (
        buildings.merge(area_ids, on="building_id", how="left")
        .dropna(subset=["codice_area_statistica"])
        .reset_index(drop=True)
    )

    print(f"Edifici assegnati a un'area statistica: {len(buildings)}")

    return buildings

# ---------------------------------------------------------------------
# Counterfactual Rule 30
# ---------------------------------------------------------------------

def compute_counterfactual_30(stat_areas, stat_grid):
    print("Calcolo controfattuale criterio 30...")

    areas = stat_areas[
        ["codice_area_statistica", "perc_canopy_cover_30", "geometry"]
    ].copy()

    areas["required_canopy_30"] = (
        0.30 * areas.geometry.area
        - areas["perc_canopy_cover_30"] / 100 * areas.geometry.area
    ).clip(lower=0)

    areas = areas[areas["required_canopy_30"] > 0]

    coverage = stat_grid[
        ["id", "codice_area_statistica", "intersect_area_statistica"]
    ].copy()

    coverage["cell_share"] = (
        coverage["intersect_area_statistica"]
        / coverage.groupby("id")["intersect_area_statistica"].transform("sum")
    )

    return coverage.merge(
        areas[["codice_area_statistica", "required_canopy_30"]],
        on="codice_area_statistica",
        how="inner",
    )

# ---------------------------------------------------------------------
# Rule 300
# ---------------------------------------------------------------------

def compute_rule_300(buildings, parks):
    parks = parks[["geometry"]].reset_index(drop=True)
    flags = np.zeros(len(buildings), dtype=bool)

    for i, geom in enumerate(tqdm(buildings.geometry, desc="Rule 300")):
        candidate_idx = list(
            parks.sindex.intersection(expand_bounds(geom, R_PARK))
        )

        if candidate_idx:
            flags[i] = (
                parks.geometry.iloc[candidate_idx].distance(geom) <= R_PARK
            ).any()

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

    cells = grid[["id", "geometry"]].rename(columns={"id": "cell_id"}).copy()
    cells["geometry"] = cells.geometry.buffer(R_PARK)

    coverage = gpd.sjoin(
        uncovered,
        cells,
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
        cell_benefit["benefit_300_count"]
        .fillna(0)
        .astype(int)
    )

    cell_benefit["benefit_300_share"] = (
        cell_benefit["benefit_300_count"] / len(uncovered)
    )

    return cell_benefit, coverage

# ---------------------------------------------------------------------
# Rule 3
# ---------------------------------------------------------------------

def compute_rule_3(buildings, trees, near_park_flags):
    trees = trees[["geometry"]].reset_index(drop=True)
    has_3_trees = np.zeros(len(buildings), dtype=bool)

    for i, centroid in enumerate(
        tqdm(buildings["centroid"], desc="Rule 3")
    ):
        candidate_idx = list(
            trees.sindex.intersection(expand_bounds(centroid, R_TREE))
        )

        if candidate_idx:
            has_3_trees[i] = (
                trees.geometry.iloc[candidate_idx].distance(centroid) <= R_TREE
            ).sum() >= 3

    return has_3_trees, has_3_trees | near_park_flags

# ---------------------------------------------------------------------
# Counterfactual Rule 3
# ---------------------------------------------------------------------

def compute_counterfactual_3(buildings, trees, grid, tree_density):
    print("Calcolo controfattuale criterio 3...")

    uncovered = buildings.loc[
        ~buildings["meet_3"],
        ["building_id", "centroid"]
    ].copy()

    centroids = gpd.GeoDataFrame(
        uncovered[["building_id"]],
        geometry=uncovered["centroid"],
        crs=buildings.crs,
    )

    counts = (
        gpd.sjoin(
            centroids,
            trees[["geometry"]],
            how="left",
            predicate="dwithin",
            distance=R_TREE,
        )
        .groupby("building_id")["index_right"]
        .count()
    )

    uncovered["existing_trees"] = (
        uncovered["building_id"].map(counts).fillna(0).astype(int)
    )

    uncovered["required_trees"] = 3 - uncovered["existing_trees"]
    uncovered["required_green_3"] = (
        uncovered["required_trees"] / tree_density
    )

    cells = grid[["id", "geometry"]].rename(columns={"id": "cell_id"}).copy()
    cells["geometry"] = cells.geometry.buffer(R_TREE)

    coverage = gpd.sjoin(
        centroids,
        cells,
        how="inner",
        predicate="intersects",
    )[["cell_id", "building_id"]].drop_duplicates()

    return coverage.merge(
        uncovered[
            [
                "building_id",
                "existing_trees",
                "required_trees",
                "required_green_3",
            ]
        ],
        on="building_id",
    )

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
    stat_areas, parks, grid = (load_layers())

    stat_grid = gpd.read_file(STAT_GRID)

    print("Righe:", len(stat_grid))
    print("Colonne:", stat_grid.columns.tolist())

    stat_grid["cell_share"] = (
        stat_grid["intersect_area_statistica"]
        / stat_grid.groupby("id")["intersect_area_statistica"].transform("sum")
    )

    print(
        stat_grid.loc[
            stat_grid["id"] == 11684,
            [
                "id",
                "codice_area_statistica",
                "area_statistica",
                "intersect_area_statistica",
                "cell_share",
            ],
        ]
    )

    print(
        stat_grid.groupby("id")["cell_share"].sum().describe()
    )
    buildings = download_buildings(stat_areas)

    buildings = (
        assign_buildings_to_statistical_areas(buildings,stat_areas)
    )
    verde = gpd.read_file(
        PROCESSED_DIR.parent / "verde.gpkg",
        layer="verde"
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

    trees = gpd.read_file(
        RAW_DIR / "alberi-manutenzioni.fgb"
    ).to_crs(CRS_METRIC)

    print("Alberi comunali:", len(trees))
    print("Geometry types:", trees.geometry.geom_type.value_counts())
    print("CRS:", trees.crs)

    print("Calcolo criterio 3...")

    (has_3_trees_flags,meet_3_flags,) = compute_rule_3(
        buildings,
        trees,
        near_park_flags,
    )

    buildings["has_3_trees"] = (has_3_trees_flags)
    buildings["meet_3"] = (meet_3_flags)

    coverage_3 = compute_counterfactual_3(
        buildings,
        trees,
        grid,
        tree_density=TREE_DENSITY
    )

    print(coverage_3.head())
    print("Righe:", len(coverage_3))
    print("Celle distinte:", coverage_3["cell_id"].nunique())
    print("Edifici distinti:", coverage_3["building_id"].nunique())

    print(
        coverage_3[["existing_trees", "required_trees", "required_green_3"]].describe()
    )

    coverage_3.to_csv(CELL_3_COVERAGE_OUT, index=False)

    coverage_30 = compute_counterfactual_30(
        stat_areas,
        stat_grid
    )

    print("\nCOUNTERFACTUAL 30")
    print("Righe:", len(coverage_30))
    print("Celle distinte:", coverage_30["id"].nunique())
    print("Aree statistiche distinte:", coverage_30["codice_area_statistica"].nunique())

    print(
        coverage_30[
            [
                "id",
                "codice_area_statistica",
                "cell_share",
                "required_canopy_30"
            ]
        ].head(10)
    )

    print(
        coverage_30[
            ["required_canopy_30"]
        ].describe()
    )

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
        f"{len(buildings)}\n"
    )

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
        f"{len(result_df)}\n"
    )

    print(f"Edifici salvati in: {BUILDINGS_OUT}")
    print(f"Indice salvato in:  {STAT_AREAS_OUT}")

if __name__ == "__main__":
    main()