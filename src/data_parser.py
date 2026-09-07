import geopandas as gpd
import numpy as np
import pandas as pd
import utils
from pathlib import Path
import argparse


WORKING_DIR_PATH = Path.cwd()
SRC_DIR_PATH = WORKING_DIR_PATH.joinpath("src")
INSTANCE_DIR_PATH = SRC_DIR_PATH.joinpath("Minizinc", "instances")
PROCESSED_DATA_DIR_PATH = WORKING_DIR_PATH.joinpath("dataset", "processed_data")
CENTER_GRID_DIR_PATH = PROCESSED_DATA_DIR_PATH.joinpath("center")
FULL_GRID_DIR_PATH = PROCESSED_DATA_DIR_PATH.joinpath("full")

# Suppress warnings
from warnings import filterwarnings
filterwarnings("ignore")


def parse(size, model, top_k_param, beta_streets, alpha_yards, alpha_uhei, gamma_330300, delta, tree_density, canopy_density):
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
    df_pop = pd.read_csv(PROCESSED_DATA_DIR_PATH.joinpath("densità_per_area_statistica.csv"), sep=';')
    gdf_macro = gpd.read_file(PROCESSED_DATA_DIR_PATH.joinpath("aree_statistiche_macro.geojson"))
    num_cells = gdf_tot.index.shape[0]

    # 3-30-300
    buildings_330300 = gpd.read_file(PROCESSED_DATA_DIR_PATH / "330300/buildings_330300.gpkg")
    num_deficit_300 = (~buildings_330300["meet_300"]).sum()
    benefit_300 = (pd.read_csv(PROCESSED_DATA_DIR_PATH / "330300/cell_300_benefit.csv").set_index("cell_id")
        .reindex(gdf_tot.index)["benefit_300_count"].fillna(0.0).to_numpy(dtype=float) / num_deficit_300)

    coverage_3 = pd.read_csv(PROCESSED_DATA_DIR_PATH / "330300/cell_3_coverage.csv")
    benefit_3_counts = (coverage_3
                .groupby(["cell_id", "required_trees"]).size().unstack(fill_value=0)
                .reindex(index=gdf_tot.index, columns=[1, 2, 3], fill_value=0).to_numpy(dtype=int))
    num_deficit_3 = (~buildings_330300["meet_3"]).sum()
    benefit_3_counts = benefit_3_counts / num_deficit_3
    
    coverage_30 = pd.read_csv(PROCESSED_DATA_DIR_PATH / "330300/cell_30_coverage.csv")
    total_canopy_deficit = (coverage_30[["codice_area_statistica", "required_canopy_30"]]
        .drop_duplicates()["required_canopy_30"].sum())
    benefit_30_factor = (coverage_30.groupby("cell_id")["cell_share"].sum()
        .reindex(gdf_tot.index, fill_value=0).to_numpy(dtype=float) / total_canopy_deficit)
    

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
        green_space[idx] = full_space[idx] if green_space[idx] > full_space[idx] else green_space[idx]
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
        instance = (num_cells,
                    top_k_param,
                    beta_streets,
                    alpha_yards,
                    delta,
                    gamma_330300,
                    tree_density,
                    canopy_density,
                    benefit_300,
                    benefit_3_counts,
                    benefit_30_factor,
                    street_space,
                    ext_space,
                    green_space,
                    num_areas,
                    num_trees,
                    macro_factors,
                    full_space)
    
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
    parser.add_argument("--tree_density",
                        type=float,
                        default=0.01,
                        help="Conversion factor from green surface to number of trees.")
    parser.add_argument("--canopy_density",
                        type=float,
                        default=0.3,
                        help="Conversion factor from green surface to canopy surface.")
    
    args = parser.parse_args()
    parse(args.size, args.model, args.max_cells, args.beta_streets, args.alpha_yards, args.alpha_uhei, 
          args.gamma_330300, args.delta, args.tree_density, args.canopy_density)
