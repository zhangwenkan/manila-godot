"""Build a small editable wall/roof/portal/sign study through local Blender-MCP."""
from pathlib import Path
import sys
import math
import json
import bpy
import bmesh
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pixel_common import *

DENSITY = 24
TILE = {"wall": (4,4), "roof": (260,4), "red": (4,260), "wood": (260,260)}
FACES = [(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)]


def color(hex_value):
    values = [int(hex_value[i:i+2],16)/255 for i in (0,2,4)]
    return tuple(v/12.92 if v <= .04045 else ((v+.055)/1.055)**2.4 for v in values) + (1,)


class Builder:
    def __init__(self, scene):
        self.scene = scene
        self.collection = bpy.data.collections.new("INS7_SampleEditable")
        scene.collection.children.link(self.collection)
        self.root = self.empty("INS7_StyleSampleRoot")
        self.root["stage"] = "Material sample only; NOT the rebuilt complete asset"
        self.groups = {k:self.empty("INS7_"+k,self.root) for k in ("Office","Roof","Crane","Dock")}
        self.materials = {}
        self.parts = []
        self.mapping = []
        self.atlas = bpy.data.images.load(str(SOURCE / "textures/sample_atlas.png"), check_existing=False)
        self.signs = bpy.data.images.load(str(SOURCE / "textures/sample_signs.png"), check_existing=False)
        for image in [self.atlas,self.signs]:
            image.pack()
        self.material("Atlas", "ffffff", self.atlas)
        self.material("Signs", "ffffff", self.signs)
        for name, value in {"Ink":"303841","EdgeBlue":"394952","RedLight":"b65441","RedDark":"553233","Steel":"666762","Glass":"354853","GlassLight":"7d9699"}.items():
            self.material(name,value)

    def empty(self,name,parent=None):
        assert name not in bpy.data.objects
        obj = bpy.data.objects.new(name,None)
        self.collection.objects.link(obj)
        obj.parent = parent
        return obj

    def material(self,name,value,image=None):
        mat = bpy.data.materials.new("INS7_"+name)
        mat.diffuse_color = color(value)
        mat.use_nodes = True
        bsdf = mat.node_tree.nodes.get("Principled BSDF")
        bsdf.inputs["Base Color"].default_value = color(value)
        bsdf.inputs["Roughness"].default_value = 1
        bsdf.inputs["Metallic"].default_value = 0
        bsdf.inputs["Specular IOR Level"].default_value = 0
        if image:
            texture = mat.node_tree.nodes.new("ShaderNodeTexImage")
            texture.image = image
            texture.interpolation = "Closest"
            texture.extension = "EXTEND"
            mat.node_tree.links.new(texture.outputs["Color"],bsdf.inputs["Base Color"])
        self.materials[name] = mat
        return mat

    def mesh(self,name,verts,faces,group,kind=None,mat="Ink"):
        full_name = "INS7_"+name
        assert full_name not in bpy.data.objects
        data = bpy.data.meshes.new(full_name+"Mesh")
        data.from_pydata(verts,[],faces)
        data.update()
        bm = bmesh.new(); bm.from_mesh(data)
        bmesh.ops.recalc_face_normals(bm,faces=bm.faces)
        bm.to_mesh(data); bm.free()
        obj = bpy.data.objects.new(full_name,data)
        self.collection.objects.link(obj)
        obj.parent = self.groups[group]
        data.materials.append(self.materials["Atlas" if kind else mat])
        for face in data.polygons:
            face.use_smooth = False
        if kind:
            layer = data.uv_layers.new(name="PixelUV")
            x0,y0 = TILE[kind]
            for face in data.polygons:
                normal = face.normal
                first = data.vertices[data.loops[face.loop_start].vertex_index].co
                # Prefer local X as texture U; V follows the surface, without per-face stretching.
                u = Vector((1,0,0)) - normal * normal.x
                if u.length < .01:
                    u = Vector((0,1,0)) - normal * normal.y
                u.normalize()
                v = normal.cross(u).normalized()
                points = [data.vertices[data.loops[i].vertex_index].co for i in face.loop_indices]
                px = [p.dot(u) for p in points]; py = [p.dot(v) for p in points]
                dx,dy = max(px)-min(px),max(py)-min(py)
                assert max(dx,dy)*DENSITY <= 240, (name,dx,dy)
                for i,p in zip(face.loop_indices,points):
                    tx = x0+4+(p.dot(u)-min(px))*DENSITY
                    ty = y0+4+(max(py)-p.dot(v))*DENSITY
                    layer.data[i].uv = (tx/512,1-ty/512)
                self.mapping.append({"object":full_name,"face":face.index,"density":DENSITY,"max_extent_texels":max(dx,dy)*DENSITY})
        self.parts.append(obj)
        return obj

    def box(self,name,center,size,group,kind=None,mat="Ink"):
        x,y,z=[s/2 for s in size]
        verts=[(-x,-y,-z),(x,-y,-z),(x,y,-z),(-x,y,-z),(-x,-y,z),(x,-y,z),(x,y,z),(-x,y,z)]
        obj=self.mesh(name,verts,FACES,group,kind,mat)
        obj.location=center
        return obj

    def beam(self,name,a,b,width,depth=None,kind="red",mat="Ink"):
        start,end=Vector(a),Vector(b)
        obj=self.box(name,(start+end)/2,(width,depth or width,(end-start).length),"Crane",kind,mat)
        obj.rotation_mode="QUATERNION"
        obj.rotation_quaternion=(end-start).to_track_quat('Z','Y')
        return obj

    def sign(self,name,center,width,height,rect,group):
        x,y,z=center
        self.box(name+"Frame",(x,y+.035,z),(width+.16,.15,height+.16),group,mat="Ink")
        self.box(name+"RimTop",(x,y-.05,z+height/2+.035),(width+.08,.04,.04),group,mat="Steel")
        obj=self.box(name+"Face",(x,y-.055,z),(width,.04,height),group,mat="Signs")
        layer=obj.data.uv_layers.new(name="BitmapSignUV")
        left,top,right,bottom=rect
        for face in obj.data.polygons:
            if face.normal.y < -.9:
                for i in face.loop_indices:
                    p=obj.data.vertices[obj.data.loops[i].vertex_index].co
                    layer.data[i].uv=((left+(p.x/width+.5)*(right-left))/256,1-(top+(.5-p.z/height)*(bottom-top))/64)
            else:
                for i in face.loop_indices:
                    layer.data[i].uv=(.5,.05)
        obj["density_exception"]="Complete bitmap sign with readable margins"


verify_input()
fresh(ASSET / "insurance_pixel_sample.glb")
fresh(SOURCE / "sample_source_library.blend")
assert bpy.data.scenes.get(REFERENCE_SCENE) and bpy.data.scenes[REFERENCE_SCENE].get("stage_complete")
with preserve_session():
    scene=independent_scene(SAMPLE_SCENE)
    b=Builder(scene)
    # A facade slice, not the complete office: true window recess with dark return surfaces.
    b.box("WallLeft",(-4.2,0,2.05),(1.2,.25,2.9),"Office","wall")
    b.box("WallRight",(-.6,0,2.05),(2.4,.25,2.9),"Office","wall")
    b.box("WallBelowWindow",(-2.7,0,1.0),(1.8,.25,.8),"Office","wall")
    b.box("WallAboveWindow",(-2.7,0,3.25),(1.8,.25,.5),"Office","wall")
    b.box("WindowRecess",(-2.7,.16,2.2),(1.8,.10,1.6),"Office",mat="Glass")
    for x in [-3.65,-1.75]:
        b.box("WindowJamb"+str(x),(x,-.18,2.2),(.12,.15,1.76),"Office",mat="Ink")
    for z in [1.34,3.06]:
        b.box("WindowSill"+str(z),(-2.7,-.20,z),(2.04,.22,.12),"Office",mat="Ink")
    for x in [-3.0,-2.4]:
        b.box("WindowMullion"+str(x),(x,-.03,2.2),(.07,.09,1.6),"Office",mat="EdgeBlue")
    b.box("WindowTransom",(-2.7,-.03,2.2),(1.8,.09,.07),"Office",mat="EdgeBlue")
    b.box("WindowReflection",(-3.25,.099,2.72),(.37,.015,.20),"Office",mat="GlassLight")
    b.box("WallBottomTrim",(-2.1,-.17,.64),(5.52,.12,.14),"Office",mat="EdgeBlue")
    # Flat roof plates with actual thickness and no smoothing/subdivision.
    for side in [-1,1]:
        xc=-2.1
        x1=xc if side==1 else xc-3
        x2=xc+3 if side==1 else xc
        z1,z2=(4.9,3.85) if side==1 else (3.85,4.9)
        verts=[(x1,-.45,z1-.14),(x2,-.45,z2-.14),(x2,2.1,z2-.14),(x1,2.1,z1-.14),(x1,-.45,z1),(x2,-.45,z2),(x2,2.1,z2),(x1,2.1,z1)]
        b.mesh("RoofPlate"+str(side),verts,FACES,"Roof","roof")
        edge=b.box("Fascia"+str(side),((x1+x2)/2,-.50,(z1+z2)/2-.04),(math.hypot(x2-x1,z2-z1),.13,.16),"Roof",mat="Ink")
        edge.rotation_euler.y=-math.atan2(z2-z1,x2-x1)
    # A closed triangular gable completes the wall/roof junction in this facade slice.
    b.mesh("Gable",[(-4.8,-.125,3.5),(.6,-.125,3.5),(-2.1,-.125,4.77),(-4.8,.125,3.5),(.6,.125,3.5),(-2.1,.125,4.77)],[(0,2,1),(3,4,5),(0,1,4,3),(1,2,5,4),(2,0,3,5)],"Office","wall")
    b.box("Ridge",(-2.1,.825,4.94),(.18,2.72,.10),"Roof",mat="Steel")
    b.sign("OfficeSign",(-2.1,-.29,3.61),5.0,1.0,(4,4,124,28),"Office")
    # Coarse portal and two large triangular openings; no dense decorative X lattice.
    for x in [2.15,5.85]:
        b.beam("PortalPost"+str(x),(x,.05,.65),(x,.05,6.45),.42)
        b.box("PostHighlight"+str(x),(x-.155,-.181,3.55),(.065,.035,5.75),"Crane",mat="RedLight")
        b.box("BaseShoe"+str(x),(x,.05,.68),(.72,.70,.16),"Crane",mat="RedDark")
    b.beam("PortalHeader",(1.9,.05,6.4),(6.1,.05,6.4),.46)
    b.beam("PortalCrossbar",(2.15,.05,4.1),(5.85,.05,4.1),.25)
    b.beam("BraceLeft",(2.15,.05,4.1),(4.0,.05,6.4),.25)
    b.beam("BraceRight",(5.85,.05,4.1),(4.0,.05,6.4),.25)
    b.sign("CraneSign",(4.0,-.25,6.22),3.65,.755,(132,4,248,28),"Crane")
    for i in range(2):
        b.box("DeckSlice"+str(i),(-2.625+i*6.35,.65,.42),(6.35,3.2,.35),"Dock","wood")
    b.box("DeckFrontBeam",(.55,-1.0,.37),(12.7,.18,.44),"Dock",mat="Ink")
    scene["stage_complete"]=True
    scene["visual_approval"]=False
    bpy.context.view_layer.update()
    stats=[]
    for obj in b.parts:
        bm=bmesh.new(); bm.from_mesh(obj.data)
        assert all(e.is_manifold for e in bm.edges),obj.name
        assert all(f.calc_area()>1e-9 for f in bm.faces),obj.name
        assert not any(p.use_smooth for p in obj.data.polygons),obj.name
        stats.append({"name":obj.name,"vertices":len(bm.verts),"faces":len(bm.faces),"closed":True})
        bm.free()
    # Save only the sample scene dependency closure, never the user's original or Reference scene.
    bpy.data.libraries.write(str(SOURCE / "sample_source_library.blend"),{scene},fake_user=True,compress=True)
    report={"stage":"partial style sample; not full reconstruction","input_sha256":INPUT_SHA,"bounds_z_up":bounds(b.parts),"parts":stats,"uv_mapping":b.mapping,"master_density":DENSITY,"reference_orientation":"Unregistered: final silhouette/landmark alignment still requires visual review","materials":list(b.materials)}
    write_json(SOURCE / "sample_build.json",report)
    export_scene=independent_scene("INS7_SampleExport")
    root=bpy.data.objects.new("InsurancePixelSample",None); export_scene.collection.objects.link(root)
    for name,group in b.groups.items():
        copies=[]
        for original in b.parts:
            if original.parent != group:
                continue
            data=original.data.copy()
            data.transform(original.matrix_world)
            obj=bpy.data.objects.new("INS7_ExportPart",data)
            export_scene.collection.objects.link(obj)
            copies.append(obj)
        bpy.ops.object.select_all(action='DESELECT')
        for obj in copies: obj.select_set(True)
        bpy.context.view_layer.objects.active=copies[0]
        bpy.ops.object.join()
        joined=copies[0]
        joined.name="INS_"+name+"Geometry"
        joined.parent=root
        assert joined.name=="INS_"+name+"Geometry"
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.export_scene.gltf(filepath=str(ASSET / "insurance_pixel_sample.glb"),export_format='GLB',use_selection=True,use_active_scene=True,export_yup=True,export_apply=True,export_cameras=False,export_lights=False,export_animations=False,export_image_format='AUTO')
    print(json.dumps({"sample_parts":len(b.parts),"source_faces":sum(x['faces'] for x in stats),"export_meshes":4,"bounds":report['bounds_z_up'],"visual_approval":False},ensure_ascii=True))
verify_input()
