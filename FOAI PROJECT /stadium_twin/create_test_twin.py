import sys
import os

sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models import Twin, User
from app.api_twin import create_twin
import json

def main():
    engine = create_engine('sqlite:///stadium_twin.db')
    Session = sessionmaker(bind=engine)
    session = Session()

    # find an admin user or just user 1
    current_user = session.query(User).first()
    
    # We will create a new twin for a place that has footways
    print("Creating new twin...")
    new_twin = create_twin(name="Test Twin", lat=13.0628, lon=80.2793, db=session, current_user=current_user)
    
    print(f"Twin created with ID {new_twin.id}")
    
    # analyze risk points
    from app.analysis.risk_points import analyze_risk_points
    results = analyze_risk_points(new_twin.graph_json, [])
    
    for r in results:
        if 'Narrow path' in r['reason']:
            print(f"Risk point {r['id']}: {r['reason']}")
            
if __name__ == "__main__":
    main()
