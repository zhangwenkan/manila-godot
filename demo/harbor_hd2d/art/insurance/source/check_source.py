"""Read-only check: run with Blender --background insurance.blend --python this_file."""
import bpy, json
assert len(bpy.data.scenes)==1, [s.name for s in bpy.data.scenes]
s=bpy.data.scenes[0]
assert s.name=='InsuranceAssetSource'
assert all(o.type in ['MESH','EMPTY'] for o in s.objects)
assert all(o.name not in ['Cube','Camera','Light','INS_ReviewCamera','INS_Key'] for o in s.objects)
root=bpy.data.objects['InsuranceAsset']
assert set(o.name for o in root.children)=={'Office','Roof','Crane','Dock','Props','Tug'}
images=[i for i in bpy.data.images if i.type=='IMAGE']
assert len(images)==4 and all(i.packed_file for i in images)
assert all(i.size[0]>0 and i.size[1]>0 for i in images)
assert len(root.children_recursive)==len(s.objects)-1
assert all(m.materials for m in bpy.data.meshes if m.users)
assert not any('Blockout' in o.name for o in s.objects)
print('INSURANCE_BLEND_PASS',json.dumps({'objects':len(s.objects),'packed_images':[i.name for i in images],'camera':s.camera.name if s.camera else None}))
