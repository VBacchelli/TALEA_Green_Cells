# Sustainable City via Trustworthy Digital Twin: a Use Case
In this work we examined the city of Bologna to find out the best location where to place new green areas.

## Usage
To reproduce our results, ensure Docker is installed on your system. Once Docker is installed, to run the docker the following scripts should be executed from the terminal while in the Dockerfile directory:

- To build and run the docker

    ```
    docker-compose up --build -d
    ```

- To exec docker commands from your terminal

    ```
    docker exec -it TALEA bash
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

### Link

GUI - https://talea-gui.netlify.app/
Documentation - https://talea-documentation.netlify.app/