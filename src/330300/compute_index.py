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
CELL_300_COVERAGE_OUT = PROCESSED_DIR / "cell_300_coverage.csv"
CELL_3_COVERAGE_OUT = PROCESSED_DIR / "cell_3_coverage.csv"
CELL_30_COVERAGE_OUT = PROCESSED_DIR / "cell_30_coverage.csv"

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

    return minx - distance, miny - distance, maxx + distance, maxy + distance


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

    bounding_polygon = (
        stat_areas.to_crs(4326).geometry.union_all().convex_hull.buffer(0.01)
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

    buildings = buildings[["geometry"]].explode(index_parts=False)
    buildings = buildings.reset_index(drop=True).to_crs(CRS_METRIC)
    buildings["geometry"] = buildings.geometry.apply(make_valid)
    print(f"Edifici residenziali scaricati: {len(buildings)}")

    return buildings


# ---------------------------------------------------------------------
# Assign buildings to statistical areas
# ---------------------------------------------------------------------


def assign_buildings_to_statistical_areas(buildings, stat_areas):
    print("Assegnazione edifici alle aree statistiche...")

    buildings["building_id"] = buildings.index
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

    # Deficit residuo di canopy della singola area statistica [m²].
    # L'area statistica è ricavata dalla geometria metrica del poligono.
    areas["required_canopy_30"] = (
        areas.geometry.area * (0.30 - areas["perc_canopy_cover_30"] / 100)
    ).clip(lower=0)

    areas = areas[areas["required_canopy_30"] > 0]

    coverage = stat_grid[
        ["id", "codice_area_statistica", "intersect_area_statistica"]
    ].copy()

    # Una sola relazione per coppia cella-area, anche se il layer di
    # intersezione contiene più frammenti geometrici della stessa coppia.
    coverage = (
        coverage.groupby(["id", "codice_area_statistica"], as_index=False)[
            "intersect_area_statistica"
        ].sum()
    )

    # Quota fisica della cella ricadente in ciascuna area statistica.
    # In MiniZinc va applicata una sola volta ad added_canopy_i.
    coverage["cell_share"] = coverage["intersect_area_statistica"] / coverage.groupby(
        "id"
    )["intersect_area_statistica"].transform("sum")

    coverage = coverage.rename(columns={"id": "cell_id"}).merge(
        areas[["codice_area_statistica", "required_canopy_30"]],
        on="codice_area_statistica",
        how="inner",
    )

    return coverage[
        ["cell_id", "codice_area_statistica", "cell_share", "required_canopy_30"]
    ]


# ---------------------------------------------------------------------
# Rule 300
# ---------------------------------------------------------------------


def compute_rule_300(buildings, parks):
    flags = np.zeros(len(buildings), dtype=bool)

    for i, geom in enumerate(tqdm(buildings.geometry, desc="Rule 300")):
        candidate_idx = list(parks.sindex.intersection(expand_bounds(geom, R_PARK)))

        if candidate_idx:
            flags[i] = (
                parks.geometry.iloc[candidate_idx].distance(geom) <= R_PARK
            ).any()

    return flags


# ---------------------------------------------------------------------
# Counterfactual Rule 300
# ---------------------------------------------------------------------


def compute_counterfactual_300(buildings, grid):
    print("Calcolo copertura controfattuale criterio 300...")

    uncovered = buildings.loc[
        ~buildings["meet_300"],
        ["building_id", "codice_area_statistica", "geometry"],
    ].copy()

    # Deficit residuo dell'area: numero di edifici che non soddisfano il criterio 300.
    deficit_300 = (
        uncovered.groupby("codice_area_statistica")
        .size()
        .rename("deficit_300_area")
    )

    cells = grid[["id", "geometry"]].rename(columns={"id": "cell_id"})
    cells["geometry"] = cells.geometry.buffer(R_PARK)

    coverage = gpd.sjoin(
        uncovered,
        cells,
        how="inner",
        predicate="intersects",
    )[["cell_id", "building_id", "codice_area_statistica"]].drop_duplicates(
        ["cell_id", "building_id"]
    )

    coverage = coverage.merge(
        deficit_300.reset_index(),
        on="codice_area_statistica",
        how="left",
    )

    return coverage


# ---------------------------------------------------------------------
# Rule 3
# ---------------------------------------------------------------------


def compute_rule_3(buildings, trees, near_park_flags):
    n_trees = np.zeros(len(buildings), dtype=int)

    for i, centroid in enumerate(tqdm(buildings["centroid"], desc="Rule 3")):
        candidate_idx = list(trees.sindex.intersection(expand_bounds(centroid, R_TREE)))

        if candidate_idx:
            n_trees[i] = (
                trees.geometry.iloc[candidate_idx].distance(centroid) <= R_TREE
            ).sum()

    has_3_trees = n_trees >= 3
    meet_3 = has_3_trees | np.asarray(near_park_flags, dtype=bool)

    score_3 = np.minimum(n_trees / 3.0, 1.0)

    # Per l'assunzione adottata, la vicinanza a un parco
    # equivale al pieno soddisfacimento del criterio 3.
    score_3[np.asarray(near_park_flags, dtype=bool)] = 1.0

    return has_3_trees, meet_3, n_trees, score_3


# ---------------------------------------------------------------------
# Counterfactual Rule 3
# ---------------------------------------------------------------------


def compute_counterfactual_3(buildings, grid):
    print("Calcolo controfattuale criterio 3...")

    # Solo edifici che non soddisfano già il criterio 3.
    # Questo esclude sia edifici con >= 3 alberi sia edifici near_park.
    uncovered = buildings.loc[
        ~buildings["meet_3"],
        [
            "building_id",
            "codice_area_statistica",
            "centroid",
            "n_trees_50m",
        ],
    ].copy()

    uncovered["existing_trees"] = uncovered["n_trees_50m"].astype(int)

    # Deficit residuo del singolo edificio rispetto alla soglia dei 3 alberi.
    uncovered["required_trees"] = (
        (3 - uncovered["existing_trees"]).clip(lower=0, upper=3).astype(int)
    )

    # Deficit totale dell'area, espresso in unità normalizzate sul requisito di 3 alberi.
    deficit_3 = (
        uncovered.assign(deficit_building=uncovered["required_trees"] / 3.0)
        .groupby("codice_area_statistica")["deficit_building"]
        .sum()
        .rename("deficit_3_area")
    )

    centroids = gpd.GeoDataFrame(
        uncovered[["building_id", "codice_area_statistica"]],
        geometry=uncovered["centroid"],
        crs=buildings.crs,
    )

    cells = grid[["id", "geometry"]].rename(columns={"id": "cell_id"})
    cells["geometry"] = cells.geometry.buffer(R_TREE)

    coverage = gpd.sjoin(
        centroids,
        cells,
        how="inner",
        predicate="intersects",
    )[["cell_id", "building_id", "codice_area_statistica"]].drop_duplicates(
        ["cell_id", "building_id"]
    )

    coverage = coverage.merge(
        uncovered[["building_id", "existing_trees", "required_trees"]],
        on="building_id",
        how="left",
    ).merge(
        deficit_3.reset_index(),
        on="codice_area_statistica",
        how="left",
    )

    # Contributi elementari mantenuti per compatibilità/diagnostica.
    # Il benefit_3_ia finale dipende da added_trees_i in MiniZinc e va poi
    # diviso per deficit_3_area; qui non si assume alcun added_trees fisso.
    coverage["benefit_tree_1"] = np.where(
        coverage["required_trees"] >= 1, 1.0 / 3.0, 0.0
    )

    coverage["benefit_tree_2"] = np.where(
        coverage["required_trees"] >= 2, 1.0 / 3.0, 0.0
    )

    coverage["benefit_tree_3"] = np.where(
        coverage["required_trees"] >= 3, 1.0 / 3.0, 0.0
    )

    return coverage


# ---------------------------------------------------------------------
# Counterfactual diagnostics
# ---------------------------------------------------------------------


def validate_counterfactual_coverages(coverage_3, coverage_30, coverage_300):
    print("Controlli diagnostici coverage controfattuali...")

    if not coverage_3["required_trees"].isin([1, 2, 3]).all():
        invalid = sorted(coverage_3.loc[
            ~coverage_3["required_trees"].isin([1, 2, 3]), "required_trees"
        ].unique())
        raise ValueError(f"required_trees contiene valori non validi: {invalid}")

    if not (coverage_3["deficit_3_area"] > 0).all():
        raise ValueError("Esistono aree nel coverage 3 con deficit_3_area <= 0")

    if not (coverage_30["required_canopy_30"] > 0).all():
        raise ValueError("Esistono aree nel coverage 30 con required_canopy_30 <= 0")

    if not (coverage_300["deficit_300_area"] > 0).all():
        raise ValueError("Esistono aree nel coverage 300 con deficit_300_area <= 0")

    if coverage_3.duplicated(["cell_id", "building_id"]).any():
        raise ValueError("Duplicati (cell_id, building_id) nel coverage 3")

    if coverage_300.duplicated(["cell_id", "building_id"]).any():
        raise ValueError("Duplicati (cell_id, building_id) nel coverage 300")

    if coverage_30.duplicated(["cell_id", "codice_area_statistica"]).any():
        raise ValueError(
            "Duplicati (cell_id, codice_area_statistica) nel coverage 30"
        )

    print("Controlli diagnostici coverage: OK")


# ---------------------------------------------------------------------
# Aggregate per statistical area
# ---------------------------------------------------------------------


def aggregate_results(buildings, stat_areas):
    print("Aggregazione per area statistica...")

    aggregation = (
        buildings.groupby("codice_area_statistica")
        .agg(
            num_buildings=("building_id", "count"),
            num_buildings_meet_3=("meet_3", "sum"),
            num_buildings_meet_300=("meet_300", "sum"),
            score_3=("score_3", "mean"),
            score_300=("score_300", "mean"),
        )
        .reset_index()
    )

    aggregation["perc_buildings_near_3_trees"] = (
        aggregation["num_buildings_meet_3"] / aggregation["num_buildings"] * 100
    )

    aggregation["perc_buildings_within_300m_park"] = (
        aggregation["num_buildings_meet_300"] / aggregation["num_buildings"] * 100
    )

    result = stat_areas[
        [
            "codice_area_statistica",
            "area_statistica",
            "perc_canopy_cover_30",
            "geometry",
        ]
    ].copy()

    result = result.merge(
        aggregation,
        on="codice_area_statistica",
        how="left",
    )

    result["score_30"] = (result["perc_canopy_cover_30"] / 30.0).clip(
        lower=0.0, upper=1.0
    )

    result["meet_3"] = result["perc_buildings_near_3_trees"] >= 100
    result["meet_30"] = result["perc_canopy_cover_30"] >= 30
    result["meet_300"] = result["perc_buildings_within_300m_park"] >= 100

    result["index_330300"] = (
        result["score_3"] + result["score_30"] + result["score_300"]
    ) / 3.0

    result["num_conditions_met"] = result[["meet_3", "meet_30", "meet_300"]].sum(axis=1)

    return result


# ---------------------------------------------------------------------
# Save results
# ---------------------------------------------------------------------


def save_results(buildings, result):
    buildings.drop(columns=["centroid"]).to_file(
        BUILDINGS_OUT, layer="buildings_330300", driver="GPKG"
    )

    result = result.rename(
        columns={
            "codice_area_statistica": "stat_area_id",
            "area_statistica": "stat_area_name",
        }
    )

    result_df = pd.DataFrame(result)

    result_df["geometry"] = result.geometry.to_wkt()

    result_df = result_df[[
        "stat_area_id",
        "stat_area_name",
        "geometry",
        "perc_buildings_near_3_trees",
        "perc_canopy_cover_30",
        "perc_buildings_within_300m_park",
        "score_3",
        "score_30",
        "score_300",
        "index_330300",
        "num_conditions_met",
        "meet_3",
        "meet_30",
        "meet_300",
    ]]

    result_df.to_csv(STAT_AREAS_OUT, index=False)


# ---------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------


def main():
    stat_areas, parks, grid = load_layers()

    stat_grid = gpd.read_file(STAT_GRID)

    buildings = download_buildings(stat_areas)

    buildings = assign_buildings_to_statistical_areas(buildings, stat_areas)

    print("Calcolo criterio 300...")
    buildings["near_park"] = compute_rule_300(buildings, parks)
    buildings["meet_300"] = buildings["near_park"]
    buildings["score_300"] = buildings["meet_300"].astype(float)

    trees = gpd.read_file(RAW_DIR / "alberi-manutenzioni.fgb").to_crs(CRS_METRIC)

    print("Calcolo criterio 3...")

    has_3_trees_flags, meet_3_flags, n_trees, score_3 = compute_rule_3(
        buildings, trees, buildings["near_park"]
    )

    buildings["has_3_trees"] = has_3_trees_flags
    buildings["meet_3"] = meet_3_flags
    buildings["n_trees_50m"] = n_trees
    buildings["score_3"] = score_3

    # counterfactual 
    coverage_300 = compute_counterfactual_300(buildings, grid)
    coverage_300.to_csv(CELL_300_COVERAGE_OUT, index=False)

    coverage_3 = compute_counterfactual_3(buildings, grid)
    coverage_3.to_csv(CELL_3_COVERAGE_OUT, index=False)

    coverage_30 = compute_counterfactual_30(stat_areas, stat_grid)
    coverage_30.to_csv(CELL_30_COVERAGE_OUT, index=False)

    validate_counterfactual_coverages(coverage_3, coverage_30, coverage_300)

    result = aggregate_results(buildings, stat_areas)

    print("\nRange score_3:", result["score_3"].min(), result["score_3"].max())
    print("Range score_30:", result["score_30"].min(), result["score_30"].max())
    print("Range score_300:", result["score_300"].min(), result["score_300"].max())
    print("Range index_330300:", result["index_330300"].min(), result["index_330300"].max())

    save_results(buildings, result)

    print(
        f"\n{'=' * 80}\n"
        "CALCOLO 3-30-300 COMPLETATO\n"
        f"{'=' * 80}\n"
        f"Edifici che soddisfano il criterio 3:   {buildings['meet_3'].sum()} / {len(buildings)}\n"
        f"Edifici che soddisfano il criterio 300: {buildings['meet_300'].sum()} / {len(buildings)}\n\n"
        f"Aree che soddisfano il criterio 3:   {result['meet_3'].sum()} / {len(result)}\n"
        f"Aree che soddisfano il criterio 30:  {result['meet_30'].sum()} / {len(result)}\n"
        f"Aree che soddisfano il criterio 300: {result['meet_300'].sum()} / {len(result)}\n\n"
        f"Edifici salvati in: {BUILDINGS_OUT}\n"
        f"Indice salvato in:  {STAT_AREAS_OUT}"
    )


if __name__ == "__main__":
    main()
