# Read-only geometry and grounding audit, evaluated in Blender via MCP.
exec((Path(bpy.data.filepath).parent/'shore_21_context.py').read_text(encoding='utf8'),globals())
from collections import Counter
old=np.load(str(LOG/'terrain_before.npz'))
old_arrays={k:old[k] for k in old.files};old.close()
old=old_arrays
oldfaces=[old['loops'][s:s+n].tolist() for s,n in zip(old['starts'],old['sizes'])]
old_bvh=BVHTree.FromPolygons([Vector(v) for v in old['positions']],oldfaces)
def old_height(x,z):
    h,*_=old_bvh.ray_cast(Vector((x,-z,80)),Vector((0,0,-1)),300)
    return h.z if h else -15
def border(positions,faces):
    edges=Counter()
    for ids in faces:
        for a,b in zip(ids,ids[1:]+ids[:1]):edges[tuple(sorted((a,b)))]+=1
    boundary={tuple(sorted(tuple(round(float(v),5) for v in positions[i]) for i in e)) for e,n in edges.items() if n==1}
    return boundary,sum(n>2 for n in edges.values())
newfaces=[list(p.vertices) for p in mesh.polygons]
old_boundary,_=border(old['positions'],oldfaces)
new_boundary,nonmanifold=border([v.co for v in mesh.vertices],newfaces)
mesh.calc_loop_triangles()
negative=[];degenerate=[]
for t in mesh.loop_triangles:
    a,b,c=[mesh.vertices[i].co for i in t.vertices];cross=(b-a).cross(c-a)
    if cross.z<-.000001:negative.append({'poly':t.polygon_index,'center':list((a+b+c)/3),'nz':t.normal.z})
    if cross.length<1e-9:degenerate.append(t.polygon_index)
foundation={}
for name in ['HarborTavern','RosiesDiner','SariSari','TravelOffice','IslaSchool']:
    obs=[o for o in bpy.data.collections['Reference_Town'].objects if o.get('town_building')==name and o.type=='MESH']
    floor=next(o for o in obs if o.name.startswith('Town_Floor'))
    pts=[floor.matrix_world@v.co for v in floor.data.vertices]
    vals=[ground(p.x,-p.y)-old_height(p.x,-p.y) for p in pts]
    foundation[name]={'samples':len(vals),'ground_delta_range':[min(vals),max(vals)]}
cargo=[]
for name in ['R20_UpperHull','R20_LowerHull','R20_HullBottom']:
    o=bpy.data.objects[name]
    for poly in o.data.polygons:
        ps=[o.data.vertices[i].co for i in poly.vertices]
        for p in ps+[sum(ps,Vector())/len(ps)]:
            p=o.matrix_world@p
            if p.z<.6:cargo.append(p.z-ground(p.x,-p.y))
cache=json.loads((OUT/'shore_relief_height.json').read_text(encoding='utf8'))
err=[]
for row in range(0,cache['rows'],17):
    z=cache['z0']+row*cache['step']
    for col in range(0,cache['columns'],13):
        d=cache['d0']+col*cache['step'];err.append(abs(cache['heights'][row*cache['columns']+col]-ground(float(shore(z)+d),z)))
report={'source':bpy.data.filepath,'dirty':bpy.data.is_dirty,'triangles':len(mesh.loop_triangles),'vertices':len(mesh.vertices),
 'new_internal_boundary_edges':len(new_boundary-old_boundary),'removed_boundary_edges':len(old_boundary-new_boundary),'nonmanifold_edges':nonmanifold,
 'negative_triangles':negative,'degenerate_triangles':degenerate,'building_floor_support':foundation,'cargo_samples':len(cargo),'cargo_min_clearance':min(cargo),
 'height_cache_samples':len(err),'height_cache_max_error':max(err)}
(LOG/'geometry_audit.json').write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf8')
print(json.dumps(report,ensure_ascii=False))
