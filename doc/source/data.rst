Data
============


Data Collection
------------------
Data collection is one of the most important part of this project. Aiming to insert new green areas in the city of Bologna is necessary to have
information about the already present green space, the human infrastructures and the population.
Those informations have been gathered from `Open Data Bologna <https://opendata.comune.bologna.it/>`_ and 
`Geoportale Emilia Romagna <https://geoportale.regione.emilia-romagna.it/>`_.
Opend Data Bologna, so as Geoportale Emilia Romagna, is a project which aims to collect and make the data of the city public, respecting the 
Italian and European directive about the open data. 
The data selected for this study are the followings:

<insert a list with all the dataset and their explanations>


Those data are not thinked to be used in an algorithmic contest. Indeed, they lack of a usable structure, there is no unique dataset for the same data leading
to multiple duplicates, some geospatial information are corrupted and need to be refined. Furthermore, some data are missing, requiring modifcation which leads to non-exact solutions.
To overcome these problems an heavily processing step is required.

Preprocessing
------------------------------------
The data were not ready to use, they needed to be regorganized.
One of the most useful tool to work with geospatial data is Qgis, which offers also a python interface. 
The border of the city of Bologna has been extracted from the dataset "aree-statistiche", and then used for the creation of the grid structure.
By default each cell of the grid has dimension 100x100 meters.
Unfortunately, most areas along the borders have been removed by the dataset. This was necessary since there were a lack of information
which caused the model to fail drammatically. 
The final area under consideration is the one below <insert figure>.
The dataset created has the cell grid as samples and the features are:

- green area: the area occupied by already present green space;
- buildings area: the area occupied by buildings;
- road area: the area occupied by roads;
- railways area the area occupied by railways;
- number of trees: the number of trees;
- free space: the area where new green space could be placed;
- free space number: how muhc the free space is segmented.

To obtain these features, we created different datasets from which to extract information.
To obtain a unique, and exhaustive, dataset containing all the Bologna green space, we have merged, without overlapping, four dataset: un_gest, verde_privato_urbanizzato, aree_boschive, aree_fluviali.
It has been found that some spatial data in un_gest dataset were corrupted, and those creates gemotries inconsistencies. To avoid those, small amount of pixels have been removed.

The only datasets available for railways and roads are made up as lines. Since areas cannot be extracted from lines, a buffer around them as been made. Of course, this lead to an approximation, which is necessary to avoid missing data in the final model.

The features have also been aggregated for each "area statistica", to obtain a global (macro) vision of the informations.