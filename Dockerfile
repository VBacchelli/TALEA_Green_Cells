FROM qgis/qgis

# Set environment variables for QGIS
ENV QGIS_PREFIX_PATH=/usr
ENV QT_QPA_PLATFORM=offscreen
ENV XDG_RUNTIME_DIR=/tmp/runtime-root

# Set the working directory in the container
WORKDIR /app

# Install Minizinc
RUN wget https://github.com/MiniZinc/MiniZincIDE/releases/download/2.8.4/MiniZincIDE-2.8.4-bundle-linux-x86_64.tgz &&\
tar -xf MiniZincIDE-2.8.4-bundle-linux-x86_64.tgz &&\
mv MiniZincIDE-2.8.4-bundle-linux-x86_64 minizinc &&\
cp -r minizinc/bin/* /usr/local/bin &&\
cp -r minizinc/lib/* /usr/local/lib &&\
cp -r minizinc/share/* /usr/local/share &&\
cp -r minizinc/lib/* /usr/local/lib

# Install Python dependencies before copying application sources so code
# changes do not invalidate the cached dependency installation layer.
COPY requirements.txt /app/requirements.txt

# Keep access to Debian's PyQGIS packages without replacing apt-managed packages.
RUN apt-get update && \
apt-get install -y python3-pip python3-venv wget unzip && \
python3 -m venv --system-site-packages /opt/talea-venv && \
/opt/talea-venv/bin/python -m pip install -r requirements.txt

# Use the virtual environment for all subsequent Python commands.
ENV PATH="/opt/talea-venv/bin:${PATH}"

# Only application changes (rather than requirement changes) invalidate this layer.
COPY . /app
RUN find /app/config -name "*.yaml" -exec sed -i 's/\r$//' {} +

# Make the pipeline script executable
COPY run_pipeline /usr/local/bin/run_pipeline
COPY run_model /usr/local/bin/run_model

RUN sed -i 's/\r$//' /usr/local/bin/run_pipeline &&\
chmod +x /usr/local/bin/run_pipeline
RUN sed -i 's/\r$//' /usr/local/bin/run_model &&\
chmod +x /usr/local/bin/run_model

# Keep the container alive
CMD ["tail", "-f", "/dev/null"]