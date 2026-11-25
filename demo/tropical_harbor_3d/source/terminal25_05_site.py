import bpy
exec(compile('''
from mathutils.bvhtree import BVHTree
import hashlib
assert not (LOG/'site.json').exists(),'Do not replay site operations'
plan=json.loads((ROOT.parent.parent/'docs/terminal_rebuild_20261125/current_terminal_plan.json').read_text(encoding='utf8'))
oldnames=plan['archive_structure_names']+plan['associated_prop_names']
assert len(oldnames)==918 and len(set(oldnames))==918
archive=bpy.data.collections.new('Archive_TerminalSimpleHouses_20261125');bpy.context.scene.collection.children.link(archive)
for name in oldnames:
 o=bpy.data.objects[name];archive.objects.link(o)
 for col in list(o.users_collection):
  if col!=archive:col.objects.unlink(o)
archive.hide_render=True;archive.hide_viewport=True
t=bpy.data.objects['C25_ContourBuiltCoast'];m=t.data
prior=np.load(LOG/'terrain_before.npz');p=prior['positions'].copy();tri=prior['triangles']
bvh_before=BVHTree.FromPolygons(p.tolist(),tri.tolist(),all_triangles=True)
def h_at(x,y,bvh=None):
 hit=(bvh or bvh_before).ray_cast(Vector((x,y,40)),Vector((0,0,-1)),80)[0]
 assert hit is not None,(x,y)
 return float(hit.z)
# Only the right tower's buried floor footprint needs a cut into the existing rise.
# No road, shore, platform, or other terrain region is reshaped.
x=p[:,0];y=p[:,1]
dx=np.maximum(np.maximum(-.03-x,x-2.93),0);dy=np.maximum(np.maximum(23.57-y,y-26.98),0)
dist=np.sqrt(dx*dx+dy*dy);weight=np.clip(1-dist/.32,0,1);weight=weight*weight*(3-2*weight)
cut=np.maximum(p[:,2]-1.68,0)*weight;p[:,2]-=cut
m.vertices.foreach_set('co',p.ravel());m.update();bpy.context.view_layer.update()
bvh=BVHTree.FromPolygons(p.tolist(),tri.tolist(),all_triangles=True)
# Remove grass leaves whose roots lie inside the newly occupied footprint.
# Each connected component is one authored leaf, and whole leaves are removed.
grass_report=[]
rects=[(-7.45,3.35,22.72,27.18),(-9.20,-7.2,23.65,25.4)]
for cname in ['Reference_Foliage','Reference_GroundCover']:
 for o in list(bpy.data.collections[cname].objects):
  if o.type!='MESH' or not any(k in o.name for k in ['Grass','Tuft']):continue
  bm=bmesh.new();bm.from_mesh(o.data);bm.verts.ensure_lookup_table();seen=set();delete=[];count=0
  for v in bm.verts:
   if v in seen:continue
   component=[];stack=[v];seen.add(v)
   while stack:
    q=stack.pop();component.append(q)
    for e in q.link_edges:
     n=e.other_vert(q)
     if n not in seen:seen.add(n);stack.append(n)
   world=[o.matrix_world@q.co for q in component];rootpos=min(world,key=lambda q:q.z)
   if any(a<=rootpos.x<=b and c<=rootpos.y<=d for a,b,c,d in rects):delete.extend(component);count+=1
  if delete:
   bmesh.ops.delete(bm,geom=delete,context='VERTS');bm.to_mesh(o.data);o.data.update();grass_report.append({'object':o.name,'leaves_removed':count,'vertices_removed':len(delete)})
  bm.free()
# Move the one conflicting palm as a complete group, preserving its internal shape.
names=plan['foliage_groups']['palm_17']['names'];assert len(names)==32
trunk=bpy.data.objects['Palm_Trunk.017'];box=[trunk.matrix_world@Vector(v) for v in trunk.bound_box];base=min(box,key=lambda q:q.z)
dx=-8.20-float(base.x);dy=28.55-float(base.y);dz=h_at(float(base.x)+dx,float(base.y)+dy)-h_at(base.x,base.y)
for name in names:bpy.data.objects[name].location+=Vector((dx,dy,dz))
# Restore sensible foundations under the new floor, down to the actual ground.
for name in ['TN25_MainBuriedFooting','TN25_SmallBuriedFooting','TN25_GalleryFoundation']:
 o=bpy.data.objects[name];bpy.data.objects.remove(o,do_unlink=True)
for prefix,cx,cy,w,d in [('Main',-4.9,25.35,3.7,3.3),('Small',1.45,25.275,2.7,3.15),('Gallery',-1.475,25.15,3.15,2.25)]:
 # Closed segment foundations, embedded slightly at each sampled base.
 for axis,plane,a,b in [(1,cy-d/2,cx-w/2,cx+w/2),(1,cy+d/2,cx-w/2,cx+w/2),(0,cx-w/2,cy-d/2,cy+d/2),(0,cx+w/2,cy-d/2,cy+d/2)]:
  n=max(3,round((b-a)/.68))
  for j in range(n):
   u=a+(j+.5)*(b-a)/n;px,py=(u,plane) if axis==1 else (plane,u)
   heights=[h_at(px+ox,py+oy,bvh) for ox,oy in [(-.10,-.10),(-.1,.1),(.1,-.1),(.1,.1)]]
   bottom=min(heights)-.12;top=1.80
   if bottom>=top:continue
   size=((b-a)/n-.008,.23,top-bottom) if axis==1 else (.23,(b-a)/n-.008,top-bottom)
   B(prefix+'GroundStone',(px,py,(bottom+top)/2),size,'stone',.018)
 # A rear support beam spans the limited retaining cut.
 B(prefix+'BaseBearer',(cx,cy,1.68),(w+.08,d+.04,.16),'beam',.01)
# Porch supports continue into the beach; their top heights stay fixed.
for o in list(C.objects):
 if not o.name.startswith('TN25_PorchFoundation'):continue
 cx,cy,_=o.location;bottom=h_at(cx,cy,bvh)-.16;top=1.76
 o.location.z=(bottom+top)/2
 # Original dimensions are .32/.62/.72, so scale the local mesh height only.
 for v in o.data.vertices:v.co.z*=max(.10,top-bottom)/.72
 o.data.update()
bpy.context.view_layer.update()
changed=np.flatnonzero(np.abs(p[:,2]-prior['positions'][:,2])>1e-7)
report={'archived_structures':873,'archived_attached_props':45,'archived_names':oldnames,'terrain_changed_vertices':len(changed),'terrain_changed_indices':changed.tolist(),'max_cut_m':float(cut.max()),'scope':'Right tower buried floor only; original coast and public road vertices outside halo unchanged','palm_group':names,'palm_delta':[dx,dy,dz],'grass':grass_report}
(LOG/'site.json').write_text(json.dumps(report,indent=2),encoding='utf8')
print(json.dumps({k:v for k,v in report.items() if k not in ['archived_names','terrain_changed_indices','palm_group']},ensure_ascii=False))
''','terminal25_05_site.py','exec'),bpy.app.driver_namespace['terminal25'])
