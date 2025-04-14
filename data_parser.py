import geopandas as gpd
import os
import numpy as np


def to_mzn(instance):
    """
    Takes the problem instance and converts it to a string in the format required by MiniZinc.
    
    Input:
    - instance: tuple
    Output:
    - text: string

    """

    n_rows, n_cols, free_space, green_space = instance
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

def parse(input_dataset, output_dir):
    """
    Generates the parsed file in the Minizinc data format from the input dataset to the specified output directory.

    Input:
    - input_dataset: str, path to the input dataset
    - output_dir: str, path to the output directory

    """

    # Read the data
    gdf = gpd.read_file(input_dataset)
    gdf.set_index("id", inplace=True)
    n_rows, n_cols = np.max(gdf['row_index']) + 1, np.max(gdf['col_index']) + 1

    # Data pre-processing
    gdf_new = gdf.drop(columns=['left', 'top', 'right', 'bottom', 'un_gest_pc', 'verde_privato_urbanizzato_pc', \
                    'rifter_edif_pl_pc', 'rifter_arcstra_li_pc', 'le-aree-verdi-e-le-vie-di-bologna-dedicate-alle-donne_pc', 'geometry'])
    green_space = np.zeros((n_rows, n_cols), dtype=int)
    free_space = np.zeros((n_rows, n_cols), dtype=int)
    for _, row in gdf_new.iterrows():
        row_index = int(row['row_index'])
        col_index = int(row['col_index'])
        green_space[row_index][col_index] = int(row['un_gest_area'] + row['verde_privato_urbanizzato_area'] + 20*row['NUMPOINTS'])
        free_space[row_index][col_index] = int(10000 - row['rifter_edif_pl_area'] - row['rifter_arcstra_li_area'])
        green_space[row_index][col_index] = 10000 if green_space[row_index][col_index] > 10000 else green_space[row_index][col_index]
        free_space[row_index][col_index] = 0 if free_space[row_index][col_index] < 0 else free_space[row_index][col_index]
    instance = (n_rows, n_cols, free_space, green_space)

    # Create the output directory if it doesn't exist
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # File creation
    output_text = to_mzn(instance)
    output_file_path = os.path.join(output_dir, "instance.dzn")
    with open(output_file_path, "w") as output_file:
       output_file.write(output_text)

if __name__ == '__main__':
    parse("./dataset/polygon_trees.geojson", "./Minizinc")
