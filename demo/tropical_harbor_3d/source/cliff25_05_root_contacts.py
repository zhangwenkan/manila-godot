"""Reconcile current-round grass and embedded fragments with local cliff sculpt."""
import bpy,bmesh,json,os,numpy as np
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
assert os.getpid()==9864 and bpy.types.blendermcp_server.port==9881 and not bpy.app.background
ROOT=Path(bpy.data.filepath).parent.parent;LOG=ROOT/'captures/cliff_contacts_20261125'
terrain=bpy.data.objects['C25_ContourBuiltCoast'];bpy.context.view_layer.update()
new=BVHTree.FromObject(terrain,bpy.context.evaluated_depsgraph_get());raw=np.load(LOG/'baseline.npz')
old=BVHTree.FromPolygons(raw['positions'].tolist(),raw['triangles'].tolist(),all_triangles=True)
land=np.load(LOG/'land_data.npz')['land'];n=len(land)
def ray(x,y):return new.ray_cast(Vector((float(x),float(y),60)),Vector((0,0,-1)),200)
def role(x,y):return land[int(np.clip((-y+15)/97*n,0,n-1)),int(np.clip((x+4)/48*n,0,n-1))]
def local(p):return 15<p.x<27 and 21<-p.y<46
reports=[]
for name in ('L24_GrassTuftClusters','G23_RootedGrassMargins'):
    ob=bpy.data.objects[name];key='CLIFF25_BASE_'+name
    original=bpy.data.meshes.get(key)
    if original is None:original=ob.data.copy();original.name=key;original.use_fake_user=True
    bm=bmesh.new();bm.from_mesh(original);bm.faces.ensure_lookup_table();remove=[];kept=0;maxgap=-100
    inv=ob.matrix_world.to_3x3().inverted()
    for f in bm.faces:
        assert len(f.verts)==3 and all(len(v.link_faces)==1 for v in f.verts)
        pp=[ob.matrix_world@v.co for v in f.verts];root=(pp[0]+pp[1])/2
        if not local(root):continue
        h,normal,_,_=ray(root.x,root.y);w=role(root.x,root.y)
        if h is None or normal.z<.73 or w[0]<.62 or w[1]>.30 or w[2]>.16 or w[3]>.35:remove.append(f);continue
        feet=[ray(q.x,q.y)[0] for q in pp[:2]]
        if any(q is None for q in feet):remove.append(f);continue
        dz=min(h.z-root.z,*(q.z-v.z for q,v in zip(feet,pp[:2])))-.012
        shift=inv@Vector((0,0,dz))
        for v in f.verts:v.co+=shift
        maxgap=max(maxgap,root.z+dz-h.z);kept+=1
    if remove:bmesh.ops.delete(bm,geom=[v for f in remove for v in f.verts],context='VERTS')
    result=original.copy();result.name=name+'_Cliff25';bm.to_mesh(result);bm.free();result.update();ob.data=result
    reports.append({'object':name,'baseline_leaves':len(original.polygons),'final_leaves':len(result.polygons),'removed':len(remove),'local_regrounded':kept,'max_root_gap_m':maxgap})
ob=bpy.data.objects['G23_EmbeddedSlopeFragments'];key='CLIFF25_BASE_FRAGMENTS';original=bpy.data.meshes.get(key)
if original is None:original=ob.data.copy();original.name=key;original.use_fake_user=True
bm=bmesh.new();bm.from_mesh(original);todo=set(bm.verts);remove=[];shifted=0
while todo:
    queue=[next(iter(todo))];group=set()
    while queue:
        v=queue.pop()
        if v in group:continue
        group.add(v);queue.extend(e.other_vert(v) for e in v.link_edges)
    todo-=group;pp=[ob.matrix_world@v.co for v in group];center=sum(pp,Vector())/len(pp)
    if not local(center):continue
    h,normal,_,_=ray(center.x,center.y);w=role(center.x,center.y)
    if h is None or w[2]>.22 or normal.z<.55:remove.extend(group);continue
    oldh=old.ray_cast(Vector((center.x,center.y,60)),Vector((0,0,-1)),200)[0]
    if oldh:
        shift=ob.matrix_world.to_3x3().inverted()@Vector((0,0,h.z-oldh.z))
        for v in group:v.co+=shift
        shifted+=1
if remove:bmesh.ops.delete(bm,geom=remove,context='VERTS')
result=original.copy();result.name='G23_Fragments_Cliff25';bm.to_mesh(result);bm.free();result.update();ob.data=result
report={'grass':reports,'fragment_removed_vertices':len(remove),'fragment_groups_regrounded':shifted,'visual_accepted':False}
(LOG/'grass.json').write_text(json.dumps(report,indent=2),encoding='utf8');print(json.dumps(report))
