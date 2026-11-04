import argparse
from itertools import combinations
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import yaml

# Post-hoc evaluation: same data and assumptions for every model.
ROOT = next(
    parent
    for parent in Path(__file__).resolve().parents
    if (parent / "dataset").is_dir() and (parent / "results").is_dir()
)

models = {
    "STD": "std",
    "Counterfactual": "std_330300",
    "MaxCoverage": "std_330300_maxcoverage",
}

parser = argparse.ArgumentParser(
    description="Compare post-hoc 3-30-300 KPIs, TALEA utility, and Jaccard"
)
parser.add_argument(
    "--scenario",
    choices=(
        "default",
        "tree_density_low", "tree_density_medium", "tree_density_high",
        "gamma_0", "gamma_low", "gamma_medium", "gamma_high",
    ),
    default="default",
    help="Sensitivity scenario in config/full/<scenario>.yaml (default: default)",
)
parser.add_argument(
    "--tree-density-street",
    type=float,
    default=None,
    help="Post-hoc override for the default baseline (trees/m² of street space)",
)
parser.add_argument(
    "--tree-density-yard",
    type=float,
    default=None,
    help="Post-hoc override for the default baseline (trees/m² of yard space)",
)
parser.add_argument(
    "--canopy-density-street",
    type=float,
    default=None,
    help="Post-hoc override for the default baseline (m² canopy/m² of street space)",
)
parser.add_argument(
    "--canopy-density-yard",
    type=float,
    default=None,
    help="Post-hoc override for the default baseline (m² canopy/m² of yard space)",
)
parser.add_argument(
    "--spatial-buffer-m",
    type=float,
    default=100.0,
    help="Buffer around cell polygons, in metres (default: 100)",
)
args = parser.parse_args()

density_fields = (
    "tree_density_street",
    "tree_density_yard",
    "canopy_density_street",
    "canopy_density_yard",
)
overrides = {
    "tree_density_street": args.tree_density_street,
    "tree_density_yard": args.tree_density_yard,
    "canopy_density_street": args.canopy_density_street,
    "canopy_density_yard": args.canopy_density_yard,
}
if args.scenario != "default" and any(v is not None for v in overrides.values()):
    parser.error(
        "Numeric overrides are allowed only for default: "
        "sensitivity scenario placements must match their YAML file."
    )

scenario_path = ROOT / "config" / "full" / f"{args.scenario}.yaml"
if not scenario_path.is_file():
    parser.error(f"Scenario profile not found: {scenario_path}")

with scenario_path.open(encoding="utf-8") as config_file:
    scenario_config = yaml.safe_load(config_file)

scenario_profiles = {}
for model in ("std_330300", "std_330300_maxcoverage"):
    profile = scenario_config.get(model) if isinstance(scenario_config, dict) else None
    if not isinstance(profile, dict):
        parser.error(f"Missing {model} profile in {scenario_path}")

    if profile.get("res_name") != args.scenario or profile.get("size") != "full":
        parser.error(
            f"{model} profile: res_name must be '{args.scenario}' "
            "and size must be 'full'."
        )
    if profile.get("max_cells") != 100:
        parser.error(
            f"{model} profile: this evaluation uses the 100-cell STD baseline; "
            "a max_cells sweep requires a dedicated evaluation."
        )

    values = {}
    for field in density_fields:
        try:
            value = float(profile[field])
        except (KeyError, TypeError, ValueError):
            parser.error(f"Missing or non-numeric {field} value for {model}")
        if not (np.isfinite(value) and value >= 0):
            parser.error(f"Invalid {field} value for {model}: {value}")
        values[field] = value
    scenario_profiles[model] = values

if scenario_profiles["std_330300"] != scenario_profiles["std_330300_maxcoverage"]:
    parser.error("The two 3-30-300 models must use the same densities.")

# The gamma sweep keeps physical densities fixed; the actual weight is
# recorded in the CSV files for reproducible comparisons.
scenario_gamma = None
if args.scenario.startswith("gamma_"):
    gamma_values = []
    for model in ("std_330300", "std_330300_maxcoverage"):
        try:
            gamma = float(scenario_config[model]["gamma_330300"])
        except (KeyError, TypeError, ValueError):
            parser.error(f"Missing or non-numeric gamma_330300 for {model}")
        if not np.isfinite(gamma):
            parser.error(f"Non-finite gamma_330300 for {model}")
        gamma_values.append(gamma)
    if not np.isclose(gamma_values[0], gamma_values[1], rtol=0, atol=1e-12):
        parser.error("The two models must use the same gamma_330300.")
    scenario_gamma = gamma_values[0]

density_values = scenario_profiles["std_330300"].copy()
density_values.update({key: val for key, val in overrides.items() if val is not None})
for key, value in density_values.items():
    if not (np.isfinite(value) and value >= 0):
        parser.error(f"{key} must be a finite number >= 0")

TREE_DENSITY_STREET = density_values["tree_density_street"]
TREE_DENSITY_YARD = density_values["tree_density_yard"]
CANOPY_DENSITY_STREET = density_values["canopy_density_street"]
CANOPY_DENSITY_YARD = density_values["canopy_density_yard"]
SPATIAL_BUFFER_M = args.spatial_buffer_m
if not (np.isfinite(SPATIAL_BUFFER_M) and SPATIAL_BUFFER_M > 0):
    parser.error("--spatial-buffer-m must be a finite number > 0")

# STD does not use tree/canopy data during optimization and remains the baseline.
# The other two models use the selected scenario's results.
result_names = {
    "STD": "default",
    "Counterfactual": args.scenario,
    "MaxCoverage": args.scenario,
}
solutions = {}
for name, folder in models.items():
    result_name = result_names[name]
    geojson_path = ROOT / "results" / "full" / folder / f"{result_name}.geojson"
    if not geojson_path.is_file():
        if args.scenario != "default":
            raise FileNotFoundError(
                f"Missing optimized result for {name} in scenario "
                f"'{args.scenario}': {geojson_path}. "
                f"Eseguire prima run_model --config {scenario_path} --model {folder} "
                "(STD always uses default)."
            )
        print(f"WARNING: result missing for {name}: {geojson_path}")
        continue
    solutions[name] = gpd.read_file(geojson_path)

if "STD" not in solutions:
    raise FileNotFoundError("STD default.geojson is required for comparison")

# Original utility reported by the STD solver.
std_solution = solutions["STD"]

if "utility" not in std_solution.columns:
    raise ValueError("Utility missing from the STD solution")

std_original_utility = std_solution["utility"].sum() / 100

# Independent reconstruction of the original TALEA utility.
# Parameters are read from the STD MiniZinc instance.

dzn_path = ROOT / "src/Minizinc/instances/std_instance.dzn"
dzn = dzn_path.read_text(encoding="utf-8")

def read_dzn_array(name):
    prefix = f"{name} = ["
    if prefix not in dzn:
        raise ValueError(f"Missing MiniZinc parameter: {name}")
    values = dzn.split(prefix, 1)[1].split("];", 1)[0]
    return np.fromstring(values, sep=",")

alpha_yard = float(dzn.split("alpha_yard = ", 1)[1].split(";", 1)[0])
top_k = int(dzn.split("top_k = ", 1)[1].split(";", 1)[0])

fields = [
    "street_space", "ext_space", "green_space",
    "num_areas", "num_trees", "macro_factors"
]

grid_ids = gpd.read_file(
    ROOT / "dataset/processed_data/full/final_grid.geojson",
    ignore_geometry=True
)["id"]

if grid_ids.isna().any() or grid_ids.duplicated().any():
    raise ValueError("Invalid grid IDs")

base = pd.DataFrame(
    {field: read_dzn_array(field) for field in fields},
    index=grid_ids.to_numpy()
)

# Global scaling references, computed across ALL cells.
max_street = base["street_space"].max()
max_yard = base["ext_space"].max()
max_areas = base["num_areas"].max()
max_green = base["green_space"].max()
max_trees = base["num_trees"].max()

# The GeoPackage contains ALL initial buildings: denominators must not exclude
# buildings unreachable from candidate cells.
buildings_path = ROOT / "dataset/processed_data/330300/buildings_330300.gpkg"
if not buildings_path.is_file():
    raise FileNotFoundError(f"Initial dataset not found: {buildings_path}")
buildings = gpd.read_file(
    buildings_path, layer="buildings_330300", ignore_geometry=True
)
required_building_columns = {"building_id", "meet_3", "n_trees_50m", "meet_300"}
if not required_building_columns.issubset(buildings.columns):
    raise ValueError(
        f"Missing fields in buildings_330300.gpkg: "
        f"{required_building_columns - set(buildings.columns)}"
    )
if buildings["building_id"].isna().any() or buildings["building_id"].duplicated().any():
    raise ValueError("Initial building IDs are missing or duplicated")
for column in ["meet_3", "meet_300"]:
    if (
        buildings[column].isna().any()
        or not buildings[column].isin([0, 1, False, True]).all()
    ):
        raise ValueError(f"Invalid {column} values in the initial dataset")
if buildings["n_trees_50m"].isna().any():
    raise ValueError("Missing n_trees_50m values in the initial dataset")

# KPI 3: buildings that do not meet the initial TALEA condition.
# 'meet_3' also treats buildings near a park as compliant.
# For each other building, deficit d_b is 3 minus existing trees.
noncompliant_3 = buildings.loc[
    buildings["meet_3"] == 0, ["building_id", "n_trees_50m"]
].copy()
noncompliant_3["required_trees"] = 3 - noncompliant_3["n_trees_50m"]
if (
    not noncompliant_3["required_trees"].isin([1, 2, 3]).all()
    or not (noncompliant_3["n_trees_50m"] >= 0).all()
):
    raise ValueError("Inconsistent initial Rule 3 deficits")

# Building-indexed series, including buildings without relationships.
deficit_3 = noncompliant_3.set_index("building_id")["required_trees"].astype(int)
initial_noncompliant_3 = len(deficit_3)
initial_missing_trees_3 = int(deficit_3.sum())
if initial_noncompliant_3 <= 0 or initial_missing_trees_3 <= 0:
    raise ValueError("No initial Rule 3 deficit")

# KPI 300: use the same complete denominator as the original version.
uncovered_300 = set(buildings.loc[buildings["meet_300"] == 0, "building_id"])
total_deficit_300 = len(uncovered_300)
if total_deficit_300 <= 0:
    raise ValueError("No initially uncovered buildings: P300 cannot be computed")

# KPI 30: initial canopy deficit by statistical area.
# The denominator also includes areas unreachable from cells.
stat_areas_path = ROOT / "dataset/processed_data/330300/stat_areas.gpkg"
stat_areas = gpd.read_file(stat_areas_path, layer="stat_areas").to_crs("EPSG:32632")

required_columns_30 = {"codice_area_statistica", "perc_canopy_cover_30"}
if not required_columns_30.issubset(stat_areas.columns):
    raise ValueError("Missing fields in the statistical areas dataset")

if (
    stat_areas["codice_area_statistica"].isna().any()
    or stat_areas["codice_area_statistica"].duplicated().any()
):
    raise ValueError("Statistical area IDs are missing or duplicated")

if stat_areas.geometry.isna().any() or stat_areas.geometry.is_empty.any():
    raise ValueError("Statistical area geometries are missing or empty")

canopy_pct = stat_areas["perc_canopy_cover_30"].astype(float)
if not (np.isfinite(canopy_pct).all() and canopy_pct.between(0, 100).all()):
    raise ValueError("Invalid initial canopy percentages")

stat_areas["required_canopy_30"] = (
    stat_areas.geometry.area * (0.30 - canopy_pct / 100)
).clip(lower=0)

# Only areas that are initially non-compliant.
deficit_30 = stat_areas.loc[
    stat_areas["required_canopy_30"] > 0,
    ["codice_area_statistica", "required_canopy_30"],
].set_index("codice_area_statistica")["required_canopy_30"]

initial_noncompliant_30 = len(deficit_30)
total_deficit_30 = float(deficit_30.sum())

if initial_noncompliant_30 <= 0 or total_deficit_30 <= 0:
    raise ValueError("No initial Rule 30 deficit")

# Precomputed spatial relationships: no new geometry calculations.
coverage_3 = pd.read_csv(ROOT / "dataset/processed_data/330300/cell_3_coverage.csv")
coverage_300 = pd.read_csv(ROOT / "dataset/processed_data/330300/cell_300_coverage.csv")
coverage_30 = pd.read_csv(ROOT / "dataset/processed_data/330300/cell_30_coverage.csv")

required_30_columns = {
    "cell_id",
    "codice_area_statistica",
    "cell_share",
    "required_canopy_30",
}

if not required_30_columns.issubset(coverage_30.columns):
    raise ValueError("Missing fields in Rule 30 CSV")

if coverage_30[list(required_30_columns)].isna().any().any():
    raise ValueError("Missing values in Rule 30 relationships")

if coverage_30.duplicated(["cell_id", "codice_area_statistica"]).any():
    raise ValueError("Duplicate cell-area relationships in Rule 30 CSV")

if not coverage_30["cell_share"].between(0, 1).all():
    raise ValueError("Invalid cell_share values")

# Each relationship must reference an initially non-compliant area
# and contain its correct initial deficit.
expected_deficit_30 = coverage_30["codice_area_statistica"].map(deficit_30)

if (
    expected_deficit_30.isna().any()
    or not np.isclose(
        coverage_30["required_canopy_30"], expected_deficit_30, rtol=1e-9, atol=1e-6
    ).all()
):
    raise ValueError("Rule 30 relationships do not match initial deficits")
if not {"cell_id", "building_id", "required_trees"}.issubset(coverage_3.columns):
    raise ValueError("Missing cell_id/building_id/required_trees fields in Rule 3 CSV")
if not {"cell_id", "building_id"}.issubset(coverage_300.columns):
    raise ValueError("Missing cell_id/building_id fields in Rule 300 CSV")
if (
    coverage_3[["cell_id", "building_id", "required_trees"]].isna().any().any()
    or coverage_300[["cell_id", "building_id"]].isna().any().any()
):
    raise ValueError("Missing IDs or deficits in coverage CSVs")
if coverage_3.duplicated(["cell_id", "building_id"]).any():
    raise ValueError("Duplicate cell-building relationships in cell_3_coverage.csv")
if not set(coverage_300["building_id"]).issubset(uncovered_300):
    raise ValueError("Rule 300 relationships do not match initially uncovered buildings")

# Rule 3 relationships must reference NON-compliant buildings and contain the
# same individual deficit from the GeoPackage, before evaluating the models.
expected_deficit = coverage_3["building_id"].map(deficit_3)
if (
    expected_deficit.isna().any()
    or not coverage_3["required_trees"].eq(expected_deficit).all()
):
    raise ValueError("Rule 3 relationships do not match GeoPackage deficits")

rows = []
selected_ids_by_model = {}
buffered_areas_by_model = {}
for name, solution in solutions.items():
    required = {"id", "street_cells", "yard_cells"}
    if not required.issubset(solution.columns):
        raise ValueError(
            f"Missing columns in {name} solution: {required - set(solution.columns)}"
        )
    if solution["id"].isna().any() or solution["id"].duplicated().any():
        raise ValueError(f"Cell IDs are missing or duplicated in {name} solution")
    if solution[["street_cells", "yard_cells"]].isna().any().any():
        raise ValueError(f"Missing allocations in {name} solution")
    if (solution[["street_cells", "yard_cells"]] < 0).any().any():
        raise ValueError(f"Negative allocations in {name} solution")

    # Active cell = strictly positive converted surface.
    selected_allocations = solution.loc[
        (solution["street_cells"] + solution["yard_cells"]) > 0,
        ["id", "street_cells", "yard_cells"],
    ].copy()
    selected = selected_allocations["id"]
    # Same grid for every model: IDs identify selected positions
    # without duplicate counts.
    selected_ids_by_model[name] = set(selected)

    # Spatial Jaccard: influence area is the union of converted cell polygons,
    # each extended by the configurable buffer. Build the buffer in a metric
    # CRS, never in degrees or EPSG:3857.
    if solution.crs is None:
        raise ValueError(f"Missing coordinate system in {name} solution")
    selected_geometries = solution.loc[selected_allocations.index, ["geometry"]]
    if (
        selected_geometries.geometry.isna().any()
        or selected_geometries.geometry.is_empty.any()
    ):
        raise ValueError(f"Selected geometries are missing or empty for {name}")
    if not selected_geometries.geometry.is_valid.all():
        raise ValueError(f"Selected geometries are invalid for {name}")
    buffered_areas_by_model[name] = (
        selected_geometries.to_crs("EPSG:32632")
        .geometry.buffer(SPATIAL_BUFFER_M)
        .union_all()
        if not selected_geometries.empty
        else None
    )

    # KPI 300 unchanged: a building reached by multiple cells counts once.
    covered_300 = int(
        coverage_300.loc[
            coverage_300["cell_id"].isin(selected), "building_id"
        ].nunique()
    )
    if covered_300 > total_deficit_300:
        raise ValueError(f"Inconsistent Rule 300 coverage for {name}")

    # KPI 3: trees added by each active cell.
    # Apply floor PER CELL, as in the MiniZinc model.
    selected_allocations["added_trees"] = np.floor(
        TREE_DENSITY_STREET * selected_allocations["street_cells"]
        + TREE_DENSITY_YARD * selected_allocations["yard_cells"]
    ).astype(int)
    trees_by_cell = selected_allocations.set_index("id")["added_trees"]

    # Each building receives trees from every active cell within reach
    # (50 m relationships computed during preprocessing).
    reachable_3 = coverage_3.loc[coverage_3["cell_id"].isin(selected)].copy()
    reachable_3["added_trees"] = reachable_3["cell_id"].map(trees_by_cell)
    if reachable_3["added_trees"].isna().any():
        raise ValueError(f"Rule 3 relationships lack a matching allocation for {name}")
    added_trees_by_building = (
        reachable_3.groupby("building_id")["added_trees"]
        .sum()
        .reindex(deficit_3.index, fill_value=0)
    )

    # g_b = min(d_b, reachable added trees): each building's benefit is
    # capped at its initial missing trees.
    gains_3 = added_trees_by_building.clip(upper=deficit_3)
    new_compliant_3 = int((gains_3 == deficit_3).sum())
    filled_deficit_3 = int(gains_3.sum())

    # KPI 30: canopy added by each active cell [m²].
    # No floor: canopy is a continuous surface.
    selected_allocations["added_canopy"] = (
        CANOPY_DENSITY_STREET * selected_allocations["street_cells"]
        + CANOPY_DENSITY_YARD * selected_allocations["yard_cells"]
    )

    canopy_by_cell = selected_allocations.set_index("id")["added_canopy"]

    # Relationships between selected cells and statistical areas.
    reachable_30 = coverage_30.loc[coverage_30["cell_id"].isin(selected)].copy()

    # Distribute canopy using cell_share.
    reachable_30["added_canopy_area"] = (
        reachable_30["cell_id"].map(canopy_by_cell) * reachable_30["cell_share"]
    )

    # Sum all cell contributions for each area.
    # Areas without reachable cells receive zero benefit.
    added_canopy_by_area = (
        reachable_30.groupby("codice_area_statistica")["added_canopy_area"]
        .sum()
        .reindex(deficit_30.index, fill_value=0.0)
    )

    # Cap the benefit at each area's initial deficit.
    gains_30 = added_canopy_by_area.clip(upper=deficit_30)

    # P30: total recovered deficit area.
    filled_deficit_30 = float(gains_30.sum())

    # C30: initially non-compliant areas reaching 30%.
    # Numerical tolerance: 1e-6 m².
    new_compliant_30 = int((added_canopy_by_area >= deficit_30 - 1e-6).sum())

    # Independent C30 check: rebuild the effective post-intervention
    # canopy percentage.
    areas_30 = stat_areas.set_index("codice_area_statistica").loc[deficit_30.index]

    initial_pct = areas_30["perc_canopy_cover_30"].astype(float)
    area_m2 = areas_30.geometry.area

    final_pct = initial_pct + 100 * added_canopy_by_area / area_m2

    # Use the same 1e-6 m² tolerance as the C30 calculation.
    recomputed_compliant = int((final_pct >= 30 - 100 * 1e-6 / area_m2).sum())

    if recomputed_compliant != new_compliant_30:
        raise ValueError(f"Inconsistent C30 result for {name}")

    rows.append(
        {
            "model": name,
            "tree_density_street": TREE_DENSITY_STREET,
            "tree_density_yard": TREE_DENSITY_YARD,
            "selected_cells": int(selected.nunique()),
            "initial_noncompliant_buildings_3": initial_noncompliant_3,
            "initial_missing_trees_3": initial_missing_trees_3,
            "new_buildings_meeting_3": new_compliant_3,
            "C3_percent": 100 * new_compliant_3 / initial_noncompliant_3,
            "P3_percent": 100 * filled_deficit_3 / initial_missing_trees_3,
            "canopy_density_street": CANOPY_DENSITY_STREET,
            "canopy_density_yard": CANOPY_DENSITY_YARD,
            "initial_noncompliant_areas_30": initial_noncompliant_30,
            "initial_missing_canopy_30_m2": total_deficit_30,
            "recovered_canopy_30_m2": filled_deficit_30,
            "new_areas_meeting_30": new_compliant_30,
            "P30_percent": 100 * filled_deficit_30 / total_deficit_30,
            "C30_percent": 100 * new_compliant_30 / initial_noncompliant_30,
            "initial_uncovered_buildings": total_deficit_300,
            "new_buildings_covered": covered_300,
            "P300_percent": 100 * covered_300 / total_deficit_300,
        }
    )

comparison = pd.DataFrame(rows)
if args.scenario != "default":
    comparison.insert(0, "scenario", args.scenario)
    comparison.insert(2, "placement", comparison["model"].map(result_names))
    if scenario_gamma is not None:
        comparison.insert(1, "gamma_330300", scenario_gamma)


# Aggregate 3-30-300 KPI: average of the three percentages.
comparison["KPI_330300_percent"] = comparison[
    ["P3_percent", "P30_percent", "P300_percent"]
].mean(axis=1)


# Post-hoc evaluation of the original TALEA utility.
# Same objective function and parameters for every model.
original_utility_by_model = {}

for name, solution in solutions.items():

    allocations = solution.loc[
        (solution["street_cells"] + solution["yard_cells"]) > 0,
        ["id", "street_cells", "yard_cells"]
    ]

    cell_data = base.reindex(allocations["id"].to_numpy())

    if cell_data.isna().any().any():
        raise ValueError(f"Missing cells in original data: {name}")

    benefit = (
        alpha_yard * allocations["yard_cells"].to_numpy() / max_yard
        + allocations["street_cells"].to_numpy() / max_street
    )

    penalty = (
        cell_data["num_areas"].to_numpy() / max_areas
        + cell_data["green_space"].to_numpy() / max_green
        + cell_data["num_trees"].to_numpy() / max_trees
        + 1e-8
    )

    utility = (
        cell_data["macro_factors"].to_numpy()
        * benefit / penalty
    ).sum() / top_k

    original_utility_by_model[name] = float(utility)

# Verify that the STD calculation matches the solver.
if not np.isclose(
    original_utility_by_model["STD"],
    std_original_utility,
    rtol=1e-7,
    atol=1e-7
):
    raise ValueError("STD utility is inconsistent")

# Add utility to the KPI comparison.
comparison["TALEA_original_utility"] = (
    comparison["model"].map(original_utility_by_model)
)

# Percentage change from the original STD utility.
comparison["TALEA_utility_change_percent"] = (
    100 * (
        comparison["TALEA_original_utility"] - std_original_utility
    ) / std_original_utility
)

print(comparison.to_string(index=False, float_format=lambda x: f"{x:.4f}"))


output_suffix = "" if args.scenario == "default" else f"_{args.scenario}"
output = ROOT / f"analysis/kpi_comparison{output_suffix}.csv"
output.parent.mkdir(parents=True, exist_ok=True)
comparison.to_csv(output, index=False)
print(f"\nComparison saved to: {output}")

# Jaccard comparison of cells selected by the different models.
# The first compares cell IDs; the second compares geometry after buffering
# selected POLYGONS. Geometries are already in EPSG:32632 (metres), not EPSG:3857.
jaccard_rows = []
for (model_a, ids_a), (model_b, ids_b) in combinations(
    selected_ids_by_model.items(), 2
):
    common = len(ids_a & ids_b)
    union = len(ids_a | ids_b)

    geom_a = buffered_areas_by_model[model_a]
    geom_b = buffered_areas_by_model[model_b]
    if geom_a is None or geom_b is None:
        # If either set is empty, overlap is zero; if both are empty,
        # Jaccard is undefined.
        spatial_intersection = 0.0
        spatial_union = (geom_a.area if geom_a is not None else 0.0) + (
            geom_b.area if geom_b is not None else 0.0
        )
    else:
        spatial_intersection = geom_a.intersection(geom_b).area
        spatial_union = geom_a.union(geom_b).area

    jaccard_rows.append(
        {
            "model_a": model_a,
            "model_b": model_b,
            "selected_cells_a": len(ids_a),
            "selected_cells_b": len(ids_b),
            "common_cells": common,
            "union_cells": union,
            "jaccard_percent": 100 * common / union if union else float("nan"),
            "spatial_buffer_m": SPATIAL_BUFFER_M,
            "spatial_intersection_m2": spatial_intersection,
            "spatial_union_m2": spatial_union,
            "spatial_jaccard_percent": (
                100 * spatial_intersection / spatial_union
                if spatial_union > 0
                else float("nan")
            ),
        }
    )

jaccard_comparison = pd.DataFrame(jaccard_rows)
if args.scenario != "default":
    jaccard_comparison.insert(0, "scenario", args.scenario)
    if scenario_gamma is not None:
        jaccard_comparison.insert(1, "gamma_330300", scenario_gamma)
if not jaccard_comparison.empty:
    print("\nExact-cell and spatial Jaccard (polygon buffer):")
    print(jaccard_comparison.to_string(index=False, float_format=lambda x: f"{x:.4f}"))

jaccard_output = ROOT / f"analysis/jaccard_comparison{output_suffix}.csv"
jaccard_comparison.to_csv(jaccard_output, index=False)
print(f"Jaccard comparison saved to: {jaccard_output}")
