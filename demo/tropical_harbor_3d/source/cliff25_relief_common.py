"""Finite, authored mid-scale fractures on cliff25's established rock masses.

Pure numerical proposal only. Never opens Blender or writes runtime assets.
The (Z,H) polygons describe the actual exposed rock face in metres; unequal
signed cuts are deliberately sparse, not a tessellated tile or random noise.
"""
import numpy as np
from structure23_common import polygon_distance
from cliff25_geometry_common import smoothstep, MASSES

# Each cut has a different endpoint, height and aspect. Core relief is a plane,
# with short straight bevels at its boundary. Negative pieces are recesses;
# positive pieces expose a short ledge above their lower diagonal edge.
RELIEF_FEATURES=[
    {'name':'sea_short_diagonal_ledge','mass':0,'amplitude':.160,'bevel':.13,'tilt':(-.10,.17),
     'polygon':[(22.90,2.55),(23.40,2.35),(24.20,2.90),(24.35,3.30),(23.70,3.60),(23.15,3.25)]},
    {'name':'sea_turn_recess','mass':0,'amplitude':-.135,'bevel':.11,'tilt':(.16,-.13),
     'polygon':[(24.80,2.70),(25.45,2.72),(26.35,3.25),(26.30,3.90),(25.55,3.95),(24.95,3.35)]},
    {'name':'clinic_north_ledge','mass':1,'amplitude':.175,'bevel':.12,'tilt':(.06,.18),
     'polygon':[(27.54,2.63),(28.22,2.47),(28.88,2.84),(28.81,3.30),(28.33,3.52),(27.70,3.15)]},
    {'name':'clinic_mid_return_recess','mass':1,'amplitude':-.155,'bevel':.12,'tilt':(-.08,.14),
     'polygon':[(28.72,3.18),(29.18,2.94),(29.79,3.32),(29.65,3.92),(29.15,4.04),(28.84,3.67)]},
    {'name':'clinic_south_low_wedge','mass':1,'amplitude':.155,'bevel':.12,'tilt':(.13,-.11),
     'polygon':[(30.22,2.00),(30.75,1.92),(31.52,2.53),(31.48,2.92),(30.97,3.15),(30.57,2.65)]},
    {'name':'clinic_terminal_facet','mass':1,'amplitude':-.125,'bevel':.13,'tilt':(.08,.16),
     'polygon':[(31.48,3.35),(31.94,3.10),(32.58,3.43),(32.57,3.81),(32.10,3.96),(31.64,3.75)]},
    {'name':'tavern_north_shoulder_chip','mass':2,'amplitude':-.130,'bevel':.12,'tilt':(-.14,.10),
     'polygon':[(38.50,2.37),(39.03,2.16),(39.72,2.64),(39.55,3.08),(38.88,3.20),(38.62,2.82)]},
    {'name':'tavern_mid_broken_ledge','mass':2,'amplitude':.170,'bevel':.13,'tilt':(.14,.06),
     'polygon':[(40.38,2.72),(40.92,2.47),(41.70,3.02),(41.69,3.52),(41.14,3.75),(40.62,3.31)]},
    {'name':'tavern_rear_visible_recess','mass':2,'amplitude':-.180,'bevel':.12,'tilt':(-.09,.16),
     'polygon':[(42.18,3.00),(42.64,2.69),(43.28,3.05),(43.57,3.72),(43.01,3.95),(42.37,3.57)]},
    {'name':'tavern_south_short_wedge','mass':2,'amplitude':.145,'bevel':.13,'tilt':(.10,-.16),
     'polygon':[(43.07,2.18),(43.58,1.99),(44.14,2.43),(44.21,2.78),(43.72,3.04),(43.28,2.67)]},
]

def midscale_relief(positions, mass_weights, freedom, locked):
    """Return bounded added H relief plus auditable per-feature components."""
    p=np.asarray(positions,float);x,z,h=p[:,0],-p[:,1],p[:,2]
    masks=[];components=[];reports=[]
    for f in RELIEF_FEATURES:
        points=np.array(f['polygon'],float);i=f['mass'];mass=MASSES[i]
        near=(z>points[:,0].min()-.05)&(z<points[:,0].max()+.05)&(h>points[:,1].min()-.05)&(h<points[:,1].max()+.05)
        d=np.full(len(p),1e6);d[near]=polygon_distance(z[near],h[near],points)
        # Piecewise-linear bevels preserve a real small plane rather than a
        # smooth ellipsoidal lump. The core is a gently tilted planar offset.
        bevel=max(f['bevel'],abs(f['amplitude'])*1.5)
        m=np.clip(-d/bevel,0,1)
        centre=points.mean(0);extent=np.ptp(points,axis=0)
        plane=1+f['tilt'][0]*(z-centre[0])/max(extent[0],.1)+f['tilt'][1]*(h-centre[1])/max(extent[1],.1)
        plane=np.clip(plane,.80,1.10)
        rows=mass['sections'];st=np.array([s[0] for s in rows]);j=np.clip(np.searchsorted(st,z,side='right')-1,0,len(rows)-2)
        u=smoothstep(0,1,(z-st[j])/(st[j+1]-st[j]));lo=np.zeros(len(p));hi=lo.copy()
        for k in range(len(rows)-1):
            take=j==k;a,b=rows[k][1],rows[k+1][1]
            lo[take]=(1-u[take])*a[0][1]+u[take]*b[0][1]
            hi[take]=(1-u[take])*a[-1][1]+u[take]*b[-1][1]
        # Feet and upper grass caps are not detail surfaces. Full prior lock
        # and fade fields remain in force; the new crate is outside all groups.
        facegate=smoothstep(lo+.35,lo+.65,h)*(1-smoothstep(hi-.30,hi-.12,h))
        m*=np.clip(mass_weights[i],0,1)*freedom*facegate
        m[locked]=0
        component=f['amplitude']*m*plane
        masks.append(m);components.append(component)
        hit=np.abs(component)>1e-6
        reports.append({'name':f['name'],'mass':mass['name'],'feature_chart_polygon_zh_m':f['polygon'],
                        'requested_amplitude_m':f['amplitude'],'bevel_m':bevel,
                        'changed_vertices':int(hit.sum()),
                        'max_raise_m':float(component.max(initial=0)),
                        'max_lower_m':float(-component.min(initial=0)),
                        'vertices_over_4cm':int((np.abs(component)>.04).sum())})
    parts=np.stack(components);delta=parts.sum(0)
    # Adjacent facets may touch; the limit prevents a superposed 30cm lump.
    delta=np.clip(delta,-.20,.20);delta[locked]=0
    return delta,reports,parts
