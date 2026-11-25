"""Finish full-width ramp grades in the owned GUI; repeatable from grade.npz.

Project actual triangle gradients, not audit samples. Keep the approved route
footprints, stair/floor protection, sea boundary and source topology intact.
"""
import bpy, json, sys, importlib
from pathlib import Path
import numpy as np
ROOT=Path(bpy.data.filepath).parent.parent
LOG=ROOT/'captures/terrain_structure_20261123'
sys.path.insert(0,str(ROOT/'source'))
import structure23_common as util
importlib.reload(util)
spec=json.loads((LOG/'design.json').read_text(encoding='utf8'))
base=np.load(LOG/'baseline.npz'); original=base['positions'].astype(float)
graded=np.load(LOG/'grade.npz'); p=graded['positions'].astype(float); tri=graded['triangles']
q=p[:,:2].copy(); q[:,1]*=-1
qt=q[tri]
inverse=np.linalg.inv(np.stack([qt[:,1]-qt[:,0],qt[:,2]-qt[:,0]],axis=1))
coeff=np.zeros((len(tri),2,3))
coeff[:,:,1:]=inverse
coeff[:,:,0]=-inverse.sum(axis=2)
constraints=[]; counts={}
chosen={'lower_trade_main','lower_trade_pier_descent','lower_work_pier_descent','north_lower_upper_ramp'}
for route in spec['routes']:
    if route['name'] not in chosen: continue
    count=0
    for a,b in zip(route['points'],route['points'][1:]):
        a=np.array(a[:2]); b=np.array(b[:2]); tangent=b-a; tangent/=np.linalg.norm(tangent)
        cross=np.array([-tangent[1],tangent[0]])
        width=route['halfwidth']+.04
        poly=np.array([a-cross*width,b-cross*width,b+cross*width,a+cross*width])
        mask=util.intersections(qt,poly); ids=np.flatnonzero(mask)
        for direction, degrees in [(tangent,27.0),(cross,11.0)]:
            c=np.einsum('d,fdk->fk',direction,coeff[ids])
            constraints.append((tri[ids],c,np.full(len(ids),np.tan(np.deg2rad(degrees)))))
        count+=len(ids)
    counts[route['name']]=count
for court in spec['platforms']:
    if court['name'] not in ('lower_market_side_court','lower_trade_court','trade_pier_sand_landing'):continue
    ids=np.flatnonzero(util.intersections(qt,np.array(court['polygon'])))
    # Bound actual full triangles across both the market and pier landing.
    for angle in np.linspace(0,np.pi,12,endpoint=False):
        c=np.einsum('d,fdk->fk',np.array([np.cos(angle),np.sin(angle)]),coeff[ids])
        constraints.append((tri[ids],c,np.full(len(ids),np.tan(np.deg2rad(11.0)))))
    counts[court['name']]=len(ids)
# The entry fork includes the full joined corner beyond each straight road
# rectangle, so constrain its actual faces as well as the two route widths.
for junction in spec['junctions']:
    if junction['name']!='trade_entry_fork':continue
    ids=np.flatnonzero(util.intersections(qt,np.array(junction['polygon_xz'])))
    for angle in np.linspace(0,np.pi,12,endpoint=False):
        c=np.einsum('d,fdk->fk',np.array([np.cos(angle),np.sin(angle)]),coeff[ids])
        constraints.append((tri[ids],c,np.full(len(ids),np.tan(np.deg2rad(26.0)))))
    counts[junction['name']]=len(ids)
vertices=np.concatenate([c[0] for c in constraints]); weights=np.concatenate([c[1] for c in constraints]); limits=np.concatenate([c[2] for c in constraints])
low=np.full(len(p),-1e6); high=np.full(len(p),1e6)
active={o['name'] for o in json.loads((LOG/'objects_before.json').read_text(encoding='utf8'))}
for obj in bpy.data.objects:
    if obj.type!='MESH' or obj.hide_render or obj.name not in active: continue
    if not obj.name.startswith(('Town_Floor','Hut_Floor','Town_TavernPorch')): continue
    if any(c.name.startswith('Archive_') or c.hide_render for c in obj.users_collection): continue
    pts=np.array([obj.matrix_world@v.co for v in obj.data.vertices])
    hull=util.convex_hull(pts[:,:2]); hit=util.intersections(original[tri,:2],hull)
    ii=np.unique(tri[hit]); low[ii]=np.maximum(low[ii],original[ii,2])
    high[ii]=np.minimum(high[ii],np.maximum(original[ii,2],pts[:,2].min()-.015))
fixed=graded['freedom']==0
low[fixed]=p[fixed,2]; high[fixed]=p[fixed,2]
# Keep the usable courtyard and its stall feet exactly where they were; only
# the outside vertices that pull a cliff across the footprint may be lowered.
court=next(r for r in spec['platforms'] if r['name']=='lower_market_side_court')
inside=util.polygon_distance(q[:,0],q[:,1],court['polygon'])<=0
low[inside]=p[inside,2]; high[inside]=p[inside,2]
free=(high-low)>1e-7
movable_weights=weights*free[vertices]
h=p[:,2].copy(); initial=h.copy(); norm=(movable_weights*movable_weights).sum(axis=1)
for iteration in range(1800):
    g=np.sum(weights*h[vertices],axis=1)
    error=g-np.clip(g,-limits,limits)
    if np.max(abs(error))<1e-6: break
    hit=(abs(error)>1e-7)&(norm>1e-12)
    delta=-error[hit,None]*movable_weights[hit]/norm[hit,None]
    add=np.zeros(len(h)); den=np.zeros(len(h))
    np.add.at(add,vertices[hit].ravel(),delta.ravel())
    np.add.at(den,vertices[hit].ravel(),1)
    h+=.85*np.divide(add,den,out=np.zeros_like(add),where=den>0)
    h=np.clip(h,low,high)
p[:,2]=h
assert np.isfinite(p).all()
ob=bpy.data.objects['C25_ContourBuiltCoast']; mesh=ob.data
mesh.vertices.foreach_set('co',p.astype(np.float32).ravel()); mesh.update(); bpy.context.view_layer.update()
actual=np.sum(weights*h[vertices],axis=1)
report={'source_baseline':'grade.npz','actual_full_triangle_constraints':len(limits),'triangles_by_area':counts,
        'iterations':iteration+1,'max_gradient_excess':float(np.maximum(abs(actual)-limits,0).max()),
        'changed_vertices':int(np.count_nonzero(abs(h-initial)>1e-6)),
        'max_height_change_m':float(np.max(abs(h-initial))),
        'limits_unchanged':True,'visual_accepted':False}
np.savez_compressed(LOG/'slope_cleanup.npz',positions=p.astype(np.float32),triangles=tri)
(LOG/'slope_cleanup.json').write_text(json.dumps(report,indent=2),encoding='utf8')
print(json.dumps(report))
exec((ROOT/'source/structure23_07_check.py').read_text(encoding='utf8'),globals())
