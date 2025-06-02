import geopandas as gpd
import numpy as np
import pandas as pd
import utils
import os
from pathlib import Path

def parse(output_dir):
    """
    Generates the parsed file in the Minizinc data format from the input dataset to the specified output directory.

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
    n_rows, n_cols = np.max(gdf_tot['row_index']) + 1, np.max(gdf_tot['col_index']) + 1
    df_pop = pd.read_csv(DATA_DIR_PATH.joinpath("popolazione_per_area_statistica.csv"), sep=";")

    ### TEMPORARY
    gdf_tot['aree-stradali_area'] = gdf_strade['aree-stradali-modified_area']
    gdf_tot = pd.merge(gdf_tot, gdf_trees['trees count'], how='outer', left_index=True, right_index=True).fillna(0.0)

    densities_df = utils.density_per_area(gdf_aree, df_pop)
    green_space = np.zeros((n_rows, n_cols), dtype=float)
    street_space = np.zeros((n_rows, n_cols), dtype=float)
    ext_space = np.zeros((n_rows, n_cols), dtype=float)
    num_areas = np.zeros((n_rows, n_cols), dtype=float)     # number of external areas in each cell
    num_trees = np.zeros((n_rows, n_cols), dtype=float)     # number of trees in each cell
    for _, row in gdf_tot.iterrows():
        row_index = int(row['row_index'])
        col_index = int(row['col_index'])
        green_space[row_index][col_index] = row['un_gest_area'] + row['verde_privato_urbanizzato_area'] + row['colli_area'] + 1
        green_space[row_index][col_index] = 10000.0 if green_space[row_index][col_index] > 10000.0 else green_space[row_index][col_index]
        street_space[row_index][col_index] = row['aree-stradali_area']
        ext_space[row_index][col_index] = row['Single parts_area']
        num_areas[row_index][col_index] = float(row['NUMPOINTS']) + 1 if street_space[row_index][col_index] > 0 else float(row['NUMPOINTS'])
        num_trees[row_index][col_index] = float(row['trees count']) + 1
        
    instance = (n_rows, n_cols, street_space, ext_space, green_space, num_areas, num_trees, densities_df)

    # Create the output directory if it doesn't exist
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # File creation
    output_text = utils.to_dzn(instance)
    output_file_path = os.path.join(output_dir, "instance.dzn")
    with open(output_file_path, "w") as output_file:
       output_file.write(output_text)

if __name__ == '__main__':
    parse("./src/Minizinc")
