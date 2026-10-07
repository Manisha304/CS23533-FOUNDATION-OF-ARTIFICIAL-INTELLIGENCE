import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models import Twin
from app.analysis.risk_points import analyze_risk_points
import json

engine = create_engine('sqlite:///stadium_twin.db')
Session = sessionmaker(bind=engine)
session = Session()

twins = session.query(Twin).all()
for twin in twins:
    print(f"Twin: {twin.name} (ID: {twin.id})")
    # run risk points
    risk_results = analyze_risk_points(twin.graph_json, [])
    # count how many have 'estimated (default)', 'OSM-tagged', 'measured from satellite imagery'
    osm = 0
    estimated = 0
    measured = 0
    for r in risk_results:
        reason = r['reason']
        if "OSM-tagged" in reason:
            osm += 1
        if "estimated (default)" in reason:
            estimated += 1
        if "measured from satellite imagery" in reason:
            measured += 1
    
    print(f"  OSM-tagged: {osm}")
    print(f"  Estimated: {estimated}")
    print(f"  Measured: {measured}")
    print("-" * 40)
