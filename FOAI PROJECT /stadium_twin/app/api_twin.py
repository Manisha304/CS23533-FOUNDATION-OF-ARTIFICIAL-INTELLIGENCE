from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
import networkx as nx

from .db import get_db
from .models import Twin, User
from .auth import get_current_user
from .geo.osm_fetch import fetch_osm_around
from .geo.graph_builder import build_graph_from_osm, haversine
from .geo.geocode import search_location
from .analysis.risk_points import analyze_risk_points

router = APIRouter(prefix="/api/twin", tags=["twin"])

class GateCreate(BaseModel):
    lat: float
    lon: float
    name: str = "Manual Gate"

@router.get("/search")
def search_places(q: str):
    return search_location(q)

@router.post("/")
def create_twin(name: str, lat: float, lon: float, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    osm_data = fetch_osm_around(lat, lon)
    built_data = build_graph_from_osm(osm_data, lat, lon)
    
    new_twin = Twin(
        name=name,
        lat=lat,
        lon=lon,
        graph_json=built_data["graph_json"],
        polygon_json=built_data["polygon_json"],
        owner_id=current_user.id
    )
    db.add(new_twin)
    db.commit()
    db.refresh(new_twin)
    return new_twin

@router.get("/")
def list_twins(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role == "admin":
        return db.query(Twin).all()
    return db.query(Twin).filter(Twin.owner_id == current_user.id).all()

@router.get("/{twin_id}")
def get_twin(twin_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    twin = db.query(Twin).filter(Twin.id == twin_id).first()
    if not twin:
        raise HTTPException(status_code=404, detail="Twin not found")
    if twin.owner_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")
    return twin

@router.post("/{twin_id}/gates")
def add_manual_gate(twin_id: int, gate: GateCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    twin = db.query(Twin).filter(Twin.id == twin_id).first()
    if not twin:
        raise HTTPException(status_code=404, detail="Twin not found")
    if twin.owner_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")
        
    G = nx.node_link_graph(twin.graph_json)
    
    nearest_node = None
    min_dist = float('inf')
    
    for n, data in G.nodes(data=True):
        if 'lat' in data and 'lon' in data:
            d = haversine(gate.lat, gate.lon, data['lat'], data['lon'])
            if d < min_dist:
                min_dist = d
                nearest_node = n
                
    if not nearest_node:
        raise HTTPException(status_code=400, detail="Graph is empty, cannot connect gate")
        
    node_id = f"manual_gate_{len(G.nodes) + 1}"
    G.add_node(node_id, lat=gate.lat, lon=gate.lon, type="gate", label=gate.name)
    
    # 1. Connect to nearest outside node
    G.add_edge(node_id, nearest_node, length=min_dist)
    
    # 2. Connect to a synthetic stadium center node (creates internal paths!)
    center_id = "stadium_center"
    if center_id not in G:
        G.add_node(center_id, lat=twin.lat, lon=twin.lon, type="center", label="Center")
    
    dist_to_center = haversine(gate.lat, gate.lon, twin.lat, twin.lon)
    G.add_edge(node_id, center_id, length=dist_to_center)
    
    twin.graph_json = nx.node_link_data(G)
    db.commit()
    db.refresh(twin)
    return twin

@router.delete("/{twin_id}")
def delete_twin(twin_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    twin = db.query(Twin).filter(Twin.id == twin_id).first()
    if not twin:
        raise HTTPException(status_code=404, detail="Twin not found")
    if twin.owner_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized to delete this twin")
    db.delete(twin)
    db.commit()
    return {"message": f"Twin '{twin.name}' deleted successfully"}

@router.get("/{twin_id}/risk-points")
def get_risk_points(twin_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    twin = db.query(Twin).filter(Twin.id == twin_id).first()
    if not twin:
        raise HTTPException(status_code=404, detail="Twin not found")
    
    # We extract gates directly from the graph logic here for simplicity,
    # identical to how sim state extract gates.
    gates = []
    if twin.graph_json:
        for n in twin.graph_json.get("nodes", []):
            nid = str(n.get("id", ""))
            ntype = n.get("type", "")
            has_label = bool(n.get("label") or n.get("name"))
            is_gate = (ntype in ("gate", "entrance") or nid.startswith("manual_gate") or has_label)
            if is_gate and n.get("lat") and n.get("lon"):
                gates.append({"id": nid, "status": "open", "lat": float(n.get("lat")), "lon": float(n.get("lon"))})
                
    capacity = {"estimated_capacity": twin.capacity_estimate} if twin.capacity_estimate else None
    
    return analyze_risk_points(twin.graph_json, gates, capacity)
