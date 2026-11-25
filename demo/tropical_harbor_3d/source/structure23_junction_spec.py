"""Build audit gates for explicitly planned connections in the shared design.

Pure Python; no bpy or authoring imports. Run build_structure23_junctions with
the final design JSON. Closest-point projection only locates a declared parent
route; it never invents connectivity between nearby independent routes.
"""
import hashlib
import json
from pathlib import Path

import numpy as np


def build_structure23_junctions(design_path, output_path=None):
    design_path=Path(design_path);raw=design_path.read_bytes();design=json.loads(raw)
    routes={r["name"]:r for r in design["routes"]}
    plans=[
        ("lower_trade_market_link","lower_trade_main","end",[("lower_trade_main","end"),("lower_seabreeze_market_main","start")]),
        ("lower_market_tavern_link","lower_seabreeze_market_main","end",[("lower_seabreeze_market_main","end"),("lower_tavern_front","start")]),
        ("lower_tavern_diner_link","lower_tavern_front","end",[("lower_tavern_front","end"),("lower_diner_sari_main","start")]),
        ("trade_beach_access","lower_trade_pier_descent","start",[("lower_trade_main","through"),("lower_trade_pier_descent","start")]),
        ("central_beach_t_junction","lower_work_pier_descent","start",[("lower_seabreeze_market_main","through"),("lower_work_pier_descent","start")]),
        ("central_uphill_t_junction","south_lower_upper_ramp","start",[("lower_seabreeze_market_main","through"),("south_lower_upper_ramp","start")]),
        ("north_lower_ascent","north_lower_upper_ramp","start",[("lower_trade_main","through"),("north_lower_upper_ramp","start")]),
        ("north_upper_merge","north_lower_upper_ramp","end",[("upper_frontage_chapel_clinic_travel","through"),("north_lower_upper_ramp","end")]),
        ("south_upper_merge","south_lower_upper_ramp","end",[("upper_frontage_chapel_clinic_travel","through"),("south_lower_upper_ramp","end")]),
        ("school_public_route_fork","upper_public_side_route_to_school","start",[("upper_frontage_chapel_clinic_travel","through"),("upper_public_side_route_to_school","start")]),
    ]
    for short,parent in [("trade","lower_trade_main"),("seabreeze","lower_seabreeze_market_main"),
                         ("tavern","lower_tavern_front"),("diner","lower_diner_sari_main"),("sari","lower_diner_sari_main")]:
        child="lower_"+short+"_entry"
        plans.append((short+"_entry_fork",child,"start",[(parent,"through"),(child,"start")]))
    def hull(points):
        points=sorted(set(tuple(map(float,p)) for p in points))
        def cross(a,b,c):return (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])
        lower=[];upper=[]
        for p in points:
            while len(lower)>1 and cross(lower[-2],lower[-1],p)<=0:lower.pop()
            lower.append(p)
        for p in reversed(points):
            while len(upper)>1 and cross(upper[-2],upper[-1],p)<=0:upper.pop()
            upper.append(p)
        return lower[:-1]+upper[:-1]
    junctions=[]
    for name,anchor_name,anchor_end,members in plans:
        anchor=np.asarray(routes[anchor_name]["points"][0 if anchor_end=="start" else -1],float)
        gates=[];corners=[];connections=[]
        for route_name,relation in members:
            route=routes[route_name];points=np.asarray(route["points"],float)
            segment_lengths=np.linalg.norm(np.diff(points[:,:2],axis=0),axis=1)
            if np.any(segment_lengths<1e-8):raise ValueError("Duplicate route controls: "+route_name)
            stations=np.r_[0,np.cumsum(segment_lengths)]
            if relation=="through":
                candidate=[]
                for i,(a,b) in enumerate(zip(points,points[1:])):
                    d=b[:2]-a[:2];t=float(np.clip(np.dot(anchor[:2]-a[:2],d)/(d@d),0,1))
                    candidate.append((float(np.linalg.norm(a[:2]+t*d-anchor[:2])),stations[i]+t*segment_lengths[i]))
                distance,s=min(candidate)
                if distance>.75:raise ValueError("Declared route is too far from junction: "+name+" / "+route_name)
                values=[max(0,s-.45),min(stations[-1],s+.45)]
                connections.append({"route":route_name,"relation":relation,"anchor_offset_m":distance})
            else:
                i=0 if relation=="start" else -1
                distance=float(np.linalg.norm(points[i,:2]-anchor[:2]))
                if distance>.75:raise ValueError("Declared endpoint is too far from junction: "+name+" / "+route_name)
                values=[min(stations[-1],.45) if relation=="start" else max(0,stations[-1]-.45)]
                connections.append({"route":route_name,"relation":relation,"anchor_offset_m":distance})
            for s in values:
                i=min(len(points)-2,int(np.searchsorted(stations,s,side="right")-1));i=max(i,0)
                t=float((s-stations[i])/segment_lengths[i]);p=points[i]*(1-t)+points[i+1]*t
                direction=(points[i+1,:2]-points[i,:2])/segment_lengths[i];side=np.array([-direction[1],direction[0]])
                width=float(route["halfwidth"])
                gates.append({"route":route_name,"segment_index":i,"at":t})
                for sign in (-1,1):
                    corner=p[:2]+side*width*sign
                    for angle in np.linspace(0,np.pi*2,8,endpoint=False):corners.append(corner+.14*np.array([np.cos(angle),np.sin(angle)]))
        junctions.append({"name":name,"polygon_xz":hull(corners),"grid_step_m":.12,"gates":gates,
            "limits":{"face_slope_deg":30,"gate_inside_fraction":1.0,"gate_target_height_error_m":.15},
            "declared_connections":connections,"anchor_xzh":anchor.tolist()})
    report={"design_sha256":hashlib.sha256(raw).hexdigest(),"junctions":junctions,
        "note":"Declared junctions include staggered beach/uphill T connections. A 30-degree face limit accommodates the combined 12-degree cross/28-degree longitudinal route components; gate errors retain the .15m route limit. Rebuild after design control changes."}
    path=Path(output_path) if output_path else design_path.with_name("junction_spec.json")
    path.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf8")
    return report
