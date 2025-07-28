# Sustainable City via Trustworthy Digital Twin: a Use Case
In this work we examined the city of Bologna to find out the best location where to place new green areas.
## Data
The data has been taken both from Open Data Bologna and Geoportale regione emilia-romagna. 
All the available data have been manipulated using the pyqgis api, which can be found in the grid_creation file and then to create a unique usable dataset. 
The dataset is structured in by dividing the city of bologna into square grid with the followings attributes:
- street area
- green space area
- yards area
- buildings area
- number of trees
- population density

The city of Bologna can be divided into aree statistiche, the population density and green area of those has also been computed.
## Model explanations

The model objective is to find the n "best" cells where place a green cell, maximizing a utility function.
The utility function is composed by:
- macro_factor, which acts as a multiplicative factor to the "real" utility function. It is composed by the green space and the population density of the whole area statistica, where the actual cell is. The macro factor increases proportionally with respect to the population density and inversely with respect to the green space;
- street_cells: streets area inside the cell, using the parameter alpha_cells we can regulate which pecentage of street we are considering during the green placement;
- yard_cells: yard area inside the cell, using the parameter alpha_yard we can regulate which pecentage of yards we are considering during the green placement;
- num_areas: the number of yard_cells inside a cell. The higher it is this number the more the yard area is fragmented;
- green_space: the amount of green area already present in the cell;
- num_trees: the number of trees in the cell.

The utility of a cell increases with respect to street_cells, yard_cells and decreases with respect to num_areas, green_space and num_trees.

## Usage

To reproduce our results, ensure Docker is installed on your system. Once Docker is installed, to run the docker the following scripts should be executed from the terminal while in the Dockerfile directory:

- To build the docker
```
docker build -t <docker_image_name> .
```
- To run the docker
```
docker run -it <container_name> <docker_image_name>
```
- To exec docker commands from your terminal
```
docker exec -it <container_name> /usr/bin/bash
```

### Usage rules

There are two modalities to run the pipeline in the docker shell:
- one for running the entire pipeline, including the grid creation step, ideal for the first run and if you want to change something in the geometry of the data ('center' or 'full')
    ```bash
    run_pipeline
    ```
- one for running only the further processing steps, including the instance creation and the solver, ideal for parameter changes
    ```bash
    run_model
    ```