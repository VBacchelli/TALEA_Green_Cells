import geopandas as gpd
import os
import numpy as np
import pandas as pd

def to_dzn(instance):
    """
    Takes the problem instance and converts it to a string in the format required by MiniZinc.
    
    Input:
    - instance: tuple, instance in the format (n_rows, n_cols, street_space, ext_space, green_space, num_areas, densities)
    Output:
    - text: string

    """

    n_rows, n_cols, street_space, ext_space, green_space, num_areas, densities = instance
    assert len(street_space) == len(green_space) and len(green_space) == len(densities), "The dimensions of the matrices do not match."

    n_rows_str = 'm = ' + str(n_rows) + ';\n'
    n_cols_str = 'n = ' + str(n_cols) + ';\n'
    street_space_str = 'street_space = [| '
    ext_space_str = 'ext_space = [| '
    green_space_str = 'green_space = [| '
    num_areas_str = 'num_areas = [| '
    densities_str = 'densities = [| '
    for i in range(n_rows):
        for j in range(n_cols):
            if j == n_cols - 1:
                street_space_str += str(street_space[i][j]) + '\n |'
                ext_space_str += str(ext_space[i][j]) + '\n |'
                green_space_str += str(green_space[i][j]) + '\n |'
                num_areas_str += str(num_areas[i][j]) + '\n |'
                densities_str += str(densities[i][j]) + '\n |'
            else:
                street_space_str += str(street_space[i][j]) + ', '
                ext_space_str += str(ext_space[i][j]) + ', '
                green_space_str += str(green_space[i][j]) + ', '
                num_areas_str += str(num_areas[i][j]) + ', '
                densities_str += str(densities[i][j]) + ', '
    street_space_str += '];\n'
    ext_space_str += '];\n'
    green_space_str += '];\n'
    num_areas_str += '];\n'
    densities_str += '];\n'

    text = n_rows_str + n_cols_str + street_space_str + ext_space_str + green_space_str + num_areas_str + densities_str
    return text

def density_estimation(gdf_area, df_dens):
    """
    Computes the density of the population in each cell of the grid based on the intersection area with the zones.

    Input:
    - gdf_area: GeoDataFrame, contains the grid data with the intersection area and zone names
    - df_dens: DataFrame, contains the population density data for each zone
    Output:
    - out: numpy array, density of the population in each cell of the grid

    """

    n_rows, n_cols = np.max(gdf_area['row_index']) + 1, np.max(gdf_area['col_index']) + 1
    out = np.zeros((n_rows, n_cols), dtype=float)
    for id in range(1, max(gdf_area['id'])+1):
        temp_df = gdf_area[gdf_area['id'] == id]
        row_index = temp_df['row_index'].values[0]
        col_index = temp_df['col_index'].values[0]
        temp_sum = 0
        for _, row in temp_df.iterrows():
            zone = row['nomezona']
            if zone == 'S. Vitale':
                zone = 'San Vitale'
            temp_dens = df_dens[df_dens['Zona'] == zone]
            temp_dens = temp_dens[temp_dens['Nomi misure'] == 'Densità di popolazione']
            density = float(temp_dens['Valori misure'].values[0].replace(',', '.'))
            temp_sum += density * row['intersect_area']
        out[row_index][col_index] = temp_sum / 10000
    return out

def parse(output_dir):
    """
    Generates the parsed file in the Minizinc data format from the input dataset to the specified output directory.

    Input:
    - output_dir: str, path of the output directory

    """

    # Read the data
    gdf_tot = gpd.read_file("./dataset/grid_with_areas.geojson")
    gdf_tot.set_index("id", inplace=True)
    #gdf_trees = gpd.read_file("./dataset/count_tree_grid.geojson")
    #gdf_trees.set_index("id", inplace=True)
    gdf_aree = gpd.read_file("./dataset/zone_bologna.geojson")
    n_rows, n_cols = np.max(gdf_tot['row_index']) + 1, np.max(gdf_tot['col_index']) + 1
    df_pop = pd.read_csv("./dataset/population_stat.csv", sep=";")

    densities_df = density_estimation(gdf_aree, df_pop)
    green_space = np.zeros((n_rows, n_cols), dtype=float)
    street_space = np.zeros((n_rows, n_cols), dtype=float)
    ext_space = np.zeros((n_rows, n_cols), dtype=float)
    num_areas = np.zeros((n_rows, n_cols), dtype=float)     # number of external areas in each cell
    for _, row in gdf_tot.iterrows():
        row_index = int(row['row_index'])
        col_index = int(row['col_index'])
        green_space[row_index][col_index] = row['un_gest_area'] + row['verde_privato_urbanizzato_area'] + row['colli_area'] + 1
        green_space[row_index][col_index] = 10000.0 if green_space[row_index][col_index] > 10000.0 else green_space[row_index][col_index]
        street_space[row_index][col_index] = row['aree-stradali_area']
        ext_space[row_index][col_index] = row['Single parts_area']
        num_areas[row_index][col_index] = float(row['NUMPOINTS']) + 1 if street_space[row_index][col_index] > 0 else float(row['NUMPOINTS'])
        
    instance = (n_rows, n_cols, street_space, ext_space, green_space, num_areas, densities_df)

    # Create the output directory if it doesn't exist
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # File creation
    output_text = to_dzn(instance)
    output_file_path = os.path.join(output_dir, "instance.dzn")
    with open(output_file_path, "w") as output_file:
       output_file.write(output_text)

if __name__ == '__main__':
    parse("./Minizinc")
