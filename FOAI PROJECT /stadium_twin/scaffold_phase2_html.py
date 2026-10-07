import os

base_dir = r'c:\Users\manis\OneDrive\Desktop\new foai\stadium_twin'

dashboard_html = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>StadiumTwin v2 - Dashboard</title>
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #f4f7f6; margin: 0; padding: 0; color: #333; }
        header { background: #2a5298; color: white; padding: 20px 40px; display: flex; justify-content: space-between; align-items: center; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        h2 { margin: 0; font-weight: 400; }
        .user-panel { font-weight: bold; }
        button { padding: 10px 20px; background-color: #ff4b2b; color: white; border: none; border-radius: 6px; cursor: pointer; font-size: 14px; font-weight: bold; transition: background 0.3s; margin-left: 20px; }
        button:hover { background-color: #ff416c; }
        .main-content { padding: 40px; max-width: 1200px; margin: 0 auto; text-align: center; }
        .card { background: white; padding: 40px; border-radius: 12px; box-shadow: 0 5px 15px rgba(0,0,0,0.05); margin-top: 30px; }
        .card h3 { color: #2a5298; margin-top: 0; font-size: 24px; }
        .twin-list { list-style: none; padding: 0; display: flex; flex-wrap: wrap; gap: 20px; justify-content: center; }
        .twin-item { background: #f9f9f9; border: 1px solid #eee; padding: 20px; border-radius: 8px; width: 250px; cursor: pointer; transition: transform 0.2s; }
        .twin-item:hover { transform: translateY(-5px); box-shadow: 0 5px 15px rgba(0,0,0,0.1); }
        .btn-primary { background: #00d2ff; color: #333; border-radius: 8px; font-size: 18px; padding: 15px 30px; margin-top: 20px; margin-left: 0; text-decoration: none; display: inline-block; }
        .btn-primary:hover { background: #3a7bd5; color: white; }
    </style>
</head>
<body>
    <header>
        <h2>StadiumTwin v2</h2>
        <div class="user-panel">
            Welcome, <span id="username">User</span>!
            <button onclick="logout()">Logout</button>
        </div>
    </header>
    
    <div class="main-content">
        <div class="card">
            <h3>My Digital Twins</h3>
            <ul id="twinList" class="twin-list">
                <!-- Twins loaded here -->
            </ul>
            <a href="/static/twin.html" class="btn-primary">Create New Twin</a>
        </div>
    </div>

    <script>
        async function fetchUser() {
            const response = await fetch('/api/me');
            if (response.ok) {
                const data = await response.json();
                document.getElementById('username').innerText = data.username;
                loadTwins();
            } else {
                window.location.href = '/static/login.html';
            }
        }
        
        async function loadTwins() {
            const response = await fetch('/api/twin/');
            if (response.ok) {
                const twins = await response.json();
                const list = document.getElementById('twinList');
                if (twins.length === 0) {
                    list.innerHTML = '<p>You do not have any saved twins yet.</p>';
                    return;
                }
                list.innerHTML = '';
                twins.forEach(twin => {
                    const li = document.createElement('li');
                    li.className = 'twin-item';
                    li.innerHTML = <h4> + twin.name + </h4><p>Lat:  + twin.lat.toFixed(4) + <br>Lon:  + twin.lon.toFixed(4) + </p>;
                    li.onclick = () => window.location.href = '/static/twin.html?id=' + twin.id;
                    list.appendChild(li);
                });
            }
        }
        
        async function logout() {
            await fetch('/auth/logout', { method: 'POST' });
            window.location.href = '/static/login.html';
        }

        fetchUser();
    </script>
</body>
</html>'''

twin_html = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>StadiumTwin v2 - Twin Editor</title>
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
    <style>
        body { font-family: 'Segoe UI', sans-serif; margin: 0; padding: 0; display: flex; height: 100vh; flex-direction: column; }
        header { background: #2a5298; color: white; padding: 10px 20px; display: flex; justify-content: space-between; align-items: center; }
        header a { color: white; text-decoration: none; font-weight: bold; }
        #main { display: flex; flex: 1; }
        #sidebar { width: 350px; background: #f4f7f6; padding: 20px; box-shadow: 2px 0 5px rgba(0,0,0,0.1); z-index: 10; display: flex; flex-direction: column; gap: 15px; }
        #map { flex: 1; z-index: 1; }
        input[type="text"] { padding: 10px; width: 100%; box-sizing: border-box; border: 1px solid #ccc; border-radius: 4px; }
        button { padding: 10px; background: #00d2ff; border: none; border-radius: 4px; font-weight: bold; cursor: pointer; }
        button:hover { background: #3a7bd5; color: white; }
        #results { list-style: none; padding: 0; margin: 0; max-height: 200px; overflow-y: auto; background: white; border-radius: 4px; }
        #results li { padding: 10px; border-bottom: 1px solid #eee; cursor: pointer; font-size: 14px; }
        #results li:hover { background: #eef; }
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
            <input type="text" id="searchInput" placeholder="Search (e.g. Chepauk Stadium)">
            <button onclick="searchPlace()">Search</button>
            <ul id="results"></ul>
            
            <hr>
            
            <h3>Generate Twin</h3>
            <p style="font-size: 12px; color: #555;">Click on the map to place a pin, or search for a location.</p>
            <input type="text" id="twinName" placeholder="Twin Name">
            <button onclick="generateTwin()" style="background: #ff4b2b; color: white;">Generate Twin from OSM</button>
            <div id="status" style="font-size: 12px; margin-top: 10px; color: green;"></div>
        </div>
        <div id="map"></div>
    </div>

    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <script>
        const map = L.map('map').setView([13.0628, 80.2793], 16); // Default Chepauk
        
        // Base layers
        const streetLayer = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '© OpenStreetMap contributors'
        });
        const satelliteLayer = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
            attribution: 'Tiles © Esri'
        });
        
        streetLayer.addTo(map);
        L.control.layers({
            "Streets": streetLayer,
            "Satellite": satelliteLayer
        }).addTo(map);

        let marker = L.marker([13.0628, 80.2793]).addTo(map);
        
        map.on('click', function(e) {
            marker.setLatLng(e.latlng);
        });

        async function searchPlace() {
            const query = document.getElementById('searchInput').value;
            if (!query) return;
            const res = await fetch('/api/twin/search?q=' + encodeURIComponent(query));
            const data = await res.json();
            const ul = document.getElementById('results');
            ul.innerHTML = '';
            data.forEach(place => {
                const li = document.createElement('li');
                li.innerText = place.display_name;
                li.onclick = () => {
                    const lat = parseFloat(place.lat);
                    const lon = parseFloat(place.lon);
                    map.setView([lat, lon], 17);
                    marker.setLatLng([lat, lon]);
                    ul.innerHTML = '';
                    document.getElementById('twinName').value = place.name || 'New Twin';
                };
                ul.appendChild(li);
            });
        }
        
        async function generateTwin() {
            const name = document.getElementById('twinName').value || 'Unnamed Twin';
            const lat = marker.getLatLng().lat;
            const lon = marker.getLatLng().lng;
            
            document.getElementById('status').innerText = "Fetching OSM data... (this may take a few seconds)";
            
            const res = await fetch(/api/twin/?name=&lat=&lon=, {
                method: 'POST'
            });
            
            if (res.ok) {
                const data = await res.json();
                document.getElementById('status').innerText = "Twin generated! Rendering...";
                renderTwinData(data);
            } else {
                document.getElementById('status').innerText = "Failed to generate.";
                document.getElementById('status').style.color = "red";
            }
        }
        
        function renderTwinData(twin) {
            // Draw polygon
            if (twin.polygon_json && twin.polygon_json.length > 0) {
                L.polygon(twin.polygon_json, {color: 'red', fillOpacity: 0.2}).addTo(map);
            }
            
            // Draw graph edges and nodes
            if (twin.graph_json && twin.graph_json.links) {
                const nodesMap = {};
                twin.graph_json.nodes.forEach(n => nodesMap[n.id] = n);
                
                twin.graph_json.links.forEach(link => {
                    const src = nodesMap[link.source];
                    const dst = nodesMap[link.target];
                    if (src && dst) {
                        L.polyline([[src.lat, src.lon], [dst.lat, dst.lon]], {color: 'blue', weight: 2}).addTo(map);
                    }
                });
                
                twin.graph_json.nodes.forEach(n => {
                    if (n.type === 'gate' || n.type === 'entrance') {
                        L.circleMarker([n.lat, n.lon], {radius: 5, color: 'orange'}).addTo(map).bindPopup("Gate/Entrance");
                    } else {
                        L.circleMarker([n.lat, n.lon], {radius: 3, color: 'blue'}).addTo(map);
                    }
                });
            }
        }
        
        // Check if loading existing twin
        const urlParams = new URLSearchParams(window.location.search);
        const twinId = urlParams.get('id');
        if (twinId) {
            fetch(/api/twin/).then(res => res.json()).then(twin => {
                document.getElementById('twinName').value = twin.name;
                map.setView([twin.lat, twin.lon], 16);
                marker.setLatLng([twin.lat, twin.lon]);
                renderTwinData(twin);
            });
        }
    </script>
</body>
</html>'''

files = {
    'static/dashboard.html': dashboard_html,
    'static/twin.html': twin_html
}

for path, content in files.items():
    full_path = os.path.join(base_dir, path.replace('/', os.sep))
    with open(full_path, 'w', encoding='utf-8') as f:
        f.write(content)

print("Phase 2 HTML scaffolded.")
