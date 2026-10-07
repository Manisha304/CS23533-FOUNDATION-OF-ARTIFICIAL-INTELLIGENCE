import networkx as nx
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
