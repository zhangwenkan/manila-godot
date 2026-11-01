"""Read-only check after reopening the delivered complete .blend in a new process."""
from pathlib import Path
import math
import bpy
import bmesh
from mathutils import Vector
from mathutils.bvhtree import BVHTree

assert bpy.app.background
filename=Path(bpy.data.filepath).name
assert filename in {'insurance_rebuild_r2.blend','insurance_rebuild_r2_1.blend'}
patched=filename=='insurance_rebuild_r2_1.blend'
assert len(bpy.data.scenes)==1
scene=bpy.data.scenes[0]
assert scene.name=='Insurance_Rebuild_R2'
meshes=[o for o in scene.objects if o.type=='MESH']
assert len(meshes)==(523 if patched else 521)
assert all(o.type in {'MESH','EMPTY'} for o in scene.objects)
assert all(o.name.startswith('INR2_') for o in scene.objects)
assert {o.parent.name for o in meshes}=={'INR2_'+name for name in ['Office','Roof','Crane','Dock','Props','Tug']}
images=set(); triangles=0
for obj in meshes:
    bm=bmesh.new(); bm.from_mesh(obj.data)
    assert all(e.is_manifold for e in bm.edges),obj.name
    assert all(f.calc_area()>1e-9 for f in bm.faces),obj.name
    assert bm.calc_volume()>0,obj.name
    bm.free()
    obj.data.calc_loop_triangles(); triangles+=len(obj.data.loop_triangles)
    assert all(not p.use_smooth for p in obj.data.polygons)
    assert len(obj.data.uv_layers)==1 and obj.data.uv_layers.active.name=='PixelUV'
    for material in obj.data.materials:
        assert material.name.startswith('INR2_')
        bsdf=material.node_tree.nodes.get('Principled BSDF')
        assert bsdf.inputs['Roughness'].default_value==1
        assert bsdf.inputs['Metallic'].default_value==0
        assert bsdf.inputs['Specular IOR Level'].default_value==0
        assert not bsdf.inputs['Normal'].is_linked
        for node in material.node_tree.nodes:
            if node.type=='TEX_IMAGE':
                assert node.interpolation=='Closest' and node.image.packed_file
                images.add(node.image)
assert sorted(tuple(i.size) for i in images)==[(512,128),(512,512)]
for name in ['INR2_InsuranceSignLetterFace','INR2_CargoCraneSignLetterFace']:
    obj=scene.objects[name]; uv=obj.data.uv_layers.active
    front=[p for p in obj.data.polygons if p.normal.y<-.9]
    assert len(front)==1
    points=[uv.data[i].uv for i in front[0].loop_indices]
    assert max(p.x for p in points)-min(p.x for p in points)>.4
    assert max(p.y for p in points)-min(p.y for p in points)>.3

# Rays from inside the office must meet the back, both sides, floor and roof.
vertices=[]; faces=[]
for obj in meshes:
    if obj.parent.name not in {'INR2_Office','INR2_Roof'}: continue
    offset=len(vertices)
    vertices.extend(obj.matrix_world@v.co for v in obj.data.vertices)
    faces.extend(tuple(offset+i for i in poly.vertices) for poly in obj.data.polygons)
bvh=BVHTree.FromPolygons(vertices,faces)
for origin,direction,limit in [((-2.45,0,1.1),(0,1,0),3.7),((-2.45,0,1.1),(-1,0,0),3.8),((-2.45,0,1.1),(1,0,0),3.8),((-2.45,0,1.1),(0,0,-1),.7),((-2.45,0,1.1),(0,0,1),4.5)]:
    hit=bvh.ray_cast(Vector(origin),Vector(direction),limit)
    assert hit[0] is not None,(origin,direction)
assert scene.objects.get('INR2_RearGable') and scene.objects.get('INR2_HighRoofEnclosedTier')
if patched:
    vertices=[]; faces=[]; names=[]
    for obj in meshes:
        offset=len(vertices)
        vertices.extend(obj.matrix_world@v.co for v in obj.data.vertices)
        faces.extend(tuple(offset+i for i in p.vertices) for p in obj.data.polygons)
        names.extend([obj.name]*len(obj.data.polygons))
    bvh=BVHTree.FromPolygons(vertices,faces)
    direction=Vector((0,-math.cos(math.radians(42)),math.sin(math.radians(42))))
    for name in ['INR2_InsuranceSignLetterFace','INR2_CargoCraneSignLetterFace']:
        obj=scene.objects[name]
        for i in range(19):
            for j in range(9):
                point=obj.matrix_world@Vector(((-.45+i*.05)*obj.dimensions.x,-.021,(-.4+j*.1)*obj.dimensions.z))
                hit=bvh.ray_cast(point+direction*25,-direction,25.02)
                assert hit[2] is not None and names[hit[2]]==name,(name,i,j)
    for name in ['TugCabin','TugEngineBox','OperatorBox']:
        obj=scene.objects['INR2_'+name]
        for side in [-1,1]:
            direction=Vector((side,0,0))
            point=obj.matrix_world@Vector((side*obj.dimensions.x*.5,0,-obj.dimensions.z*.23))
            hit=bvh.ray_cast(point+direction*10,-direction,10.02)
            assert hit[2] is not None and names[hit[2]]==obj.name,(name,side)
    print('R2_1_CLEARANCE_CHECK_PASS sign regions sampled clear; colored cabin/engine side faces exposed')
print('R2_SOURCE_CHECK_PASS',len(meshes),'closed positive-volume parts;',triangles,'triangles; shared sign UVs and packed textures; interior rays hit rear/sides/floor/roof')
print('LIMIT: ray probes do not prove every seam or cross-object intersection; rear design inferred; visual quality separate')
