import os
import json
from src.utils import load_config

def generate_html_dashboard():
    config = load_config()
    heatmap_data_path = config["forecasting"]["heatmap_data_path"]
    
    if not os.path.exists(heatmap_data_path):
        raise FileNotFoundError(f"Heatmap data not found at {heatmap_data_path}. Please run the pipeline first.")
        
    with open(heatmap_data_path, "r") as f:
        heatmap_data = json.load(f)
        
    # HTML Content with embedded JSON
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Bengaluru Traffic Gridlock Patrol Optimizer</title>
    
    <!-- Google Fonts -->
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800&family=Space+Grotesk:wght@400;500;700&display=swap" rel="stylesheet">
    
    <!-- Leaflet.js Map -->
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" integrity="sha256-p4NxAoJBhIIN+hmNHrzRCf9tD/miZyoHS5obTRR9BMY=" crossorigin=""/>
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js" integrity="sha256-20nQCchB9co0qIjJZRGuk2/Z9VM+kNiyxNV1lvTlZBo=" crossorigin=""></script>
    
    <style>
        :root {{
            --bg-dark: #07050f;
            --bg-card: rgba(18, 14, 36, 0.7);
            --border-glow: rgba(123, 97, 255, 0.15);
            --accent-red: #ff3b30;
            --accent-red-glow: rgba(255, 59, 48, 0.4);
            --accent-amber: #ff9f0a;
            --accent-amber-glow: rgba(255, 159, 10, 0.4);
            --accent-cyan: #00e5ff;
            --accent-purple: #7b61ff;
            --text-primary: #f5f4f9;
            --text-secondary: #9ea0ab;
            --font-main: 'Outfit', sans-serif;
            --font-mono: 'Space Grotesk', sans-serif;
        }}

        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            background-color: var(--bg-dark);
            color: var(--text-primary);
            font-family: var(--font-main);
            height: 100vh;
            overflow: hidden;
            display: flex;
            flex-direction: column;
        }}

        /* Header */
        header {{
            background: linear-gradient(180deg, rgba(11, 8, 25, 0.9) 0%, rgba(7, 5, 15, 0) 100%);
            border-bottom: 1px solid rgba(255, 255, 255, 0.05);
            padding: 1.25rem 2rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
            z-index: 1000;
            backdrop-filter: blur(10px);
        }}

        .logo-container {{
            display: flex;
            align-items: center;
            gap: 0.75rem;
        }}

        .logo-indicator {{
            width: 10px;
            height: 10px;
            border-radius: 50%;
            background-color: var(--accent-cyan);
            box-shadow: 0 0 10px var(--accent-cyan);
            animation: pulse 2s infinite;
        }}

        header h1 {{
            font-size: 1.4rem;
            font-weight: 700;
            letter-spacing: -0.5px;
            background: linear-gradient(90deg, #fff 0%, #a29bfe 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            font-family: var(--font-mono);
        }}

        header p {{
            font-size: 0.85rem;
            color: var(--text-secondary);
            margin-top: 2px;
        }}

        .badge {{
            background: rgba(123, 97, 255, 0.15);
            border: 1px solid rgba(123, 97, 255, 0.3);
            color: #d1c7ff;
            padding: 0.25rem 0.75rem;
            border-radius: 20px;
            font-size: 0.75rem;
            font-weight: 600;
            font-family: var(--font-mono);
        }}

        /* Dashboard Main Layout */
        .dashboard-container {{
            flex: 1;
            display: flex;
            position: relative;
            height: calc(100vh - 75px);
        }}

        /* Sidebar */
        .sidebar {{
            width: 380px;
            background-color: rgba(9, 7, 20, 0.85);
            border-right: 1px solid rgba(255, 255, 255, 0.05);
            display: flex;
            flex-direction: column;
            padding: 1.5rem;
            gap: 1.5rem;
            z-index: 1000;
            backdrop-filter: blur(15px);
            overflow-y: auto;
        }}

        /* Scrollbar styling */
        .sidebar::-webkit-scrollbar {{
            width: 4px;
        }}
        .sidebar::-webkit-scrollbar-track {{
            background: rgba(0, 0, 0, 0.1);
        }}
        .sidebar::-webkit-scrollbar-thumb {{
            background: rgba(123, 97, 255, 0.3);
            border-radius: 4px;
        }}

        /* Group Box / Glassmorphic Card */
        .card {{
            background: var(--bg-card);
            border: 1px solid var(--border-glow);
            border-radius: 12px;
            padding: 1.25rem;
            display: flex;
            flex-direction: column;
            gap: 1rem;
            box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37);
        }}

        .card-title {{
            font-size: 0.8rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 1px;
            color: var(--text-secondary);
            font-family: var(--font-mono);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}

        /* Timeband Pill Selector */
        .timeband-selector {{
            display: flex;
            background: rgba(0, 0, 0, 0.3);
            padding: 4px;
            border-radius: 8px;
            border: 1px solid rgba(255, 255, 255, 0.05);
        }}

        .timeband-btn {{
            flex: 1;
            background: none;
            border: none;
            color: var(--text-secondary);
            font-family: var(--font-mono);
            font-size: 0.75rem;
            font-weight: 500;
            padding: 0.5rem 0.25rem;
            border-radius: 6px;
            cursor: pointer;
            transition: all 0.3s cubic-bezier(0.25, 0.8, 0.25, 1);
            text-align: center;
        }}

        .timeband-btn.active {{
            background-color: var(--accent-purple);
            color: #fff;
            box-shadow: 0 4px 12px rgba(123, 97, 255, 0.3);
        }}

        /* Stats grid */
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 0.75rem;
        }}

        .stat-box {{
            background: rgba(255, 255, 255, 0.02);
            border: 1px solid rgba(255, 255, 255, 0.05);
            border-radius: 8px;
            padding: 0.75rem;
            display: flex;
            flex-direction: column;
            gap: 0.25rem;
            transition: border-color 0.3s;
        }}

        .stat-box:hover {{
            border-color: rgba(123, 97, 255, 0.3);
        }}

        .stat-value {{
            font-size: 1.4rem;
            font-weight: 700;
            color: var(--text-primary);
            font-family: var(--font-mono);
        }}

        .stat-label {{
            font-size: 0.7rem;
            color: var(--text-secondary);
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}

        /* Search */
        .search-box {{
            position: relative;
        }}

        .search-input {{
            width: 100%;
            background: rgba(0, 0, 0, 0.3);
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 8px;
            padding: 0.6rem 1rem;
            color: #fff;
            font-family: var(--font-main);
            font-size: 0.85rem;
            outline: none;
            transition: border-color 0.3s;
        }}

        .search-input:focus {{
            border-color: var(--accent-purple);
        }}

        /* List container */
        .hotspot-list-container {{
            flex: 1;
            display: flex;
            flex-direction: column;
            gap: 0.5rem;
            max-height: 400px;
            overflow-y: auto;
        }}

        .hotspot-list-container::-webkit-scrollbar {{
            width: 4px;
        }}
        .hotspot-list-container::-webkit-scrollbar-thumb {{
            background: rgba(255, 255, 255, 0.1);
            border-radius: 4px;
        }}

        .hotspot-item {{
            background: rgba(255, 255, 255, 0.02);
            border: 1px solid rgba(255, 255, 255, 0.05);
            border-radius: 8px;
            padding: 0.75rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
            cursor: pointer;
            transition: all 0.2s ease-in-out;
        }}

        .hotspot-item:hover {{
            background: rgba(255, 255, 255, 0.04);
            border-color: rgba(123, 97, 255, 0.3);
            transform: translateY(-2px);
        }}

        .hotspot-item-info {{
            display: flex;
            flex-direction: column;
            gap: 0.2rem;
            max-width: 70%;
        }}

        .hotspot-item-station {{
            font-size: 0.85rem;
            font-weight: 600;
            color: #fff;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }}

        .hotspot-item-details {{
            font-size: 0.75rem;
            color: var(--text-secondary);
        }}

        .hotspot-item-badge {{
            padding: 0.2rem 0.5rem;
            border-radius: 4px;
            font-size: 0.7rem;
            font-weight: 700;
            font-family: var(--font-mono);
            text-align: center;
        }}

        .hotspot-item-badge.Red {{
            background: rgba(255, 59, 48, 0.15);
            border: 1px solid rgba(255, 59, 48, 0.4);
            color: #ff6961;
            box-shadow: 0 0 10px rgba(255, 59, 48, 0.1);
        }}

        .hotspot-item-badge.Amber {{
            background: rgba(255, 159, 10, 0.15);
            border: 1px solid rgba(255, 159, 10, 0.4);
            color: #ffd60a;
            box-shadow: 0 0 10px rgba(255, 159, 10, 0.1);
        }}

        /* Map Container */
        .map-container {{
            flex: 1;
            height: 100%;
            position: relative;
            background-color: #12101e;
        }}

        #map {{
            width: 100%;
            height: 100%;
        }}

        /* Map custom popups */
        .leaflet-popup-content-wrapper {{
            background: rgba(13, 10, 28, 0.95) !important;
            border: 1px solid rgba(123, 97, 255, 0.3) !important;
            color: var(--text-primary) !important;
            border-radius: 12px !important;
            box-shadow: 0 10px 30px rgba(0,0,0,0.5) !important;
            backdrop-filter: blur(10px) !important;
        }}

        .leaflet-popup-tip {{
            background: rgba(13, 10, 28, 0.95) !important;
            border-left: 1px solid rgba(123, 97, 255, 0.3) !important;
            border-bottom: 1px solid rgba(123, 97, 255, 0.3) !important;
        }}

        .popup-header {{
            border-bottom: 1px solid rgba(255, 255, 255, 0.08);
            padding-bottom: 0.5rem;
            margin-bottom: 0.5rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}

        .popup-title {{
            font-size: 0.9rem;
            font-weight: 700;
            color: #fff;
            font-family: var(--font-mono);
        }}

        .popup-badge {{
            font-size: 0.65rem;
            font-weight: 800;
            padding: 1px 6px;
            border-radius: 3px;
            text-transform: uppercase;
        }}

        .popup-grid {{
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 0.5rem;
            font-size: 0.75rem;
            margin-bottom: 0.75rem;
        }}

        .popup-label {{
            color: var(--text-secondary);
        }}

        .popup-value {{
            font-weight: 600;
            color: #fff;
            text-align: right;
        }}

        .popup-dispatch-btn {{
            width: 100%;
            background: linear-gradient(90deg, #7b61ff 0%, #5923ff 100%);
            border: none;
            color: #fff;
            padding: 0.4rem;
            border-radius: 4px;
            font-weight: 600;
            font-size: 0.75rem;
            cursor: pointer;
            transition: opacity 0.2s;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            font-family: var(--font-mono);
        }}

        .popup-dispatch-btn:hover {{
            opacity: 0.9;
        }}

        /* Legend */
        .map-legend {{
            position: absolute;
            bottom: 2rem;
            right: 2rem;
            background: rgba(13, 10, 28, 0.9);
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 8px;
            padding: 0.75rem 1rem;
            z-index: 1000;
            backdrop-filter: blur(8px);
            display: flex;
            flex-direction: column;
            gap: 0.4rem;
            box-shadow: 0 4px 20px rgba(0,0,0,0.4);
        }}

        .legend-title {{
            font-size: 0.7rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            color: var(--text-secondary);
            margin-bottom: 0.2rem;
            font-family: var(--font-mono);
        }}

        .legend-item {{
            display: flex;
            align-items: center;
            gap: 0.5rem;
            font-size: 0.75rem;
        }}

        .legend-color {{
            width: 12px;
            height: 12px;
            border-radius: 50%;
        }}

        /* Animations */
        @keyframes pulse {{
            0% {{
                transform: scale(0.95);
                box-shadow: 0 0 0 0 rgba(0, 229, 255, 0.5);
            }}
            70% {{
                transform: scale(1);
                box-shadow: 0 0 0 8px rgba(0, 229, 255, 0);
            }}
            100% {{
                transform: scale(0.95);
                box-shadow: 0 0 0 0 rgba(0, 229, 255, 0);
            }}
        }}

        /* Responsive */
        @media (max-width: 768px) {{
            .dashboard-container {{
                flex-direction: column;
            }}
            .sidebar {{
                width: 100%;
                height: 40%;
                overflow-y: auto;
            }}
            .map-container {{
                height: 60%;
            }}
        }}
    </style>
</head>
<body>

    <header>
        <div class="logo-container">
            <div class="logo-indicator"></div>
            <div>
                <h1>GRIDLOCK PATROL OPTIMIZER</h1>
                <p>Tomorrow's Traffic Hotspot Predictor & Dispatch System</p>
            </div>
        </div>
        <div class="badge">PROD PATH: HIST-MEAN MODEL</div>
    </header>

    <div class="dashboard-container">
        
        <!-- Sidebar Controls -->
        <div class="sidebar">
            
            <!-- Timeband selector -->
            <div class="card">
                <div class="card-title">Select Shift Time-Band <span style="color: var(--accent-cyan)">● Live</span></div>
                <div class="timeband-selector">
                    <button class="timeband-btn active" onclick="switchTimeBand('morning_peak')">Morning Peak</button>
                    <button class="timeband-btn" onclick="switchTimeBand('mid_day')">Mid Day</button>
                    <button class="timeband-btn" onclick="switchTimeBand('late_night')">Late Night</button>
                </div>
            </div>
            
            <!-- Statistics Card -->
            <div class="card">
                <div class="card-title">Shift Risk Metrics</div>
                <div class="stats-grid">
                    <div class="stat-box">
                        <span class="stat-value" id="stat-count">0</span>
                        <span class="stat-label">Active Hotspots</span>
                    </div>
                    <div class="stat-box">
                        <span class="stat-value" id="stat-volume">0.0</span>
                        <span class="stat-label">Max Violations/Wk</span>
                    </div>
                    <div class="stat-box">
                        <span class="stat-value" id="stat-cii">0.00</span>
                        <span class="stat-label">Mean CII Impact</span>
                    </div>
                    <div class="stat-box">
                        <span class="stat-value" id="stat-priority" style="color: var(--accent-red)">0.00</span>
                        <span class="stat-label">Avg Priority</span>
                    </div>
                </div>
            </div>
            
            <!-- Search & Filter Card -->
            <div class="card" style="flex: 1; min-height: 300px; display: flex; flex-direction: column;">
                <div class="card-title">Priority Rank List</div>
                <div class="search-box">
                    <input type="text" class="search-input" id="search-input" placeholder="Search Station..." oninput="handleSearch()">
                </div>
                <div class="hotspot-list-container" id="hotspot-list">
                    <!-- Dynamic list items -->
                </div>
            </div>
            
        </div>
        
        <!-- Map Panel -->
        <div class="map-container">
            <div id="map"></div>
            
            <!-- Legend overlay -->
            <div class="map-legend">
                <div class="legend-title">Patrol Priority Tiers</div>
                <div class="legend-item">
                    <div class="legend-color" style="background-color: var(--accent-red); box-shadow: 0 0 8px var(--accent-red);"></div>
                    <span>Red Tier (Top 20% Risk)</span>
                </div>
                <div class="legend-item">
                    <div class="legend-color" style="background-color: var(--accent-amber); box-shadow: 0 0 8px var(--accent-amber);"></div>
                    <span>Amber Tier (Next 30% Risk)</span>
                </div>
            </div>
        </div>
        
    </div>

    <!-- Embedded Data -->
    <script>
        const HEATMAP_DATA = {json.dumps(heatmap_data)};
    </script>
    
    <!-- Main JS Application Logic -->
    <script>
        let currentBand = "morning_peak";
        let map;
        let markersGroup;
        let searchFilter = "";
        
        // Initialize Map
        function initMap() {{
            // Centered on Bengaluru centre
            map = L.map('map', {{
                zoomControl: false,
                attributionControl: false
            }}).setView([12.9716, 77.5946], 12);
            
            // Add zoom control at top right
            L.control.zoom({{ position: 'topright' }}).addTo(map);
            
            // CartoDB Dark Matter tile layer
            L.tileLayer('https://{{s}}.basemaps.cartocdn.com/dark_all/{{z}}/{{x}}/{{y}}{{r}}.png', {{
                maxZoom: 20
            }}).addTo(map);
            
            markersGroup = L.layerGroup().addTo(map);
        }}
        
        // Switch timeband and refresh dashboard
        function switchTimeBand(band) {{
            currentBand = band;
            
            // Update buttons state
            document.querySelectorAll('.timeband-btn').forEach(btn => {{
                if (btn.innerText.toLowerCase().replace(" ", "_") === band) {{
                    btn.classList.add('active');
                }} else {{
                    btn.classList.remove('active');
                }}
            }});
            
            document.getElementById('search-input').value = "";
            searchFilter = "";
            
            renderDashboard();
        }}
        
        // Pan/Zoom map to cluster and open popup
        function focusHotspot(lat, lon, clusterId) {{
            map.setView([lat, lon], 14, {{ animate: true, duration: 1.0 }});
            markersGroup.eachLayer(layer => {{
                if (layer.options.clusterId === clusterId) {{
                    layer.openPopup();
                }}
            }});
        }}
        
        // Search handler
        function handleSearch() {{
            searchFilter = document.getElementById('search-input').value.toLowerCase();
            renderDashboard(false); // Render dashboard without resetting map zoom/bounds
        }}
        
        // Main rendering logic
        function renderDashboard(updateMap = true) {{
            const points = HEATMAP_DATA[currentBand] || [];
            
            // Apply search filter
            const filteredPoints = points.filter(p => 
                p.station.toLowerCase().includes(searchFilter)
            );
            
            // Calculate and display statistics
            const activeCount = filteredPoints.length;
            const maxVolume = activeCount > 0 ? Math.max(...filteredPoints.map(p => p.volume)) : 0.0;
            const meanCii = activeCount > 0 ? (filteredPoints.reduce((acc, p) => acc + p.cii, 0) / activeCount) : 0.0;
            const avgPriority = activeCount > 0 ? (filteredPoints.reduce((acc, p) => acc + p.score, 0) / activeCount) : 0.0;
            
            document.getElementById('stat-count').innerText = activeCount;
            document.getElementById('stat-volume').innerText = maxVolume.toFixed(1);
            document.getElementById('stat-cii').innerText = meanCii.toFixed(2);
            document.getElementById('stat-priority').innerText = avgPriority.toFixed(3);
            
            // Render Sidebar List
            const listContainer = document.getElementById('hotspot-list');
            listContainer.innerHTML = '';
            
            filteredPoints.forEach(p => {{
                const item = document.createElement('div');
                item.className = 'hotspot-item';
                item.onclick = () => focusHotspot(p.lat, p.lon, p.cluster);
                
                item.innerHTML = `
                    <div class="hotspot-item-info">
                        <span class="hotspot-item-station">${{p.station}}</span>
                        <span class="hotspot-item-details">Cluster #${{p.cluster}} | Vol: ${{p.volume.toFixed(1)}}/wk</span>
                    </div>
                    <div class="hotspot-item-badge ${{p.tier}}">${{p.tier}}</div>
                `;
                listContainer.appendChild(item);
            }});
            
            // Render Map Markers
            if (updateMap) {{
                markersGroup.clearLayers();
                
                if (filteredPoints.length === 0) return;
                
                const bounds = [];
                
                filteredPoints.forEach(p => {{
                    const color = p.tier === 'Red' ? 'var(--accent-red)' : 'var(--accent-amber)';
                    const shadowColor = p.tier === 'Red' ? 'var(--accent-red-glow)' : 'var(--accent-amber-glow)';
                    
                    // Sizing based on priority score
                    const r = 8 + (p.score * 12); 
                    
                    const marker = L.circleMarker([p.lat, p.lon], {{
                        radius: r,
                        color: color,
                        fillColor: color,
                        fillOpacity: 0.5,
                        weight: 2,
                        clusterId: p.cluster
                    }});
                    
                    // Create Popup HTML
                    const popupHtml = `
                        <div class="popup-header">
                            <span class="popup-title">${{p.station}}</span>
                            <span class="popup-badge" style="background: ${{p.tier === 'Red' ? 'rgba(255, 59, 48, 0.2)' : 'rgba(255, 159, 10, 0.2)'}}; color: ${{p.tier === 'Red' ? '#ff6961' : '#ffd60a'}}; border: 1px solid ${{color}};">
                                ${{p.tier}} Tier
                            </span>
                        </div>
                        <div class="popup-grid">
                            <span class="popup-label">Cluster ID:</span>
                            <span class="popup-value">#${{p.cluster}}</span>
                            
                            <span class="popup-label">Est. Weekly Violations:</span>
                            <span class="popup-value">${{p.volume.toFixed(1)}}</span>
                            
                            <span class="popup-label">CII Score (Traffic Flow Impact):</span>
                            <span class="popup-value">${{p.cii.toFixed(3)}}</span>
                            
                            <span class="popup-label" style="font-weight: 700;">Final Priority Score:</span>
                            <span class="popup-value" style="color: ${{color}}; font-weight: 700;">${{p.score.toFixed(4)}}</span>
                        </div>
                        <button class="popup-dispatch-btn" onclick="alert('Patrol Unit dispatched to Cluster #${{p.cluster}} (${{p.station}}). Notification sent to terminal.')">
                            Dispatch Patrol
                        </button>
                    `;
                    
                    marker.bindPopup(popupHtml, {{ maxWidth: 280 }});
                    markersGroup.addLayer(marker);
                    bounds.push([p.lat, p.lon]);
                }});
                
                // Fit bounds to show all markers
                if (bounds.length > 0) {{
                    map.fitBounds(bounds, {{ padding: [50, 50] }});
                }}
            }}
        }}
        
        // Initial Startup
        window.onload = () => {{
            initMap();
            renderDashboard();
        }};
    </script>
</body>
</html>
"""
    
    output_html_path = os.path.join(os.path.dirname(heatmap_data_path), "..", "..", "index.html")
    output_html_path = os.path.abspath(output_html_path)
    
    with open(output_html_path, "w", encoding="utf-8") as f:
        f.write(html_content)
        
    print(f"HTML dashboard generated successfully at {output_html_path}")
    return output_html_path

if __name__ == "__main__":
    generate_html_dashboard()
