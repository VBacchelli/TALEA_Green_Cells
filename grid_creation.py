#set as python environment the one from qgis application
import os, sys
import time
#change with your path to the proj.db file and gdal file
os.environ['PROJ_LIB'] = '/Applications/QGIS-LTR.app/Contents/Resources/proj'
os.environ['GDAL_DATA'] = '/Applications/QGIS-LTR.app/Contents/Resources/gdal'

#change with you path to qgis python plugins (necessary for using processing API)
sys.path.append('/Applications/QGIS-LTR.app/Contents/Resources/python/plugins')

from qgis.core import *
from qgis.analysis import QgsNativeAlgorithms

def save_layer(output_layer, layer_name):

    output_file_path = os.path.join('dataset', f'{layer_name}.geojson')
    error = QgsVectorFileWriter.writeAsVectorFormat(output_layer, output_file_path, "UTF-8", output_layer.crs(), "GeoJSON")

    if error[0] != QgsVectorFileWriter.NoError:
        print(f"Error saving layer: {error[1]}")

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
    grid = processing.run("native:creategrid", {'TYPE':2,'EXTENT':'11.326956986,11.358076793,44.484437335,44.505651657 [EPSG:4326]','HSPACING':100,'VSPACING':100,'HOVERLAY':0,'VOVERLAY':0,'CRS':QgsCoordinateReferenceSystem('EPSG:3857'),'OUTPUT':'TEMPORARY_OUTPUT'})['OUTPUT']
    save_layer(grid, 'grid')

    '''zone_bologna = processing.run("native:intersection", {'INPUT':grid,'OVERLAY':'dataset/zone-del-comune-di-bologna.fgb','INPUT_FIELDS':[],'OVERLAY_FIELDS':[],'OVERLAY_FIELDS_PREFIX':'','OUTPUT':'TEMPORARY_OUTPUT','GRID_SIZE':None})['OUTPUT']
    zone_bologna = processing.run("native:fieldcalculator", {'INPUT':zone_bologna,'FIELD_NAME':'intersect_area','FIELD_TYPE':0,'FIELD_LENGTH':0,'FIELD_PRECISION':0,'FORMULA':'area($geometry)','OUTPUT':'TEMPORARY_OUTPUT'})['OUTPUT']
    
    #     processing.run("qgis:fieldcalculator",
    #     {
    #         "INPUT": zone_bologna,
    #         "FIELD_NAME": "intersect_area",
    #         "FIELD_TYPE": 0,  # Decimal
    #         "FIELD_LENGTH": 20,
    #         "FIELD_PRECISION": 4,
    #         "FORMULA": "area($geometry)",
    #         "OUTPUT": "TEMPORARY_OUTPUT"
    #     }
    # )

    save_layer(zone_bologna, 'zone_bologna')'''

    # cortili_interni = processing.run("native:deleteholes", {'INPUT':'dataset/rifter_edif_pl.fgb','MIN_AREA':0,'OUTPUT':'TEMPORARY_OUTPUT'})['OUTPUT']
    # cortili_interni = processing.run("native:intersection", {'INPUT':grid,'OVERLAY': cortili_interni,'INPUT_FIELDS':[],'OVERLAY_FIELDS':[],'OVERLAY_FIELDS_PREFIX':'','OUTPUT':'TEMPORARY_OUTPUT','GRID_SIZE':None})['OUTPUT']
    # #used to compute the area of each element inside the grid

    start_time = time.time()
    free_space = processing.run("native:multidifference", {'INPUT': grid,'OVERLAYS':['dataset/ferrovia.geojson', 'dataset/colli.geojson', 'dataset/verde_privato_urbanizzato.fgb', 'dataset/un_gest.fgb', 'dataset/aree-stradali.fgb', 'dataset/rifter_edif_pl.fgb'],'OUTPUT':'TEMPORARY_OUTPUT'})['OUTPUT']
    free_space = processing.run("native:multiparttosingleparts", {'INPUT':'dataset/cortili_interni.geojson','OUTPUT':'TEMPORARY_OUTPUT'})['OUTPUT']

    #to compute the area of each free_space, you will obtain the number each grid cell repetead as many times as the number of areas inside of it
    ## free_space = processing.run("native:intersection", {'INPUT':grid,'OVERLAY':free_space,'INPUT_FIELDS':[],'OVERLAY_FIELDS':[],'OVERLAY_FIELDS_PREFIX':'','OUTPUT':'TEMPORARY_OUTPUT','GRID_SIZE':None})
    # free_space = processing.run("native:fieldcalculator", {'INPUT': free_space, 'FIELD_NAME':'intersection_area','FIELD_TYPE':0,'FIELD_LENGTH':0,'FIELD_PRECISION':0,'FORMULA':'$area','OUTPUT':'TEMPORARY_OUTPUT'})['OUTPUT']
    # print(time.time()-start_time)
    save_layer(free_space, 'free_space')
    
    '''colli_grid = processing.run("native:intersection", {'INPUT':grid,'OVERLAY':'dataset/colli.geojson','INPUT_FIELDS':[],'OVERLAY_FIELDS':[],'OVERLAY_FIELDS_PREFIX':'','OUTPUT':'TEMPORARY_OUTPUT','GRID_SIZE':None})['OUTPUT']
    #save_layer(colli_grid, 'colli_grid')'''

    '''ferrovia_grid = processing.run("native:intersection", {'INPUT':grid,'OVERLAY':'dataset/ferrovia.geojson','INPUT_FIELDS':[],'OVERLAY_FIELDS':[],'OVERLAY_FIELDS_PREFIX':'','OUTPUT':'TEMPORARY_OUTPUT','GRID_SIZE':None})['OUTPUT']
    #save_layer(ferrovia_grid, 'ferrovia_grid')'''

    #compute the number of square meters free from already existing green areas and buildings
    grid_with_areas = processing.run("native:calculatevectoroverlaps", {'INPUT':grid,'LAYERS':['dataset/un_gest.fgb', 'dataset/verde_privato_urbanizzato.fgb', 'dataset/rifter_edif_pl.fgb', 'dataset/aree-stradali.fgb', 'dataset/ferrovia.geojson', 'dataset/colli.geojson', free_space],'OUTPUT':'TEMPORARY_OUTPUT','GRID_SIZE':None})['OUTPUT']
    grid_with_areas = processing.run("native:countpointsinpolygon", {'POLYGONS':grid_with_areas,'POINTS':free_space,'WEIGHT':'','CLASSFIELD':'','FIELD':'NUMPOINTS','OUTPUT':'TEMPORARY_OUTPUT'})['OUTPUT']
    save_layer(grid_with_areas, 'grid_with_areas')
    
    #compute the number of tree inside each of the areas not green
    '''grid_with_trees = processing.run("native:countpointsinpolygon", {'POLYGONS':grid_with_overlap, 'POINTS':'dataset/alberi-manutenzioni.fgb','WEIGHT':'','CLASSFIELD':'','FIELD':'NUMPOINTS','OUTPUT':'TEMPORARY_OUTPUT'})['OUTPUT']
    save_layer(grid_with_trees, 'polygon_trees')'''
    
    # #the following functions are used to count the number of trees which overlap with the green areas; process is: 
    
    # #intesect with the grid to limit the area at the city center
    # green_area_private = processing.run("native:intersection", {'INPUT': grid,'OVERLAY': 'dataset/un_gest.fgb','INPUT_FIELDS':[],'OVERLAY_FIELDS':[],'OVERLAY_FIELDS_PREFIX':'','OUTPUT':'TEMPORARY_OUTPUT','GRID_SIZE':None})['OUTPUT']


    # green_area_comune = processing.run("native:intersection", {'INPUT': grid,'OVERLAY': 'dataset/verde_privato_urbanizzato.fgb','INPUT_FIELDS':[],'OVERLAY_FIELDS':[],'OVERLAY_FIELDS_PREFIX':'','OUTPUT':'TEMPORARY_OUTPUT','GRID_SIZE':None})['OUTPUT']


    # #union between all the green areas
    # # green_areas_inside_walls = processing.run("native:union", {'INPUT':green_area_private, 'OVERLAY':green_area_comune,'OVERLAY_FIELDS_PREFIX':'','OUTPUT':'TEMPORARY_OUTPUT','GRID_SIZE':None})['OUTPUT']

    # trees_outside_green = processing.run("native:difference", {'INPUT':'dataset/alberi-manutenzioni.fgb','OVERLAY':'dataset/un_gest.fgb','OUTPUT':'TEMPORARY_OUTPUT','GRID_SIZE':None})['OUTPUT']


    # #count the number of trees in each cell
    # number_trees_grid_overlap_with_green = processing.run("native:joinbylocationsummary", {'INPUT': grid,'PREDICATE':[0],'JOIN': trees_outside_green,'JOIN_FIELDS':['NUMPOINTS'],'SUMMARIES':[5],'DISCARD_NONMATCHING':False,'OUTPUT':'TEMPORARY_OUTPUT'})['OUTPUT']

    # save_layer(number_trees_grid_overlap_with_green, 'number_trees_overlap_green')

if __name__ == "__main__":

    main()