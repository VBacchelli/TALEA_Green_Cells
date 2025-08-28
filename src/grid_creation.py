import os
import geopandas as gpd
from pathlib import Path
import pandas as pd
import argparse
from qgis.core import *
from qgis.analysis import QgsNativeAlgorithms
import processing
from processing.core.Processing import Processing


WORKING_DIR_PATH = Path.cwd()
RAW_DATA_DIR_PATH = WORKING_DIR_PATH.joinpath("dataset", "raw_data")
PROCESSED_DATA_DIR_PATH = WORKING_DIR_PATH.joinpath("dataset", "processed_data")

qgs = QgsApplication([], False)
qgs.setPrefixPath("/usr", True)
qgs.initQgis()

Processing.initialize()
qgs.processingRegistry().addProvider(QgsNativeAlgorithms())


def save_layer(output_layer, layer_name, path, remove_attrs="geo_point_2d"):
    """
    Save a QGIS vector layer to a GeoJSON file with filtered attributes.

    Input:
    - output_layer: QgsVectorLayer, the layer to save
    - layer_name: str, the name of the layer to be saved
    - path: str, the directory path where the layer will be saved
    - remove_attrs: list or str, attributes to remove from the layer

    """

    output_file_path = os.path.join(path, f'{layer_name}.geojson')

    original_fields = output_layer.fields()
    new_fields = QgsFields()
    field_indices_to_keep = []

    # Prepare field filtering
    if remove_attrs:
        if isinstance(remove_attrs, str):
            remove_attrs = [remove_attrs]

        for idx, field in enumerate(original_fields):
            if field.name() not in remove_attrs:
                new_fields.append(field)
                field_indices_to_keep.append(idx)
    else:
        # No fields to remove
        new_fields = original_fields
        field_indices_to_keep = list(range(len(original_fields)))

    # Set up writer
    geometry_type = output_layer.wkbType()
    crs = output_layer.crs()
    transform_context = QgsProject.instance().transformContext()

    options = QgsVectorFileWriter.SaveVectorOptions()
    options.driverName = "GeoJSON"
    options.fileEncoding = "UTF-8"
    options.actionOnExistingFile = QgsVectorFileWriter.CreateOrOverwriteFile

    writer = QgsVectorFileWriter.create(
        output_file_path,
        new_fields,
        geometry_type,
        crs,
        transform_context,
        options,
        QgsFeatureSink.SinkFlags()
    )

    # Write features with filtered attributes
    if writer.hasError() == QgsVectorFileWriter.NoError:
        for original_feature in output_layer.getFeatures():
            new_feature = QgsFeature()
            new_feature.setGeometry(original_feature.geometry())

            new_attributes = []
            for idx in field_indices_to_keep:
                val = original_feature.attributes()[idx]
                if val == "" or val is None:
                    val = "Unknown"  # Or any other safe default
                new_attributes.append(val)

            new_feature.setAttributes(new_attributes)
            writer.addFeature(new_feature)

        del writer
        print(f"Layer saved to: {output_file_path}")
    else:
        print(f"Failed to save layer: {writer.errorMessage()}")

def compute_weighted_uhei(grid, uhei_layer):
    """
    Compute the weighted UHEI for each grid cell based on the intersection area with UHEI data.

    Input:
    - grid: QgsVectorLayer or pathlib.Path, the grid layer or path to the grid GeoJSON file
    - uhei_layer: QgsVectorLayer or pathlib.Path, the UHEI layer or path to the GeoJSON file
    Output:
    - result: GeoDataFrame, containing the grid cells with their corresponding weighted UHEI values

    """

    grid_uhei = processing.run("native:fieldcalculator", {'INPUT':grid,'FIELD_NAME':'area_grid','FIELD_TYPE':0,'FIELD_LENGTH':0,'FIELD_PRECISION':0,'FORMULA':'$area','OUTPUT':'TEMPORARY_OUTPUT'})['OUTPUT']
    save_layer(grid_uhei, 'grid_uhei', PROCESSED_DATA_DIR_PATH)

    # Weighted UHEI on the basis of the area computation
    intersection_layer = processing.run("native:intersection", {'INPUT':grid_uhei,'OVERLAY':uhei_layer,'INPUT_FIELDS':[],'OVERLAY_FIELDS':['uhei'],'OVERLAY_FIELDS_PREFIX':'','OUTPUT':'TEMPORARY_OUTPUT','GRID_SIZE':None})['OUTPUT']
    intersection_layer = processing.run("native:fieldcalculator", {'INPUT':intersection_layer,'FIELD_NAME':'area_intersection','FIELD_TYPE':0,'FIELD_LENGTH':0,'FIELD_PRECISION':0,'FORMULA':'$area','OUTPUT':'TEMPORARY_OUTPUT'})['OUTPUT']
    intersection_layer = processing.run("native:fieldcalculator", {'INPUT':intersection_layer,'FIELD_NAME':'weighted_uhei','FIELD_TYPE':0,'FIELD_LENGTH':0,'FIELD_PRECISION':0,'FORMULA':'area_intersection/area_grid*uhei','OUTPUT':'TEMPORARY_OUTPUT'})['OUTPUT']
    save_layer(intersection_layer, 'intersection_layer_uhei', PROCESSED_DATA_DIR_PATH)

    intersection = gpd.read_file(PROCESSED_DATA_DIR_PATH.joinpath("intersection_layer_uhei.geojson"))
    grid_uhei = gpd.read_file(PROCESSED_DATA_DIR_PATH.joinpath("grid_uhei.geojson"))

    id_col = 'id'
    sum_col = 'weighted_uhei'

    intersection = intersection.drop(['area_grid', 'area_intersection', 'uhei'], axis=1)
    agg = {c: 'first' for c in intersection.columns if c not in [id_col, sum_col]}
    agg[sum_col] = 'sum'

    result = intersection.groupby(id_col, as_index=False).agg(agg)
    geom_map = grid_uhei.set_index("id")["geometry"]
    result["geometry"] = result["id"].map(geom_map)
    result = gpd.GeoDataFrame(result, geometry='geometry', crs=intersection.crs)

    return result

def compute_weighted_ndvi(grid, ndvi_layer):
    """
    Compute the weighted NDVI for each grid cell based on the intersection area with NDVI data.

    Input:
    - grid: QgsVectorLayer or pathlib.Path, the grid layer or path to the grid GeoJSON file
    - ndvi_layer: QgsVectorLayer or pathlib.Path, the NDVI index layer or path to the GeoJSON file
    Output:
    - result: GeoDataFrame, containing the grid cells with their corresponding weighted NDVI values

    """

    grid_ndvi = processing.run("native:fieldcalculator", {'INPUT':grid,'FIELD_NAME':'area_grid','FIELD_TYPE':0,'FIELD_LENGTH':0,'FIELD_PRECISION':0,'FORMULA':'$area','OUTPUT':'TEMPORARY_OUTPUT'})['OUTPUT']
    save_layer(grid_ndvi, 'grid_ndvi', PROCESSED_DATA_DIR_PATH)

    # Weighted NDVI on the basis of the area computation
    intersection_layer = processing.run("native:intersection", {'INPUT':grid_ndvi,'OVERLAY':ndvi_layer,'INPUT_FIELDS':[],'OVERLAY_FIELDS':['ndvi'],'OVERLAY_FIELDS_PREFIX':'','OUTPUT':'TEMPORARY_OUTPUT','GRID_SIZE':None})['OUTPUT']
    intersection_layer = processing.run("native:fieldcalculator", {'INPUT':intersection_layer,'FIELD_NAME':'area_intersection','FIELD_TYPE':0,'FIELD_LENGTH':0,'FIELD_PRECISION':0,'FORMULA':'$area','OUTPUT':'TEMPORARY_OUTPUT'})['OUTPUT']
    intersection_layer = processing.run("native:fieldcalculator", {'INPUT':intersection_layer,'FIELD_NAME':'weighted_ndvi','FIELD_TYPE':0,'FIELD_LENGTH':0,'FIELD_PRECISION':0,'FORMULA':'area_intersection/area_grid*ndvi','OUTPUT':'TEMPORARY_OUTPUT'})['OUTPUT']
    save_layer(intersection_layer, 'intersection_layer_ndvi', PROCESSED_DATA_DIR_PATH)

    intersection = gpd.read_file(PROCESSED_DATA_DIR_PATH.joinpath("intersection_layer_ndvi.geojson"))
    grid_ndvi = gpd.read_file(PROCESSED_DATA_DIR_PATH.joinpath("grid_ndvi.geojson"))

    id_col = 'id'
    sum_col = 'weighted_ndvi'

    intersection = intersection.drop(['area_grid', 'area_intersection', 'ndvi'], axis=1)
    agg = {c: 'first' for c in intersection.columns if c not in [id_col, sum_col]}
    agg[sum_col] = 'sum'

    result = intersection.groupby(id_col, as_index=False).agg(agg)
    geom_map = grid_ndvi.set_index("id")["geometry"]
    result["geometry"] = result["id"].map(geom_map)
    result = gpd.GeoDataFrame(result, geometry='geometry', crs=intersection.crs)

    return result

def streets_processing():
    """
    Deletion of the squares and the highway from the street data.

    Output:
    - streets: QgsVectorLayer, vector layer containing the cleaned street data
    
    """

    # Squares elimination
    gdf_streets = gpd.read_file(RAW_DATA_DIR_PATH.joinpath("aree-stradali.geojson"))
    gdf_streets_1 = gdf_streets[gdf_streets['descrizion'] != 'Tronco di intersezione tra strade a raso']
    gdf_streets_2 = gdf_streets[gdf_streets['descrizion'] == 'Tronco di intersezione tra strade a raso']
    gdf_streets_2 = gdf_streets_2[gdf_streets_2['area_ogg'] <= 7500]
    gdf_streets = pd.concat([gdf_streets_1, gdf_streets_2], axis=0)
    gdf_streets.to_file(PROCESSED_DATA_DIR_PATH.joinpath("aree-stradali-modified.geojson"), driver='GeoJSON')

    # Highway elimination
    highway = gpd.read_file(str(RAW_DATA_DIR_PATH.joinpath('uso_suolo_bologna.geojson')))
    highway = highway[highway['DESCR'] == 'Autostrade e superstrade']
    highway.to_file(str(PROCESSED_DATA_DIR_PATH.joinpath('autostrada.geojson')), driver='GeoJSON')

    streets = processing.run("native:difference", {'INPUT':str(PROCESSED_DATA_DIR_PATH.joinpath("aree-stradali-modified.geojson")),'OVERLAY':str(PROCESSED_DATA_DIR_PATH.joinpath('autostrada.geojson')),'OUTPUT':'TEMPORARY_OUTPUT','GRID_SIZE':None})['OUTPUT']
    save_layer(streets, 'aree-stradali-modified', PROCESSED_DATA_DIR_PATH)
    return streets

def create_verde(raw_data_path, processed_data_path):
    """
    Creation of the vector containig all the green elements unified from different datasets

    Input:
    - raw_data_path: pathlib.Path, path to the raw data directory
    - processed_data_path: pathlib.Path, path to the processed data directory
    Output:
    - verde: QgsVectorLayer, vector layer containing the union of all green elements

    """
    
    un_gest = processing.run("native:fixgeometries", {'INPUT':str(raw_data_path.joinpath('un_gest.fgb')), 'OUTPUT':'TEMPORARY_OUTPUT'})['OUTPUT']
    null_values = processing.run("native:extractbyattribute", {'INPUT':un_gest,'FIELD':'area_prato','OPERATOR':8,'VALUE':'','OUTPUT':'TEMPORARY_OUTPUT'})['OUTPUT']
    to_delete = processing.run("native:extractbyattribute", {'INPUT':null_values,'FIELD':'nome','OPERATOR':0,'VALUE':'AIUOLE ALBERTO MANZI','OUTPUT':'TEMPORARY_OUTPUT'})['OUTPUT']
    un_gest = processing.run("native:difference", {'INPUT':un_gest,'OVERLAY':to_delete,'OUTPUT':'TEMPORARY_OUTPUT','GRID_SIZE':None})['OUTPUT']
    verde_privato_urbanizzato = processing.run("native:fixgeometries", {'INPUT':str(raw_data_path.joinpath('verde_privato_urbanizzato.fgb')), 'OUTPUT':'TEMPORARY_OUTPUT'})['OUTPUT']

    aree_boschive_1 = QgsVectorLayer(str(raw_data_path.joinpath('aree-boschive.gpkg')) + "|layername=V_AAI_GPG", 'aree_boschive_1', 'ogr')
    aree_boschive_1 = processing.run("native:fixgeometries", {'INPUT':aree_boschive_1, 'OUTPUT':'TEMPORARY_OUTPUT'})['OUTPUT']
    aree_boschive_2 = QgsVectorLayer(str(raw_data_path.joinpath('aree-boschive.gpkg')) + "|layername=V_PSR_GPG", 'aree_boschive_2', 'ogr')
    aree_boschive_2 = processing.run("native:fixgeometries", {'INPUT':aree_boschive_2, 'OUTPUT':'TEMPORARY_OUTPUT'})['OUTPUT']
    aree_boschive_3 = QgsVectorLayer(str(raw_data_path.joinpath('aree-boschive.gpkg')) + "|layername=V_BSC_GPG", 'aree_boschive_3', 'ogr')
    aree_boschive_3 = processing.run("native:fixgeometries", {'INPUT':aree_boschive_3, 'OUTPUT':'TEMPORARY_OUTPUT'})['OUTPUT']
    aree_fluviali = QgsVectorLayer(str(raw_data_path.joinpath('aree-fluviali.gpkg')) + "|layername=V_ABA_GPG", 'aree_fluviali', 'ogr')
    aree_fluviali = processing.run("native:fixgeometries", {'INPUT':aree_fluviali, 'OUTPUT':'TEMPORARY_OUTPUT'})['OUTPUT']

    gdf = gpd.read_file(raw_data_path.joinpath('aree-statistiche.geojson'))
    gdf = gdf[gdf["area_statistica"].isin(["GIARDINI MARGHERITA"])]
    gdf.to_file(processed_data_path.joinpath("giardini_margherita.geojson"), driver="GeoJSON")

    verde = processing.run("native:multiunion", {'INPUT':un_gest,'OVERLAYS':[str(processed_data_path.joinpath('giardini_margherita.geojson')), verde_privato_urbanizzato, aree_boschive_1, aree_boschive_2, aree_boschive_3, aree_fluviali],'OVERLAY_FIELDS_PREFIX':'','OUTPUT':'TEMPORARY_OUTPUT'})['OUTPUT']
    verde = processing.run("native:fixgeometries", {'INPUT':verde, 'OUTPUT':str(PROCESSED_DATA_DIR_PATH.joinpath('verde.gpkg'))})['OUTPUT']
    print(f"Layer saved to: {str(PROCESSED_DATA_DIR_PATH.joinpath('verde.gpkg'))}")
    return verde

def create_ferrovia(raw_data_path, processed_data_path):
    """
    Creation of the vector containig all the ferrovia elements unified from different datasets

    Input:
    - raw_data_path: pathlib.Path, path to the raw data directory
    - processed_data_path: pathlib.Path, path to the processed data directory
    Output:
    - railway: QgsVectorLayer, vector layer containing the union of all railway elements

    """
    
    railway = gpd.read_file(str(raw_data_path.joinpath('uso_suolo_bologna.geojson')))
    railway = railway[railway['DESCR'] == 'Reti ferroviare']
    railway.to_file(str(processed_data_path.joinpath('ferrovia.geojson')), driver='GeoJSON')

    railway = processing.run("native:multidifference", {'INPUT':str(processed_data_path.joinpath('ferrovia.geojson')),'OVERLAYS':[str(raw_data_path.joinpath('rifter_edif_pl.geojson')), str(processed_data_path.joinpath('verde.gpkg'))],'OUTPUT':'TEMPORARY_OUTPUT'})['OUTPUT']
    return railway

def main(bologna_size):
    """
    Main function to process the Bologna data and create a grid with various attributes.

    Input:
    - bologna_size: str, size of the Bologna area to process ('full' for the entire city, 'center' for the city center)

    """

    if bologna_size == 'full':
        GRID_DIR_PATH = PROCESSED_DATA_DIR_PATH.joinpath("full")
        
        loc_abitativa = gpd.read_file(RAW_DATA_DIR_PATH.joinpath('località_abitative.gpkg'), layer="V_LAB_GPG")
        loc_abitativa = loc_abitativa[loc_abitativa["NM_LAB"] == "BOLOGNA"]
        loc_abitativa.to_file(PROCESSED_DATA_DIR_PATH.joinpath('localita_abitative.geojson'), driver="GeoJSON")
        
        area_abitata = processing.run("native:clip", {'INPUT':str(RAW_DATA_DIR_PATH.joinpath('aree-statistiche.geojson')),'OVERLAY':str(PROCESSED_DATA_DIR_PATH.joinpath('localita_abitative.geojson')),'OUTPUT':'TEMPORARY_OUTPUT'})['OUTPUT']
        save_layer(area_abitata, 'area_abitata_full', PROCESSED_DATA_DIR_PATH)
        area_abitata = gpd.read_file(PROCESSED_DATA_DIR_PATH.joinpath('area_abitata_full.geojson'))
        area_abitata = area_abitata[~ area_abitata["area_statistica"].isin(["RIGOSA", "LAVINO DI MEZZO", "AEROPORTO", "BARGELLINO", "VIA DEL VIVAIO", "LA BIRRA", "LA NOCE", "TIRO A SEGNO", "LAGHETTI DEL ROSARIO", "SAVENA ABBANDONATO", "MULINO DEL GOMITO", "CADRIANO-CALAMOSCO", "FIERA", "STRADELLI GUELFI", "LUNGO SAVENA", "OSPEDALE BELLARIA", "MONTE DONATO", "PONTE SAVENA-LA BASTIA", "PADERNO", "RAVONE", "VIA DEL GENIO", "SAN LUCA", "LUNGO RENO", "CAAB"])]
        area_abitata.to_file(PROCESSED_DATA_DIR_PATH.joinpath('area_abitata_full.geojson'), driver="GeoJSON")

        # Create the grid for the entire city
        grid_bologna = processing.run("native:creategrid", {'TYPE':2,'EXTENT':str(PROCESSED_DATA_DIR_PATH.joinpath('area_abitata_full.geojson')),'HSPACING':100,'VSPACING':100,'HOVERLAY':0,'VOVERLAY':0,'CRS':QgsCoordinateReferenceSystem('EPSG:3857'),'OUTPUT':'TEMPORARY_OUTPUT'})['OUTPUT']
        grid_bologna = processing.run("native:clip", {'INPUT':grid_bologna,'OVERLAY':str(PROCESSED_DATA_DIR_PATH.joinpath('area_abitata_full.geojson')),'OUTPUT':'TEMPORARY_OUTPUT'})['OUTPUT']

        aree_statistiche = processing.run("native:intersection", {'INPUT':grid_bologna,'OVERLAY':str(PROCESSED_DATA_DIR_PATH.joinpath('area_abitata_full.geojson')),'INPUT_FIELDS':[],'OVERLAY_FIELDS':[],'OVERLAY_FIELDS_PREFIX':'','OUTPUT':'TEMPORARY_OUTPUT','GRID_SIZE':None})['OUTPUT']
    
    else:
        GRID_DIR_PATH = PROCESSED_DATA_DIR_PATH.joinpath("center")

        loc_abitativa = gpd.read_file(RAW_DATA_DIR_PATH.joinpath('aree-statistiche.geojson'))
        loc_abitativa = loc_abitativa[loc_abitativa["area_statistica"].isin(["IRNERIO-1", "IRNERIO-2", "MARCONI-1", "MARCONI-2", "MALPIGHI-1", "MALPIGHI-2", "GALVANI-1", "GALVANI-2"])]
        loc_abitativa.to_file(PROCESSED_DATA_DIR_PATH.joinpath('localita_abitative.geojson'), driver="GeoJSON")

        area_abitata = processing.run("native:clip", {'INPUT':str(RAW_DATA_DIR_PATH.joinpath('aree-statistiche.geojson')),'OVERLAY':str(PROCESSED_DATA_DIR_PATH.joinpath('localita_abitative.geojson')),'OUTPUT':'TEMPORARY_OUTPUT'})['OUTPUT']

        # Create the grid for the city center
        grid_bologna = processing.run("native:creategrid", {'TYPE':2,'EXTENT':area_abitata,'HSPACING':100,'VSPACING':100,'HOVERLAY':0,'VOVERLAY':0,'CRS':QgsCoordinateReferenceSystem('EPSG:3857'),'OUTPUT':'TEMPORARY_OUTPUT'})['OUTPUT']
        grid_bologna = processing.run("native:clip", {'INPUT':grid_bologna,'OVERLAY':area_abitata,'OUTPUT':'TEMPORARY_OUTPUT'})['OUTPUT']

        aree_statistiche = processing.run("native:intersection", {'INPUT':grid_bologna,'OVERLAY':area_abitata,'INPUT_FIELDS':[],'OVERLAY_FIELDS':[],'OVERLAY_FIELDS_PREFIX':'','OUTPUT':'TEMPORARY_OUTPUT','GRID_SIZE':None})['OUTPUT']

    # Compute the area of each area_statistica for each grid in bologna 
    aree_statistiche = processing.run("native:fieldcalculator", {'INPUT':aree_statistiche,'FIELD_NAME':'intersect_area_statistica','FIELD_TYPE':0,'FIELD_LENGTH':0,'FIELD_PRECISION':0,'FORMULA':'area($geometry)','OUTPUT':'TEMPORARY_OUTPUT'})['OUTPUT']
    save_layer(aree_statistiche, 'aree_statistiche_grid', GRID_DIR_PATH)

    # Create the green vector layer
    verde = create_verde(RAW_DATA_DIR_PATH, PROCESSED_DATA_DIR_PATH)

    # Create the railway vector layer
    railway = create_ferrovia(RAW_DATA_DIR_PATH, PROCESSED_DATA_DIR_PATH)
    save_layer(railway, 'ferrovia', PROCESSED_DATA_DIR_PATH)

    # Clean the street data
    strade_clean = processing.run("native:multidifference", {'INPUT':str(PROCESSED_DATA_DIR_PATH.joinpath("aree-stradali-modified.geojson")),'OVERLAYS':[verde, railway],'OUTPUT':'TEMPORARY_OUTPUT'})['OUTPUT']
    save_layer(strade_clean, 'aree-stradali-modified', PROCESSED_DATA_DIR_PATH)

    # Compute the free space in which is possible to create new green cells
    available_space = gpd.read_file(str(RAW_DATA_DIR_PATH.joinpath('uso_suolo_bologna.geojson')))
    available_space = available_space[available_space['DESCR'].isin(['Tessuto residenziale compatto e denso', 'Tessuto residenziale urbano', 'Tessuto residenziale  rado'])]
    available_space.to_file(str(PROCESSED_DATA_DIR_PATH.joinpath('free_space.geojson')), driver='GeoJSON')
    free_space = processing.run("native:multidifference", {'INPUT':str(PROCESSED_DATA_DIR_PATH.joinpath('free_space.geojson')),'OVERLAYS':[verde, str(RAW_DATA_DIR_PATH.joinpath('aree-stradali.geojson')), str(RAW_DATA_DIR_PATH.joinpath('rifter_edif_pl.geojson')), railway],'OUTPUT':'TEMPORARY_OUTPUT'})['OUTPUT']
    free_space = processing.run("native:multiparttosingleparts", {'INPUT':free_space,'OUTPUT':'TEMPORARY_OUTPUT'})['OUTPUT']
    save_layer(free_space, 'free_space', PROCESSED_DATA_DIR_PATH)
    
    # Compute how many areas each elements occupy inside the cells
    grid_with_areas = processing.run("native:calculatevectoroverlaps", {'INPUT':grid_bologna,'LAYERS':[verde, str(RAW_DATA_DIR_PATH.joinpath('rifter_edif_pl.geojson')), str(PROCESSED_DATA_DIR_PATH.joinpath("aree-stradali-modified.geojson")), free_space, railway],'OUTPUT':'TEMPORARY_OUTPUT','GRID_SIZE':None})['OUTPUT']
    grid_with_areas = processing.run("native:countpointsinpolygon", {'POLYGONS':grid_with_areas,'POINTS':free_space,'WEIGHT':'','CLASSFIELD':'','FIELD':'free_space_number','OUTPUT':'TEMPORARY_OUTPUT'})['OUTPUT']
    
    # UHEI and NDVI computation
    uhei_layer = processing.run("native:fieldcalculator", {'INPUT':str(RAW_DATA_DIR_PATH.joinpath('indexes', 'urban_heat_exposure_index.geojson')),'FIELD_NAME':'uhei','FIELD_TYPE':0,'FIELD_LENGTH':0,'FIELD_PRECISION':0,'FORMULA':'to_real(value)','OUTPUT':'TEMPORARY_OUTPUT'})['OUTPUT']
    ndvi_layer = processing.run("native:fieldcalculator", {'INPUT':str(RAW_DATA_DIR_PATH.joinpath('indexes', 'ndvi_mean.geojson')),'FIELD_NAME':'ndvi','FIELD_TYPE':0,'FIELD_LENGTH':0,'FIELD_PRECISION':0,'FORMULA':'to_real(value)','OUTPUT':'TEMPORARY_OUTPUT'})['OUTPUT']
    grid_with_areas = compute_weighted_uhei(grid_with_areas, uhei_layer)
    grid_with_areas.to_file(str(GRID_DIR_PATH.joinpath("grid_with_areas.geojson")), driver="GeoJSON")
    grid_with_areas = compute_weighted_ndvi(str(GRID_DIR_PATH.joinpath("grid_with_areas.geojson")), ndvi_layer)
    grid_with_areas.to_file(str(GRID_DIR_PATH.joinpath("grid_with_areas.geojson")), driver="GeoJSON")

    # Compute the number of tree outside the green areas
    area_not_green = processing.run("native:difference", {'INPUT':grid_bologna,'OVERLAY':verde,'OUTPUT':'TEMPORARY_OUTPUT','GRID_SIZE':None})['OUTPUT']
    trees_outside_green = processing.run("native:countpointsinpolygon", {'POLYGONS':area_not_green, 'POINTS':str(RAW_DATA_DIR_PATH.joinpath('alberi-manutenzioni.fgb')),'WEIGHT':'','CLASSFIELD':'','FIELD':'tree_number','OUTPUT':'TEMPORARY_OUTPUT'})['OUTPUT']
    save_layer(trees_outside_green, 'trees_outside_green', GRID_DIR_PATH)

    # Integrate all the computed data in a single grid
    grid = gpd.read_file(GRID_DIR_PATH.joinpath('grid_with_areas.geojson'))
    trees = gpd.read_file(GRID_DIR_PATH.joinpath('trees_outside_green.geojson'))[['id', 'tree_number']]
    trees = trees[~trees['id'].isin(list(set(trees['id']) - set(grid['id'])))]

    final_grid = grid.merge(trees, how='outer', on='id').fillna(0)
    final_grid = final_grid.rename(columns={
        'Single parts_area': 'free_space_area',
        'Single parts_pc': 'free_space_pc',
        'Difference_area': 'railways_area',
        'Difference_pc': 'railways_pc',
        'verde_area': 'green_area',
        'verde_pc': 'green_pc',
        'rifter_edif_pl_area': 'buildings_area',
        'rifter_edif_pl_pc': 'buildings_pc',
        'aree-stradali-modified_area': 'road_area',
        'aree-stradali-modified_pc': 'road_pc',
        'weighted_uhei_sum': 'weighted_uhei',
        'weighted_ndvi_sum': 'weighted_ndvi',
    })
    uhei_max = final_grid['weighted_uhei'].max()
    final_grid['inverse_uhei'] = uhei_max - final_grid['weighted_uhei']
    final_grid.to_file(GRID_DIR_PATH.joinpath("final_grid.geojson"), driver="GeoJSON")
    

    # Compute the green area in each statistical area
    aree_statistiche = processing.run("native:fieldcalculator", {'INPUT':str(RAW_DATA_DIR_PATH.joinpath('aree-statistiche.geojson')),'FIELD_NAME':'area','FIELD_TYPE':0,'FIELD_LENGTH':0,'FIELD_PRECISION':0,'FORMULA':'$area','OUTPUT':'TEMPORARY_OUTPUT'})['OUTPUT']
    aree_statistiche = processing.run("native:calculatevectoroverlaps", {'INPUT':aree_statistiche,'LAYERS':[verde],'OUTPUT':'TEMPORARY_OUTPUT','GRID_SIZE':None})['OUTPUT']
    
    aree_statistiche = processing.run("native:joinbylocationsummary", {'INPUT':aree_statistiche,'PREDICATE':[0],'JOIN':uhei_layer,'JOIN_FIELDS':['uhei'],'SUMMARIES':[6],'DISCARD_NONMATCHING':False,'OUTPUT':'TEMPORARY_OUTPUT'})['OUTPUT']
    aree_statistiche = processing.run("native:joinbylocationsummary", {'INPUT':aree_statistiche,'PREDICATE':[0],'JOIN':ndvi_layer,'JOIN_FIELDS':['ndvi'],'SUMMARIES':[6],'DISCARD_NONMATCHING':False,'OUTPUT':'TEMPORARY_OUTPUT'})['OUTPUT']
    save_layer(aree_statistiche, 'aree_statistiche_stat', PROCESSED_DATA_DIR_PATH)

    aree_statistiche = gpd.read_file(PROCESSED_DATA_DIR_PATH.joinpath('aree_statistiche_stat.geojson'))
    aree_statistiche = aree_statistiche.rename(columns={
        'uhei_mean': 'uhei',
        'ndvi_mean': 'ndvi',
    })
    aree_statistiche.to_file(PROCESSED_DATA_DIR_PATH.joinpath("aree_statistiche_stat.geojson"), driver="GeoJSON")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extraction of information from data through GIS-based processing algorithms.")
    parser.add_argument("--size", 
                        type=str, 
                        default="full", 
                        choices=["center", "full"], 
                        help="Whether to run the model on the city center or on the entire cityscape.")
    args = parser.parse_args()
    
    streets_processing()
    main(args.size)
