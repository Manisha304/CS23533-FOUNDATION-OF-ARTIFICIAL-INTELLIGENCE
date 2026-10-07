import pytest
from app.analysis.risk_points import analyze_risk_points
from app.config import settings
from fastapi.testclient import TestClient
from app.main import app

def test_risk_scoring_basic():
    # create a small graph json
    graph_json = {
        "nodes": [
            {"id": "A", "lat": 1.0, "lon": 1.0},
            {"id": "B", "lat": 2.0, "lon": 2.0},
            {"id": "C", "lat": 3.0, "lon": 3.0}, # articulation point connecting A, B to D, E
            {"id": "D", "lat": 4.0, "lon": 4.0},
            {"id": "E", "lat": 5.0, "lon": 5.0}
        ],
        "links": [
            {"source": "A", "target": "B", "length": 1},
            {"source": "B", "target": "C", "length": 1, "tags": {"highway": "steps"}}, # steps here
            {"source": "C", "target": "D", "length": 1},
            {"source": "C", "target": "E", "length": 1},
            {"source": "D", "target": "E", "length": 1, "tags": {"width": "1.0m"}} # narrow here
        ]
    }
    
    gates = [{"id": "E", "status": "open", "lat": 5.0, "lon": 5.0}]
    cap = {"estimated_capacity": 2000}
    
    results = analyze_risk_points(graph_json, gates, cap)
    
    # Check results
    res_map = {r["id"]: r for r in results}
    
    # Node C is an articulation point
    assert "C" in res_map
    assert "Articulation point" in res_map["C"]["reason"]
    
    # Node B and C touch steps
    assert "B" in res_map
    assert "Stairs/steep path" in res_map["B"]["reason"]
    assert "Stairs/steep path" in res_map["C"]["reason"]
    
    # Node D and E touch narrow path
    assert "D" in res_map
    assert "Narrow path" in res_map["D"]["reason"]
    assert "E" in res_map
    assert "Narrow path" in res_map["E"]["reason"]

def test_risk_scoring_empty():
    results = analyze_risk_points({}, [], {})
    assert results == []
