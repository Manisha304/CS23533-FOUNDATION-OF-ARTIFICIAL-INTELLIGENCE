import sys
import os

# Ensure we can import from app
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models import Twin
from app.config import settings

def main():
    engine = create_engine('sqlite:///stadium_twin.db')
    Session = sessionmaker(bind=engine)
    session = Session()

    twin = session.query(Twin).filter(Twin.id == 11).first()
    if not twin:
        print("Twin not found")
        return

    print(f'Evaluating Twin: {twin.name}')
    
    # We will just iterate over edges and simulate the logic to see default vs measured
    nodes_raw = twin.graph_json.get("nodes", [])
    links_raw = twin.graph_json.get("links", [])
    
    node_map = {str(n["id"]): n for n in nodes_raw}
    
    hw_counts = {}
    for link in links_raw:
        tags = link.get("tags", {})
        hw = tags.get("highway", "none")
        hw_counts[hw] = hw_counts.get(hw, 0) + 1
        
    print(f"Highway types found: {hw_counts}")

if __name__ == "__main__":
    main()
