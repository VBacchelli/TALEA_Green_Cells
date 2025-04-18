import geopandas as gpd
import os
import numpy as np
import pandas as pd

def to_mzn(instance):
    #### TODO: add utility scores to the output instance
    """
    Takes the problem instance and converts it to a string in the format required by MiniZinc.
    
    Input:
    - instance: tuple
    Output:
    - text: string

    """

    n_rows, n_cols, free_space, green_space, utility_scores = instance
    assert len(free_space) == len(green_space)

    n_rows_str = 'm = ' + str(n_rows) + ';\n'
    n_cols_str = 'n = ' + str(n_cols) + ';\n'
    free_space_str = 'FS = [| '
    green_space_str = 'GS = [| '
    for i in range(n_rows):
        for j in range(n_cols):
            if j == n_cols - 1:
                free_space_str += str(free_space[i][j]) + '\n |'
                green_space_str += str(green_space[i][j]) + '\n |'
            else:
                free_space_str += str(free_space[i][j]) + ', '
                green_space_str += str(green_space[i][j]) + ', '
    free_space_str += '];\n'
    green_space_str += '];\n'

    text = n_rows_str + n_cols_str + free_space_str + green_space_str
    return text

def density_estimation(df):
    """
    Description
    """
    # densities = pd.DataFrame(columns=df.columns)
    # for zone in zones:
    #     temp_df = df[df['Zona'] == zone]
    #     temp_df = df[df['Nomi misure'] == 'Densità di popolazione']
    #     pd.concat([densities, temp_df], axis=0, ignore_index=True)
    
    # Compute density for each cell
    n_rows, n_cols = np.max(df['row_index']) + 1, np.max(df['col_index']) + 1
    out = np.zeros((n_rows, n_cols), dtype=float)
    for id in range(1, max(df['id'])+1):
        temp_df = df[df['id'] == id]
        row_index = temp_df['row_index'].values[0]
        col_index = temp_df['col_index'].values[0]
        temp_sum = 0
        for _, row in temp_df.iterrows():
            zone = row['nomezona']
            if zone == 'S. Vitale':
                zone = 'San Vitale'
            temp_df = df[df['Zona'] == zone]
            temp_df = df[df['Nomi misure'] == 'Densità di popolazione']
            density = float(df['Valori misure'].values[0])
            temp_sum += density * row['intersect_area']
        out[row_index][col_index] = temp_sum / 10000
    return out

def utility_index(green_est, population):
    """
    Description
    """
    return green_est / population

def parse(output_dir):
    """
    Generates the parsed file in the Minizinc data format from the input dataset to the specified output directory.

    Input:
    - output_dir: str, path to the output directory

    """

    # Read the data
    gdf_tot = gpd.read_file("./dataset/polygon_trees.geojson")
    gdf_tot.set_index("id", inplace=True)
    gdf_trees = gpd.read_file("./dataset/count_tree_grid.geojson")
    gdf_trees.set_index("id", inplace=True)
    gdf_pop = gpd.read_file("./dataset/zone_bologna.geojson")
    #gdf_pop.set_index("id", inplace=True)
    n_rows, n_cols = np.max(gdf_tot['row_index']) + 1, np.max(gdf_tot['col_index']) + 1
    df_pop = pd.read_csv("./dataset/population_stat.csv")
    #zones_bo = gdf_pop['Zona'].unique().tolist()
    #zones_bo.replace('S. Vitale', 'San Vitale', inplace=True)

    # Data pre-processing
    gdf_tot['NUMPOINTS'] = gdf_trees['NUMPOINTS']
    densities_df = density_estimation(df_pop)

    green_space = np.zeros((n_rows, n_cols), dtype=int)
    free_space = np.zeros((n_rows, n_cols), dtype=int)
    utility_scores = np.zeros((n_rows, n_cols), dtype=float)
    for _, row in gdf_tot.iterrows():
        row_index = int(row['row_index'])
        col_index = int(row['col_index'])

        green_space[row_index][col_index] = int(row['un_gest_area'] + row['verde_privato_urbanizzato_area'] + 0*row['NUMPOINTS'])
        green_space[row_index][col_index] = 10000 if green_space[row_index][col_index] > 10000 else green_space[row_index][col_index]

        free_space[row_index][col_index] = int(10000 - row['rifter_edif_pl_area'])
        free_space[row_index][col_index] = 0 if free_space[row_index][col_index] < 0 else free_space[row_index][col_index]

        min_row = row_index if row_index - 2 < 0 else row_index - 2
        max_row = row_index if row_index + 2 > n_rows - 1 else row_index + 2
        min_col = col_index if col_index - 2 < 0 else col_index - 2
        max_col = col_index if col_index + 2 > n_cols - 1 else col_index + 2
        temp_green_estention = green_space[row_index][col_index]
        for i in range(min_row, max_row + 1):
            for j in range(min_col, max_col + 1):
                if i == row_index and j == col_index:
                    continue
                elif i == row_index-1 or i == row_index+1 or j == col_index-1 or j == col_index+1:
                    temp_green_estention += green_space[i][j] / 2
                elif i == row_index-2 or i == row_index+2 or j == col_index-2 or j == col_index+2:
                    temp_green_estention += green_space[i][j] / 4
        utility_scores[row_index][col_index] = utility_index(temp_green_estention, densities_df[row_index][col_index])

    instance = (n_rows, n_cols, free_space, green_space, utility_scores)

    # Create the output directory if it doesn't exist
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # File creation
    output_text = to_mzn(instance)
    output_file_path = os.path.join(output_dir, "instance.dzn")
    with open(output_file_path, "w") as output_file:
       output_file.write(output_text)

if __name__ == '__main__':
    parse("./Minizinc")
