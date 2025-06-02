from minizinc import Instance, Model, Solver
import pandas as pd
import geopandas as gpd
import numpy as np
from pathlib import Path

def solve():

    WORKING_DIR_PATH = Path.cwd()
    RESULTS_DIR_PATH = WORKING_DIR_PATH.joinpath("results")

    # Matrix version
    # INSTANCE_PATH = WORKING_DIR_PATH.joinpath("src", "Minizinc", "instance.dzn")
    # MODEL_PATH = WORKING_DIR_PATH.joinpath("src", "Minizinc", "sec_model.mzn")

    # Linear version
    INSTANCE_PATH = WORKING_DIR_PATH.joinpath("src", "Minizinc", "instance_lin.dzn")
    MODEL_PATH = WORKING_DIR_PATH.joinpath("src", "Minizinc", "linear_model.mzn")

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

    gdf_data = gpd.read_file("dataset/grid_with_areas.geojson")
    gdf_result = gpd.GeoDataFrame(df_result, geometry=gdf_data.geometry, crs='EPSG:3857')
    gdf_result['num_areas'] = gdf_data['NUMPOINTS']
    gdf_result = gdf_result[gdf_result['street_cells'] != 0.0]
    gdf_result = gdf_result[gdf_result['yard_cells'] != 0.0]
    gdf_result.to_file(RESULTS_DIR_PATH.joinpath("result_trees.geojson"), driver='GeoJSON')

if __name__ == "__main__":
    solve()