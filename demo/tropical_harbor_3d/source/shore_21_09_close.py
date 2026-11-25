exec((Path(bpy.data.filepath).parent/'shore_21_context.py').read_text(encoding='utf8'),globals())
import bmesh
assert not terrain.get('shore21_seams_closed'),'Already applied'
bm=bmesh.new();bm.from_mesh(mesh);bm.verts.ensure_lookup_table()
A,B,C,D,E=[bm.verts[i] for i in [53371,53947,53958,53372,53959]]
face=next(f for f in A.link_faces if set(f.verts)=={A,B,D})
layer=bm.loops.layers.float_color.get('LandUse')
colors={l.vert:tuple(l[layer]) for l in face.loops}
material=face.material_index
# The old triangle crosses two constraint intersections and overlaps B-C-E.
# Replace it with the shared A-C-E-D polygon, preserving the existing B-C-E.
bm.faces.remove(face)
for e in list(bm.edges):
    if not e.link_faces:bm.edges.remove(e)
for vs in [(A,C,E),(A,E,D)]:
    f=bm.faces.new(vs);f.material_index=material;f.normal_update()
    assert f.normal.z>0,'Unexpected winding'
    for l in f.loops:l[layer]=colors.get(l.vert,(0,0,0,0))
assert not [e for e in bm.edges if e.is_boundary and all(5<v.co.x<30 and 38<-v.co.y<57 for v in e.verts)],'Shore seam remains open'
bm.to_mesh(mesh);bm.free();mesh.update()
bpy.context.view_layer.update();ground_bvh=BVHTree.FromObject(terrain,bpy.context.evaluated_depsgraph_get())
floor=next(o for o in bpy.data.collections['Reference_Town'].objects if o.get('town_building')=='TravelOffice' and o.name.startswith('Town_Floor'))
support=set()
for vert in floor.data.vertices:
    p=floor.matrix_world@vert.co
    hit,n,pi,_=ground_bvh.ray_cast(Vector((p.x,p.y,80)),Vector((0,0,-1)),300)
    if hit.z<4.13:support.update(mesh.polygons[pi].vertices)
for i in support:
    assert mesh.vertices[i].co.z>3.45,'Unexpected low face under travel office'
    mesh.vertices[i].co.z=4.14
mesh.update();bpy.context.view_layer.update();ground_bvh=BVHTree.FromObject(terrain,bpy.context.evaluated_depsgraph_get())
for vert in floor.data.vertices:
    p=floor.matrix_world@vert.co
    assert abs(ground(p.x,-p.y)-4.14)<.0001,'Support not level'
terrain['shore21_seams_closed']=True
refresh_height();export_land();bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'source/harbor_shore_control_mcp.blend'))
print(json.dumps({'replaced_overlap_triangles':1,'new_triangles':2,'support_vertices':len(support),'local_open_edges':0}))
