FROM qgis/qgis

# Set environment variables for QGIS
ENV QGIS_PREFIX_PATH=/usr
ENV QT_QPA_PLATFORM=offscreen
ENV XDG_RUNTIME_DIR=/tmp/runtime-root

# Set the working directory in the container
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app

RUN apt-get update
RUN apt-get install -y python3-pip
RUN pip3 install --no-cache-dir --break-system-packages -r requirements.txt

# Install any necessary Python dependencies from requirements.txt
#COPY requirements.txt /app/

# Run your Python script
#CMD ["python3", "dockerGrid.py"]