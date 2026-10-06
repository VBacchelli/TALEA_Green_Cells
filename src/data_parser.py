import argparse
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


def _mzn_array(values, cast=float):
    """Serialize a 1-D Python/numpy sequence as a MiniZinc array literal."""
    vals = []
    for value in values:
        if cast is int:
            vals.append(str(int(value)))
        else:
            vals.append(repr(float(value)))
    return "[" + ", ".join(vals) + "]"

def _to_dzn_std_330300(
    num_cells, top_k_param, beta_streets, alpha_yards, delta, gamma_330300,
    tree_density_street, tree_density_yard,
    canopy_density_street, canopy_density_yard,
    street_space, ext_space, green_space,
    num_areas, num_trees, macro_factors, full_space,
    rel3_cell, rel3_area, rel3_count_req1, rel3_count_req2, rel3_count_req3, rel3_deficit_area,
    rel30_cell, rel30_area, rel30_cell_share, rel30_required_canopy,
    rel300_cell, rel300_area, rel300_gain_count, rel300_deficit_area,
):
    """Serialize the sparse cell-statistical-area 3-30-300 formulation."""
    lines = [
        f"len = {int(num_cells)};",
        f"top_k = {int(top_k_param)};",
        f"alpha_yard = {float(alpha_yards)!r};",
        f"beta_streets = {float(beta_streets)!r};",
        f"gamma_330300 = {float(gamma_330300)!r};",
        f"delta = {float(delta)!r};",
        f"tree_density_street = {float(tree_density_street)!r};",
        f"tree_density_yard = {float(tree_density_yard)!r};",
        f"canopy_density_street = {float(canopy_density_street)!r};",
        f"canopy_density_yard = {float(canopy_density_yard)!r};",
        f"street_space = {_mzn_array(street_space)};",
        f"ext_space = {_mzn_array(ext_space)};",
        f"green_space = {_mzn_array(green_space)};",
        f"num_areas = {_mzn_array(num_areas)};",
        f"num_trees = {_mzn_array(num_trees)};",
        f"macro_factors = {_mzn_array(macro_factors)};",
        f"full_space = {_mzn_array(full_space)};",
        f"n_rel_3 = {len(rel3_cell)};",
        f"rel3_cell = {_mzn_array(rel3_cell, int)};",
        f"rel3_area = {_mzn_array(rel3_area, int)};",
        f"rel3_count_req1 = {_mzn_array(rel3_count_req1, int)};",
        f"rel3_count_req2 = {_mzn_array(rel3_count_req2, int)};",
        f"rel3_count_req3 = {_mzn_array(rel3_count_req3, int)};",
        f"rel3_deficit_area = {_mzn_array(rel3_deficit_area)};",
        f"n_rel_30 = {len(rel30_cell)};",
        f"rel30_cell = {_mzn_array(rel30_cell, int)};",
        f"rel30_area = {_mzn_array(rel30_area, int)};",
        f"rel30_cell_share = {_mzn_array(rel30_cell_share)};",
        f"rel30_required_canopy = {_mzn_array(rel30_required_canopy)};",
        f"n_rel_300 = {len(rel300_cell)};",
        f"rel300_cell = {_mzn_array(rel300_cell, int)};",
        f"rel300_area = {_mzn_array(rel300_area, int)};",
        f"rel300_gain_count = {_mzn_array(rel300_gain_count, int)};",
        f"rel300_deficit_area = {_mzn_array(rel300_deficit_area)};",
    ]
    return "\n".join(lines) + "\n"


def parse(size, model, top_k_param, beta_streets, alpha_yards, alpha_uhei, gamma_330300, delta, tree_density_street, tree_density_yard, 
          canopy_density_street, canopy_density_yard):
    """
    Generates the parsed file in the Minizinc data format from the input datasets, specifying the output directory and the parameters of the algorithm.

    Input:
    - size: str, specifying whether to run the model on the city center or on the entire cityscape
    - model: str, choice of the model to run
    - top_k_param: int, maximum number of cells to be placed
    - beta_streets: float, weight for the available street space
    - alpha_yards: float, weight for the utility of the yard space
    - alpha_uhei: float, weight for the UHEI influence in the diff model
    - gamma_330300: float, weight for the 3-30-300 index
    - delta: float, minimum intervention size for selected cells

    """

    # Set the data directory based on the size parameter
    if size == "center":
        PATH = CENTER_GRID_DIR_PATH
    elif size == "full":
        PATH = FULL_GRID_DIR_PATH
    
    # Load the data
    gdf_tot = gpd.read_file(PATH.joinpath("final_grid.geojson"))
    gdf_tot.set_index("id", inplace=True)
    gdf_aree = gpd.read_file(PATH.joinpath("aree_statistiche_grid.geojson")).sort_values(by='id')
    gdf_aree = gdf_aree[gdf_aree["id"].isin(gdf_tot.index)].copy()
    df_pop = pd.read_csv(PROCESSED_DATA_DIR_PATH.joinpath("densità_per_area_statistica.csv"), sep=';')
    gdf_macro = gpd.read_file(PROCESSED_DATA_DIR_PATH.joinpath("aree_statistiche_macro.geojson"))
    num_cells = gdf_tot.index.shape[0]

    # 3-30-300: preserve sparse cell-statistical-area relations.
    # No city-wide observed-max normalization and no maximum-coverage logic here.
    coverage_3 = pd.read_csv(PROCESSED_DATA_DIR_PATH / "330300/cell_3_coverage.csv")
    coverage_30 = pd.read_csv(PROCESSED_DATA_DIR_PATH / "330300/cell_30_coverage.csv")
    coverage_300 = pd.read_csv(PROCESSED_DATA_DIR_PATH / "330300/cell_300_coverage.csv")

    cell_to_pos = {cell_id: pos for pos, cell_id in enumerate(gdf_tot.index, start=1)}

    # Dense integer ids are used only as MiniZinc labels for statistical areas.
    area_values = pd.concat([
        coverage_3["codice_area_statistica"],
        coverage_30["codice_area_statistica"],
        coverage_300["codice_area_statistica"],
    ], ignore_index=True).dropna().drop_duplicates().tolist()
    area_to_pos = {area_id: pos for pos, area_id in enumerate(area_values, start=1)}

    # Criterion 3: one sparse relation per (cell, statistical area).
    # Keep the number of covered deficit buildings for required_trees = 1, 2, 3.
    req_counts = (
        coverage_3.groupby(["cell_id", "codice_area_statistica", "required_trees"])
        .size()
        .unstack(fill_value=0)
        .reindex(columns=[1, 2, 3], fill_value=0)
        .rename(columns={1: "count_req1", 2: "count_req2", 3: "count_req3"})
        .reset_index()
    )
    deficit_3 = (
        coverage_3[["cell_id", "codice_area_statistica", "deficit_3_area"]]
        .drop_duplicates(["cell_id", "codice_area_statistica"])
    )
    rel3 = req_counts.merge(
        deficit_3, on=["cell_id", "codice_area_statistica"], how="left"
    )
    rel3 = rel3[rel3["cell_id"].isin(cell_to_pos)].copy()

    rel3_cell = rel3["cell_id"].map(cell_to_pos).to_numpy(dtype=int)
    rel3_area = rel3["codice_area_statistica"].map(area_to_pos).to_numpy(dtype=int)
    rel3_count_req1 = rel3["count_req1"].to_numpy(dtype=int)
    rel3_count_req2 = rel3["count_req2"].to_numpy(dtype=int)
    rel3_count_req3 = rel3["count_req3"].to_numpy(dtype=int)
    rel3_deficit_area = rel3["deficit_3_area"].to_numpy(dtype=float)

    # Criterion 30: coverage is already one relation per (cell, statistical area).
    rel30 = coverage_30[
        ["cell_id", "codice_area_statistica", "cell_share", "required_canopy_30"]
    ].copy()
    rel30 = rel30[rel30["cell_id"].isin(cell_to_pos)].copy()

    rel30_cell = rel30["cell_id"].map(cell_to_pos).to_numpy(dtype=int)
    rel30_area = rel30["codice_area_statistica"].map(area_to_pos).to_numpy(dtype=int)
    rel30_cell_share = rel30["cell_share"].to_numpy(dtype=float)
    rel30_required_canopy = rel30["required_canopy_30"].to_numpy(dtype=float)

    # Criterion 300: one sparse relation per (cell, statistical area).
    # gain_count is the number of currently deficit buildings covered by that cell.
    rel300 = (
        coverage_300.groupby(["cell_id", "codice_area_statistica"], as_index=False)
        .agg(
            gain_count=("building_id", "count"),
            deficit_300_area=("deficit_300_area", "first"),
        )
    )
    rel300 = rel300[rel300["cell_id"].isin(cell_to_pos)].copy()

    rel300_cell = rel300["cell_id"].map(cell_to_pos).to_numpy(dtype=int)
    rel300_area = rel300["codice_area_statistica"].map(area_to_pos).to_numpy(dtype=int)
    rel300_gain_count = rel300["gain_count"].to_numpy(dtype=int)
    rel300_deficit_area = rel300["deficit_300_area"].to_numpy(dtype=float)

    # Macro scale computations
    macro_factors = utils.macro_factor_per_area(gdf_aree, gdf_macro)

    # Density estimation
    densities_df = utils.density_per_area(gdf_aree, df_pop)
    densities_df.set_index("id", inplace=True)
    densities_gdf = gpd.GeoDataFrame(densities_df, geometry=gdf_tot.geometry, crs='EPSG:3857')
    densities_gdf.to_file(PATH.joinpath("densities_grid.geojson"), driver='GeoJSON')

    # Total space computation
    full_space = utils.full_space_per_area(gdf_aree)

    # Instance creation
    green_space = np.zeros((num_cells, ), dtype=float)
    street_space = np.zeros((num_cells, ), dtype=float)
    ext_space = np.zeros((num_cells, ), dtype=float)
    num_areas = np.zeros((num_cells, ), dtype=float)
    num_trees = np.zeros((num_cells, ), dtype=float)
    for idx, cell_id in enumerate(gdf_tot.index):
        row = gdf_tot.loc[cell_id]
        green_space[idx] = row['green_area'] + 1
        green_space[idx] = min(green_space[idx], full_space[idx])
        street_space[idx] = row['road_area']
        ext_space[idx] = row['free_space_area']
        num_areas[idx] = float(row['free_space_number']) + 1 if street_space[idx] > 0 else float(row['free_space_number'])
        num_trees[idx] = float(row['tree_number']) + 1
    
    if model == "std":
        instance = (num_cells, 
                    top_k_param, 
                    beta_streets, 
                    alpha_yards, 
                    street_space, 
                    ext_space, 
                    green_space, 
                    num_areas, 
                    num_trees, 
                    macro_factors,
                    full_space)

    elif model == "std_330300":
        instance = None  # Serialized explicitly below because it contains sparse relations.
    
    elif model == "diff":
        uhei = np.zeros((num_cells, ), dtype=float)
        for idx, cell_id in enumerate(gdf_tot.index):
            row = gdf_tot.loc[cell_id]
            uhei[idx] = row['weighted_uhei']
        instance = (num_cells, 
                    top_k_param, 
                    beta_streets, 
                    alpha_yards, 
                    alpha_uhei, 
                    street_space, 
                    ext_space, 
                    green_space, 
                    num_areas, 
                    num_trees, 
                    macro_factors,
                    full_space, 
                    uhei)
    
    elif model == "inverse_uhei":
        # UHEI normalization factors (computed from the data available)
        inverse_uhei_5p = gdf_tot['inverse_uhei'].quantile(0.05)
        inverse_uhei_95p = gdf_tot['inverse_uhei'].quantile(0.95)
        instance = (num_cells, 
                    top_k_param, 
                    beta_streets, 
                    alpha_yards, 
                    inverse_uhei_95p, 
                    inverse_uhei_5p, 
                    street_space, 
                    ext_space, 
                    green_space, 
                    num_areas, 
                    num_trees, 
                    macro_factors,
                    full_space)
    
    elif model == "ndvi":
        # NDVI normalization factors (choosen according to the values used for the collection)
        ndvi_norm_max = 0.8
        ndvi_norm_min = 0.0
        ndvi = np.zeros((num_cells, ), dtype=float)
        for idx, cell_id in enumerate(gdf_tot.index):
            row = gdf_tot.loc[cell_id]
            ndvi[idx] = row['weighted_ndvi']
        instance = (num_cells, 
                    top_k_param, 
                    beta_streets, 
                    alpha_yards, 
                    ndvi_norm_max,
                    ndvi_norm_min, 
                    street_space, 
                    ext_space, 
                    green_space, 
                    num_areas, 
                    num_trees, 
                    macro_factors,
                    full_space, 
                    ndvi)

    # Create the output directory if it doesn't exist
    if not Path.exists(INSTANCE_DIR_PATH):
        INSTANCE_DIR_PATH.mkdir(parents=True)
    
    # File creation
    if model == "std_330300":
        output_text = _to_dzn_std_330300(
            num_cells, top_k_param, beta_streets, alpha_yards, delta, gamma_330300,
            tree_density_street, tree_density_yard, canopy_density_street, canopy_density_yard, 
            street_space, ext_space, green_space, num_areas, num_trees, macro_factors, full_space,
            rel3_cell, rel3_area, rel3_count_req1, rel3_count_req2, rel3_count_req3, rel3_deficit_area,
            rel30_cell, rel30_area, rel30_cell_share, rel30_required_canopy,
            rel300_cell, rel300_area, rel300_gain_count, rel300_deficit_area,
        )
    else:
        output_text = utils.to_dzn(model, instance)
    INSTANCE_PATH = INSTANCE_DIR_PATH.joinpath(f"{model}_instance.dzn")
    with open(INSTANCE_PATH, "w") as output_file:
       output_file.write(output_text)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generates the parsed file in the Minizinc data format from the input datasets, specifying the output directory and the parameters of the algorithm.")
    parser.add_argument("--size", 
                        type=str, 
                        default="full", 
                        choices=["center", "full"], 
                        help="Whether to run the model on the city center or on the entire cityscape.")
    parser.add_argument("--model", 
                        type=str, 
                        default="std", 
                        choices=["std", "std_330300", "diff", "inverse_uhei", "ndvi"], 
                        help="Choice of the model to run.")
    parser.add_argument("--max_cells", 
                        type=int, 
                        default=100, 
                        help="Maximum number of cells to be placed.")
    parser.add_argument("--beta_streets", 
                        type=float, 
                        default=0.2, 
                        help="Weight for the available street space.")
    parser.add_argument("--alpha_yards", 
                        type=float, 
                        default=0.8, 
                        help="Weight for the utility of the yard space.")
    parser.add_argument("--alpha_uhei",
                        type=float, 
                        default=0.0, 
                        help="Weight for the UHEI influence in the diff model. If you choose another model this parameter is ignored.")
    parser.add_argument("--delta",
                        type=float,
                        default=1.0,
                        help="Minimum intervention size for each selected cell.")
    parser.add_argument("--gamma_330300",
                        type=float,
                        default=1.0,
                        help="Weight of the counterfactual 3-30-300 benefit.")
    parser.add_argument("--tree_density_street",
                        type=float,
                        default=0.01,
                        help="Conversion factor from allocated street green surface to number of trees.")
    parser.add_argument("--tree_density_yard",
                        type=float,
                        default=0.01,
                        help="Conversion factor from allocated yard green surface to number of trees.")
    parser.add_argument("--canopy_density_street",
                        type=float,
                        default=0.3,
                        help="Conversion factor from allocated street green surface to canopy surface.")
    parser.add_argument("--canopy_density_yard",
                        type=float,
                        default=0.3,
                        help="Conversion factor from allocated yard green surface to canopy surface.")
    
    args = parser.parse_args()
    parse(args.size, args.model, args.max_cells, args.beta_streets, args.alpha_yards, args.alpha_uhei, 
          args.gamma_330300, args.delta, args.tree_density_street, args.tree_density_yard, args.canopy_density_street, args.canopy_density_yard)
