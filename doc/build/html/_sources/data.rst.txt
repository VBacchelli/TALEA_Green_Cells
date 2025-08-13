Data
============


Data Collection
------------------

Data collection is one of the most important part of this project. Aiming to insert new green areas in the city of Bologna is necessary to have
information about the already present green space, the human infrastructures and the population.
This information have been gathered from `Open Data Bologna <https://opendata.comune.bologna.it/>`_ and 
`Geoportale Emilia Romagna <https://geoportale.regione.emilia-romagna.it/>`_.
Open Data Bologna, so as Geoportale Emilia Romagna, is a project which aims to collect and make the data of the city public, respecting the 
Italian and European directive about the open data. 
In this study we used the followings' dataset:


- :doc:`General information about Bologna land usage <script/data/land_usage>`
- :doc:`Green datasets <script/data/green_dataset>`
- :doc:`Human infrastructure datasets <script/data/buildable>`
- :doc:`Statistical dataset <script/data/statistics>`


Those data are not thought to be used in an algorithmic contest. Indeed, they lack of a usable structure, there is no unique dataset for the same data leading
to multiple duplicates, some geospatial information are corrupted and need to be refined. Furthermore, some data are missing, requiring modifcation which leads to non-exact solutions.
To overcome these problems a heavily processing step is required.

Preprocessing
------------------------------------
The data were not ready to use, they needed to be reorganized and processed in order to extrapolate the relevant information.
One of the most useful tool to work with geospatial data is Qgis, which offers also a python interface. 
Furthermore, many dataset present overlapping information which should not be duplicated.

To understand the preprocessing steps, let's define some approximation used during the definition of this study. 
To place new green areas it is important to understand where to place them. On this purpose, it has been defined
the "free space". The free space is the remaining space in the city, once you removed buildings, roads, all the human infrastructure and
the green space. Basically, in most of the cases is the yard court of the buildings.

Furthermore, it has been hypothesized that the roads are places where new green areas could be inserted. Of course, this is an approximation, 
but to make it as realistic as possible it has been decided to exclude all the squares and the highways, where it would have been
more complex (or even impossible) to build upon.

The steps done during preprocessing are the followings:

- The green datasets contents have been aggregated under a unique dataset avoiding duplicates. In this process has been found that the dataset "un_gest", contains some geospatial information that were corrupted, causing errors in the union. To avoid this, we performed a geometry fixing operation which aims to connect this "holes" avoiding the aforementioned error;
- The road dataset also contains squares and highways in it. To remove the squares, since no dataset for squares is available, the attribute "incorci stradali a raso" has been filterd. Empirically, has been found that setting a threshold which removes all the elements who's area is bigger than 7500 square meters is a good trade-off. Instead, for the highways, it has been made a difference operation with the dataset uso_del_suolo, which contains in the description the feature "Autostrade e superstrade".
- The free space has been computed by selecting the residential areas from the dataset "uso_del_suolo" ('Tessuto residenziale compatto e denso', 'Tessuto residenziale urbano', 'Tessuto residenziale rado'). Then the difference between all the human infrastructures and green spaces has been made.
- The border of the city of Bologna has been extracted from the dataset "aree-statistiche". Another approximation has been required.  Some areas in Bologna's borders lacks of information about the green space and buildings, so it has been decided to remove them. The final usable area is the one on the image. <insert image> 
- Once delimited the area of work, it has been divided into a grid. Each cell of the grid is 100x100 meters.
- The final dataset to be passed inside the optimization model is composed by all the cells of the grid and for each of them has been computed the area occupied by the green, buildings, road, free space and the number of free spaces and trees. The number of free spaces tells how much the free space is fragmented.

<insert image>

This "final dataset", only represents information under a small-scale view. It's also important to have a big-scale view. 
This macro scale has been represented by the division in the dataset "aree-statistiche". 
An important information about the macro-scale view is the population density. 
This information has been obtained from the dataset "popolazione-per-area-statistica", dividing the population by the area itself.
The new macro dataset contains all the used "aree statistiche" with information about the population density and the green space present there.

.. grid:: 2

    .. grid-item::

        .. figure:: script/data/images/green_space.png
           :width: 150px

           Green areas

    .. grid-item::

        .. figure:: script/data/images/population_density.png
           :width: 150px

           Population densities

As shown in the images above, the city center exhibits the highest population density and the lowest proportion of green areas.
Moving toward the outskirts, population density gradually decreases.
Unsurprisingly, the areas with the highest concentration of green space are the Colli.