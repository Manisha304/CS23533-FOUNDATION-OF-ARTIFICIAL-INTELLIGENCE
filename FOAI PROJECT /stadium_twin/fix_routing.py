import os

content = '''from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
import networkx as nx

from .db import get_db
from .models import Twin, User
from .auth import get_current_user
from .geo.osm_fetch import fetch_osm_around
from .geo.graph_builder import build_graph_from_osm, haversine
from .geo.geocode import search_location

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
    built_data = build_graph_from_osm(osm_data)
    
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
    G.add_edge(node_id, nearest_node, length=min_dist)
    
    twin.graph_json = nx.node_link_data(G)
    db.commit()
    db.refresh(twin)
    return twin
'''

with open(r'c:\Users\manis\OneDrive\Desktop\new foai\stadium_twin\app\api_twin.py', 'w', encoding='utf-8') as f:
    f.write(content)
