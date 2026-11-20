import bpy, os, json, ast, math, random, numpy as np
from pathlib import Path
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree
from mathutils.geometry import delaunay_2d_cdt
ROOT=Path(bpy.data.filepath).parent.parent;OUT=ROOT/'assets/reference';LOG=ROOT/'captures/shore_control_mesh_20261120'
C=bpy.data.collections['Reference_Terrain'];fol=bpy.data.collections['Reference_Foliage'];town=bpy.data.collections['Reference_Town'];coast=bpy.data.collections['Reference_Coast'];rocks=bpy.data.collections['Reference_Rocks']
terrain=bpy.data.objects['L24_AuthoredCoastalMasses'];old_bvh=BVHTree.FromObject(terrain,bpy.context.evaluated_depsgraph_get())
def old_ground(x,z):
    hit,*_=old_bvh.ray_cast(Vector((x,-z,80)),Vector((0,0,-1)),300)
    return hit.z if hit else -15
def smooth(a,b,x):
    t=np.clip((x-a)/(b-a),0,1);return t*t*(3-2*t)
def shore(z):return 7.8+1.45*np.sin(z*.12)+.48*np.sin(z*.29)-21*smooth(-18.7,-26,z)
SITES=json.loads((ROOT/'captures/harbor_composition_20261120/layout_authored.json').read_text(encoding='utf8'))['sites']
BASE={o.name:o.matrix_world.copy() for o in bpy.data.objects if o.type=='MESH'}
print('OWNED',os.getpid(),bpy.data.filepath,'terrain',len(terrain.data.vertices))
print(delaunay_2d_cdt.__doc__)
print('grid endpoints',[(i,tuple(terrain.data.vertices[i].co)) for i in [0,16,85,145,146,147]])
bpy.app.driver_namespace['control20']=globals()
