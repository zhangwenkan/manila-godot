"""Rooted grass margins and partly buried fragments. Run through owned MCP."""
import bpy,json,math,random,numpy as np
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT=Path(bpy.data.filepath).parent.parent;LOG=ROOT/'captures/ground_integration_20261123';OUT=ROOT/'assets/reference'
terrain=bpy.data.objects['C25_ContourBuiltCoast'];bpy.context.view_layer.update()
bvh=BVHTree.FromObject(terrain,bpy.context.evaluated_depsgraph_get())
land=np.load(str(LOG/'land_data.npz'))['land'];n=len(land)
collection=bpy.data.collections.get('Reference_GroundCover')
if collection:
    for ob in list(collection.objects):bpy.data.objects.remove(ob,do_unlink=True)
else:
    collection=bpy.data.collections.new('Reference_GroundCover');bpy.context.scene.collection.children.link(collection)
def role(x,z):return land[min(n-1,max(0,int((z+15)/97*n))),min(n-1,max(0,int((x+4)/48*n)))]
def linear(v):return v/12.92 if v<=.04045 else ((v+.055)/1.055)**2.4
def mat(name):
    m=bpy.data.materials.get(name) or bpy.data.materials.new(name);m.use_nodes=True
    ns=m.node_tree.nodes;pr=next(n for n in ns if n.type=='BSDF_PRINCIPLED')
    pr.inputs['Roughness'].default_value=.94
    color=ns.get('G23Color') or ns.new('ShaderNodeVertexColor');color.name='G23Color';color.layer_name='Color'
    m.node_tree.links.new(color.outputs['Color'],pr.inputs['Base Color'])
    return m
def meshob(name,verts,faces,colors,material):
    m=bpy.data.meshes.new(name);m.from_pydata(verts,[],faces);m.update();m.materials.append(material)
    ca=m.color_attributes.new(name='Color',type='FLOAT_COLOR',domain='POINT');m.color_attributes.active_color=ca
    ca.data.foreach_set('color',np.array(colors,np.float32).ravel())
    ob=bpy.data.objects.new(name,m);collection.objects.link(ob);return ob
# Protect actual building/platform footprints, so the new grass never coats floors.
boxes=[]
for colname in ('Reference_Town','Reference_Coast'):
    for ob in bpy.data.collections[colname].objects:
        if ob.type!='MESH' or not any(s in ob.name for s in ('Floor','Step','Deck','Platform','Foundation')):continue
        corners=[ob.matrix_world@Vector(p) for p in ob.bound_box]
        boxes.append((min(p.x for p in corners)-.12,max(p.x for p in corners)+.12,
                      min(-p.y for p in corners)-.12,max(-p.y for p in corners)+.12))
def obstructed(x,z):return any(a<x<b and c<z<d for a,b,c,d in boxes)
verts=[];faces=[];cols=[];rng=random.Random(2334);roots=[];basal_gaps=[];root_gaps=[]
for z0 in np.arange(-6,62,.135):
  for x0 in np.arange(8,31,.135):
    x=float(x0)+rng.uniform(-.055,.055);z=float(z0)+rng.uniform(-.055,.055);r=role(x,z)
    if r[0]<.38 or r[2]>.36 or r[1]>.42:continue
    neighbors=[role(x+.23,z)[0],role(x-.23,z)[0],role(x,z+.23)[0],role(x,z-.23)[0]]
    edge=max(neighbors)-min(neighbors)
    patch=(math.sin(x*1.4+z*.53)+math.sin(x*.63-z*1.13))*.5
    # Broken rooted clumps, with intervals of worn/short growth at contacts.
    # A uniform dense fringe makes another artificial stripe around every role.
    chance=(.70 if patch>.20 else .25) if edge>.19 else (.25 if patch>.20 else .07)
    if rng.random()>chance or obstructed(x,z):continue
    hit,no,_,_=bvh.ray_cast(Vector((x,-z,40)),Vector((0,0,-1)),100)
    if hit is None or hit.z<.4 or no.z<.60:continue
    roots.append((x,z,float(hit.z)));tone=rng.uniform(-.022,.028)
    base=(.31+tone,.418+tone,.132+tone*.45)
    direction=rng.uniform(0,math.tau)
    for blade in range(rng.randint(4,6)):
        a=direction+rng.uniform(-1.5,1.5);dx,dz=math.cos(a),math.sin(a)
        off=rng.uniform(0,.038);px=x+dx*off;pz=z+dz*off
        bh,_,_,_=bvh.ray_cast(Vector((px,-pz,40)),Vector((0,0,-1)),100)
        if bh is None:continue
        hh=rng.uniform(.065,.145);width=rng.uniform(.018,.035);lean=rng.uniform(.025,.075)
        corners=[(px-dz*width,-pz-dx*width),(px+dz*width,-pz+dx*width)]
        supports=[bvh.ray_cast(Vector((cx,cy,40)),Vector((0,0,-1)),100)[0] for cx,cy in corners]
        if any(p is None for p in supports):continue
        base_z=min(bh.z,*(p.z for p in supports))-.008
        root_gaps.append(float(base_z-bh.z));basal_gaps.extend(float(base_z-p.z) for p in supports)
        j=len(verts);verts.extend([(corners[0][0],corners[0][1],base_z),(corners[1][0],corners[1][1],base_z),(px+dx*lean,-pz-dz*lean,base_z+.008+hh)])
        faces.append((j+1,j,j+2))
        for tip in (0,0,1):cols.append(tuple(linear(min(1,max(0,v+(0.025 if tip else -.007)))) for v in base)+(1,))
grass=meshob('G23_RootedGrassMargins',verts,faces,cols,mat('G23_LivingGrass'))
# Local fragments collect at exposed soil/rock feet and sandy cut mouths.
# They are sparse and partly embedded, never a uniformly spaced border necklace.
verts=[];faces=[];cols=[];fragments=[];rng=random.Random(2355)
for k in range(2200):
    x=rng.uniform(8.5,24);z=rng.uniform(-4,61);r=role(x,z)
    if r[2]>.32 or r[0]>.86 or obstructed(x,z):continue
    near=[role(x+.45,z),role(x-.45,z),role(x,z+.45),role(x,z-.45)]
    rocknear=max(t[1] for t in near);soilnear=max(t[3] for t in near)
    if rocknear<.25 and soilnear<.36:continue
    hit,no,_,_=bvh.ray_cast(Vector((x,-z,40)),Vector((0,0,-1)),100)
    if hit is None or hit.z<.26 or no.z<.78:continue
    if rng.random()>.28:continue
    radius=rng.uniform(.065,.19)*(1.3 if rocknear>.3 else 1)
    depth=radius*rng.uniform(.28,.58);ang=rng.uniform(0,math.tau)
    j=len(verts);count=6
    # Two irregular rings and a shallow top; bottom is below the continuous soil.
    for ring in (0,1):
      for q in range(count):
        a=ang+q*math.tau/count;rr=radius*rng.uniform(.82,1.13)*(1 if ring==0 else .68)
        verts.append((x+math.cos(a)*rr,-z+math.sin(a)*rr*.72,hit.z+(-depth*.45 if ring==0 else depth*rng.uniform(.6,1))))
    verts.append((x+radius*.1,-z,hit.z+depth*1.13))
    for q in range(count):
        nq=(q+1)%count;faces.extend([(j+q,j+nq,j+count+nq,j+count+q),(j+count+q,j+count+nq,j+12)])
    faces.append(tuple(j+i for i in reversed(range(count))))
    base=np.array([.43,.425,.355]) if rocknear>.25 else np.array([.45,.365,.245])
    base+=rng.uniform(-.035,.045)
    cols.extend([tuple(linear(float(np.clip(v,0,1))) for v in base)+(1,)]*13)
    fragments.append((x,z,float(hit.z),radius))
stones=meshob('G23_EmbeddedSlopeFragments',verts,faces,cols,mat('G23_FragmentStone'))
for ob in (grass,stones):
    ob['ground23_origin']='Authored via GUI Blender MCP; roots embedded in actual terrain'
bpy.ops.object.select_all(action='DESELECT')
grass.select_set(True);stones.select_set(True);bpy.context.view_layer.objects.active=grass
bpy.ops.export_scene.gltf(filepath=str(OUT/'ground_cover.glb'),export_format='GLB',use_selection=True,export_apply=True,export_yup=True,export_materials='EXPORT',export_vertex_color='ACTIVE')
assert max(root_gaps)<0 and max(basal_gaps)<0
(LOG/'contacts.json').write_text(json.dumps({'grass_clumps':len(roots),'grass_triangles':len(grass.data.polygons),'fragments':len(fragments),'grounded_roots':roots,'fragments_centers':fragments,'protected_footprints':len(boxes),'grass_root_gap_range_m':[min(root_gaps),max(root_gaps)],'grass_basal_corner_gap_range_m':[min(basal_gaps),max(basal_gaps)],'floating_basal_corners':sum(v>0 for v in basal_gaps)},indent=2),encoding='utf8')
print(json.dumps({'grass_clumps':len(roots),'grass_blades':len(grass.data.polygons),'embedded_fragments':len(fragments),'new_asset':'ground_cover.glb'}))
