"""Grade complete road beds and shores, only in the owned GUI Blender MCP.
Each review revision is derived from this turn's immutable baseline, not an
accumulation of nudges. No saved source or exported asset is overwritten here.
"""
import bpy,json,sys,numpy as np
from pathlib import Path
from mathutils import Vector
assert not bpy.app.background
ROOT=Path(bpy.data.filepath).parent.parent;LOG=ROOT/'captures/terrain_structure_20261123'
sys.path.insert(0,str(ROOT/'source'))
import importlib,structure23_common as util;importlib.reload(util)
spec=json.loads((LOG/'design.json').read_text(encoding='utf8'))
base=np.load(LOG/'baseline.npz');before=base['positions'].astype(float);tri=base['triangles']
ob=bpy.data.objects['C25_ContourBuiltCoast'];mesh=ob.data
assert len(mesh.vertices)==len(before) and len(mesh.polygons)==len(tri)
p=before.copy();x=p[:,0];z=-p[:,1]
fixed=before[:,2]<=.10
edge=np.sort(np.concatenate([tri[:,[0,1]],tri[:,[1,2]],tri[:,[2,0]]]),axis=1)
edge,count=np.unique(edge,axis=0,return_counts=True);fixed[np.unique(edge[count==1])]=True
freedom=np.ones(len(p));supports=[];support_cap=np.full(len(p),1e6);support_floor=np.full(len(p),-1e6)
active={o['name'] for o in json.loads((LOG/'objects_before.json').read_text(encoding='utf8'))}
for o in bpy.data.objects:
    if o.type!='MESH' or o.hide_render or o.name not in active:continue
    if not o.name.startswith(('Town_Floor','Hut_Floor','Town_TavernPorch')):continue
    if any(c.name.startswith('Archive_') or c.hide_render for c in o.users_collection):continue
    pts=np.array([o.matrix_world@v.co for v in o.data.vertices])
    hull=util.convex_hull(pts[:,:2]);hit=util.intersections(before[tri,:2],hull)
    ids=np.unique(tri[hit])
    # Fill may meet existing structural undersides, never penetrate them.
    # Freezing old low under-floor terrain created false cliffs beside roads.
    support_cap[ids]=np.minimum(support_cap[ids],np.maximum(before[ids,2],pts[:,2].min()-.015))
    inside=util.polygon_distance(x,p[:,1],hull)<=0
    support_floor[ids]=before[ids,2]
    supports.append(o.name)
freedom[fixed]=0
# Broad low grass shores share the grade of the continuous lower road. Their
# toes are authored uneven control lines, not repeating parallel bands.
sections=np.array(spec.get('shore_sections',[]),float)
if len(sections):
    zz=sections[:,0];toe=np.interp(z,zz,sections[:,1]);bench=np.interp(z,zz,sections[:,2]);bh=np.interp(z,zz,sections[:,3])
    target=.28+(bh-.28)*util.ss(toe,bench,x)
    scope=util.ss(zz[0]-.8,zz[0]+.5,z)*(1-util.ss(zz[-1]-.5,zz[-1]+.8,z))
    scope*=util.ss(toe-.3,toe+.25,x)*(1-util.ss(bench+.1,bench+1.2,x))
    scope*=1-util.ss(2.0,2.8,before[:,2])
    p[:,2]+=scope*(target-p[:,2])*freedom
# The complete trade shore shares the low access bench instead of retaining
# old high grass ridges on both sides of a newly cut narrow route.
def finish_trade_access_background():
    access=np.asarray(spec.get('trade_access_sections',[]),float)
    if not len(access):return
    prior=p[:,2].copy()
    zz=access[:,0];outer=np.interp(z,zz,access[:,1]);inner=np.interp(z,zz,access[:,2]);low=np.interp(z,zz,access[:,3])
    main=next(r for r in spec['routes'] if r['name']=='lower_trade_main')
    pts=np.asarray(main['points']);topx=np.interp(z,pts[:,1],pts[:,0])-main['halfwidth']-.03
    high=np.interp(z,pts[:,1],pts[:,2]);toe=np.interp(z,[7,9,11,13,15.3],[9.5,9.4,9.35,9.4,9.6])
    # Almost-linear slopes retain the available rise/run; broad smoothstep
    # would make a steeper middle wall and excessively wide flat shoulders.
    def rounded_grade(t):
        t=np.clip(t,0,1);e=.10
        return np.where(t<e,t*t/(2*e),np.where(t>1-e,1-e-(1-t)**2/(2*e),t-e/2))/(1-e)
    lowbank=.28+(low-.28)*rounded_grade((x-toe)/np.maximum(outer-toe,.15))
    inland=low+(high-low)*rounded_grade((x-inner)/np.maximum(topx-inner,.15))
    section=np.where(x<outer,lowbank,np.where(x<inner,low,inland))
    weight=util.ss(6.6,8.0,z)*(1-util.ss(14.4,15.6,z))
    weight*=util.ss(toe-.30,toe+.20,x)*(1-util.ss(topx,topx+.12,x))
    p[:,2]+=(section-p[:,2])*weight*freedom
    # Retain only the actual usable widths, not their old broad high shoulder.
    # The external bank meets those widths through the one shared section.
    keep=np.zeros(len(p))
    for r in spec['routes']:
        if r['name'] not in ('lower_trade_main','lower_trade_entry','lower_trade_pier_descent'):continue
        d,_=util.route_profile(x,z,r['points'])
        keep=np.maximum(keep,1-util.ss(r['halfwidth']+.08,r['halfwidth']+.22,d))
    for court in spec['platforms']:
        if court['name'] not in ('lower_trade_court','trade_pier_sand_landing'):continue
        d=util.polygon_distance(x,z,court['polygon'])
        keep=np.maximum(keep,1-util.ss(.08,.20,d))
    p[:,2]+=keep*(prior-p[:,2])
# Two broad upper rock shoulders alter the long school's crown in depth.
# Keeping XY fixed makes this height-field change preserve all sea boundaries.
for shape in spec.get('rock_shoulders',[]):
    cx,cz,rx,rz,dh=shape
    d=np.sqrt(((x-cx)/rx)**2+((z-cz)/rz)**2)
    w=1-util.ss(.12,1,d)
    p[:,2]+=dh*w*freedom*util.ss(.65,1.3,before[:,2])
target,influence,paint=util.design_field(x,z,spec)
p[:,2]+=(target-p[:,2])*influence*freedom
finish_trade_access_background()
p[:,2]=np.minimum(p[:,2],support_cap)
p[:,2]=np.maximum(p[:,2],support_floor)
p[fixed]=before[fixed]
assert np.isfinite(p).all()
n=np.cross(p[tri[:,1]]-p[tri[:,0]],p[tri[:,2]]-p[tri[:,0]])
oldn=np.cross(before[tri[:,1]]-before[tri[:,0]],before[tri[:,2]]-before[tri[:,0]])
assert not np.any((n[:,2]*oldn[:,2])<0),'Projected triangle inversion'
assert np.min(np.linalg.norm(n,axis=1))>1e-10
mesh.vertices.foreach_set('co',p.astype(np.float32).ravel());mesh.update();bpy.context.view_layer.update()
np.savez_compressed(LOG/'grade.npz',positions=p.astype(np.float32),triangles=tri,freedom=freedom,paint=paint)
delta=p[:,2]-before[:,2]
report={'changed_vertices':int(np.count_nonzero(abs(delta)>1e-5)),'max_raise':float(delta.max()),'max_lower':float(-delta.min()),'fixed_vertices':int(fixed.sum()),'fixed_supports':supports,'routes':len(spec['routes']),'platforms':len(spec['platforms']),'vertices':len(p),'triangles':len(tri),'fixed_boundary_and_seafloor':True,'visual_accepted':False}
ob['structure23_grade']=True
(LOG/'grade.json').write_text(json.dumps(report,indent=2),encoding='utf8');print(json.dumps(report))
