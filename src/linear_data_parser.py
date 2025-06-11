import geopandas as gpd
import numpy as np
import pandas as pd
import utils
from pathlib import Path
import argparse


WORKING_DIR_PATH = Path.cwd()
SRC_DIR_PATH = WORKING_DIR_PATH.joinpath("src")
PROCESSED_DATA_DIR_PATH = WORKING_DIR_PATH.joinpath("dataset", "processed_data")
CENTER_GRID_DIR_PATH = PROCESSED_DATA_DIR_PATH.joinpath("center")
FULL_GRID_DIR_PATH = PROCESSED_DATA_DIR_PATH.joinpath("full")


def parse(OUTPUT_DIR_PATH, size, top_k_param, streets_param, yard_param):
    """
    Generates the parsed file in the Minizinc data format from the input datasets, specifying the output directory and the parameters of the algorithm.

    Input:
    - OUTPUT_DIR_PATH: str, path of the output directory
    - size: str, flag to run the model on the city center or on the entire cityscape
    - top_k_param: int, maximum number of cells that can be placed
    - streets_param: float, weight for the available street space
    - yard_param: float, weight for the available yard space
    - density_param: float, weight for the population density in the macro utility function
    - green_param: float, weight for the green space in the macro utility function

    """
    # Set the data directory based on the size parameter
    if size == "center":
        PATH = CENTER_GRID_DIR_PATH
    elif size == "full":
        PATH = FULL_GRID_DIR_PATH
    
    # Load the data
    gdf_tot = gpd.read_file(PATH.joinpath("grid_with_areas.geojson"))
    gdf_tot.set_index("id", inplace=True)
    gdf_strade = gpd.read_file(PATH.joinpath("strada_no_piazze.geojson"))
    gdf_strade.set_index("id", inplace=True)
    gdf_trees = gpd.read_file(PATH.joinpath("trees_outside_green.geojson"))
    gdf_trees.set_index("id", inplace=True)
    gdf_aree = gpd.read_file(PATH.joinpath("aree_statistiche_grid.geojson"))
    df_pop = pd.read_csv(PROCESSED_DATA_DIR_PATH.joinpath("densità_per_area_statistica.csv"), sep=';')
    gdf_macro = gpd.read_file(PROCESSED_DATA_DIR_PATH.joinpath("aree_statistiche_macro_factors.geojson"))
    num_cells = np.max(gdf_tot.index)

    ### TEMPORARY
    gdf_tot['aree-stradali_area'] = gdf_strade['aree-stradali-modified_area']
    gdf_tot = pd.merge(gdf_tot, gdf_trees['trees count'], how='outer', left_index=True, right_index=True).fillna(0.0)

    # Macro scale computations
    macro_factors = utils.macro_factor_per_area(gdf_aree, gdf_macro)

    # Density estimation
    densities_df = utils.density_per_area(gdf_aree, df_pop)
    densities_df.set_index("id", inplace=True)
    densities_df = pd.merge(densities_df, gdf_tot['geometry'], how='outer', left_index=True, right_index=True)
    densities_gdf = gpd.GeoDataFrame(densities_df)
    densities_gdf.to_file(PROCESSED_DATA_DIR_PATH.joinpath("densities_grid.geojson"), driver='GeoJSON')

    green_space = np.zeros((num_cells, ), dtype=float)
    street_space = np.zeros((num_cells, ), dtype=float)
    ext_space = np.zeros((num_cells, ), dtype=float)
    num_areas = np.zeros((num_cells, ), dtype=float)     # number of external areas in each cell
    num_trees = np.zeros((num_cells, ), dtype=float)     # number of trees in each cell
    for idx, row in gdf_tot.iterrows():
        green_space[idx - 1] = row['un_gest_area'] + row['verde_privato_urbanizzato_area'] + row['colli_area'] + 1
        green_space[idx - 1] = 10000.0 if green_space[idx - 1] > 10000.0 else green_space[idx - 1]
        street_space[idx - 1] = row['aree-stradali_area']
        ext_space[idx - 1] = row['Single parts_area']
        num_areas[idx - 1] = float(row['NUMPOINTS']) + 1 if street_space[idx - 1] > 0 else float(row['NUMPOINTS'])
        num_trees[idx - 1] = float(row['trees count']) + 1
        
    instance = (num_cells, 
                top_k_param, 
                streets_param, 
                yard_param, 
                street_space, 
                ext_space, 
                green_space, 
                num_areas, 
                num_trees, 
                macro_factors)

    # Create the output directory if it doesn't exist
    if not Path.exists(OUTPUT_DIR_PATH):
        OUTPUT_DIR_PATH.mkdir(parents=True)
    
    # File creation
    output_text = utils.to_dzn(instance)
    INSTANCE_PATH = OUTPUT_DIR_PATH.joinpath("instance_lin.dzn")
    with open(INSTANCE_PATH, "w") as output_file:
       output_file.write(output_text)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generates the parsed file in the Minizinc data format from the input datasets, specifying the output directory and the parameters of the algorithm.")
    parser.add_argument("--output_dir", 
                        type=type(WORKING_DIR_PATH), 
                        default=SRC_DIR_PATH.joinpath("Minizinc"), 
                        help="Output directory for the parsed data.")
    parser.add_argument("--size", 
                        type=str, 
                        default="center", 
                        choices=["center", "full"], 
                        help="Whether to run the model on the city center or on the entire cityscape.")
    parser.add_argument("--max_cells", 
                        type=int, 
                        default=50, 
                        help="Maximum number of cells that can be placed.")
    parser.add_argument("--streets_param", 
                        type=float, 
                        default=0.4, 
                        help="Weight for the available street space.")
    parser.add_argument("--yard_param", 
                        type=float, 
                        default=0.8, 
                        help="Weight for the available yard space.")
    args = parser.parse_args()

    parse(args.output_dir, args.size, args.max_cells, args.streets_param, args.yard_param)
