from minizinc import Instance, Model, Solver
import pandas as pd
import geopandas as gpd
import numpy as np
from pathlib import Path
import argparse


WORKING_DIR_PATH = Path.cwd()
PROCESSED_DATA_DIR_PATH = WORKING_DIR_PATH.joinpath("dataset", "processed_data")
CENTER_GRID_DIR_PATH = PROCESSED_DATA_DIR_PATH.joinpath("center")
FULL_GRID_DIR_PATH = PROCESSED_DATA_DIR_PATH.joinpath("full")
MINIZINC_DIR_PATH = WORKING_DIR_PATH.joinpath("src", "Minizinc")
INSTANCE_PATH = MINIZINC_DIR_PATH.joinpath("instance.dzn")
MODEL_PATH = MINIZINC_DIR_PATH.joinpath("linear_model.mzn")


def solve(size, res_name):

    model = Model(MODEL_PATH)
    solver = Solver.lookup('highs')
    instance = Instance(solver, model)
    instance.add_file(INSTANCE_PATH)

    result = instance.solve()
    street_cells = np.array(result.solution.street_cells)
    yard_cells = np.array(result.solution.yard_cells)
    df_result = pd.DataFrame(columns=['id', 'street_cells', 'yard_cells'])
    for i in range(len(street_cells)):
        df_result.loc[len(df_result)] = {'id': i+1, 'street_cells': street_cells[i], 'yard_cells': yard_cells[i]}

    if size == "center":
        PATH = CENTER_GRID_DIR_PATH
    elif size == "full":
        PATH = FULL_GRID_DIR_PATH
    
    gdf_data = gpd.read_file(PATH.joinpath("final_grid.geojson"))
    gdf_result = gpd.GeoDataFrame(df_result, geometry=gdf_data.geometry, crs='EPSG:3857')
    gdf_result['num_areas'] = gdf_data['free_space_number']
    gdf_result = gdf_result[gdf_result['street_cells'] != 0.0]
    gdf_result = gdf_result[gdf_result['yard_cells'] != 0.0]

    RESULTS_DIR_PATH = WORKING_DIR_PATH.joinpath("results", size)
    if not RESULTS_DIR_PATH.exists():
        RESULTS_DIR_PATH.mkdir(parents=True)
    gdf_result.to_file(RESULTS_DIR_PATH.joinpath(f"{res_name}.geojson"), driver='GeoJSON')

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Solve the linear model for green cells placement optimization (specify again the size).")
    parser.add_argument("--size",
                        type=str,
                        default="center",
                        choices=["center", "full"],
                        help="Whether to run the model on the city center or on the entire cityscape.")
    parser.add_argument("--res_name",
                        type=str,
                        default="result",
                        help="Name of the result file to be saved.")
    args = parser.parse_args()
    solve(args.size, args.res_name)
