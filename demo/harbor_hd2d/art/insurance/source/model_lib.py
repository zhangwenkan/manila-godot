"""Shared Blender-only modeling helpers. Coordinates are Z-up, facade faces -Y."""
import bpy
import bmesh
import math
from mathutils import Vector
from pathlib import Path

SOURCE = Path(__file__).parent
SCENE_NAME = "Insurance_Model_v5"
PREFIX = "INS_"


def scene():
    return bpy.data.scenes[SCENE_NAME]


def collection():
    return bpy.data.collections["INS_Model"]


def group(name, parent=None, position=(0, 0, 0)):
    obj = bpy.data.objects.new(name, None)
    collection().objects.link(obj)
    obj.parent = parent
    obj.location = position
    return obj


def mesh(name, vertices, faces, material, parent=None, bevel=0):
    data = bpy.data.meshes.new(name + "_mesh")
    data.from_pydata(vertices, [], faces)
    data.update()
    bm = bmesh.new()
    bm.from_mesh(data)
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    bm.to_mesh(data)
    bm.free()
    obj = bpy.data.objects.new(name, data)
    collection().objects.link(obj)
    obj.parent = parent
    if material:
        data.materials.append(bpy.data.materials[material])
    uv = data.uv_layers.new(name="SurfaceUV")
    for poly in data.polygons:
        axis = max(range(3), key=lambda i: abs(poly.normal[i]))
        axes = [(1, 2), (0, 2), (0, 1)][axis]
        coords = [(data.vertices[data.loops[i].vertex_index].co[axes[0]], data.vertices[data.loops[i].vertex_index].co[axes[1]]) for i in poly.loop_indices]
        lo = [min(c[k] for c in coords) for k in range(2)]
        span = [max(c[k] for c in coords) - lo[k] for k in range(2)]
        for i, coord in zip(poly.loop_indices, coords):
            uv.data[i].uv = tuple((coord[k] - lo[k]) / max(span[k], 0.0001) for k in range(2))
    if bevel:
        modifier = obj.modifiers.new("Crafted edge", "BEVEL")
        modifier.width = bevel
        modifier.segments = 1
        modifier.affect = "EDGES"
    return obj


def box(name, position, size, material, parent=None, bevel=0.015):
    x, y, z = (v * 0.5 for v in size)
    vertices = [(-x,-y,-z),(x,-y,-z),(x,y,-z),(-x,y,-z),(-x,-y,z),(x,-y,z),(x,y,z),(-x,y,z)]
    faces = [(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)]
    obj = mesh(name, vertices, faces, material, parent, bevel)
    obj.location = position
    return obj


def beam(name, a, b, width, material, parent=None, depth=None, bevel=0.012):
    a, b = Vector(a), Vector(b)
    obj = box(name, (a + b) * .5, (width, width if depth is None else depth, (b-a).length), material, parent, bevel)
    obj.rotation_mode = "QUATERNION"
    obj.rotation_quaternion = (b-a).to_track_quat('Z', 'Y')
    return obj


def cylinder(name, position, radius, depth, material, parent=None, vertices=12, direction=(0,0,1), top_radius=None):
    r2 = radius if top_radius is None else top_radius
    points = [(r * math.cos(i*math.tau/vertices), r * math.sin(i*math.tau/vertices), z) for r,z in [(radius,-depth/2),(r2,depth/2)] for i in range(vertices)]
    faces = [tuple(reversed(range(vertices))), tuple(range(vertices,vertices*2))]
    faces += [(i,(i+1)%vertices,(i+1)%vertices+vertices,i+vertices) for i in range(vertices)]
    obj = mesh(name, points, faces, material, parent, .008)
    obj.location = position
    obj.rotation_mode = "QUATERNION"
    obj.rotation_quaternion = Vector(direction).to_track_quat('Z','Y')
    return obj


def tube(name, points, radius, material, parent=None, sides=8):
    points = [Vector(p) for p in points]
    vertices = []
    for i, p in enumerate(points):
        tangent = points[min(i+1,len(points)-1)]-points[max(0,i-1)]
        q = tangent.to_track_quat('Z','Y')
        for j in range(sides):
            vertices.append(p + q @ Vector((radius*math.cos(j*math.tau/sides),radius*math.sin(j*math.tau/sides),0)))
    faces = [tuple(reversed(range(sides))),tuple(range((len(points)-1)*sides,len(points)*sides))]
    for i in range(len(points)-1):
        for j in range(sides):
            faces.append((i*sides+j,i*sides+(j+1)%sides,(i+1)*sides+(j+1)%sides,(i+1)*sides+j))
    return mesh(name, vertices, faces, material, parent)


def ring(name, center, radius, thickness, material, parent=None, plane="XY", steps=24):
    points=[]
    for i in range(steps+1):
        a=i*math.tau/steps
        u,v=radius*math.cos(a),radius*math.sin(a)
        delta={"XY":(u,v,0),"XZ":(u,0,v),"YZ":(0,u,v)}[plane]
        points.append(Vector(center)+Vector(delta))
    return tube(name,points,thickness,material,parent)


def slab(name, outline, thickness, material, parent=None):
    top=[Vector(p) for p in outline]
    normal=(top[1]-top[0]).cross(top[2]-top[0]).normalized()
    if normal.z<0:
        top.reverse()
        normal=-normal
    vertices=top+[p-normal*thickness for p in top]
    n=len(top)
    faces=[tuple(range(n)),tuple(reversed(range(n,n*2)))]
    faces += [(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
    return mesh(name,vertices,faces,material,parent,.015)


def text(name, body, position, width, material, parent=None, size=.4):
    data=bpy.data.curves.new(name+"_font","FONT")
    data.body=body
    data.align_x='CENTER'
    data.align_y='CENTER'
    data.size=size
    data.extrude=.007
    data.bevel_depth=.001
    data.resolution_u=2
    obj=bpy.data.objects.new(name,data)
    collection().objects.link(obj)
    obj.parent=parent
    obj.location=position
    obj.rotation_euler=(math.pi/2,0,0)
    bpy.context.view_layer.update()
    scale=width/max(obj.dimensions.x,.001)
    obj.scale=(scale,scale,scale)
    depsgraph=bpy.context.evaluated_depsgraph_get()
    converted=bpy.data.meshes.new_from_object(obj.evaluated_get(depsgraph),depsgraph=depsgraph)
    original=obj.data
    replacement=bpy.data.objects.new(name+"_letters",converted)
    collection().objects.link(replacement)
    replacement.parent=parent
    replacement.matrix_basis=obj.matrix_basis.copy()
    converted.materials.append(bpy.data.materials[material])
    bpy.data.objects.remove(obj,do_unlink=True)
    bpy.data.curves.remove(original)
    return replacement


def material(name, color, texture=None, metallic=0.0, roughness=.88):
    m=bpy.data.materials.new(name)
    m.diffuse_color=(*color,1)
    m.use_nodes=True
    p=m.node_tree.nodes.get('Principled BSDF')
    p.inputs['Base Color'].default_value=(*color,1)
    p.inputs['Roughness'].default_value=roughness
    p.inputs['Metallic'].default_value=metallic
    p.inputs['Specular IOR Level'].default_value=.12
    if texture:
        image=bpy.data.images.load(str(SOURCE/'textures'/texture),check_existing=True)
        image.pack()
        tex=m.node_tree.nodes.new('ShaderNodeTexImage')
        tex.image=image
        tex.interpolation='Closest'
        m.node_tree.links.new(tex.outputs['Color'],p.inputs['Base Color'])
    return m


def activate():
    bpy.context.window.scene=scene()
    return bpy.data.objects['InsuranceAsset']


def export_glb(path):
    path=Path(path)
    if path.exists():
        raise RuntimeError('Refusing to overwrite '+str(path))
    root=activate()
    for obj in bpy.context.view_layer.objects:
        obj.select_set(False)
    whitelist=[root]+list(root.children_recursive)
    for obj in whitelist:
        assert obj.type in ['EMPTY','MESH'], (obj.name,obj.type)
        obj.select_set(True)
    bpy.context.view_layer.objects.active=root
    bpy.ops.export_scene.gltf(filepath=str(path),export_format='GLB',use_selection=True,use_active_scene=True,export_yup=True,export_apply=True,export_cameras=False,export_lights=False,export_animations=False,export_materials='EXPORT',export_image_format='AUTO')
    print('GLB_EXPORTED',str(path),len(whitelist))
