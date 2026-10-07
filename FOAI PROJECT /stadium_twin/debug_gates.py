import sys; sys.path.insert(0, '.')
from app.db import get_db
from app.models import Twin

db = next(get_db())
twins = db.query(Twin).all()
for t in twins:
    print(f"Twin {t.id}: {t.name}")
    g = t.graph_json
    if g:
        nodes = g.get("nodes", [])
        print(f"  Total nodes: {len(nodes)}")
        gate_nodes = []
        for n in nodes:
            nid = str(n.get("id",""))
            ntype = n.get("type","")
            label = n.get("label","")
            name = n.get("name","")
            if ntype in ("gate","entrance") or nid.startswith("manual_gate") or label or name:
                gate_nodes.append(n)
                print(f"  GATE: id={nid}, type={ntype}, label={label}, lat={n.get('lat')}, lon={n.get('lon')}")
        if not gate_nodes:
            print("  NO GATE NODES FOUND")
            # Show first 3 nodes as sample
            for n in nodes[:3]:
                print(f"  Sample node: {n}")
