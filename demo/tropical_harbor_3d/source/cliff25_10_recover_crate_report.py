"""Relocate the complete crate to the travel-office service side via GUI MCP.

One-shot current-session authoring; no terrain pad, no dimension changes.
Uses immutable object transforms and validates the full footprint before edit.
"""
import bpy, os, sys, json
from pathlib import Path
import numpy as np
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

assert os.getpid()==9864 and not bpy.app.background
assert bpy.types.blendermcp_server.port==9881
ROOT=Path(bpy.data.filepath).parent.parent
LOG=ROOT/'captures/cliff_contacts_20261125'
REPORT=LOG/'crate_relocation.json'
assert not REPORT.exists(),'Already relocated; do not blindly replay'
sys.path.insert(0,str(ROOT/'source'))
from structure23_common import route_profile,convex_hull

catalog={r['name']:r for r in json.loads((LOG/'objects_before.json').read_text(encoding='utf8'))}
names=['Crate_Diagonal.032','Crate_Diagonal.033','Crate_Frame.064','Crate_Frame.065',
       'Crate_Frame.066','Crate_Frame.067','Crate_Rail.064','Crate_Rail.065',
       'Crate_Rail.066','Crate_Rail.067','Prop_Crate.016']
assert len(names)==11 and all(n in catalog and n in bpy.data.objects for n in names)
original={n:Matrix(catalog[n]['matrix']) for n in names}
# Recovery: the preceding one-shot applied transforms then failed JSON serialization.
# Recompute expected destination from immutable baseline and verify it, without moving again.

ground=bpy.data.objects['C25_ContourBuiltCoast'];mesh=ground.data
vertices=[ground.matrix_world@v.co for v in mesh.vertices]
bvh=BVHTree.FromPolygons(vertices,[list(f.vertices) for f in mesh.polygons],all_triangles=True)
def height(x,y):
    hit=bvh.ray_cast(Vector((float(x),float(y),50)),Vector((0,0,-1)))
    assert hit[0] is not None,'No terrain under crate'
    return float(hit[0].z)

# North service edge of the existing travel building: near the public route,
# but outside its entire usable width and clear of its corner junction.
target_x,target_z=24.50,43.25
old_centre=np.array(original['Prop_Crate.016'].translation)
dx=target_x-old_centre[0];dy=-target_z-old_centre[1]
world_points={n:np.array([original[n]@v.co for v in bpy.data.objects[n].data.vertices]) for n in names}
all_points=np.concatenate(list(world_points.values()))
new_xy=all_points[:,:2]+np.array([dx,dy])
lo,hi=new_xy.min(0),new_xy.max(0)
hull=np.array(convex_hull(new_xy))
samples=[new_xy.mean(0)]
for a,b in zip(hull,np.roll(hull,-1,axis=0)):
    samples.extend((a*(1-t)+b*t) for t in np.linspace(0,1,17))
samples.extend(np.array([x,y]) for x in np.linspace(lo[0],hi[0],9) for y in np.linspace(lo[1],hi[1],9))
samples=np.array(samples);heights=np.array([height(x,y) for x,y in samples])
assert np.ptp(heights)<.035,'Not a level service yard'

spec=json.loads((LOG/'design.json').read_text(encoding='utf8'))
route_clearances=[]
for r in spec['routes']:
    d,_=route_profile(samples[:,0],-samples[:,1],r['points'])
    clearance=float(d.min()-r['halfwidth'])
    assert clearance>.15,'Crate blocks usable route '+r['name']
    route_clearances.append({'route':r['name'],'full_width_clearance_m':clearance})

# Body and low rails sit on the same horizontal foundation. Sink at most
# 8 mm into the highest point; the terrain spread is < 35 mm across the hull.
body_bottom=float(world_points['Prop_Crate.016'][:,2].min())
new_bottom=float(heights.max()-.008)
dz=new_bottom-body_bottom
final=all_points+np.array([dx,dy,dz])
fmin,fmax=final.min(0),final.max(0)
collisions=[]
clearances=[]
for name,record in catalog.items():
    if name in names or name not in bpy.data.objects:continue
    # Individual grass blades and the existing merged fine soil fragments
    # are cover, not architectural obstacles. All other objects are checked.
    if 'Grass' in name or name in ('C25_ContourBuiltCoast','G23_EmbeddedSlopeFragments'):continue
    ob=bpy.data.objects[name]
    if ob.type!='MESH' or ob.hide_render:continue
    pp=np.array([ob.matrix_world@Vector(c) for c in ob.bound_box]);a,b=pp.min(0),pp.max(0)
    if b[2]<fmin[2]-.03 or a[2]>fmax[2]+.05:continue
    sep=np.maximum(a[:2]-fmax[:2],fmin[:2]-b[:2])
    gap=float(np.linalg.norm(np.maximum(sep,0)))
    if np.all(sep<.05):collisions.append(name)
    if gap<1.0:clearances.append({'object':name,'aabb_plan_gap_m':gap})
assert not collisions,'Obstacle overlap: '+str(collisions)

# All validation finished. Apply the identical rigid translation to every
# board, rail and diagonal; geometry, materials and relative offsets persist.
delta=Matrix.Translation((dx,dy,dz))
# No mutation in this recovery script; validate current matrices below.
bpy.context.view_layer.update()
for n in names:
    assert np.max(np.abs(np.array(bpy.data.objects[n].matrix_world)-np.array(delta@original[n])))<1e-5
report={
    'recovered_after_report_serialization_error':True,'read_only_recovery':True,'pid':os.getpid(),'objects':names,'component_count':len(names),
    'source':'immutable objects_before.json','destination':'travel office north service edge',
    'target_godot_xz':[target_x,target_z],'translation_blender_xyz':[float(dx),float(dy),float(dz)],
    'footprint_sample_count':len(samples),'terrain_height_range_m':[float(heights.min()),float(heights.max())],
    'footprint_ground_spread_m':float(np.ptp(heights)),
    'body_bottom_gap_range_m':[float(new_bottom-heights.max()),float(new_bottom-heights.min())],
    'route_clearances':route_clearances,'nearby_object_clearances':clearances,
    'no_terrain_edit':True,'relative_group_transform_preserved':True,'visual_accepted':False,
}
REPORT.write_text(json.dumps(report,indent=2),encoding='utf8')
print(json.dumps(report))
