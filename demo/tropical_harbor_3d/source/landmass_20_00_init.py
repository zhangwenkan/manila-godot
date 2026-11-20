# Payload for the verified isolated Blender MCP session only.
import bpy, os, math, json, ast, random, hashlib, numpy as np
from pathlib import Path
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree
ROOT=Path(bpy.data.filepath).parent.parent
OUT=ROOT/'assets/reference'
LOG=ROOT/'captures/landform_mass_20261120'
C=bpy.data.collections['Reference_Terrain']
fol=bpy.data.collections['Reference_Foliage']
town=bpy.data.collections['Reference_Town']
coast=bpy.data.collections['Reference_Coast']
rocks=bpy.data.collections['Reference_Rocks']
oldterrain=bpy.data.objects['S23_ContinuousCoastalLandform']
old_bvh=BVHTree.FromObject(oldterrain,bpy.context.evaluated_depsgraph_get())
def old_ground(x,z):
    hit,*_=old_bvh.ray_cast(Vector((x,-z,80)),Vector((0,0,-1)),300)
    return hit.z if hit else -15
def smooth(a,b,x):
    t=np.clip((x-a)/(b-a),0,1)
    return t*t*(3-2*t)
def shore(z):
    return 7.8+1.45*np.sin(z*.12)+.48*np.sin(z*.29)-21*smooth(-18.7,-26,z)
def center(ob):
    return sum((ob.matrix_world@Vector(p) for p in ob.bound_box),Vector())/8
def foot(ob):
    ps=[ob.matrix_world@v.co for v in ob.data.vertices]
    low=min(p.z for p in ps)
    bottom=[p for p in ps if p.z<low+.04]
    return sum(bottom,Vector())/len(bottom)
def suffix(ob):
    s=ob.name.rsplit('.',1)[-1]
    return int(s) if s.isdigit() else 0
BASE={o.name:o.matrix_world.copy() for o in bpy.data.objects if o.type=='MESH'}
SITES=json.loads((ROOT/'captures/harbor_composition_20261120/layout_authored.json').read_text(encoding='utf8'))['sites']
scene_info={'pid':os.getpid(),'source':bpy.data.filepath,'terrain':[(o.name,len(o.data.vertices)) for o in C.objects], 'site_ground':[(s['name'],s['center'][0],s['gz'],old_ground(s['center'][0],s['gz'])) for s in SITES]}
print(json.dumps(scene_info))
(LOG/'source_before.json').write_text(json.dumps(scene_info,indent=2),encoding='utf8')
bpy.app.driver_namespace['landmass20']=globals()
