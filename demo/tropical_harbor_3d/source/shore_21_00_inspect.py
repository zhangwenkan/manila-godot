import bpy, json, os
from mathutils import Vector
terrain=bpy.data.objects.get('C25_ContourBuiltCoast')
def bounds(o):
    pts=[o.matrix_world @ Vector(p) for p in o.bound_box]
    return [[round(min(p[i] for p in pts),3),round(max(p[i] for p in pts),3)] for i in range(3)]
print(json.dumps({'pid':os.getpid(),'file':bpy.data.filepath,'dirty':bpy.data.is_dirty,
 'collections':[(c.name,len(c.objects)) for c in bpy.data.collections if c.name.startswith('Reference')],
 'terrain':{'name':terrain.name,'bounds':bounds(terrain),'verts':len(terrain.data.vertices),'faces':len(terrain.data.polygons),'props':dict(terrain.items()),'materials':[m.name for m in terrain.data.materials]},
 'scene_props':dict(bpy.context.scene.items()),
 'text_blocks':[t.name for t in bpy.data.texts]},ensure_ascii=False,default=str))
