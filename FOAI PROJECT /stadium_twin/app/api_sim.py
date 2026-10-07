"""
Simulation API — Phase 5 & 6 endpoints.

POST /api/sim/{twin_id}/capacity   → compute capacity estimate
POST /api/sim/{twin_id}/route      → A* route from zone to best open gate
POST /api/sim/{twin_id}/block_gate → block/unblock a gate
GET  /api/sim/{twin_id}/state      → full sim state (gates, crowd, status)
POST /api/sim/{twin_id}/tick       → advance one simulation tick (crowd moves)
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
import json
import math

from .db import get_db
from .models import Twin, User
from .auth import get_current_user
from .capacity.estimator import estimate_capacity
from .agents.crowd_agents import SafetyAgent, CrowdAgent, RouteAgent, Coordinator, haversine
from .analysis.risk_points import analyze_risk_points

router = APIRouter(prefix="/api/sim", tags=["simulation"])

# ---------------------------------------------------------------------------
# In-memory simulation state (per twin_id)
# Simple dict; resets on server restart (fine for demo / viva)
# ---------------------------------------------------------------------------
_sim_state: dict = {}


def _get_state(twin_id: int, graph_json: dict) -> dict:
    """Return or initialise the simulation state for a twin."""
    if twin_id not in _sim_state:
        _sim_state[twin_id] = {
            "gates": {},          # {gate_id: {id, lat, lon, label, status, crowd}}
            "crowd_agents": [],   # list of moving crowd agents
            "tick": 0,
            "capacity": None,
            "risk_scores": {},    # {node_id: score}
        }
    return _sim_state[twin_id]

def _ensure_risk_scores(state: dict, graph_json: dict):
    if not state.get("risk_scores"):
        capacity_dict = {"estimated_capacity": state["capacity"]} if isinstance(state["capacity"], (int, float)) else state["capacity"]
        gates_list = list(state.get("gates", {}).values())
        risk_list = analyze_risk_points(graph_json, gates_list, capacity_dict)
        state["risk_scores"] = {r["id"]: r["score"] for r in risk_list}


def _extract_gates(graph_json: dict) -> dict:
    """Pull gate nodes out of the graph JSON.
    Matches: type==gate, type==entrance, id starts with manual_gate, or has a 'label' field.
    """
    gates = {}
    if not graph_json:
        return gates
    for n in graph_json.get("nodes", []):
        nid = str(n.get("id", ""))
        ntype = n.get("type", "")
        has_label = bool(n.get("label") or n.get("name"))
        is_gate = (
            ntype in ("gate", "entrance")
            or nid.startswith("manual_gate")
            or has_label
        )
        if is_gate and n.get("lat") and n.get("lon"):
            gates[nid] = {
                "id": nid,
                "lat": float(n.get("lat", 0)),
                "lon": float(n.get("lon", 0)),
                "label": n.get("label") or n.get("name") or nid,
                "status": "open",
                "crowd": 0,
            }
    return gates


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class RouteRequest(BaseModel):
    lat: float
    lon: float

class BlockGateRequest(BaseModel):
    gate_id: str
    action: str = "block"  # "block" or "open"

class TickRequest(BaseModel):
    spawn_count: int = 5   # crowd agents to spawn per tick
    zone_lat: Optional[float] = None
    zone_lon: Optional[float] = None

class EmergencyRequest(BaseModel):
    incident_node: str
    severity: str = "high"


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/{twin_id}/capacity")
def compute_capacity(twin_id: int, db: Session = Depends(get_db),
                     current_user: User = Depends(get_current_user)):
    twin = db.query(Twin).filter(Twin.id == twin_id).first()
    if not twin:
        raise HTTPException(404, "Twin not found")
    if not twin.polygon_json or len(twin.polygon_json) < 3:
        raise HTTPException(400, "Twin has no polygon. Generate the twin first.")

    result = estimate_capacity(twin.polygon_json)
    twin.capacity_estimate = result["estimated_capacity"]
    db.commit()

    # Seed sim state
    state = _get_state(twin_id, twin.graph_json)
    state["capacity"] = result
    if not state["gates"]:
        state["gates"] = _extract_gates(twin.graph_json)

    return result


@router.get("/{twin_id}/state")
def get_state(twin_id: int, db: Session = Depends(get_db),
              current_user: User = Depends(get_current_user)):
    twin = db.query(Twin).filter(Twin.id == twin_id).first()
    if not twin:
        raise HTTPException(404, "Twin not found")

    state = _get_state(twin_id, twin.graph_json)
    if not state["gates"]:
        state["gates"] = _extract_gates(twin.graph_json)

    return {
        "twin_id": twin_id,
        "twin_name": twin.name,
        "tick": state["tick"],
        "capacity": state["capacity"],
        "gates": list(state["gates"].values()),
        "crowd_agents": state["crowd_agents"],
    }


@router.post("/{twin_id}/block_gate")
def block_gate(twin_id: int, req: BlockGateRequest,
               db: Session = Depends(get_db),
               current_user: User = Depends(get_current_user)):
    twin = db.query(Twin).filter(Twin.id == twin_id).first()
    if not twin:
        raise HTTPException(404, "Twin not found")

    state = _get_state(twin_id, twin.graph_json)

    # Always re-seed gates from graph (handles server restart / first call)
    fresh_gates = _extract_gates(twin.graph_json)
    for gid, gdata in fresh_gates.items():
        if gid not in state["gates"]:
            state["gates"][gid] = gdata

    if req.gate_id not in state["gates"]:
        available = list(state["gates"].keys())
        raise HTTPException(400, f"Gate '{req.gate_id}' not found. Available gates: {available}")

    new_status = req.action if req.action in ("open", "blocked") else "blocked"
    state["gates"][req.gate_id]["status"] = new_status
    return {
        "gate_id": req.gate_id,
        "new_status": new_status,
        "message": f"Gate {req.gate_id} is now {new_status}",
        "all_gates": list(state["gates"].values()),
    }


@router.post("/{twin_id}/route")
def compute_route(twin_id: int, req: RouteRequest,
                  db: Session = Depends(get_db),
                  current_user: User = Depends(get_current_user)):
    twin = db.query(Twin).filter(Twin.id == twin_id).first()
    if not twin:
        raise HTTPException(404, "Twin not found")
    if not twin.graph_json:
        raise HTTPException(400, "Twin has no graph. Generate the twin first.")

    state = _get_state(twin_id, twin.graph_json)
    if not state["gates"]:
        state["gates"] = _extract_gates(twin.graph_json)

    if not state["gates"]:
        raise HTTPException(400, "No gates found. Please add manual gates first.")

    gates_list = list(state["gates"].values())

    safety = SafetyAgent(gates_list)
    crowd = CrowdAgent(gates_list)
    route_agent = RouteAgent()
    coord = Coordinator(safety, crowd, route_agent)

    # Apply current blocked state from sim
    for g in gates_list:
        if g["status"] == "blocked":
            safety.block_gate(g["id"], "simulation")
        crowd.update_crowd(g["id"], g.get("crowd", 0))

    _ensure_risk_scores(state, twin.graph_json)
    
    result = coord.best_gate(twin.graph_json, req.lat, req.lon, gates_list, risk_scores=state["risk_scores"])
    return result

@router.post("/{twin_id}/emergency-response")
def emergency_response(twin_id: int, req: EmergencyRequest,
                       db: Session = Depends(get_db),
                       current_user: User = Depends(get_current_user)):
    from .geo.osm_fetch import fetch_emergency_services
    from .agents.emergency_agent import EmergencyAgent
    
    twin = db.query(Twin).filter(Twin.id == twin_id).first()
    if not twin:
        raise HTTPException(404, "Twin not found")
        
    nodes_raw = twin.graph_json.get("nodes", [])
    node_map = {str(n["id"]): n for n in nodes_raw}
    
    if req.incident_node not in node_map:
        raise HTTPException(400, "Incident node not found in graph")
        
    ilat = node_map[req.incident_node].get("lat")
    ilon = node_map[req.incident_node].get("lon")
    
    if not ilat or not ilon:
        raise HTTPException(400, "Incident node missing coordinates")
        
    services = fetch_emergency_services(ilat, ilon, 5000)
    
    agent = EmergencyAgent(req.incident_node, ilat, ilon, req.severity)
    agent.update_responders(services)
    
    result = agent.deliberate(twin.graph_json, db)
    if "error" in result:
        raise HTTPException(400, result["error"])
        
    return result


@router.post("/{twin_id}/tick")
def tick_simulation(twin_id: int, req: TickRequest,
                    db: Session = Depends(get_db),
                    current_user: User = Depends(get_current_user)):
    """
    One simulation tick:
    1. Spawn `spawn_count` new crowd agents near zone_lat/lon (or twin centre).
    2. For each crowd agent, route it to best open gate via A*.
    3. Move agents one step along their path.
    4. Remove agents that have reached their gate.
    """
    twin = db.query(Twin).filter(Twin.id == twin_id).first()
    if not twin:
        raise HTTPException(404, "Twin not found")

    state = _get_state(twin_id, twin.graph_json)
    if not state["gates"]:
        state["gates"] = _extract_gates(twin.graph_json)

    zone_lat = req.zone_lat if req.zone_lat else twin.lat
    zone_lon = req.zone_lon if req.zone_lon else twin.lon

    gates_list = list(state["gates"].values())
    open_gates = [g for g in gates_list if g["status"] == "open"]
    if not open_gates:
        return {"error": "All gates are blocked! Simulation cannot proceed."}

    route_agent = RouteAgent()

    # Spawn new crowd agents with small random offset
    import random
    for i in range(req.spawn_count):
        offset_lat = zone_lat + random.uniform(-0.002, 0.002)
        offset_lon = zone_lon + random.uniform(-0.002, 0.002)
        
        # Pick nearest open gate as target
        target_gate = min(open_gates, key=lambda g: haversine(offset_lat, offset_lon, g["lat"], g["lon"]))
        
        _ensure_risk_scores(state, twin.graph_json)
        
        route = route_agent.astar(
            twin.graph_json, 
            offset_lat, 
            offset_lon, 
            [target_gate["id"]], 
            risk_scores=state["risk_scores"]
        )
        path = route.get("path", [])
        
        if path:
            agent = {
                "id": f"agent_{state['tick']}_{i}",
                "lat": offset_lat,
                "lon": offset_lon,
                "target_gate": target_gate["id"],
                "path": path,
                "path_index": 0,
                "status": "moving",
            }
            state["crowd_agents"].append(agent)

    # Move existing agents one step along their path
    arrived = []
    for agent in state["crowd_agents"]:
        if agent["status"] == "arrived":
            arrived.append(agent)
            continue
        
        idx = agent["path_index"]
        path = agent["path"]
        
        if idx + 1 < len(path):
            agent["path_index"] += 1
            agent["lat"] = path[agent["path_index"]][0]
            agent["lon"] = path[agent["path_index"]][1]
        else:
            agent["status"] = "arrived"
            # Increment crowd count at the gate
            gate_id = agent["target_gate"]
            if gate_id in state["gates"]:
                state["gates"][gate_id]["crowd"] += 1
            arrived.append(agent)

    # Remove arrived agents to keep state small
    state["crowd_agents"] = [a for a in state["crowd_agents"] if a["status"] == "moving"]

    state["tick"] += 1

    return {
        "tick": state["tick"],
        "active_agents": len(state["crowd_agents"]),
        "arrived_this_tick": len(arrived),
        "gates": list(state["gates"].values()),
        "agents": state["crowd_agents"][:100],  # cap at 100 for response size
    }


# ---------------------------------------------------------------------------
# Hospital Admin API (E2: Occupancy is SIMULATED — manually set, not live)
# ---------------------------------------------------------------------------

class OccupancyUpdate(BaseModel):
    current_occupancy: int
    total_beds: Optional[int] = None

@router.get("/hospitals")
def list_hospitals(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    from .models import Hospital
    hospitals = db.query(Hospital).all()
    return [
        {
            "id": h.id, "osm_id": h.osm_id, "name": h.name,
            "lat": h.lat, "lon": h.lon,
            "total_beds": h.total_beds,
            "current_occupancy": h.current_occupancy,
            "occupancy_pct": round(h.current_occupancy / h.total_beds * 100, 1) if h.total_beds else 0,
        }
        for h in hospitals
    ]

@router.patch("/hospitals/{hospital_id}/occupancy")
def set_hospital_occupancy(hospital_id: int, update: OccupancyUpdate,
                            db: Session = Depends(get_db),
                            current_user: User = Depends(get_current_user)):
    from .models import Hospital
    h = db.query(Hospital).filter(Hospital.id == hospital_id).first()
    if not h:
        raise HTTPException(404, "Hospital not found")
    h.current_occupancy = update.current_occupancy
    if update.total_beds is not None:
        h.total_beds = update.total_beds
    db.commit()
    db.refresh(h)
    return {
        "id": h.id, "name": h.name,
        "total_beds": h.total_beds,
        "current_occupancy": h.current_occupancy,
        "occupancy_pct": round(h.current_occupancy / h.total_beds * 100, 1) if h.total_beds else 0,
        "note": "Hospital occupancy is SIMULATED — manually set, not a live feed."
    }

