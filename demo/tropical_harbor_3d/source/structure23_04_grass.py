"""Reconcile rooted blades and slope fragments with the authored ground in MCP."""
import bpy,bmesh,json,numpy as np
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT=Path(bpy.data.filepath).parent.parent;LOG=ROOT/'captures/terrain_structure_20261123'
assert not bpy.app.background
terrain=bpy.data.objects['C25_ContourBuiltCoast'];assert terrain.get('structure23_land')
raw=np.load(LOG/'baseline.npz');old=BVHTree.FromPolygons(raw['positions'].tolist(),raw['triangles'].tolist(),all_triangles=True)
bpy.context.view_layer.update();new=BVHTree.FromObject(terrain,bpy.context.evaluated_depsgraph_get())
land=np.load(LOG/'land_data.npz')['land'];n=len(land)
def sample(x,y):
    i=int(np.clip((x+4)/48*n,0,n-1));j=int(np.clip((-y+15)/97*n,0,n-1));return land[j,i]
def ray(x,y):return new.ray_cast(Vector((float(x),float(y),60)),Vector((0,0,-1)),200)
reports=[]
for name in ('L24_GrassTuftClusters','G23_RootedGrassMargins'):
    ob=bpy.data.objects[name];key='STRUCTURE23_BASE_'+name
    original=bpy.data.meshes.get(key)
    if original is None:
        original=ob.data.copy();original.name=key;original.use_fake_user=True
    bm=bmesh.new();bm.from_mesh(original);bm.faces.ensure_lookup_table();remove=[];kept=0;max_gap=-100
    for f in bm.faces:
        assert len(f.verts)==3 and all(len(v.link_faces)==1 for v in f.verts)
        p=[ob.matrix_world@v.co for v in f.verts];root=(p[0]+p[1])/2
        if not (8<root.x<37 and -2<-root.y<68):continue
        h,no,_,_=ray(root.x,root.y);role=sample(root.x,root.y)
        if h is None or no.z<.73 or role[0]<.63 or role[2]>.16 or role[1]>.30 or role[3]>.35:
            remove.append(f);continue
        hs=[ray(q.x,q.y)[0] for q in p[:2]]
        if any(q is None for q in hs):remove.append(f);continue
        dz=min(h.z-root.z,*(q.z-v.z for q,v in zip(hs,p[:2])))-.012
        shift=ob.matrix_world.to_3x3().inverted()@Vector((0,0,dz))
        for v in f.verts:v.co+=shift
        max_gap=max(max_gap,root.z+dz-h.z);kept+=1
    if remove:bmesh.ops.delete(bm,geom=[v for f in remove for v in f.verts],context='VERTS')
    result=original.copy();result.name=name+'_Structure23';bm.to_mesh(result);bm.free();result.update();ob.data=result
    reports.append({'object':name,'before':len(original.polygons),'after':len(result.polygons),'removed':len(remove),'regrounded':kept,'max_root_gap':max_gap})
ob=bpy.data.objects['G23_EmbeddedSlopeFragments'];key='STRUCTURE23_BASE_FRAGMENTS';original=bpy.data.meshes.get(key)
if original is None:original=ob.data.copy();original.name=key;original.use_fake_user=True
bm=bmesh.new();bm.from_mesh(original);todo=set(bm.verts);removed=[];shifted=0
while todo:
    queue=[next(iter(todo))];group=set()
    while queue:
        v=queue.pop()
        if v in group:continue
        group.add(v);queue.extend(e.other_vert(v) for e in v.link_edges)
    todo-=group;p=[ob.matrix_world@v.co for v in group];center=sum(p,Vector())/len(p)
    if not (8<center.x<37 and -2<-center.y<68):continue
    h,no,_,_=ray(center.x,center.y);role=sample(center.x,center.y)
    if h is None or role[2]>.22 or no.z<.55:removed.extend(group);continue
    oldh=old.ray_cast(Vector((center.x,center.y,60)),Vector((0,0,-1)),200)[0]
    if oldh:
        dz=h.z-oldh.z
        for v in group:v.co+=ob.matrix_world.to_3x3().inverted()@Vector((0,0,dz))
        shifted+=1
if removed:bmesh.ops.delete(bm,geom=removed,context='VERTS')
result=original.copy();result.name='G23_Fragments_Structure23';bm.to_mesh(result);bm.free();result.update();ob.data=result
terrain['structure23_grass']=True
report={'blades':reports,'fragments_removed_vertices':len(removed),'fragments_regrounded':shifted,'visual_accepted':False}
(LOG/'grass.json').write_text(json.dumps(report,indent=2),encoding='utf8');print(json.dumps(report))
