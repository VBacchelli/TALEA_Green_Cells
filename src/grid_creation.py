#set as python environment the one from qgis application
import os, sys
import time
import geopandas as gpd
#change with your path to the proj.db file and gdal file
os.environ['PROJ_LIB'] = '/Applications/QGIS-LTR.app/Contents/Resources/proj'
os.environ['GDAL_DATA'] = '/Applications/QGIS-LTR.app/Contents/Resources/gdal'

#change with you path to qgis python plugins (necessary for using processing API)
sys.path.append('/Applications/QGIS-LTR.app/Contents/Resources/python/plugins')

from qgis.core import *
from qgis.analysis import QgsNativeAlgorithms

def save_layer(output_layer, layer_name):

    output_file_path = os.path.join('dataset', f'{layer_name}.geojson')
    
    fields = output_layer.fields()
    geometry_type = output_layer.wkbType()
    crs = output_layer.crs()
    transform_context = QgsProject.instance().transformContext()

    options = QgsVectorFileWriter.SaveVectorOptions()
    options.driverName = "GeoJSON"
    options.fileEncoding = "UTF-8"
    options.actionOnExistingFile = QgsVectorFileWriter.CreateOrOverwriteFile

    writer = QgsVectorFileWriter.create(
        output_file_path,
        fields,
        geometry_type,
        crs,
        transform_context,
        options,
        QgsFeatureSink.SinkFlags()
    )

    if writer.hasError() == QgsVectorFileWriter.NoError:
        for feature in output_layer.getFeatures():
            writer.addFeature(feature)
        del writer
        print(f"Layer saved to: {output_file_path}")
    else:
        print(f"Failed to save layer: {writer.errorMessage()}")
def create_ferrovia():
    import processing
    from processing.core.Processing import Processing

    binari_ferroviari = change_coordinate_system('dataset/carta-tecnica-comunale-binari-ferroviari.geojson')
    binari_ferroviari = processing.run("native:dissolve", {'INPUT':binari_ferroviari, 'FIELD':[], 'SEPARATE_DISJOINT':False, 'OUTPUT':'TEMPORARY_OUTPUT'})['OUTPUT']
    binari_ferroviari = processing.run("native:buffer", {'INPUT':binari_ferroviari,'DISTANCE':10,'SEGMENTS':5,'END_CAP_STYLE':0,'JOIN_STYLE':0,'MITER_LIMIT':2,'DISSOLVE':False,'SEPARATE_DISJOINT':False,'OUTPUT':'TEMPORARY_OUTPUT'})['OUTPUT']
    gdf = gpd.read_file('dataset/aree_statistiche.geojson')
    gdf = gdf[gdf["area_statistica"].isin(["SCALO MERCI SAN DONATO", "SCALO RAVONE"])]
    gdf.to_file("dataset/ferrovia.geojson", driver="GeoJSON")
    ferrovia = processing.run("native:union", {'INPUT':'dataset/ferrovia.geojson','OVERLAY':binari_ferroviari,'OVERLAY_FIELDS_PREFIX':'','OUTPUT':'TEMPORARY_OUTPUT','GRID_SIZE':None})['OUTPUT']
    ferrovia = processing.run("native:dissolve", {'INPUT': ferrovia,'FIELD':[],'SEPARATE_DISJOINT':False,'OUTPUT':'TEMPORARY_OUTPUT'})['OUTPUT']
    return ferrovia

def create_verde():
    import processing
    from processing.core.Processing import Processing

    un_gest = processing.run("qgis:checkvalidity", {'INPUT_LAYER':'dataset/un_gest.fgb','METHOD':1,'IGNORE_RING_SELF_INTERSECTION':False,'VALID_OUTPUT':'TEMPORARY_OUTPUT','INVALID_OUTPUT':'TEMPORARY_OUTPUT','ERROR_OUTPUT':'TEMPORARY_OUTPUT'})['VALID_OUTPUT']

    verde_privato_urbanizzato = processing.run("qgis:checkvalidity", {'INPUT_LAYER':'dataset/verde_privato_urbanizzato.fgb','METHOD':1,'IGNORE_RING_SELF_INTERSECTION':False,'VALID_OUTPUT':'TEMPORARY_OUTPUT','INVALID_OUTPUT':'TEMPORARY_OUTPUT','ERROR_OUTPUT':'TEMPORARY_OUTPUT'})['VALID_OUTPUT']
    
    aree_boschive = processing.run("qgis:checkvalidity", {'INPUT_LAYER':'dataset/aree-boschive.gpkg','METHOD':1,'IGNORE_RING_SELF_INTERSECTION':False,'VALID_OUTPUT':'TEMPORARY_OUTPUT','INVALID_OUTPUT':'TEMPORARY_OUTPUT','ERROR_OUTPUT':'TEMPORARY_OUTPUT'})['VALID_OUTPUT']
    
    aree_fluviali = processing.run("qgis:checkvalidity", {'INPUT_LAYER':'dataset/aree-fluviali.gpkg','METHOD':1,'IGNORE_RING_SELF_INTERSECTION':False,'VALID_OUTPUT':'TEMPORARY_OUTPUT','INVALID_OUTPUT':'TEMPORARY_OUTPUT','ERROR_OUTPUT':'TEMPORARY_OUTPUT'})['VALID_OUTPUT']

    gdf = gpd.read_file('dataset/aree_statistiche.geojson')
    gdf = gdf[gdf["area_statistica"].isin(["GIARDINI MARGHERITA"])]
    gdf.to_file("dataset/giardini_margherita.geojson", driver="GeoJSON")

    verde = processing.run("native:multiunion", {'INPUT':un_gest,'OVERLAYS':["dataset/giardini_margherita.geojson", verde_privato_urbanizzato, aree_boschive, aree_fluviali],'OVERLAY_FIELDS_PREFIX':'','OUTPUT':'TEMPORARY_OUTPUT'})['OUTPUT']
    
    return verde

def change_coordinate_system(path_to_layer):
    import processing
    from processing.core.Processing import Processing

    input_layer = QgsVectorLayer(path_to_layer)

    # Define the target CRS (EPSG:3857)
    target_crs = QgsCoordinateReferenceSystem("EPSG:3857")

    # Reproject using the 'reprojectlayer' processing algorithm
    params = {
        'INPUT': input_layer,
        'TARGET_CRS': target_crs,
        'OUTPUT': 'memory:'  # or use a file path like 'reprojected_layer.geojson'
    }

    return processing.run("native:reprojectlayer", params)['OUTPUT']

def main():
    directory = 'dataset'
    if not os.path.exists(directory):
        os.makedirs(directory)

    #change with you path to python location
    QgsApplication.setPrefixPath("/Applications/QGIS-LTR.app/Contents/MacOS/", True)
    app = QgsApplication([], False)
    
    import processing
    from processing.core.Processing import Processing

    Processing.initialize()
    QgsApplication.processingRegistry().addProvider(QgsNativeAlgorithms())

    #create grid structure around Bologna's center
    #initial_grid = processing.run("native:creategrid", {'TYPE':2,'EXTENT':'11.326956986,11.358076793,44.484437335,44.505651657 [EPSG:4326]','HSPACING':100,'VSPACING':100,'HOVERLAY':0,'VOVERLAY':0,'CRS':QgsCoordinateReferenceSystem('EPSG:3857'),'OUTPUT':'TEMPORARY_OUTPUT'})['OUTPUT']

    gdf = gpd.read_file('dataset/localita_abitative.gpkg', layer="V_LAB_GPG")
    gdf = gdf[gdf["NM_LAB"] == "BOLOGNA"]
    gdf.to_file("dataset/localita_abitative.geojson", driver="GeoJSON")
    
    area_abitata = processing.run("native:clip", {'INPUT':'dataset/aree-statistiche.fgb','OVERLAY':'dataset/localita_abitative.geojson','OUTPUT':'TEMPORARY_OUTPUT'})['OUTPUT']
    #save_layer(area_abitata, 'new_loc_abit')
    

    grid_bologna = processing.run("native:creategrid", {'TYPE':2,'EXTENT':area_abitata,'HSPACING':100,'VSPACING':100,'HOVERLAY':0,'VOVERLAY':0,'CRS':QgsCoordinateReferenceSystem('EPSG:3857'),'OUTPUT':'TEMPORARY_OUTPUT'})['OUTPUT']
    grid_bologna = processing.run("native:extractbylocation", {'INPUT':grid_bologna,'PREDICATE':[0],'INTERSECT':area_abitata,'OUTPUT':'TEMPORARY_OUTPUT'})['OUTPUT']
    save_layer(grid_bologna, 'grid_bologna') #11.229655388,11.433714394,44.421110029,44.556205390 [EPSG:4326]
    

    #compute the area of each area_statistica for each grid in bologna 
    aree_statistiche = processing.run("native:intersection", {'INPUT':grid_bologna,'OVERLAY':area_abitata,'INPUT_FIELDS':[],'OVERLAY_FIELDS':[],'OVERLAY_FIELDS_PREFIX':'','OUTPUT':'TEMPORARY_OUTPUT','GRID_SIZE':None})['OUTPUT']
    aree_statistiche = processing.run("native:fieldcalculator", {'INPUT':aree_statistiche,'FIELD_NAME':'intersect_area_statistica','FIELD_TYPE':0,'FIELD_LENGTH':0,'FIELD_PRECISION':0,'FORMULA':'area($geometry)','OUTPUT':'TEMPORARY_OUTPUT'})['OUTPUT']
    #save_layer(aree_statistiche, 'aree_statistiche')
    
    #grid_bologna = processing.run("native:joinattributestable", {'INPUT':grid_bologna,'FIELD':'id','INPUT_2':aree_statistiche,'FIELD_2':'id','FIELDS_TO_COPY':['area_statistica, intersect_area_statistica'],'METHOD':0,'DISCARD_NONMATCHING':False,'PREFIX':'','OUTPUT':'TEMPORARY_OUTPUT'})['OUTPUT']
    #save_layer(grid_bologna, 'new_grid_bologna')
    
    ferrovia = create_ferrovia()
    save_layer(ferrovia, 'ferrovia')

    '''verde = create_verde()
    save_layer(verde, 'verde')'''

    #compute the free space in which is possible to create new green cells
    '''free_space = processing.run("native:multidifference", {'INPUT': grid_bologna,'OVERLAYS':[verde, 'dataset/aree-stradali.fgb', 'data_pl.fgb', ferrovia],'OUTPUT':'TEMPORARY_OUTPUT'})['OUTPUT']
    free_space = processing.run("native:multiparttosingleparts", {'INPUT':free_space,'OUTPUT':'TEMPORARY_OUTPUT'})['OUTPUT']
    save_layer(free_space, 'free_space')'''

    #compute how many areas each elements occupy inside the cells
    grid_with_areas = processing.run("native:calculatevectoroverlaps", {'INPUT':grid_bologna,'LAYERS':['dataset/verde.geojson', 'dataset/rifter_edif_pl.fgb', 'dataset/aree-stradali-modified.geojson', 'dataset/free_space.geojson', ferrovia],'OUTPUT':'TEMPORARY_OUTPUT','GRID_SIZE':None})['OUTPUT']
    grid_with_areas = processing.run("native:countpointsinpolygon", {'POLYGONS':grid_with_areas,'POINTS':'dataset/free_space.geojson','WEIGHT':'','CLASSFIELD':'','FIELD':'free_space_number','OUTPUT':'TEMPORARY_OUTPUT'})['OUTPUT']
    save_layer(grid_with_areas, 'grid_with_areas')
    
    #compute the number of tree outside the green areas
    area_not_green = processing.run("native:multidifference", {'INPUT': grid_bologna,'OVERLAYS':['dataset/verde.geojson'],'OUTPUT':'TEMPORARY_OUTPUT'})['OUTPUT']
    save_layer(area_not_green, 'area_not_green')
    trees_outside_green = processing.run("native:countpointsinpolygon", {'POLYGONS':area_not_green, 'POINTS':'dataset/alberi-manutenzioni.fgb','WEIGHT':'','CLASSFIELD':'','FIELD':'tree_number','OUTPUT':'TEMPORARY_OUTPUT'})['OUTPUT']

    #trees_outside_green = processing.run("native:joinattributestable", {'INPUT':grid_bologna,'FIELD':'id','INPUT_2':trees_outside_green,'FIELD_2':'id','FIELDS_TO_COPY':['tree_number'],'METHOD':0,'DISCARD_NONMATCHING':False,'PREFIX':'','OUTPUT':'TEMPORARY_OUTPUT'})['OUTPUT']
    
    save_layer(trees_outside_green, 'trees_outside_green')
    
if __name__ == "__main__":

    main()