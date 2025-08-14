Engineering Approach
=========================
The entire project, along with its environment, has been containerized using **Docker**.
This is noteworthy because it makes the entire study fully reproducible and easy to share.

Reproducibility was a significant challenge in this project due to the use of *QGIS* and *PyQGIS*.
PyQGIS cannot be easily installed in a local environment via common package managers such as ``pip`` or ``conda``.
Instead, you must install the QGIS application on your local machine and then manually configure the path to the Python packages inside the application, which are OS-dependent.
This process reduces the shareability of the code and imposes a significant barrier for end users wishing to run the project.
By using a QGIS-based Docker image within the container, this limitation has been completely overcome.

Additionally, this project relies on spatial data, which is best understood when visualized -- especially for transformation processes and results.
Displaying such data in tables often leads to ambiguity and poor clarity.
To eliminate the need for a third-party application, a simple Graphical User Interface (GUI) has been developed, which currently allows the visualization of results and data in GeoJSON format.