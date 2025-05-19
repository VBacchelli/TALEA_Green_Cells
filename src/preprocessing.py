import pandas as pd
import geopandas as gpd

def squares_elimination():
    """
    Deletion of the squares from the street data.
    
    """
    gdf_streets = gpd.read_file('dataset/aree-stradali.geojson')
    gdf_streets_1 = gdf_streets[gdf_streets['descrizion'] != 'Tronco di intersezione tra strade a raso']
    gdf_streets_2 = gdf_streets[gdf_streets['descrizion'] == 'Tronco di intersezione tra strade a raso']
    gdf_streets_2 = gdf_streets_2[gdf_streets_2['area_ogg'] <= 1500]
    gdf_streets = pd.concat([gdf_streets_1, gdf_streets_2], axis=0)
    gdf_streets.to_file('dataset/aree-stradali-modified.geojson', driver='GeoJSON')

def density_estimation():
    """
    Enlarges the dataset of the population per statistical area with the relative density.

    """
    gdf_area = gpd.read_file("dataset/aree_statistiche_area.geojson")
    df_pop = pd.read_csv("dataset/popolazione_per_area_statistica.csv", sep=";")
    df_pop = df_pop[df_pop['Codice Area Statistica'] != 99]
    densities = []
    for _, row in df_pop.iterrows():
        code = row['Codice Area Statistica']
        temp_gdf = gdf_area[gdf_area['codice_area_statistica'] == code]
        area_km2 = temp_gdf['area'].values[0] / 1000000
        densities.append(row['Residenti'] / area_km2)
    df_pop['Densità'] = densities
    df_pop.to_csv("dataset/popolazione_per_area_statistica.csv", sep=";", index=False)

if __name__ == "__main__":
    density_estimation()
    squares_elimination()