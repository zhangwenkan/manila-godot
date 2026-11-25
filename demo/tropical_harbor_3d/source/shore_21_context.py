# Definitions only. Loaded inside the verified Blender MCP session.
import bpy, os, json, ast, math, numpy as np
from pathlib import Path
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree
ROOT=Path(bpy.data.filepath).parent.parent
OUT=ROOT/'assets/reference'
LOG=ROOT/'captures/shore_refinement_20261121'
terrain=bpy.data.objects['C25_ContourBuiltCoast']
mesh=terrain.data
def smooth(a,b,x):
    t=np.clip((x-a)/(b-a),0,1)
    return t*t*(3-2*t)
def shore(z):
    return 7.8+1.45*np.sin(z*.12)+.48*np.sin(z*.29)-21*smooth(-18.7,-26,z)
def ground(x,z):
    hit,*_=ground_bvh.ray_cast(Vector((x,-z,80)),Vector((0,0,-1)),300)
    return hit.z if hit else -15
def bounds(o):
    pts=[o.matrix_world@Vector(v) for v in o.bound_box]
    return [[min(p[i] for p in pts),max(p[i] for p in pts)] for i in range(3)]
def center(o):
    return sum((o.matrix_world@Vector(v) for v in o.bound_box),Vector())/8
def export_land():
    bpy.ops.object.select_all(action='DESELECT')
    terrain.hide_set(False);terrain.select_set(True)
    bpy.context.view_layer.objects.active=terrain
    bpy.ops.export_scene.gltf(filepath=str(OUT/'terrain.glb'),export_format='GLB',use_selection=True,export_apply=True,export_yup=True,export_texcoords=True,export_normals=True,export_materials='EXPORT',export_vertex_color='ACTIVE')
def refresh_height():
    values=[round(ground(float(shore(z)+d),float(z)),5) for z in np.arange(-30,90.001,.25) for d in np.arange(-20,50.001,.25)]
    (OUT/'shore_relief_height.json').write_text(json.dumps({'d0':-20,'z0':-30,'step':.25,'columns':281,'rows':481,'heights':values}),encoding='utf8')
code=json.loads((ROOT/'source/reference_detail_01_materials.mcp.json').read_text(encoding='utf8'))['code']
for node in ast.parse(code).body:
    if isinstance(node,ast.FunctionDef) and node.name=='export_collection':
        exec(compile(ast.Module(body=[node],type_ignores=[]),'export','exec'),globals())
bpy.context.view_layer.update()
ground_bvh=BVHTree.FromObject(terrain,bpy.context.evaluated_depsgraph_get())
