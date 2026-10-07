import os

base_dir = r'c:\Users\manis\OneDrive\Desktop\new foai\stadium_twin'

twin_html = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>StadiumTwin v2 - Twin Editor</title>
    <!-- Leaflet CSS -->
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
    <style>
        body, html { margin: 0; padding: 0; height: 100%; font-family: 'Segoe UI', sans-serif; display: flex; flex-direction: column; overflow: hidden; }
        header { background: #2a5298; color: white; padding: 15px 20px; display: flex; justify-content: space-between; align-items: center; z-index: 1000; box-shadow: 0 2px 5px rgba(0,0,0,0.2); }
        header a { color: white; text-decoration: none; font-weight: bold; }
        #main { display: flex; flex: 1; height: calc(100vh - 60px); position: relative; }
        #sidebar { width: 350px; background: #f4f7f6; padding: 20px; box-shadow: 2px 0 5px rgba(0,0,0,0.1); z-index: 1000; display: flex; flex-direction: column; gap: 15px; overflow-y: auto; }
        #map { flex: 1; height: 100%; z-index: 1; background: #ddd; }
        input[type="text"] { padding: 10px; width: 100%; box-sizing: border-box; border: 1px solid #ccc; border-radius: 4px; }
        button { padding: 10px; background: #00d2ff; border: none; border-radius: 4px; font-weight: bold; cursor: pointer; transition: background 0.2s; }
        button:hover { background: #3a7bd5; color: white; }
        .btn-action { background: #ff4b2b; color: white; }
        .btn-action:hover { background: #ff416c; }
        #results { list-style: none; padding: 0; margin: 0; max-height: 200px; overflow-y: auto; background: white; border-radius: 4px; border: 1px solid #eee; }
        #results li { padding: 10px; border-bottom: 1px solid #eee; cursor: pointer; font-size: 14px; }
        #results li:hover { background: #eef; }
        #status { font-size: 13px; font-weight: bold; margin-top: 10px; padding: 10px; border-radius: 4px; display: none; }
    </style>
</head>
<body>
    <header>
        <div>
            <a href="/static/dashboard.html">⬅ Back to Dashboard</a>
        </div>
        <h3 style="margin:0;">Twin Editor</h3>
    </header>
    
    <div id="main">
        <div id="sidebar">
            <h3>Location</h3>
            <div style="display: flex; gap: 5px;">
                <input type="text" id="searchInput" placeholder="Search (e.g. Chepauk Stadium)">
                <button onclick="searchPlace()">Search</button>
            </div>
            <ul id="results"></ul>
            
            <hr style="width: 100%; border: 0; border-top: 1px solid #ddd;">
            
            <h3>Generate Twin</h3>
            <p style="font-size: 12px; color: #555; margin-top: 0;">Click on the map to place a pin, or search for a location above.</p>
            <input type="text" id="twinName" placeholder="Twin Name">
            <button onclick="generateTwin()" class="btn-action">Generate Twin from OSM</button>
            <div id="status"></div>
        </div>
        <div id="map"></div>
    </div>

    <!-- Leaflet JS -->
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <script>
        document.addEventListener("DOMContentLoaded", function() {
            try {
                // Initialize map
                const map = L.map('map').setView([13.0628, 80.2793], 16);
                
                // Add layers
                const streetLayer = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
                    maxZoom: 19,
                    attribution: '© OpenStreetMap'
                });
                const satelliteLayer = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
                    maxZoom: 19,
                    attribution: 'Tiles © Esri'
                });
                
                streetLayer.addTo(map);
                L.control.layers({
                    "Streets": streetLayer,
                    "Satellite": satelliteLayer
                }).addTo(map);

                let marker = L.marker([13.0628, 80.2793], {draggable: true}).addTo(map);
                
                map.on('click', function(e) {
                    marker.setLatLng(e.latlng);
                });
                
                // Expose globally
                window.map = map;
                window.marker = marker;
                
                // Load existing twin if ID is in URL
                const urlParams = new URLSearchParams(window.location.search);
                const twinId = urlParams.get('id');
                if (twinId) {
                    fetch('/api/twin/' + twinId)
                        .then(res => res.json())
                        .then(twin => {
                            document.getElementById('twinName').value = twin.name;
                            map.setView([twin.lat, twin.lon], 16);
                            marker.setLatLng([twin.lat, twin.lon]);
                            renderTwinData(twin);
                        })
                        .catch(err => console.error("Error loading twin:", err));
                }
            } catch (err) {
                console.error("Map initialization failed:", err);
                document.getElementById('map').innerHTML = "<div style='padding:20px; color:red;'>Map failed to load. Check console for errors.</div>";
            }
        });

        function showStatus(msg, isError=false) {
            const el = document.getElementById('status');
            el.style.display = 'block';
            el.innerText = msg;
            el.style.backgroundColor = isError ? '#ffebee' : '#e8f5e9';
            el.style.color = isError ? '#c62828' : '#2e7d32';
        }

        async function searchPlace() {
            const query = document.getElementById('searchInput').value;
            if (!query) return;
            
            showStatus("Searching...", false);
            try {
                const res = await fetch('/api/twin/search?q=' + encodeURIComponent(query));
                if (!res.ok) throw new Error("Search failed on server");
                
                const data = await res.json();
                const ul = document.getElementById('results');
                ul.innerHTML = '';
                
                if (data.length === 0) {
                    showStatus("No results found.", true);
                    return;
                }
                
                showStatus("Results loaded.", false);
                setTimeout(() => { document.getElementById('status').style.display = 'none'; }, 2000);
                
                data.forEach(place => {
                    const li = document.createElement('li');
                    li.innerText = place.display_name;
                    li.onclick = () => {
                        const lat = parseFloat(place.lat);
                        const lon = parseFloat(place.lon);
                        window.map.setView([lat, lon], 17);
                        window.marker.setLatLng([lat, lon]);
                        ul.innerHTML = '';
                        document.getElementById('twinName').value = place.name || place.display_name.split(',')[0] || 'New Twin';
                    };
                    ul.appendChild(li);
                });
            } catch (err) {
                console.error(err);
                showStatus("Search failed. Check console.", true);
            }
        }
        
        async function generateTwin() {
            const name = document.getElementById('twinName').value || 'Unnamed Twin';
            const lat = window.marker.getLatLng().lat;
            const lon = window.marker.getLatLng().lng;
            
            showStatus("Fetching OSM data... (this may take 10-20 seconds)", false);
            
            try {
                const res = await fetch(/api/twin/?name= + encodeURIComponent(name) + &lat= + lat + &lon= + lon, {
                    method: 'POST'
                });
                
                if (res.ok) {
                    const data = await res.json();
                    showStatus("Twin successfully generated and saved!", false);
                    renderTwinData(data);
                } else {
                    const errText = await res.text();
                    showStatus("Failed to generate: " + errText, true);
                }
            } catch (err) {
                console.error(err);
                showStatus("Error generating twin. Check console.", true);
            }
        }
        
        function renderTwinData(twin) {
            // Draw polygon
            if (twin.polygon_json && twin.polygon_json.length > 0) {
                L.polygon(twin.polygon_json, {color: 'red', fillColor: '#f03', fillOpacity: 0.1}).addTo(window.map);
            }
            
            // Draw graph edges and nodes
            if (twin.graph_json && twin.graph_json.links) {
                const nodesMap = {};
                twin.graph_json.nodes.forEach(n => nodesMap[n.id] = n);
                
                let linkCount = 0;
                twin.graph_json.links.forEach(link => {
                    const src = nodesMap[link.source];
                    const dst = nodesMap[link.target];
                    if (src && dst) {
                        linkCount++;
                        L.polyline([[src.lat, src.lon], [dst.lat, dst.lon]], {color: 'blue', weight: 2, opacity: 0.6}).addTo(window.map);
                    }
                });
                
                twin.graph_json.nodes.forEach(n => {
                    if (n.type === 'gate' || n.type === 'entrance') {
                        L.circleMarker([n.lat, n.lon], {radius: 6, color: 'orange', fillColor: 'orange', fillOpacity: 1}).addTo(window.map).bindPopup("Gate");
                    } else {
                        L.circleMarker([n.lat, n.lon], {radius: 3, color: 'blue', border: false, fillOpacity: 0.5}).addTo(window.map);
                    }
                });
                console.log("Rendered", linkCount, "edges.");
            }
        }
    </script>
</body>
</html>'''

with open(os.path.join(base_dir, 'static', 'twin.html'), 'w', encoding='utf-8') as f:
    f.write(twin_html)

print("twin.html updated.")
