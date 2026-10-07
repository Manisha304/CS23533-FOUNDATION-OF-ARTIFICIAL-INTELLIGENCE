# FlowGuard (StadiumTwin v2) Block Architecture

This document provides a detailed block diagram of the FlowGuard system architecture.

```mermaid
flowchart TB
    %% Styling
    classDef frontend fill:#d4edda,stroke:#28a745,stroke-width:2px,color:#155724;
    classDef backend fill:#cce5ff,stroke:#007bff,stroke-width:2px,color:#004085;
    classDef core fill:#fff3cd,stroke:#ffc107,stroke-width:2px,color:#856404;
    classDef database fill:#e2e3e5,stroke:#6c757d,stroke-width:2px,color:#383d41;
    classDef external fill:#f8d7da,stroke:#dc3545,stroke-width:2px,color:#721c24;

    %% ----------------------------------------------------
    %% FRONTEND LAYER
    %% ----------------------------------------------------
    subgraph Frontend_Layer ["FRONTEND CLIENT LAYER (HTML / JS / CSS)"]
        direction LR
        UI["UI Components<br/>(Dashboard, Twin Editor, Sim View)"]
        Map["Leaflet Map Engine<br/>(Visualizes Graphs & Agents)"]
        WSC["WebSocket Client<br/>(Real-Time Updates)"]
        UI ~~~ Map ~~~ WSC
    end
    class Frontend_Layer,UI,Map,WSC frontend

    %% ----------------------------------------------------
    %% BACKEND LAYER
    %% ----------------------------------------------------
    subgraph Backend_Layer ["FASTAPI BACKEND LAYER"]
        direction LR
        AuthAPI["Auth Module<br/>(auth.py)"]
        TwinAPI["Twin REST API<br/>(api_twin.py)"]
        SimAPI["Simulation & WebSockets<br/>(api_sim.py)"]
        AuthAPI ~~~ TwinAPI ~~~ SimAPI
    end
    class Backend_Layer,AuthAPI,TwinAPI,SimAPI backend

    %% ----------------------------------------------------
    %% CORE PROCESSING MODULES
    %% ----------------------------------------------------
    subgraph Core_Layer ["CORE ENGINE LAYER (app/)"]
        direction TB
        
        subgraph Geo_Module ["Geo Processing (app/geo)"]
            direction LR
            OSMFetch["OSM Fetcher"]
            GraphBuilder["Graph Builder"]
            Geocode["Geocoder"]
        end
        
        subgraph Capacity_Module ["Capacity & Vision (app/capacity)"]
            direction LR
            Estimator["Capacity Estimator"]
            PathWidth["OpenCV Path Width"]
        end

        subgraph Analysis_Module ["Analysis (app/analysis)"]
            direction LR
            RiskPoints["Risk Points Scoring"]
        end

        subgraph Simulation_Module ["Simulation Engine (app/agents & planning)"]
            direction LR
            Routing["A* Path Routing"]
            Crowd["Crowd Agents"]
            Emergency["Emergency Agents"]
        end
        
        Geo_Module ~~~ Capacity_Module
        Analysis_Module ~~~ Simulation_Module
    end
    class Core_Layer,Geo_Module,Capacity_Module,Analysis_Module,Simulation_Module,OSMFetch,GraphBuilder,Geocode,Estimator,PathWidth,RiskPoints,Routing,Crowd,Emergency core

    %% ----------------------------------------------------
    %% DATA STORAGE LAYER
    %% ----------------------------------------------------
    subgraph Storage_Layer ["DATA PERSISTENCE LAYER"]
        direction LR
        ORM["SQLAlchemy ORM<br/>(models.py, db.py)"]
        DB[("SQLite Database<br/>(stadium_twin.db)")]
        ORM --> DB
    end
    class Storage_Layer,ORM,DB database

    %% ----------------------------------------------------
    %% EXTERNAL APIS
    %% ----------------------------------------------------
    subgraph External_Layer ["EXTERNAL APIS"]
        direction LR
        OSM_API["Overpass / Nominatim API"]
        ArcGIS_API["ArcGIS Satellite Tiles"]
    end
    class External_Layer,OSM_API,ArcGIS_API external

    %% ----------------------------------------------------
    %% CONNECTIONS & DATA FLOW
    %% ----------------------------------------------------
    
    %% Client to Server
    UI <-->|REST HTTP| AuthAPI
    UI <-->|REST HTTP| TwinAPI
    Map <-->|Loads GeoJSON| TwinAPI
    WSC <-->|WebSocket Stream| SimAPI

    %% Backend to Storage
    AuthAPI --> ORM
    TwinAPI --> ORM
    SimAPI --> ORM

    %% Backend to Core
    TwinAPI --> Geo_Module
    TwinAPI --> Capacity_Module
    TwinAPI --> Analysis_Module
    SimAPI --> Simulation_Module

    %% Internal Core Logic Flows
    Geo_Module -->|Generates NetworkX Graph| Routing
    Capacity_Module -->|Provides Metrics| Analysis_Module
    Analysis_Module -->|Risk Overlay| GraphBuilder
    Routing -->|Movement Paths| Crowd

    %% Core to External
    OSMFetch -->|Requests Bounds/Ways| OSM_API
    PathWidth -->|Requests Imagery| ArcGIS_API
```

## Layer Definitions

1. **Frontend Client Layer**: The presentation tier running in the browser. It handles interactive mapping (Leaflet), UI forms for parameters, and establishes a WebSocket connection for a smooth 60FPS simulation feed.
2. **FastAPI Backend Layer**: Acts as the central controller. It exposes REST API endpoints for state mutations and a WebSocket manager that broadcasts live agent coordinates to connected clients.
3. **Core Engine Layer**: The domain logic, heavily compartmentalized:
   - **Geo**: Pulls raw OSM data and translates it into a mathematical `NetworkX` graph.
   - **Capacity & Vision**: Runs geometric estimations (Shoelace) and Computer Vision pipelines (OpenCV satellite imagery) to augment data.
   - **Analysis**: Cross-references graph metrics (centrality) with geometrical constraints to generate risk scores.
   - **Simulation**: Agent-based modeling loop managing individual agent lifecycles, velocities, dynamic obstacle avoidance, and A* routing.
4. **Data Persistence Layer**: Synchronous `SQLAlchemy` ORM mapping models (Users, Twins) to a local SQLite database for local deployments.
5. **External APIs**: Third-party geographic providers necessary to build the accurate digital twin foundation.
