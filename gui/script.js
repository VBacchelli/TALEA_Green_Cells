window.onload = function () {

    const initialCoords = [44.494981, 11.342641];
    const initialZoom = 13;

    const map = L.map('map').setView(initialCoords, initialZoom);

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; OpenStreetMap contributors'
    }).addTo(map);

    let uploadedLayer = null;

    // ✅ Create a custom dropdown control
    const resultsControl = L.control({ position: 'topleft' });

    resultsControl.onAdd = function () {
        const container = L.DomUtil.create('div', 'leaflet-bar leaflet-control');
        container.style.background = 'white';
        container.style.padding = '4px';

        // Dropdown menu
        const select = L.DomUtil.create('select', '', container);
        select.style.width = '80px';
        select.style.height = '30px';
        select.style.cursor = 'pointer';

        // Options
        const defaultOpt = L.DomUtil.create('option', '', select);
        defaultOpt.text = 'Results';
        defaultOpt.value = '';

        const loadOpt = L.DomUtil.create('option', '', select);
        loadOpt.text = 'Load GeoJSON';
        loadOpt.value = 'load';

        const loadUtilityOpt = L.DomUtil.create('option', '', select);
        loadUtilityOpt.text = 'Load w/ Utility Style';
        loadUtilityOpt.value = 'loadUtility';

        const removeOpt = L.DomUtil.create('option', '', select);
        removeOpt.text = 'Remove Layers';
        removeOpt.value = 'remove';

        // Hidden file input
        const fileInput = L.DomUtil.create('input', '', container);
        fileInput.type = 'file';
        fileInput.accept = '.geojson,.json';
        fileInput.style.display = 'none';

        // Handle dropdown actions
        select.addEventListener('change', function () {
            if (select.value === 'load') {
                fileInput.dataset.styleMode = 'normal';   // ✅ mark style mode
                fileInput.click();
            } else if (select.value === 'loadUtility') {
                fileInput.dataset.styleMode = 'utility';  // ✅ mark style mode
                fileInput.click();
            } else if (select.value === 'remove') {
                if (uploadedLayer) {
                    map.removeLayer(uploadedLayer);
                    uploadedLayer = null;
                    alert("Layer removed.");
                } else {
                    alert("No layer to remove.");
                }
            }
            select.value = ''; // reset dropdown after action
        });

        // Handle file upload
        fileInput.addEventListener('change', function (event) {
            const file = event.target.files[0];
            if (!file) return;

            const styleMode = fileInput.dataset.styleMode || 'normal';

            const reader = new FileReader();
            reader.onload = function (e) {
                try {
                    let geojson = JSON.parse(e.target.result);

                    // EPSG:3857 to EPSG:4326 transformation
                    function reprojectCoords(coords) {
                        if (typeof coords[0] === "number") {
                            const [x, y] = coords;
                            return proj4('EPSG:3857', 'EPSG:4326', [x, y]);
                        } else {
                            return coords.map(reprojectCoords);
                        }
                    }

                    geojson.features.forEach(feature => {
                        feature.geometry.coordinates = reprojectCoords(feature.geometry.coordinates);
                    });

                    if (uploadedLayer) {
                        map.removeLayer(uploadedLayer);
                    }

                    uploadedLayer = L.geoJSON(geojson, {
                        style: function (feature) {
                            if (styleMode === 'utility') {
                                let utility = feature.properties.utility || 0;
                                let maxUtility = Math.max(...geojson.features.map(f => f.properties.utility || 0));
                                let opacity = (maxUtility > 0) ? (utility / maxUtility) : 0.3;
                                return { color: "red", weight: 1, fillOpacity: opacity };
                            } else {
                                return { color: "red", weight: 1, fillOpacity: 0.3 };
                            }
                        }
                    }).addTo(map);

                    map.setView(initialCoords, initialZoom);
                    console.log("GeoJSON loaded.");
                } catch (err) {
                    console.error("Error parsing GeoJSON:", err);
                    alert("Invalid GeoJSON file.");
                }
            };
            reader.readAsText(file);
        });

        L.DomEvent.disableClickPropagation(container);
        return container;
    };

    resultsControl.addTo(map);
};