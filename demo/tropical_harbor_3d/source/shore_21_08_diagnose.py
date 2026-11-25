exec((Path(bpy.data.filepath).parent/'shore_21_context.py').read_text(encoding='utf8'),globals())
import bmesh
bm=bmesh.new();bm.from_mesh(mesh);bm.verts.ensure_lookup_table();bm.faces.ensure_lookup_table()
edges=[e for e in bm.edges if e.is_boundary and all(5<v.co.x<30 and 38<-v.co.y<57 for v in e.verts)]
verts={v for e in edges for v in e.verts}
data={'dirty':bpy.data.is_dirty,'edges':[[v.index for v in e.verts] for e in edges], 'vertices':{v.index:list(v.co) for v in verts},'faces':[{ 'index':f.index,'vertices':[(v.index,list(v.co)) for v in f.verts]} for f in {f for v in verts for f in v.link_faces}]}
floor=next(o for o in bpy.data.collections['Reference_Town'].objects if o.get('town_building')=='TravelOffice' and o.name.startswith('Town_Floor'))
data['floor']=[]
for v in floor.data.vertices:
    p=floor.matrix_world@v.co
    hit,n,pi,_=ground_bvh.ray_cast(Vector((p.x,p.y,80)),Vector((0,0,-1)),300)
    data['floor'].append({'point':list(p),'hit':list(hit),'poly':pi,'verts':[(i,list(mesh.vertices[i].co)) for i in mesh.polygons[pi].vertices]})
(LOG/'seam_diagnosis.json').write_text(json.dumps(data,indent=2),encoding='utf8')
bm.free();print(json.dumps(data))
