"""Targeted R2.1 repairs via local Blender-MCP; preserve the first R2 files."""
from pathlib import Path
import sys
import json
import math
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree
sys.path.insert(0,str(Path(__file__).resolve().parent))
from rebuild_lib import *

verify_input()
b=current_model()
assert b.scene.get('export_complete') and not b.scene.get('clearance_patch_complete')
library=fresh(SOURCE/'insurance_r2_1_library.blend')
output=fresh(ASSET/'insurance_rebuild_r2_1.glb')
record=fresh(SOURCE/'clearance_patch_record.json')


def scene_bvh():
    vertices=[]; faces=[]; names=[]
    for obj in b.parts:
        offset=len(vertices)
        vertices.extend(obj.matrix_world@v.co for v in obj.data.vertices)
        faces.extend(tuple(offset+i for i in p.vertices) for p in obj.data.polygons)
        names.extend([obj.name]*len(obj.data.polygons))
    return BVHTree.FromPolygons(vertices,faces),names


def sign_hits(tree,names):
    direction=Vector((0,-math.cos(math.radians(42)),math.sin(math.radians(42))))
    results={}
    for short in ['InsuranceSignLetterFace','CargoCraneSignLetterFace']:
        obj=b.scene.objects[PREFIX+short]
        width,height=obj.dimensions.x,obj.dimensions.z
        hits=[]
        for i in range(19):
            for j in range(9):
                point=obj.matrix_world@Vector(((-.45+i*.05)*width,-.021,(-.4+j*.1)*height))
                hit=tree.ray_cast(point+direction*25,-direction,25.02)
                hits.append(names[hit[2]] if hit[2] is not None else None)
        results[short]={'samples':len(hits),'obstructed_by':sorted(set(h for h in hits if h!=obj.name),key=str),'clear':sum(h==obj.name for h in hits)}
    return results


def exterior_hits(tree,names):
    results={}
    for short in ['TugCabin','TugEngineBox','OperatorBox']:
        obj=b.scene.objects[PREFIX+short]; hits={}
        for label,direction in [('front',Vector((0,-1,0))),('left',Vector((-1,0,0))),('right',Vector((1,0,0)))]:
            point=obj.matrix_world@Vector((direction.x*obj.dimensions.x*.5,direction.y*obj.dimensions.y*.5,0))
            # Body mid-height, below the windows, rather than a decorative inset.
            point.z=obj.location.z-obj.dimensions.z*.23
            hit=tree.ray_cast(point+direction*10,-direction,10.02)
            hits[label]=names[hit[2]] if hit[2] is not None else None
        results[short]=hits
    return results


with preserve_session():
    switch(b.scene)
    bpy.context.view_layer.update()
    tree,names=scene_bvh()
    before={'signs':sign_hits(tree,names),'body_faces':exterior_hits(tree,names)}
    assert before['signs']['InsuranceSignLetterFace']['obstructed_by']

    # Put the entire sign assembly ahead of the eave and add actual wall mounts.
    for suffix in ['Frame','InsetRim','LetterFace']:
        obj=b.scene.objects[PREFIX+'InsuranceSign'+suffix]
        obj.location.y-=.37
    for x in [-3.85,-1.05]:
        b.box('InsuranceSignWallMount'+str(x),(x,-1.61,3.70),(.11,.44,.17),'Office',mat='WoodDark')

    # Close the small gable-to-roof seam without filling the facade apertures.
    for short in ['FrontGable','RearGable']:
        obj=b.scene.objects[PREFIX+short]
        for vertex in obj.data.vertices:
            if vertex.co.z>4.0:
                vertex.co.z=4.75
            else:
                vertex.co.x=-2.45+(vertex.co.x+2.45)*(7.44/7.20)
        obj.data.update()

    # A solid oversized "outline" box concealed the colored cabin/engine walls.
    # Turn these into thin foundation rims, not full enclosing black volumes.
    changes=[('TugCabinShadow',1.10,(1.47,1.36,.12)),
             ('TugEngineBoxDark',1.045,(.97,1.24,.10)),
             ('OperatorBoxOutline',6.29,(1.20,1.0,.15))]
    for short,z,size in changes:
        obj=b.scene.objects[PREFIX+short]
        old=tuple(obj.dimensions)
        for vertex in obj.data.vertices:
            vertex.co=Vector(tuple(vertex.co[i]*size[i]/old[i] for i in range(3)))
        obj.location.z=z
        obj.data.update()
    bpy.context.view_layer.update()
    tree,names=scene_bvh()
    after={'signs':sign_hits(tree,names),'body_faces':exterior_hits(tree,names)}
    assert all(not value['obstructed_by'] for value in after['signs'].values()),after
    assert all('Shadow' not in (hit or '') and 'BoxDark' not in (hit or '') and 'BoxOutline' not in (hit or '') for values in after['body_faces'].values() for hit in values.values()),after
    b.scene['clearance_patch_complete']=True
    b.root['revision']='R2.1: sign clearance, gable seam, exposed cabin/engine sides'
    bpy.data.libraries.write(str(library),{b.scene},fake_user=True,compress=True)

    # Temporarily reserve the six runtime names, leaving the first export intact.
    old_export=bpy.data.scenes['Insurance_R2_Export']
    reserved=[(obj,obj.name) for obj in old_export.objects]
    export=None
    try:
        for obj,name in reserved: obj.name='R2Initial_'+name
        export=bpy.data.scenes.new('Insurance_R2_1_Export'); switch(export)
        root=bpy.data.objects.new('InsuranceRebuildR2',None); export.collection.objects.link(root)
        for name,group in b.groups.items():
            copies=[]
            for original in b.parts:
                if original.parent!=group: continue
                mesh=original.data.copy(); mesh.transform(original.matrix_world)
                obj=bpy.data.objects.new('R2PatchExportPart',mesh); export.collection.objects.link(obj); copies.append(obj)
            assert copies
            bpy.ops.object.select_all(action='DESELECT')
            for obj in copies: obj.select_set(True)
            bpy.context.view_layer.objects.active=copies[0]; bpy.ops.object.join()
            joined=copies[0]; joined.name='INS_'+name+'Geometry'; joined.parent=root
            assert joined.name=='INS_'+name+'Geometry'
            assert len(joined.data.uv_layers)==1 and joined.data.uv_layers.active.name=='PixelUV'
        bpy.ops.object.select_all(action='SELECT')
        bpy.ops.export_scene.gltf(filepath=str(output),export_format='GLB',use_selection=True,use_active_scene=True,export_yup=True,export_apply=True,export_cameras=False,export_lights=False,export_animations=False,export_image_format='AUTO')
    finally:
        switch(b.scene)
        if export:
            for obj in list(export.objects):
                mesh=obj.data if obj.type=='MESH' else None
                bpy.data.objects.remove(obj,do_unlink=True)
                if mesh and mesh.users==0: bpy.data.meshes.remove(mesh)
            bpy.data.scenes.remove(export)
        for obj,name in reserved: obj.name=name
    record.write_text(json.dumps({'revision':'r2_1','input_sha256':SHA,'parts':len(b.parts),'before':before,'after':after,'limit':'Ray checks establish sampled visibility, not screen-space legibility or art approval. Rear remains inferred.'},indent=2),encoding='utf-8')
    print('R2_1_CLEARANCE_FIXED',json.dumps(after),'parts',len(b.parts))
verify_input()
