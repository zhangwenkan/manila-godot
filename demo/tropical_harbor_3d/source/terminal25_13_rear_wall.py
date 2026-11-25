"""One-time correction of the terminal's unnecessarily wide rear retaining wall."""
import bpy
exec(compile('''
assert not (LOG/'rear_wall_fix.json').exists(), 'Do not replay rear-wall fix'
from mathutils.bvhtree import BVHTree
terrain=bpy.data.objects['C25_ContourBuiltCoast']
terrain.data.calc_loop_triangles()
positions=[terrain.matrix_world@v.co for v in terrain.data.vertices]
faces=[tuple(t.vertices) for t in terrain.data.loop_triangles]
current_bvh=BVHTree.FromPolygons(positions,faces,all_triangles=True)
old=[o for o in C.objects if o.name=='TN25_RearRetainingWall' or o.name.startswith('TN25_RetainingCap')]
assert len(old)==11
archive=bpy.data.collections.new('Archive_TN25_WideRearWall_20261125')
bpy.context.scene.collection.children.link(archive)
previous=[]
for o in old:
 previous.append({'name':o.name,'matrix':[list(v) for v in o.matrix_world],'bounds':[list(o.matrix_world@Vector(v)) for v in o.bound_box]})
 archive.objects.link(o)
 C.objects.unlink(o)
archive.hide_render=True;archive.hide_viewport=True
# The rear support belongs to the small tower's cut only. The main tower and
# gallery already have individually grounded stone foundations.
# Keep the entire landward wall face inside the flat cut (rear y=26.97),
# instead of slicing through the narrow, irregular exterior slope.
x0,x1=.10,2.90
rear=26.97;depth=.25;bottom=1.40;top=3.42
made=[]
for i in range(4):
 cx=x0+(i+.5)*(x1-x0)/4
 o=B('RearCutSupport',(cx,rear-depth/2,(bottom+top)/2),((x1-x0)/4-.006,depth,top-bottom),'stone',.012)
 made.append(o.name)
 o=B('RearCutCap',(cx,rear-depth/2,3.46),((x1-x0)/4-.010,depth,.12),'stone',.012)
 made.append(o.name)
bpy.context.view_layer.update()
support=[]
for name in made:
 if 'Cap' in name:continue
 o=bpy.data.objects[name]
 box=[o.matrix_world@Vector(v) for v in o.bound_box]
 lo=Vector(tuple(min(v[j] for v in box) for j in range(3)))
 hi=Vector(tuple(max(v[j] for v in box) for j in range(3)))
 heights=[]
 for x in np.linspace(lo.x,hi.x,9):
  for y in np.linspace(lo.y,hi.y,9):
   hit=current_bvh.ray_cast(Vector((float(x),float(y),40)),Vector((0,0,-1)),80)[0]
   assert hit is not None
   heights.append(float(hit.z))
 assert lo.z<=min(heights)-.10,(name,lo.z,min(heights))
 support.append({'name':name,'samples':len(heights),'bottom':float(lo.z),'min_terrain':min(heights),'max_terrain':max(heights),'embed_min':min(heights)-float(lo.z)})
report={'archived':previous,'created':made,'terrain_unchanged':True,'scope':'Only terminal rear retaining wall; main/gallery original grounded footings retained','rear_face_y':rear,'small_tower_x':[x0,x1],'support_checks':support,'source_not_yet_saved':True}
(LOG/'rear_wall_fix.json').write_text(json.dumps(report,indent=2),encoding='utf8')
print(json.dumps({'archived':len(old),'created':len(made),'support_checks':support}))
''','terminal25_13_rear_wall.py','exec'),bpy.app.driver_namespace['terminal25'])
