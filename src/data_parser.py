import argparse
from dataclasses import dataclass
from pathlib import Path
from warnings import filterwarnings

import geopandas as gpd
import numpy as np
import pandas as pd

import utils

filterwarnings("ignore")

WORKING_DIR_PATH = Path.cwd()
SRC_DIR_PATH = WORKING_DIR_PATH.joinpath("src")
INSTANCE_DIR_PATH = SRC_DIR_PATH.joinpath("Minizinc", "instances")
PROCESSED_DATA_DIR_PATH = WORKING_DIR_PATH.joinpath("dataset", "processed_data")
CENTER_GRID_DIR_PATH = PROCESSED_DATA_DIR_PATH.joinpath("center")
FULL_GRID_DIR_PATH = PROCESSED_DATA_DIR_PATH.joinpath("full")


MODELS_330300 = ("std_330300", "std_330300_maxcoverage")


@dataclass
class BaseData:
    grid: gpd.GeoDataFrame
    num_cells: int
    street_space: np.ndarray
    ext_space: np.ndarray
    green_space: np.ndarray
    num_areas: np.ndarray
    num_trees: np.ndarray
    macro_factors: np.ndarray
    full_space: np.ndarray

    def common_instance(self, top_k, beta_streets, alpha_yards):
        return (
            self.num_cells, top_k, beta_streets, alpha_yards,
            self.street_space, self.ext_space, self.green_space,
            self.num_areas, self.num_trees, self.macro_factors,
            self.full_space,
        )


@dataclass
class CoverageData:
    three: pd.DataFrame
    thirty: pd.DataFrame
    three_hundred: pd.DataFrame
    cell_positions: dict
    area_positions: dict


def _load_base_data(size):
    if size == "center":
        path = CENTER_GRID_DIR_PATH
    elif size == "full":
        path = FULL_GRID_DIR_PATH
    else:
        raise ValueError(f"Unsupported grid size: {size}")

    grid = gpd.read_file(path / "final_grid.geojson")
    grid.set_index("id", inplace=True)
    areas = gpd.read_file(path / "aree_statistiche_grid.geojson").sort_values(by="id")
    areas = areas[areas["id"].isin(grid.index)].copy()
    population = pd.read_csv(
        PROCESSED_DATA_DIR_PATH / "densità_per_area_statistica.csv", sep=";"
    )
    macro_areas = gpd.read_file(PROCESSED_DATA_DIR_PATH / "aree_statistiche_macro.geojson")

    macro_factors = utils.macro_factor_per_area(areas, macro_areas)
    densities = utils.density_per_area(areas, population)
    densities.set_index("id", inplace=True)
    gpd.GeoDataFrame(
        densities, geometry=grid.geometry, crs="EPSG:3857"
    ).to_file(path / "densities_grid.geojson", driver="GeoJSON")

    full_space = utils.full_space_per_area(areas)
    num_cells = len(grid)
    green_space = np.zeros(num_cells, dtype=float)
    street_space = np.zeros(num_cells, dtype=float)
    ext_space = np.zeros(num_cells, dtype=float)
    num_areas = np.zeros(num_cells, dtype=float)
    num_trees = np.zeros(num_cells, dtype=float)

    # Retain the source ordering and numerical adjustments of the original parser.
    for idx, cell_id in enumerate(grid.index):
        row = grid.loc[cell_id]
        green_space[idx] = min(row["green_area"] + 1, full_space[idx])
        street_space[idx] = row["road_area"]
        ext_space[idx] = row["free_space_area"]
        num_areas[idx] = float(row["free_space_number"]) + (1 if street_space[idx] > 0 else 0)
        num_trees[idx] = float(row["tree_number"]) + 1

    # The source grid and its surface attributes use EPSG:3857 planar areas.
    # Convert every model's physical surface inputs to metric areas (UTM 32N).
    # Keep dimensionless macro_factors and the tree/fragment counts unchanged.
    # Applying this uniformly also preserves the existing 3-30-300 instances.
    grid_area = grid.geometry.area.to_numpy()
    metric_area = grid.to_crs("EPSG:32632").geometry.area.to_numpy()
    if np.any(~np.isfinite(grid_area)) or np.any(grid_area <= 0):
        raise ValueError("Grid contains invalid or non-positive projected areas")
    if np.any(~np.isfinite(metric_area)) or np.any(metric_area <= 0):
        raise ValueError("Grid contains invalid or non-positive metric areas")
    factor = metric_area / grid_area
    street_space *= factor
    ext_space *= factor
    green_space *= factor
    full_space *= factor

    return BaseData(
        grid, num_cells, street_space, ext_space, green_space,
        num_areas, num_trees, macro_factors, full_space,
    )


def _standard_instance(model, base, top_k, beta_streets, alpha_yards, alpha_uhei):
    common = base.common_instance(top_k, beta_streets, alpha_yards)
    if model == "std":
        return common
    if model == "diff":
        uhei = base.grid["weighted_uhei"].to_numpy(dtype=float)
        return (*common[:4], alpha_uhei, *common[4:], uhei)
    if model == "inverse_uhei":
        inverse_uhei = base.grid["inverse_uhei"]
        return (*common[:4], inverse_uhei.quantile(0.95), inverse_uhei.quantile(0.05), *common[4:])
    if model == "ndvi":
        ndvi = base.grid["weighted_ndvi"].to_numpy(dtype=float)
        return (*common[:4], 0.8, 0.0, *common[4:], ndvi)
    raise ValueError(f"Unsupported model: {model}")


def _load_coverage(base):
    directory = PROCESSED_DATA_DIR_PATH / "330300"
    three = pd.read_csv(directory / "cell_3_coverage.csv")
    thirty = pd.read_csv(directory / "cell_30_coverage.csv")
    three_hundred = pd.read_csv(directory / "cell_300_coverage.csv")
    cell_positions = {cell_id: pos for pos, cell_id in enumerate(base.grid.index, start=1)}
    area_values = pd.concat(
        [three["codice_area_statistica"], thirty["codice_area_statistica"],
         three_hundred["codice_area_statistica"]], ignore_index=True,
    ).dropna().drop_duplicates().tolist()
    area_positions = {area: pos for pos, area in enumerate(area_values, start=1)}
    return CoverageData(three, thirty, three_hundred, cell_positions, area_positions)


def _sort_relations(key, total, *values):
    """Stable sort of parallel arrays, followed by 1-based CSR offsets."""
    order = np.argsort(key, kind="stable")
    return (key[order], *(value[order] for value in values), utils.csr_offsets(key[order], total))


def _criterion_3_counterfactual(coverage):
    three = coverage.three
    counts = (
        three.groupby(["cell_id", "codice_area_statistica", "required_trees"])
        .size().unstack(fill_value=0)
        .reindex(columns=[1, 2, 3], fill_value=0)
        .rename(columns={1: "count_req1", 2: "count_req2", 3: "count_req3"})
        .reset_index()
    )
    deficits = three[["cell_id", "codice_area_statistica", "deficit_3_area"]].drop_duplicates(
        ["cell_id", "codice_area_statistica"]
    )
    relations = counts.merge(deficits, on=["cell_id", "codice_area_statistica"], how="left")
    relations = relations[relations["cell_id"].isin(coverage.cell_positions)].copy()
    return (
        relations["cell_id"].map(coverage.cell_positions).to_numpy(dtype=int),
        relations["codice_area_statistica"].map(coverage.area_positions).to_numpy(dtype=int),
        relations["count_req1"].to_numpy(dtype=int),
        relations["count_req2"].to_numpy(dtype=int),
        relations["count_req3"].to_numpy(dtype=int),
        relations["deficit_3_area"].to_numpy(dtype=float),
    )


def _criterion_30(coverage):
    relations = coverage.thirty[
        ["cell_id", "codice_area_statistica", "cell_share", "required_canopy_30"]
    ].copy()
    relations = relations[relations["cell_id"].isin(coverage.cell_positions)].copy()
    return (
        relations["cell_id"].map(coverage.cell_positions).to_numpy(dtype=int),
        relations["codice_area_statistica"].map(coverage.area_positions).to_numpy(dtype=int),
        relations["cell_share"].to_numpy(dtype=float),
        relations["required_canopy_30"].to_numpy(dtype=float),
    )


def _criterion_300_counterfactual(coverage):
    relations = coverage.three_hundred.groupby(
        ["cell_id", "codice_area_statistica"], as_index=False
    ).agg(gain_count=("building_id", "count"), deficit_300_area=("deficit_300_area", "first"))
    relations = relations[relations["cell_id"].isin(coverage.cell_positions)].copy()
    return (
        relations["cell_id"].map(coverage.cell_positions).to_numpy(dtype=int),
        relations["codice_area_statistica"].map(coverage.area_positions).to_numpy(dtype=int),
        relations["gain_count"].to_numpy(dtype=int),
        relations["deficit_300_area"].to_numpy(dtype=float),
    )


def _initial_330300_deficits():
    """Full initial 3-30-300 deficits, including locations with no reachable cells."""
    directory = PROCESSED_DATA_DIR_PATH / "330300"
    buildings = gpd.read_file(
        directory / "buildings_330300.gpkg",
        layer="buildings_330300",
        ignore_geometry=True,
    )
    missing_3 = buildings["meet_3"].eq(False)
    total_3 = int(
        (3 - buildings.loc[missing_3, "n_trees_50m"].astype(int))
        .clip(lower=0, upper=3)
        .sum()
    )
    total_300 = int(buildings["meet_300"].eq(False).sum())

    # Same deficit definition as compute_counterfactual_30(), prior to coverage joins.
    areas = gpd.read_file(
        directory / "stat_areas.gpkg", layer="stat_areas"
    ).to_crs("EPSG:32632")
    total_30 = float((
        areas.geometry.area *
        (0.30 - areas["perc_canopy_cover_30"].astype(float) / 100.0)
    ).clip(lower=0).sum())

    return total_3, total_30, total_300


def _criterion_3_maxcoverage(coverage, total_deficit):
    relations = coverage.three[coverage.three["cell_id"].isin(coverage.cell_positions)].copy()
    relations = relations.drop_duplicates(subset=["cell_id", "building_id"])
    building_codes, building_values = pd.factorize(relations["building_id"])
    n_buildings = len(building_values)
    cells = relations["cell_id"].map(coverage.cell_positions).to_numpy(dtype=int)
    buildings = building_codes + 1
    order = np.argsort(buildings, kind="stable")
    cells, buildings = cells[order], buildings[order]
    offsets = utils.csr_offsets(buildings, n_buildings)
    required_trees = (
        relations.drop_duplicates("building_id").set_index("building_id")
        .loc[building_values, "required_trees"].to_numpy(dtype=int)
    )
    return n_buildings, total_deficit, cells, buildings, offsets, required_trees


def _criterion_300_maxcoverage(coverage, total_deficit):
    relations = coverage.three_hundred[
        coverage.three_hundred["cell_id"].isin(coverage.cell_positions)
    ].copy()
    building_codes, building_values = pd.factorize(relations["building_id"])
    n_buildings = len(building_values)
    cells = relations["cell_id"].map(coverage.cell_positions).to_numpy(dtype=int)
    buildings = building_codes + 1
    order = np.argsort(buildings, kind="stable")
    cells, buildings = cells[order], buildings[order]
    offsets = utils.csr_offsets(buildings, n_buildings)
    return n_buildings, total_deficit, cells, buildings, offsets


def _serialize_330300(model, base, coverage, params):
    (
        top_k, beta_streets, alpha_yards, delta, gamma_330300,
        tree_density_street, tree_density_yard,
        canopy_density_street, canopy_density_yard,
    ) = params
    instance = {
        "len": base.num_cells,
        "top_k": top_k,
        "beta_streets": beta_streets,
        "alpha_yard": alpha_yards,
        "delta": delta,
        "gamma_330300": gamma_330300,
        "tree_density_street": tree_density_street,
        "tree_density_yard": tree_density_yard,
        "canopy_density_street": canopy_density_street,
        "canopy_density_yard": canopy_density_yard,
        "street_space": base.street_space,
        "ext_space": base.ext_space,
        "green_space": base.green_space,
        "num_areas": base.num_areas,
        "num_trees": base.num_trees,
        "macro_factors": base.macro_factors,
        "full_space": base.full_space,
    }
    rel30 = _criterion_30(coverage)
    if model == "std_330300":
        rel3 = _criterion_3_counterfactual(coverage)
        rel300 = _criterion_300_counterfactual(coverage)
        rel3 = _sort_relations(rel3[0], base.num_cells, *rel3[1:])
        rel30 = _sort_relations(rel30[0], base.num_cells, *rel30[1:])
        rel300 = _sort_relations(rel300[0], base.num_cells, *rel300[1:])
        instance.update(dict(zip((
            "rel3_cell", "rel3_area", "rel3_count_req1", "rel3_count_req2",
            "rel3_count_req3", "rel3_deficit_area", "rel3_offset",
        ), rel3)))
        instance.update(dict(zip((
            "rel30_cell", "rel30_area", "rel30_cell_share",
            "rel30_required_canopy", "rel30_offset",
        ), rel30)))
        instance.update(dict(zip((
            "rel300_cell", "rel300_area", "rel300_gain_count",
            "rel300_deficit_area", "rel300_offset",
        ), rel300)))
    elif model == "std_330300_maxcoverage":
        total_3, total_30, total_300 = _initial_330300_deficits()
        rel3 = _criterion_3_maxcoverage(coverage, total_3)
        rel300 = _criterion_300_maxcoverage(coverage, total_300)
        instance["total_deficit_30"] = total_30
        instance.update(dict(zip((
            "n_buildings_3", "total_deficit_3", "rel3_cell", "rel3_building",
            "rel3_offset", "required_trees_3",
        ), rel3)))
        instance.update(dict(zip((
            "rel30_cell", "rel30_area", "rel30_cell_share",
            "rel30_required_canopy",
        ), rel30)))
        instance.update(dict(zip((
            "n_buildings_300", "total_deficit_300", "rel300_cell",
            "rel300_building", "rel300_offset",
        ), rel300)))
    else:
        raise ValueError(f"Unsupported 3-30-300 model: {model}")
    return utils.to_dzn(model, instance)


def parse(
    size, model, top_k_param, beta_streets, alpha_yards, alpha_uhei,
    gamma_330300, delta, tree_density_street, tree_density_yard,
    canopy_density_street, canopy_density_yard,
):
    """Build one MiniZinc instance from the processed TALEA geospatial datasets."""
    base = _load_base_data(size)
    if model in MODELS_330300:
        coverage = _load_coverage(base)
        output_text = _serialize_330300(
            model, base, coverage,
            (top_k_param, beta_streets, alpha_yards, delta, gamma_330300,
             tree_density_street, tree_density_yard,
             canopy_density_street, canopy_density_yard),
        )
    else:
        instance = _standard_instance(
            model, base, top_k_param, beta_streets, alpha_yards, alpha_uhei,
        )
        output_text = utils.to_dzn(model, instance)

    INSTANCE_DIR_PATH.mkdir(parents=True, exist_ok=True)
    instance_path = INSTANCE_DIR_PATH / f"{model}_instance.dzn"
    with open(instance_path, "w") as output_file:
        output_file.write(output_text)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Generates the parsed file in the Minizinc data format from the input datasets, specifying the output directory and the parameters of the algorithm."
    )
    parser.add_argument(
        "--size",
        type=str,
        default="full",
        choices=["center", "full"],
        help="Whether to run the model on the city center or on the entire cityscape.",
    )
    parser.add_argument(
        "--model",
        type=str,
        default="std",
        choices=[
            "std",
            "std_330300",
            "std_330300_maxcoverage",
            "diff",
            "inverse_uhei",
            "ndvi",
        ],
        help="Choice of the model to run.",
    )
    parser.add_argument(
        "--max_cells",
        type=int,
        default=100,
        help="Maximum number of cells to be placed.",
    )
    parser.add_argument(
        "--beta_streets",
        type=float,
        default=0.2,
        help="Weight for the available street space.",
    )
    parser.add_argument(
        "--alpha_yards",
        type=float,
        default=0.8,
        help="Weight for the utility of the yard space.",
    )
    parser.add_argument(
        "--alpha_uhei",
        type=float,
        default=0.0,
        help="Weight for the UHEI influence in the diff model. If you choose another model this parameter is ignored.",
    )
    parser.add_argument(
        "--delta",
        type=float,
        default=1.0,
        help="Minimum intervention size for each selected cell.",
    )
    parser.add_argument(
        "--gamma_330300",
        type=float,
        default=1.0,
        help="Weight of the counterfactual 3-30-300 benefit.",
    )
    parser.add_argument(
        "--tree_density_street",
        type=float,
        default=0.2,
        help="Conversion factor from allocated street green surface to number of trees.",
    )
    parser.add_argument(
        "--tree_density_yard",
        type=float,
        default=0.2,
        help="Conversion factor from allocated yard green surface to number of trees.",
    )
    parser.add_argument(
        "--canopy_density_street",
        type=float,
        default=0.3,
        help="Conversion factor from allocated street green surface to canopy surface.",
    )
    parser.add_argument(
        "--canopy_density_yard",
        type=float,
        default=0.3,
        help="Conversion factor from allocated yard green surface to canopy surface.",
    )

    args = parser.parse_args()
    parse(
        args.size,
        args.model,
        args.max_cells,
        args.beta_streets,
        args.alpha_yards,
        args.alpha_uhei,
        args.gamma_330300,
        args.delta,
        args.tree_density_street,
        args.tree_density_yard,
        args.canopy_density_street,
        args.canopy_density_yard,
    )
