from minizinc import Instance, Model, Solver
import pandas as pd
import geopandas as gpd
import numpy as np

def solve():

    instance_path = "Minizinc/instance.dzn"
    model_path = "Minizinc/sec_model.mzn"

    model = Model(model_path)
    solver = Solver.lookup('highs')
    instance = Instance(solver, model)
    instance.add_file(instance_path)

    result = instance.solve()
    street_cells = np.array(result.solution.street_cells).T
    yard_cells = np.array(result.solution.yard_cells).T
    df_result = pd.DataFrame(columns=['id', 'row_index', 'col_index', 'street_cells', 'yard_cells'])
    id = 1
    for i in range(len(street_cells)):
        for j in range(len(street_cells[i])):
            df_result.loc[len(df_result)] = {'id': id, 'row_index': i, 'col_index': j, 'street_cells': street_cells[i][j], 'yard_cells': yard_cells[i][j]}
            id += 1

    gdf_data = gpd.read_file("dataset/grid_with_areas.geojson")
    gdf_result = gpd.GeoDataFrame(df_result, geometry=gdf_data.geometry, crs="EPSG:3857")
    gdf_result['num_areas'] = gdf_data['NUMPOINTS']
    gdf_result = gdf_result[gdf_result['street_cells'] != 0.0]
    gdf_result = gdf_result[gdf_result['yard_cells'] != 0.0]
    gdf_result.to_file('result.geojson', driver='GeoJSON')

if __name__ == "__main__":
    solve()