import geopandas as gpd
import numpy as np
import pandas as pd
import utils
import os
from pathlib import Path
import argparse

def parse(output_dir, top_k, beta_streets, alpha_yard):
    """
    Generates the parsed file in the Minizinc data format from the input datasets, specifying the output directory and the parameters of the algorithm.

    Input:
    - output_dir: str, path of the output directory

    """
    WORKING_DIR_PATH = Path.cwd()
    SRC_DIR_PATH = WORKING_DIR_PATH.joinpath("src")
    DATA_DIR_PATH = WORKING_DIR_PATH.joinpath("dataset")

    # Load the data
    gdf_tot = gpd.read_file(DATA_DIR_PATH.joinpath("grid_with_areas.geojson"))
    gdf_tot.set_index("id", inplace=True)
    gdf_strade = gpd.read_file(DATA_DIR_PATH.joinpath("strada_no_piazze.geojson"))
    gdf_strade.set_index("id", inplace=True)
    gdf_trees = gpd.read_file(DATA_DIR_PATH.joinpath("trees_outside_green.geojson"))
    gdf_trees.set_index("id", inplace=True)
    gdf_aree = gpd.read_file(DATA_DIR_PATH.joinpath("aree_statistiche_grid.geojson"))
    df_pop = pd.read_csv(DATA_DIR_PATH.joinpath("popolazione_per_area_statistica.csv"), sep=";")
    num_cells = np.max(gdf_tot.index)

    ### TEMPORARY
    gdf_tot['aree-stradali_area'] = gdf_strade['aree-stradali-modified_area']
    gdf_tot = pd.merge(gdf_tot, gdf_trees['trees count'], how='outer', left_index=True, right_index=True).fillna(0.0)

    densities_df = utils.density_per_area(gdf_aree, df_pop)
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
                top_k, 
                beta_streets, 
                alpha_yard, 
                street_space, 
                ext_space, 
                green_space, 
                num_areas, 
                num_trees, 
                densities_df)

    # Create the output directory if it doesn't exist
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # File creation
    output_text = utils.to_dzn(instance)
    output_file_path = os.path.join(output_dir, "instance_lin.dzn")
    with open(output_file_path, "w") as output_file:
       output_file.write(output_text)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Generates the parsed file in the Minizinc data format from the input datasets, specifying the output directory and the parameters of the algorithm.")
    parser.add_argument("--output_dir", type=str, default="./src/Minizinc", help="Output directory for the parsed data.")
    parser.add_argument("--max_cells", type=int, default=50, help="Maximum number of cells that can be placed.")
    parser.add_argument("--beta_streets", type=float, default=0.4, help="Weight for the available street space.")
    parser.add_argument("--alpha_yard", type=float, default=0.8, help="Weight for the available yard space.")
    args = parser.parse_args()

    parse(args.output_dir, args.max_cells, args.beta_streets, args.alpha_yard)
