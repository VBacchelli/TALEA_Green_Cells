#set as python environment the one from qgis application
import os, sys
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
    grid = processing.run("native:creategrid", {'TYPE':2,'EXTENT':'11.326956986,11.358076793,44.484437335,44.505651657 [EPSG:4326]','HSPACING':100,'VSPACING':100,'HOVERLAY':0,'VOVERLAY':0,'CRS':QgsCoordinateReferenceSystem('EPSG:3857'),'OUTPUT':'TEMPORARY_OUTPUT'})
    grid = grid['OUTPUT']

    #compute the number of square meters free from already existing green areas and buildings
    grid_with_overlap = processing.run("native:calculatevectoroverlaps", {'INPUT':grid,'LAYERS':['dataset/un_gest.fgb', 'dataset/verde_privato_urbanizzato.fgb', 'dataset/rifter_edif_pl.fgb', 'dataset/rifter_arcstra_li.fgb', 'dataset/le-aree-verdi-e-le-vie-di-bologna-dedicate-alle-donne.fgb'],'OUTPUT':'TEMPORARY_OUTPUT','GRID_SIZE':None})
    grid_with_overlap = grid_with_overlap['OUTPUT']
    
    print('overlap done')
    #compute the number of tree for each cell
    grid_with_trees = processing.run("native:countpointsinpolygon", {'POLYGONS':grid_with_overlap, 'POINTS':'dataset/alberi-manutenzioni.fgb','WEIGHT':'','CLASSFIELD':'','FIELD':'NUMPOINTS','OUTPUT':'TEMPORARY_OUTPUT'})
    grid_with_trees = grid_with_trees['OUTPUT']


    save_layer(grid_with_trees, 'polygon_trees')
    
    #the following functions are used to count the number of trees which overlap with the green areas; process is: 
    #union between all the green areas
    green_areas_total = processing.run("native:union", {'INPUT':'dataset/verde_privato_urbanizzato.fgb', 'OVERLAY':'dataset/un_gest.fgb','OVERLAY_FIELDS_PREFIX':'','OUTPUT':'TEMPORARY_OUTPUT','GRID_SIZE':None})

    #intesect with the grid to limit the area at the city center
    green_areas_inside_walls = processing.run("native:intersection", {'INPUT': grid,'OVERLAY': green_areas_total,'INPUT_FIELDS':[],'OVERLAY_FIELDS':[],'OVERLAY_FIELDS_PREFIX':'','OUTPUT':'TEMPORARY_OUTPUT','GRID_SIZE':None})

    #count the number of trees in each green area
    number_trees_over_green = processing.run("native:countpointsinpolygon", {'POLYGONS':green_areas_inside_walls, 'POINTS':'dataset/alberi-manutenzioni.fgb','WEIGHT':'','CLASSFIELD':'','FIELD':'NUMPOINTS','OUTPUT':'TEMPORARY_OUTPUT'})

    #count the number of trees in each cell
    number_trees_grid_overlap_with_green = processing.run("native:joinbylocationsummary", {'INPUT': grid,'PREDICATE':[4],'JOIN': number_trees_over_green,'JOIN_FIELDS':['NUMPOINTS'],'SUMMARIES':[5],'DISCARD_NONMATCHING':False,'OUTPUT':'TEMPORARY_OUTPUT'})

    save_layer(number_trees_grid_overlap_with_green, 'number_trees_overlap_green')

if __name__ == "__main__":

    main()