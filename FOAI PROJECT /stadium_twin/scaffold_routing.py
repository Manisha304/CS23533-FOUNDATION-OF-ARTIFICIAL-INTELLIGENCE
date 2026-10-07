import os

base_dir = r'c:\Users\manis\OneDrive\Desktop\new foai\stadium_twin'

routing_py = '''import heapq
import math
import networkx as nx
from typing import List, Tuple, Optional

def haversine(lat1, lon1, lat2, lon2):
    R = 6371000  # Earth radius in meters
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    a = math.sin(delta_phi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

def manual_dijkstra(G: nx.Graph, start: str, goal: str) -> Tuple[Optional[List[str]], float]:
    """Classical Dijkstra implementation using heapq."""
    queue = []
    heapq.heappush(queue, (0.0, start))
    came_from = {start: None}
    cost_so_far = {start: 0.0}
    
    while queue:
        current_cost, current = heapq.heappop(queue)
        
        if current == goal:
            break
            
        for neighbor in G.neighbors(current):
            if G.nodes[neighbor].get('blocked', False):
                continue
                
            edge_data = G.get_edge_data(current, neighbor)
            weight = edge_data.get('length', 1.0)
            multiplier = edge_data.get('congestion_multiplier', 1.0)
            
            new_cost = cost_so_far[current] + (weight * multiplier)
            
            if neighbor not in cost_so_far or new_cost < cost_so_far[neighbor]:
                cost_so_far[neighbor] = new_cost
                heapq.heappush(queue, (new_cost, neighbor))
                came_from[neighbor] = current
                
    if goal not in came_from:
        return None, float('inf')
        
    path = []
    curr = goal
    while curr is not None:
        path.append(curr)
        curr = came_from[curr]
    path.reverse()
    return path, cost_so_far[goal]

def manual_astar(G: nx.Graph, start: str, goal: str) -> Tuple[Optional[List[str]], float]:
    """Classical A* implementation with Haversine heuristic."""
    queue = []
    heapq.heappush(queue, (0.0, start))
    came_from = {start: None}
    cost_so_far = {start: 0.0}
    
    goal_node = G.nodes.get(goal)
    if not goal_node:
        return None, float('inf')
        
    while queue:
        current_priority, current = heapq.heappop(queue)
        
        if current == goal:
            break
            
        for neighbor in G.neighbors(current):
            if G.nodes[neighbor].get('blocked', False):
                continue
                
            edge_data = G.get_edge_data(current, neighbor)
            weight = edge_data.get('length', 1.0)
            multiplier = edge_data.get('congestion_multiplier', 1.0)
            
            new_cost = cost_so_far[current] + (weight * multiplier)
            
            if neighbor not in cost_so_far or new_cost < cost_so_far[neighbor]:
                cost_so_far[neighbor] = new_cost
                
                # Heuristic
                n_node = G.nodes[neighbor]
                h = haversine(n_node['lat'], n_node['lon'], goal_node['lat'], goal_node['lon'])
                
                priority = new_cost + h
                heapq.heappush(queue, (priority, neighbor))
                came_from[neighbor] = current
                
    if goal not in came_from:
        return None, float('inf')
        
    path = []
    curr = goal
    while curr is not None:
        path.append(curr)
        curr = came_from[curr]
    path.reverse()
    return path, cost_so_far[goal]
'''

test_routing_py = '''import networkx as nx
import pytest
from app.planning.routing import manual_dijkstra, manual_astar

@pytest.fixture
def sample_graph():
    G = nx.Graph()
    G.add_node("A", lat=0.0, lon=0.0)
    G.add_node("B", lat=0.0, lon=0.01)
    G.add_node("C", lat=0.01, lon=0.01)
    G.add_node("D", lat=0.01, lon=0.0)
    
    G.add_edge("A", "B", length=1113.2)
    G.add_edge("B", "C", length=1113.2)
    G.add_edge("A", "D", length=1113.2)
    G.add_edge("D", "C", length=1113.2)
    G.add_edge("A", "C", length=1574.0) # Diagonal
    return G

def test_dijkstra_vs_networkx(sample_graph):
    manual_path, manual_cost = manual_dijkstra(sample_graph, "A", "C")
    nx_path = nx.dijkstra_path(sample_graph, "A", "C", weight="length")
    nx_cost = nx.dijkstra_path_length(sample_graph, "A", "C", weight="length")
    
    assert manual_path == nx_path
    assert round(manual_cost, 2) == round(nx_cost, 2)

def test_astar_vs_networkx(sample_graph):
    manual_path, manual_cost = manual_astar(sample_graph, "A", "C")
    # NetworkX A* doesn't easily return cost without recreating, but path should match
    nx_path = nx.astar_path(sample_graph, "A", "C", weight="length")
    
    assert manual_path == nx_path
    
def test_blocked_nodes(sample_graph):
    # Block diagonal and path via B
    sample_graph.nodes["B"]["blocked"] = True
    sample_graph.remove_edge("A", "C") # pretend diagonal doesn't exist
    
    manual_path, manual_cost = manual_dijkstra(sample_graph, "A", "C")
    # Must route via D
    assert manual_path == ["A", "D", "C"]
'''

files = {
    'app/planning/__init__.py': '',
    'app/planning/routing.py': routing_py,
    'tests/test_routing.py': test_routing_py
}

for path, content in files.items():
    full_path = os.path.join(base_dir, path.replace('/', os.sep))
    with open(full_path, 'w', encoding='utf-8') as f:
        f.write(content)

print("Routing and tests scaffolded.")
