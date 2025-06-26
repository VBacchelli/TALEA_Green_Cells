import numpy as np
import pandas as pd
from pathlib import Path


WORKING_DIR_PATH = Path.cwd()
RAW_DATA_DIR_PATH = WORKING_DIR_PATH.joinpath("dataset", "raw_data")
PROCESSED_DATA_DIR_PATH = WORKING_DIR_PATH.joinpath("dataset", "processed_data")


def to_dzn(instance):
    """
    Takes the problem instance and converts it to a string in the format required by MiniZinc.
    
    Input:
    - instance: tuple, instance in the format (num_cells, top_k, beta_streets, alpha_yard, street_space, ext_space, green_space, num_areas, num_trees, macro_factors)
    Output:
    - text: string

    """

    num_cells, top_k, beta_streets, alpha_yard, street_space, ext_space, green_space, num_areas, num_trees, macro_factors = instance

    num_cells_str = 'len = ' + str(num_cells) + ';\n'
    top_k_str = 'top_k = ' + str(top_k) + ';\n'
    beta_streets_str = 'beta_streets = ' + str(beta_streets) + ';\n'
    alpha_yard_str = 'alpha_yard = ' + str(alpha_yard) + ';\n'
    street_space_str = 'street_space = [ '
    ext_space_str = 'ext_space = [ '
    green_space_str = 'green_space = [ '
    num_areas_str = 'num_areas = [ '
    num_trees_str = 'num_trees = [ '
    macro_factors_str = 'macro_factors = [ '
    for i in range(num_cells):
        if i == num_cells - 1:
            street_space_str += str(street_space[i]) + ' ];\n'
            ext_space_str += str(ext_space[i]) + ' ];\n'
            green_space_str += str(green_space[i]) + ' ];\n'
            num_areas_str += str(num_areas[i]) + ' ];\n'
            num_trees_str += str(num_trees[i]) + ' ];\n'
            macro_factors_str += str(macro_factors[i]) + ' ];\n'
        else:
            street_space_str += str(street_space[i]) + ', '
            ext_space_str += str(ext_space[i]) + ', '
            green_space_str += str(green_space[i]) + ', '
            num_areas_str += str(num_areas[i]) + ', '
            num_trees_str += str(num_trees[i]) + ', '
            macro_factors_str += str(macro_factors[i]) + ', '

    text = num_cells_str + top_k_str + beta_streets_str + alpha_yard_str + street_space_str + ext_space_str + green_space_str + num_areas_str + num_trees_str + macro_factors_str
    return text

def density_per_area(gdf_area, df_dens):
    """
    Computes the density of the population in each cell of the grid based on the intersection area with the statistic areas of Bologna.

    Input:
    - gdf_area: GeoDataFrame, contains the grid data with the intersection area and zone names
    - df_dens: DataFrame, contains the population data for each zone
    Output:
    - out: numpy array, density of the population in each cell of the grid

    """

    cells_values = gdf_area['id'].unique()
    num_cells = len(cells_values)
    df_out = pd.DataFrame(columns=['id', 'density'])
    for i in range(num_cells):
        temp_df = gdf_area.loc[gdf_area['id'] == cells_values[i]]
        temp_sum = 0
        for _, row in temp_df.iterrows():
            code = row['codice_area_statistica']
            temp_dens = df_dens[df_dens['Codice Area Statistica'] == code]
            density = float(temp_dens['Densità'].values[0])
            temp_sum += density * row['intersect_area_statistica']
        df_out.loc[len(df_out)] = [i+1, temp_sum / 10000]
    return df_out

def macro_factor_per_area(gdf_area, gdf_macro):
    """
    Computes the macro utility factor for each area based on the statistic area occupancy.

    Input:
    - gdf_area: GeoDataFrame, contains the grid data with the intersection area of the statistic areas
    - gdf_macro: GeoDataFrame, contains the macro utility factors for each statistic area
    Output:
    - out: numpy array, macro utility factor for each cell of the grid
    
    """

    cells_values = gdf_area['id'].unique()
    num_cells = len(cells_values)
    out = np.zeros((num_cells, ), dtype=float)
    for i in range(num_cells):
        temp_df = gdf_area.loc[gdf_area['id'] == cells_values[i]]
        temp_sum = 0
        for row in temp_df.itertuples():
            temp_factor = gdf_macro[gdf_macro['codice_area_statistica'] == row.codice_area_statistica]['macro_utility_factor'].values[0]
            temp_sum += temp_factor * row.intersect_area_statistica
        out[i] = temp_sum / 10000
    return out