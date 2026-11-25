"""Read-only geographic/material diagnosis of the final road23 terrain.

This script does not import Blender, launch Godot, or change an asset.  It
compares the whole visible road footprint with actual triangle planes.  Angle
thresholds locate candidate problems; they are not visual acceptance criteria.
"""
from __future__ import annotations

from collections import defaultdict
import hashlib
import json
from pathlib import Path

import numpy as np

from audit_road23_contacts import sample, glb_geometry
from audit_ground23_runtime import triangle_signature

ROOT = Path(__file__).resolve().parents[2]
LOG = ROOT / "demo/tropical_harbor_3d/captures/road_contacts_20261123"
OUT = Path(__file__).with_suffix(".json")


class Surface:
    def __init__(self, points, triangles):
        self.tri = points[triangles].astype(float)
        self.xz = self.tri[:, :, (0, 2)]
        a, b = self.tri[:, 1] - self.tri[:, 0], self.tri[:, 2] - self.tri[:, 0]
        normal = np.cross(a, b)
        self.gradient = -normal[:, (0, 2)] / normal[:, 1, None]
        self.slope = np.degrees(np.arctan(np.linalg.norm(self.gradient, axis=1)))
        self.bucket_size = .75
        self.buckets = defaultdict(list)
        lo = np.floor(self.xz.min(1) / self.bucket_size).astype(int)
        hi = np.floor(self.xz.max(1) / self.bucket_size).astype(int)
        for i in range(len(triangles)):
            if hi[i, 0] < 7 or lo[i, 0] > 40 or hi[i, 1] < -12 or lo[i, 1] > 90:
                continue
            for x in range(lo[i, 0], hi[i, 0] + 1):
                for z in range(lo[i, 1], hi[i, 1] + 1):
                    self.buckets[x, z].append(i)
        self.buckets = {key: np.asarray(value) for key, value in self.buckets.items()}

    def query(self, xz):
        xz = np.asarray(xz, float)
        keys = np.floor(xz / self.bucket_size).astype(int)
        groups = defaultdict(list)
        for i, key in enumerate(keys): groups[tuple(key)].append(i)
        ids = np.full(len(xz), -1, int)
        height = np.full(len(xz), np.nan)
        for key, members in groups.items():
            members = np.asarray(members)
            candidates = self.buckets.get(key)
            if candidates is None: continue
            t = self.xz[candidates]
            q = xz[members]
            dx = q[:, 0, None] - t[None, :, 2, 0]
            dz = q[:, 1, None] - t[None, :, 2, 1]
            den = ((t[:, 1, 1]-t[:, 2, 1])*(t[:, 0, 0]-t[:, 2, 0])
                   +(t[:, 2, 0]-t[:, 1, 0])*(t[:, 0, 1]-t[:, 2, 1]))
            u = ((t[:, 1, 1]-t[:, 2, 1])*dx+(t[:, 2, 0]-t[:, 1, 0])*dz)/den
            v = ((t[:, 2, 1]-t[:, 0, 1])*dx+(t[:, 0, 0]-t[:, 2, 0])*dz)/den
            w = 1-u-v
            h = (u*self.tri[candidates, 0, 1]+v*self.tri[candidates, 1, 1]
                 +w*self.tri[candidates, 2, 1])
            h[(u < -1e-6)|(v < -1e-6)|(w < -1e-6)] = -np.inf
            best = h.argmax(1)
            good = np.isfinite(h[np.arange(len(members)), best])
            height[members[good]] = h[np.arange(len(members))[good], best[good]]
            ids[members[good]] = candidates[best[good]]
        if (ids < 0).any():
            raise RuntimeError(f"{(ids < 0).sum()} points were not on the terrain")
        return height, self.slope[ids], self.gradient[ids], ids


def rounded(v):
    if isinstance(v, np.ndarray): return np.round(v, 6).tolist()
    return round(float(v), 6)


def stats(values):
    values = np.asarray(values)
    if not values.size: return None
    return dict(zip(("min", "median", "p95", "max"), rounded(np.quantile(values, [0, .5, .95, 1]))))


def main():
    with np.load(LOG / "grade_before_after.npz") as raw:
        points, triangles = raw["positions"].copy(), raw["triangles"].copy()
    points = points[:, [0, 2, 1]]; points[:, 2] *= -1
    exported, _, _ = glb_geometry("terrain.glb")
    same_export = bool(np.array_equal(triangle_signature(exported), triangle_signature(points[triangles])))
    assert same_export
    surface = Surface(points, triangles)
    with np.load(LOG / "baseline.npz") as raw:
        original_triangle_roles = raw["colors"].reshape(-1, 3, 4).mean(1)
    with np.load(LOG / "land_data.npz") as raw:
        land, smooth_normal, scope = (raw[k].copy() for k in ("land", "normal", "scope"))
    routes = json.loads((LOG / "occupancy.json").read_text(encoding="utf-8"))["routes"]

    def facts(q):
        h, sl, grad, tri_id = surface.query(q)
        weights = sample(land, q)
        weights = np.column_stack((weights, np.maximum(0, 1-weights.sum(1))))
        return dict(height=h, slope=sl, gradient=grad, triangle=tri_id,
                    weights=weights, leading=weights.argmax(1),
                    source_roles=original_triangle_roles[tri_id],
                    shading_slope=np.degrees(np.arccos(np.clip(sample(smooth_normal, q), -1, 1))),
                    scope=sample(scope, q))

    def hotspots(q, data, mask, score, count=6, separation=.65):
        result=[]
        for i in np.flatnonzero(mask)[np.argsort(score[mask])[::-1]]:
            if any(np.linalg.norm(q[i]-np.asarray(row["xz"])) < separation for row in result): continue
            result.append({"xz": rounded(q[i]), "height_m": rounded(data["height"][i]),
                           "face_slope_deg": rounded(data["slope"][i]),
                           "occupancy_interpolated_normal_y_angle_deg": rounded(data["shading_slope"][i]),
                           "weights_grass_rock_path_soil_sand": rounded(data["weights"][i]),
                           "source_triangle_mean_grass_rock_path_soil": rounded(data["source_roles"][i]),
                           "road23_scope": rounded(data["scope"][i]),
                           "triangle": int(data["triangle"][i])})
            if len(result) >= count: break
        return result

    route_reports=[]
    for route in routes:
        centers=[]; tangent=[]; distances=[]; distance=0
        for a, b in zip(route["points"], route["points"][1:]):
            a,b=np.asarray(a),np.asarray(b); vec=b-a; length=np.linalg.norm(vec)
            n=max(1,int(np.ceil(length/.12)))
            for i in range(n):
                centers.append(a+vec*i/n);tangent.append(vec/length);distances.append(distance+length*i/n)
            distance+=length
        centers=np.asarray(centers); tangent=np.asarray(tangent)
        lateral=np.column_stack((-tangent[:,1],tangent[:,0]))
        halfwidth=max(route["halfwidth"], .70 if route["name"]=="clinic_ramp" else 0)
        fractions=np.linspace(-1.25,1.25,21)
        q=(centers[:,None,:]+lateral[:,None,:]*halfwidth*fractions[None,:,None]).reshape(-1,2)
        data=facts(q); path=data["leading"]==2
        cross=np.degrees(np.arctan(abs(np.sum(data["gradient"]*np.repeat(lateral,21,axis=0),axis=1))))
        longitudinal=np.degrees(np.arctan(abs(np.sum(data["gradient"]*np.repeat(tangent,21,axis=0),axis=1))))
        data["cross_slope"] = cross
        data["longitudinal_slope"] = longitudinal
        mid=data["weights"][:,2].reshape(-1,21)[:,10]
        h=data["height"].reshape(-1,21)
        route_reports.append({"name":route["name"],"diagnostic_envelope_halfwidth_m":halfwidth*1.25,
            "length_m":rounded(distance),"samples":len(q),"path_dominant_samples":int(path.sum()),
            "path_dominant_fraction":rounded(path.mean()),"path_face_slope_deg":stats(data["slope"][path]),
            "path_cross_slope_deg":stats(cross[path]),"path_longitudinal_slope_deg":stats(longitudinal[path]),
            "path_samples_face_slope_over_30_deg":int((path&(data["slope"]>30)).sum()),
            "path_samples_face_slope_over_45_deg":int((path&(data["slope"]>45)).sum()),
            "nominal_width_side_height_difference_m":stats(abs(h[:,2]-h[:,-3])),
            "center_path_weight":stats(mid),"scope_range":stats(data["scope"]),
            "steep_path_locations":hotspots(q,data,path,data["slope"]),
            "center_path_under_050_locations":hotspots(centers,{k:v.reshape((-1,21)+v.shape[1:])[:,10] for k,v in data.items()},mid<.5,1-mid,3)})

    regions={"trade":(10,15.8,9,20.5),"grill":(10,15.4,20.5,28),
             "clinic":(20.5,25.6,29,34.2),"diner":(10.8,14.8,45,53.5),
             "sari":(10.5,15.5,53.5,62.5),"school":(18,24.5,53.5,65)}
    region_reports=[]
    for name,(x0,x1,z0,z1) in regions.items():
        x,z=np.meshgrid(np.arange(x0+.05,x1,.1),np.arange(z0+.05,z1,.1))
        q=np.column_stack((x.ravel(),z.ravel()));d=facts(q)
        path=d["leading"]==2; soil=d["leading"]==3;sand=d["leading"]==4;rock=d["leading"]==1
        region_reports.append({"name":name,"bounds_xz":[x0,z0,x1,z1],"grid_interval_m":.1,
            "path_area_approx_m2":rounded(path.sum()*.01),"path_face_slope_deg":stats(d["slope"][path]),
            "path_area_over_30_deg_m2":rounded((path&(d["slope"]>30)).sum()*.01),
            "path_area_over_45_deg_m2":rounded((path&(d["slope"]>45)).sum()*.01),
            "sand_height_m":stats(d["height"][sand]),"sand_face_slope_deg":stats(d["slope"][sand]),
            "soil_face_slope_deg":stats(d["slope"][soil]),"rock_face_slope_deg":stats(d["slope"][rock]),
            "road23_scope_range":stats(d["scope"]),
            "steep_path_locations":hotspots(q,d,path,d["slope"],8),
            "steep_sand_locations":hotspots(q,d,sand,d["slope"],5)})

    cross_sections=[]
    for name,z,x0,x1 in [("trade_sand_mouth",11.5,10.8,15),("trade_inner_cove",13,10.8,15.5),
                        ("trade_grass_shoulder",16.7,11,15.5),("grill_apron",24,10.5,15.5),
                        ("diner_apron",49.3,10,15),("sari_shoulder",56,10,15.5),
                        ("school_rock",58.5,17,24)]:
        q=np.column_stack((np.arange(x0,x1+.01,.25),np.full(len(np.arange(x0,x1+.01,.25)),z)))
        d=facts(q)
        cross_sections.append({"name":name,"z":z,"samples":[{"x":rounded(q[i,0]),"h":rounded(d["height"][i]),"slope":rounded(d["slope"][i]),"weights":rounded(d["weights"][i])} for i in range(len(q))]})

    selected=[]
    for route_name, xz in [("clinic_ramp",[21.95,30.55]),("clinic_ramp",[23.55,32.15]),
                           ("trading_lower_lane",[13.75,15.45]),("trading_lower_lane",[13.75,16.7]),
                           ("lower_lane",[12.55,21.95]),("lower_lane",[12.5,24]),
                           ("diner_sari_shared_lane",[13.49,53.04]),("diner_sari_shared_lane",[13.75,52.55])]:
        route=next(r for r in routes if r["name"]==route_name)
        a=np.asarray(route["points"][:-1]);b=np.asarray(route["points"][1:]);vec=b-a
        fraction=np.clip(((np.asarray(xz)-a)*vec).sum(1)/(vec*vec).sum(1),0,1)
        nearest=a+vec*fraction[:,None];segment=int(np.argmin(np.linalg.norm(nearest-np.asarray(xz),axis=1)))
        tan=vec[segment]/np.linalg.norm(vec[segment]);side=np.array([-tan[1],tan[0]])
        halfwidth=.70 if route_name=="clinic_ramp" else (.53 if route_name=="lower_lane" else route["halfwidth"])
        q=np.asarray([xz]); d=facts(q)
        edges=np.asarray([nearest[segment]-side*halfwidth,nearest[segment]+side*halfwidth]);ed=facts(edges)
        record=hotspots(q,d,np.ones(1,bool),d["slope"],1)[0]
        record.update(route=route_name,nearest_route_xz=rounded(nearest[segment]),
            local_cross_slope_deg=rounded(np.degrees(np.arctan(abs(d["gradient"][0]@side)))),
            local_longitudinal_slope_deg=rounded(np.degrees(np.arctan(abs(d["gradient"][0]@tan)))),
            nominal_width_m=halfwidth*2,nominal_left_right_xz=rounded(edges),
            nominal_left_right_height_m=rounded(ed["height"]),
            nominal_left_right_path_weights=rounded(ed["weights"][:,2]))
        selected.append(record)

    bend_radii=[]
    for route in routes:
        q=np.asarray(route["points"]); a=q[:-2];b=q[1:-1];c=q[2:]
        ab=b-a;bc=c-b;ac=c-a
        area2=abs(ab[:,0]*ac[:,1]-ab[:,1]*ac[:,0])
        radius=np.linalg.norm(ab,axis=1)*np.linalg.norm(bc,axis=1)*np.linalg.norm(ac,axis=1)/np.maximum(2*area2,1e-12)
        valid=np.flatnonzero((area2>1e-6)&(radius<2))
        if valid.size:
            i=valid[np.argmin(radius[valid])]
            bend_radii.append({"route":route["name"],"three_point_radius_m":rounded(radius[i]),"at_xz":rounded(b[i]),
                "note":"A local three-control-point curvature indicator. These are distance-band centerlines, not a promise that the physical ground was shaped to this bend."})

    report={"purpose":"Locate actual geometry/material disagreements, not accept road centerline connectivity",
        "visual_acceptance":False,"assets_modified":False,"game_or_blender_launched":False,
        "grade_matches_exported_terrain":same_export,
        "terrain_sha256":hashlib.sha256((ROOT/'demo/tropical_harbor_3d/assets/reference/terrain.glb').read_bytes()).hexdigest(),
        "method":"Exact barycentric triangle height/plane gradient. Sample final NPZ occupancy bilinearly. Path footprint means largest of grass/rock/path/soil/sand before shader edge sharpening. The 30/45 degree bins only locate candidate visual problems, not legal/walkability/visual pass criteria.",
        "route_envelope_note":"21 lateral samples span +/-1.25 nominal route halfwidth, at <=.12m stations; clinic uses .70m override. Scope outside the 3 road23 rectangles still uses G23 old width fields. Region scans measure actual path-leading area independently of nominal routes.",
        "regions":region_reports,"routes":route_reports,"cross_sections":cross_sections,
        "selected_visible_locations":selected,"tight_control_bends":bend_radii,
        "limitations":["No occlusion culling: region scans include ground under buildings; use screenshot and coordinates before treating a location as visibly exposed.","Shader grass-edge perturbation and texture bump do not change triangle heights; measured weights are upstream occupancy, not reconstructed screenshot colors.","No conclusion that every steep path point is wrong: steps, short banks and actual visible route purpose require visual interpretation."]}
    OUT.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps({"output":str(OUT),"regions":[{k:r[k] for k in ("name","path_area_approx_m2","path_area_over_30_deg_m2","path_area_over_45_deg_m2")} for r in region_reports]},ensure_ascii=False))


if __name__=="__main__":main()
