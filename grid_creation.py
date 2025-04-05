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
    grid_with_overlap = processing.run("native:calculatevectoroverlaps", {'INPUT':grid,'LAYERS':['dataset/un_gest.fgb', 'dataset/verde_privato_urbanizzato.fgb', 'dataset/rifter_edif_pl.fgb'],'OUTPUT':'TEMPORARY_OUTPUT','GRID_SIZE':None})
    grid_with_overlap = grid_with_overlap['OUTPUT']
    
    #compute the number of tree for each cell
    grid_with_trees = processing.run("native:countpointsinpolygon", {'POLYGONS':grid_with_overlap, 'POINTS':'dataset/alberi-manutenzioni.fgb','WEIGHT':'','CLASSFIELD':'','FIELD':'NUMPOINTS','OUTPUT':'TEMPORARY_OUTPUT'})
    grid_with_trees = grid_with_trees['OUTPUT']

    save_layer(grid_with_trees, 'polygon_trees')


if __name__ == "__main__":
    main()