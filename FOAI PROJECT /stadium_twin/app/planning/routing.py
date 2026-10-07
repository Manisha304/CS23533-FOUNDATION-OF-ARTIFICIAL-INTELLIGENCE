import heapq
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
