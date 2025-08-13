window.onload = function () {
    const initialCoords = [44.494981, 11.342641];
    const initialZoom = 13;

    const map = L.map('map').setView(initialCoords, initialZoom);

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; OpenStreetMap contributors'
    }).addTo(map);

    const layers = {};

    const resultsControl = L.control({ position: 'topleft' });

    resultsControl.onAdd = function () {
        const container = L.DomUtil.create('div', 'leaflet-bar leaflet-control');
        container.style.background = 'white';
        container.style.padding = '4px';

        const select = L.DomUtil.create('select', '', container);
        select.style.width = '100px';
        select.style.height = '30px';
        select.style.cursor = 'pointer';

        const defaultOpt = L.DomUtil.create('option', '', select);
        defaultOpt.text = 'Add Layer';
        defaultOpt.value = '';

        const loadRes = L.DomUtil.create('option', '', select);
        loadRes.text = 'Load Results';
        loadRes.value = 'results';

        const loadData = L.DomUtil.create('option', '', select);
        loadData.text = 'Load Data';
        loadData.value = 'data';

        const fileInput = L.DomUtil.create('input', '', container);
        fileInput.type = 'file';
        fileInput.accept = '.geojson,.json,.gpkg,.fgb';
        fileInput.style.display = 'none';

        select.addEventListener('change', function () {
            if (select.value === 'results') {
                fileInput.dataset.styleMode = 'utility';
                fileInput.click();
            } else if (select.value === 'data') {
                fileInput.dataset.styleMode = 'normal';
                fileInput.click();
            }
            select.value = '';
        });

        fileInput.addEventListener('change', async function (event) {
            const file = event.target.files[0];
            if (!file) return;

            const extension = file.name.split('.').pop().toLowerCase();
            const styleMode = fileInput.dataset.styleMode || 'normal';

            let geojson = null;

            try {
                if (extension === 'geojson' || extension === 'json') {
                    const text = await file.text();
                    geojson = JSON.parse(text);
                } else if (extension === 'fgb') {
                    const arrayBuffer = await file.arrayBuffer();
                    const features = [];

                    await window.flatgeobuf.deserialize(arrayBuffer, (feature) => {
                        features.push(feature);
                    });
                    geojson = { type: "FeatureCollection", features };
                } else if (extension === 'gpkg') {
                    const arrayBuffer = await file.arrayBuffer();
                    const geoPackage = await window.GeoPackage.openGeoPackageByteArray(arrayBuffer);
                    const tables = await geoPackage.getFeatureTables();
                    if (tables.length === 0) throw new Error("No feature tables found in GPKG.");
                    const features = await geoPackage.getGeoJSONFeatures(tables[0]);
                    geojson = { type: "FeatureCollection", features };
                } else {
                    alert("Unsupported file type.");
                    return;
                }

                const crs = geojson.crs?.properties?.name || '';
                if (crs.includes('3857')) {
                    geojson.features = geojson.features.map(reprojectFeature3857to4326);
                }

                const defaultColor = "#ff0000";

                const layer = L.geoJSON(geojson, {
                    style: function (feature) {
                        if (styleMode === 'utility') {
                            let utility = feature.properties.utility || 0;
                            let maxUtility = Math.max(...geojson.features.map(f => f.properties.utility || 0));
                            let opacity = (maxUtility > 0) ? (utility / maxUtility) : 0.3;
                            return { color: defaultColor, weight: 1, fillOpacity: opacity };
                        } else {
                            return { color: defaultColor, weight: 1, fillOpacity: 0.3 };
                        }
                    }
                });

                layer.addTo(map);
                const filename = file.name;
                layers[filename] = layer;
                addLayerToSidebar(filename, defaultColor);
                document.getElementById('sidebar').style.display = 'block';

            } catch (err) {
                console.error("Error loading file:", err);
                alert("Failed to load file.");
            }
        });

        L.DomEvent.disableClickPropagation(container);
        return container;
    };

    resultsControl.addTo(map);

    const sidebar = document.getElementById('sidebar');
    const toggleBtn = document.getElementById('toggle-sidebar');

    toggleBtn.addEventListener('click', function () {
        sidebar.style.display = (sidebar.style.display === 'none') ? 'block' : 'none';
    });

    function addLayerToSidebar(name, initialColor = '#ff0000') {
        const list = document.getElementById('layer-list');

        const container = document.createElement('div');
        container.style.display = 'flex';
        container.style.alignItems = 'center';
        container.style.marginBottom = '4px';
        container.style.gap = '6px';

        const checkbox = document.createElement('input');
        checkbox.type = 'checkbox';
        checkbox.checked = true;

        checkbox.addEventListener('change', function () {
            if (checkbox.checked) {
                layers[name].addTo(map);
            } else {
                map.removeLayer(layers[name]);
            }
        });

        const colorPicker = document.createElement('input');
        colorPicker.type = 'color';
        colorPicker.value = initialColor;
        colorPicker.title = 'Change layer color';

        colorPicker.addEventListener('input', function () {
            layers[name].setStyle({ color: colorPicker.value });
        });

        const label = document.createElement('span');
        label.textContent = name;
        label.style.fontFamily = 'monospace';

        container.appendChild(checkbox);
        container.appendChild(colorPicker);
        container.appendChild(label);
        list.appendChild(container);
    }

    function reprojectFeature3857to4326(feature) {
        function projectCoord(coord) {
            const x = coord[0], y = coord[1];
            const lon = x * 180 / 20037508.34;
            const lat = 180 / Math.PI * (2 * Math.atan(Math.exp(y / 20037508.34 * Math.PI)) - Math.PI / 2);
            return [lon, lat];
        }

        function recurseCoords(coords) {
            if (typeof coords[0] === 'number') {
                return projectCoord(coords);
            }
            return coords.map(recurseCoords);
        }

        const reprojected = JSON.parse(JSON.stringify(feature));
        reprojected.geometry.coordinates = recurseCoords(reprojected.geometry.coordinates);
        return reprojected;
    }
};
