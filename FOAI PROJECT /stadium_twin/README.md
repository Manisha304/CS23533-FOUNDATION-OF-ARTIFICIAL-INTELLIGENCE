# StadiumTwin — MA Chidambaram Stadium (Chepauk) Crowd Management Digital Twin

> **College AI Course Project** | Classical Artificial Intelligence, Real-Time Pygame Crowd Simulation & Dijkstra Pathfinding (No ML/DL Dependencies)

**StadiumTwin** is a classical AI digital twin simulation of **MA Chidambaram Stadium (Chepauk), Chennai**. The system features a realistic top-down 2D Pygame rendering engine with 300–500 live moving crowd spectator sprites, underlying NetworkX spatial pathfinding graph, Dijkstra search with Min-Heap priority queues, Max-Heap emergency hazard handling, and a Rule-Based Meta-Coordinator.

---

## Chepauk Stadium Features & Map Layout

The simulation models real spatial zones of Chepauk Stadium mapped to a 1000x800 canvas:
- **Lush Green Cricket Pitch**: Center ground with white crease lines.
- **5 Seating Stands**:
  - `Anna Pavilion` (North Stand)
  - `Pavilion Stand` (South Stand)
  - `P4 Upper Stand` (East Stand)
  - `C & D Stand` (West Stand)
  - `MA Chidambaram Grandstand` (Main Stand)
- **4 Perimeter Entrances**: `Gate 1 (Wallajah Rd)`, `Gate 2 (Bells Rd)`, `Gate 3 (Pattabiram Rd)`, `Gate 4 (Vattaram / Victoria Hostel Rd)`.
- **Exterior Parking Zone**: West parking lot with car shapes.
- **Emergency Safety Exit**: North-East exit marked with red/white hazard stripes.

---

## Classical AI Algorithms Used

| Component | Classical AI Concept | Viva Explanation |
| :--- | :--- | :--- |
| **`layout.py`** | **Weighted Graph $G = (V, E)$ in 2D Euclidean Space** | 13 spatial nodes (Gates, Stands, Concourses, Exits) mapped to exact pixel coordinates. Edges represent physical walkway travel distances. |
| **`crowd.py`** | **Linear Interpolation & Sprite Movement** | 300–500 `Person` sprites moving smoothly along path waypoints. Dynamically reassigns paths mid-motion when Coordinator changes routing (`reassign_paths`). |
| **`crowd_agent.py`** | **Threshold Rule Classification** | Calculates node load ratios ($\text{Load} / \text{Capacity}$). Categorizes nodes into `OK` ($\le 70\%$), `WARNING` ($> 70\%$), `OVERLOADED` ($> 90\%$), or `BLOCKED`. |
| **`route_agent.py`** | **Dijkstra Search with Min-Heap (`heapq`)** | Manual Dijkstra implementation with load-penalty tie-breaking to prefer less-dense pathways. Cross-checked with `networkx.dijkstra_path`. |
| **`safety_agent.py`** | **Max-Heap Priority Queue (`heapq`)** | Orders active hazards by severity ($1 = \text{Low}$ to $5 = \text{Critical}$). Ensures critical fires preempt all routine routing. |
| **`coordinator.py`** | **Hierarchical Rule Expert System** | 1. *Safety Emergency* $\rightarrow$ Evacuation Directive to `Emergency_Exit`.<br>2. *Overload/Blockage* $\rightarrow$ Route crowd to least-loaded valid gates.<br>3. *Normal* $\rightarrow$ System remains in Monitoring Mode. |

---

## 🚀 Setup & Execution Guide

### Prerequisites
- Python 3.10+
- `pygame` & `networkx`

### Installation
```bash
pip install -r requirements.txt
```

### Running the Pygame Simulation
```bash
python main.py
```

### Keyboard Hotkeys & Controls
- `[1]`: Scenario 1 — Gate 1 (Wallajah Rd) Closed (Congestion Reroute)
- `[2]`: Scenario 2 — Emergency at Anna Pavilion (Fire Evacuation to Emergency Exit)
- `[3]`: Scenario 3 — High Spectator Inflow (30,000 Fan Arrival Stress Test)
- `[4]`: Scenario 4 — Combo Crisis (Blocked Gate + Fire Hazard + High Inflow)
- `[R]`: Reset to Baseline Normal Flow
- `[ESC] / [Q]`: Exit Simulation

---

## 🎓 Viva Voce Explanation Guide

1. **How do sprites move smoothly on screen?**
   - *"Each `Person` sprite has a target path (list of node IDs). In `crowd.py`, `update(dt)` uses direction vectors and velocity scaling to linearly interpolate sprite position toward target waypoints."*
2. **How does the crowd bend toward a new gate live mid-simulation?**
   - *"When the Coordinator issues a new Action Plan, it calls `CrowdManager.reassign_paths(...)`. Active `Person` sprites update their target waypoint list immediately, causing them to physically bend and change direction on screen."*
3. **Why Dijkstra with `heapq`?**
   - *"We implemented Dijkstra manually using Python's `heapq` min-heap priority queue ($O((V+E)\log V)$). Edge weights include dynamic crowd load penalties so ties favor less-congested walkways."*
