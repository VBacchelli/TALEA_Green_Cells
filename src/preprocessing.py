import pandas as pd
import geopandas as gpd
from pathlib import Path
import argparse


WORKING_DIR_PATH = Path.cwd()
RAW_DATA_DIR_PATH = WORKING_DIR_PATH.joinpath("dataset", "raw_data")
PROCESSED_DATA_DIR_PATH = WORKING_DIR_PATH.joinpath("dataset", "processed_data")


def density_estimation():
    """
    Enlarges the dataset of the population per statistical area with the relative density.

    """

    gdf_area = gpd.read_file(PROCESSED_DATA_DIR_PATH.joinpath("aree_statistiche_area.geojson"))
    df_pop = pd.read_csv(RAW_DATA_DIR_PATH.joinpath("popolazione_per_area_statistica.csv"))
    df_pop = df_pop[df_pop['Codice Area Statistica'] != 99]
    densities = []
    for _, row in df_pop.iterrows():
        code = row['Codice Area Statistica']
        temp_gdf = gdf_area[gdf_area['codice_area_statistica'] == code]
        area_km2 = temp_gdf['area'].values[0] / 1000000
        densities.append(row['Residenti'] / area_km2)
    df_pop['Densità'] = densities
    df_pop.to_csv(PROCESSED_DATA_DIR_PATH.joinpath("densità_per_area_statistica.csv"), sep=';', index=False)

def macro_factors_computation(density_param=0.5, green_param=0.5):
    """
    Estimates the factor to be applied to the macro utility function for statitistical areas.

    Input:
    - density_param: float, weight for the population density in the macro utility function (default 0.5)
    - green_param: float, weight for the green space in the macro utility function (default 0.5)

    """

    if density_param + green_param != 1.0:
        raise ValueError("The sum of density_param and green_param must be equal to 1.0.")
    else:
        gdf_area = gpd.read_file(PROCESSED_DATA_DIR_PATH.joinpath("aree_statistiche_con_verde.geojson"))
        df_dens = pd.read_csv(PROCESSED_DATA_DIR_PATH.joinpath("densità_per_area_statistica.csv"), sep=';')
        max_density = df_dens['Densità'].max()
        factors = []
        for row in gdf_area.itertuples():
            green_factor = 100.0 - row.Unione_pc
            green_factor = green_factor / 100.0
            density = df_dens[df_dens['Codice Area Statistica'] == row.codice_area_statistica]['Densità'].values[0]
            density_factor = density / max_density
            factors.append((density_param * density_factor) + (green_param * green_factor))
        gdf_area['macro_utility_factor'] = factors
        gdf_area.to_file(PROCESSED_DATA_DIR_PATH.joinpath("aree_statistiche_macro_factors.geojson"), driver='GeoJSON')

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Preprocess the data in order to adapt them to the model.")
    parser.add_argument("--density_param", 
                        type=float, 
                        default=0.5, 
                        help="Weight for the population density in the macro utility function.")
    parser.add_argument("--green_param", 
                        type=float, 
                        default=0.5, 
                        help="Weight for the green space in the macro utility function.")
    args = parser.parse_args()

    density_estimation()
    macro_factors_computation(args.density_param, args.green_param)
