exec((Path(bpy.data.filepath).parent/'shore_21_context.py').read_text(encoding='utf8'),globals())
import bmesh
assert not terrain.get('shore21_seams_closed'),'Already applied'
bm=bmesh.new();bm.from_mesh(mesh)
def local_edges():return [e for e in bm.edges if e.is_boundary and all(5<v.co.x<30 and 38<-v.co.y<57 for v in e.verts)]
splits=0
for _ in range(10):
    edges=local_edges();vs={v for e in edges for v in e.verts};found=None
    for e in edges:
        a,b=e.verts;delta=b.co-a.co
        for v in vs:
            if v in e.verts:continue
            t=(v.co-a.co).dot(delta)/delta.length_squared
            if .00001<t<.99999 and (v.co-(a.co+t*delta)).length<.00015:
                found=(e,a,v,t);break
        if found:break
    if not found:break
    e,a,v,t=found;newedge,newvert=bmesh.utils.edge_split(e,a,t);newvert.co=v.co.copy()
    bmesh.ops.remove_doubles(bm,verts=[newvert,v],dist=.00001);splits+=1
edges=local_edges()
result=bmesh.ops.holes_fill(bm,edges=edges,sides=8)
layer=bm.loops.layers.float_color.get('LandUse')
for f in result['faces']:
    f.normal_update()
    if f.normal.z<0:f.normal_flip()
    for l in f.loops:l[layer]=(0,0,0,0)
assert not local_edges(),'Shore seam remains open'
bm.to_mesh(mesh);bm.free();mesh.update()
bpy.context.view_layer.update();ground_bvh=BVHTree.FromObject(terrain,bpy.context.evaluated_depsgraph_get())
floor=next(o for o in bpy.data.collections['Reference_Town'].objects if o.get('town_building')=='TravelOffice' and o.name.startswith('Town_Floor'))
support=set()
for vert in floor.data.vertices:
    p=floor.matrix_world@vert.co
    hit,n,pi,_=ground_bvh.ray_cast(Vector((p.x,p.y,80)),Vector((0,0,-1)),300)
    if hit.z<4.13:
        support.update(mesh.polygons[pi].vertices)
for i in support:
    assert mesh.vertices[i].co.z>3.45,'Unexpected low face under travel office'
    mesh.vertices[i].co.z=4.14
mesh.update();bpy.context.view_layer.update();ground_bvh=BVHTree.FromObject(terrain,bpy.context.evaluated_depsgraph_get())
terrain['shore21_seams_closed']=True
refresh_height();export_land();bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'source/harbor_shore_control_mcp.blend'))
print(json.dumps({'boundary_splits':splits,'filled_faces':len(result['faces']),'support_vertices':len(support)}))
