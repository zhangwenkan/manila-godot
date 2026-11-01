"""Scoped mesh construction for the complete R2 asset, used through Blender-MCP."""
from pathlib import Path
from contextlib import contextmanager
import math
import hashlib
import bpy
import bmesh
from mathutils import Vector

SOURCE=Path(__file__).resolve().parent
ASSET=SOURCE.parent
INPUT=Path(r'C:/Users/51440/Downloads/harbor dock 3d model.glb')
SHA='b809395557fa853da7ef64f20a267515974bc3e5d58598a8ba64c86f4317a85c'
PREFIX='INR2_'
SCENE='Insurance_Rebuild_R2'
DENSITY=32
FACES=[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)]
TILES={'wall':(4,4),'roof':(260,4),'red':(4,260),'wood':(260,260)}


def fresh(path):
    path=Path(path)
    assert not path.exists(), f'Refusing to overwrite {path}'
    path.parent.mkdir(parents=True,exist_ok=True)
    return path


def verify_input():
    assert hashlib.sha256(INPUT.read_bytes()).hexdigest()==SHA


@contextmanager
def preserve_session():
    window=bpy.context.window
    scene,layer=window.scene,window.view_layer
    selected=list(bpy.context.selected_objects); active=layer.objects.active
    mode=active.mode if active else 'OBJECT'; filepath=bpy.data.filepath
    try:
        if mode!='OBJECT': bpy.ops.object.mode_set(mode='OBJECT')
        yield
    finally:
        if bpy.context.object and bpy.context.object.mode!='OBJECT': bpy.ops.object.mode_set(mode='OBJECT')
        window.scene=scene; window.view_layer=layer
        for obj in layer.objects: obj.select_set(False)
        for obj in selected:
            if obj.name in layer.objects: obj.select_set(True)
        layer.objects.active=active
        if active and mode!='OBJECT': bpy.ops.object.mode_set(mode=mode)
        assert bpy.data.filepath==filepath


def switch(scene):
    bpy.context.window.scene=scene
    bpy.context.window.view_layer=scene.view_layers[0]


def linear(hexcode):
    values=[int(hexcode[i:i+2],16)/255 for i in (0,2,4)]
    return tuple(v/12.92 if v<=.04045 else ((v+.055)/1.055)**2.4 for v in values)+(1,)


class Model:
    def __init__(self,scene):
        self.scene=scene
        self.collection=bpy.data.collections.new(PREFIX+'Editable')
        scene.collection.children.link(self.collection)
        self.root=self.empty('CompleteHarbor')
        self.groups={key:self.empty(key,self.root) for key in ['Office','Roof','Crane','Dock','Props','Tug']}
        self.materials={}
        atlas=bpy.data.images.load(str(SOURCE/'textures/harbor_pixels.png'),check_existing=False)
        signs=bpy.data.images.load(str(SOURCE/'textures/harbor_signs.png'),check_existing=False)
        for image in [atlas,signs]: image.pack()
        self.material('Atlas','ffffff',atlas); self.material('Signs','ffffff',signs)
        for name,value in {'Ink':'302d36','Steel':'59616b','SteelLight':'8e9695','WallDark':'46575f','WallLight':'7e9296','RedDark':'603439','Red':'934742','RedLight':'be7560','WoodDark':'5c4a3d','Wood':'9a805f','WoodLight':'bca27b','Glass':'3e5665','GlassLight':'779398','Cream':'c2b9a8','CreamLight':'e0d5bd','Hull':'3e596d','HullLight':'617e90','Water':'668f9e','Rope':'86765d'}.items():
            self.material(name,value)
        self.parts=[]

    def empty(self,name,parent=None):
        name=PREFIX+name
        assert name not in bpy.data.objects
        obj=bpy.data.objects.new(name,None); self.collection.objects.link(obj); obj.parent=parent
        return obj

    def material(self,name,value,image=None):
        material=bpy.data.materials.new(PREFIX+name); material.diffuse_color=linear(value)
        material.use_nodes=True; bsdf=material.node_tree.nodes.get('Principled BSDF')
        bsdf.inputs['Base Color'].default_value=linear(value)
        bsdf.inputs['Roughness'].default_value=1; bsdf.inputs['Metallic'].default_value=0
        bsdf.inputs['Specular IOR Level'].default_value=0
        if image:
            node=material.node_tree.nodes.new('ShaderNodeTexImage'); node.image=image
            node.interpolation='Closest'; node.extension='EXTEND'
            material.node_tree.links.new(node.outputs['Color'],bsdf.inputs['Base Color'])
        self.materials[name]=material

    def mesh(self,name,vertices,faces,group,texture=None,mat='Ink',uv_axis=None):
        name=PREFIX+name
        assert name not in bpy.data.objects, name
        data=bpy.data.meshes.new(name+'Mesh'); data.from_pydata(vertices,[],faces); data.update()
        bm=bmesh.new(); bm.from_mesh(data); bmesh.ops.recalc_face_normals(bm,faces=bm.faces); bm.to_mesh(data); bm.free()
        data.update()
        obj=bpy.data.objects.new(name,data); self.collection.objects.link(obj); obj.parent=self.groups[group]
        data.materials.append(self.materials['Atlas' if texture else mat])
        # Every part has the SAME active layer, including signs, before runtime joining.
        uv=data.uv_layers.new(name='PixelUV'); data.uv_layers.active_index=0
        if texture:
            ox,oy=TILES[texture]
            for face in data.polygons:
                face.use_smooth=False
                n=face.normal
                preferred=Vector(uv_axis or ((0,1,0) if abs(n.x)>.95 else (1,0,0)))
                u=preferred-n*preferred.dot(n)
                if u.length<.001: u=Vector((1,0,0))-n*n.x
                if u.length<.001: u=Vector((0,0,1))-n*n.z
                u.normalize(); v=n.cross(u).normalized()
                pts=[data.vertices[data.loops[i].vertex_index].co for i in face.loop_indices]
                uu=[p.dot(u) for p in pts]; vv=[p.dot(v) for p in pts]
                assert max(max(uu)-min(uu),max(vv)-min(vv))*DENSITY<=240.01,(name,face.index)
                for loop,p in zip(face.loop_indices,pts):
                    uv.data[loop].uv=((ox+4+(p.dot(u)-min(uu))*DENSITY)/512,1-(oy+4+(max(vv)-p.dot(v))*DENSITY)/512)
        self.parts.append(obj)
        return obj

    def box(self,name,center,size,group,texture=None,mat='Ink',uv_axis=None):
        x,y,z=[s/2 for s in size]
        obj=self.mesh(name,[(-x,-y,-z),(x,-y,-z),(x,y,-z),(-x,y,-z),(-x,-y,z),(x,-y,z),(x,y,z),(-x,y,z)],FACES,group,texture,mat,uv_axis)
        obj.location=center
        return obj

    def beam(self,name,a,b,width,depth=None,group='Crane',texture=None,mat='Red'):
        a,b=Vector(a),Vector(b)
        obj=self.box(name,(a+b)/2,(width,depth or width,(b-a).length),group,texture,mat)
        obj.rotation_mode='QUATERNION'; obj.rotation_quaternion=(b-a).to_track_quat('Z','Y')
        return obj

    def prism(self,name,profile,y0,y1,group,texture=None,mat='Ink'):
        n=len(profile); verts=[(x,y,z) for y in [y0,y1] for x,z in profile]
        faces=[tuple(reversed(range(n))),tuple(range(n,2*n))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
        return self.mesh(name,verts,faces,group,texture,mat)

    def cylinder(self,name,center,radius,depth,group,mat='Steel',sides=12,axis='Z'):
        vertices=[(radius*math.cos(i*math.tau/sides),radius*math.sin(i*math.tau/sides),z) for z in [-depth/2,depth/2] for i in range(sides)]
        faces=[tuple(reversed(range(sides))),tuple(range(sides,2*sides))]+[(i,(i+1)%sides,(i+1)%sides+sides,i+sides) for i in range(sides)]
        obj=self.mesh(name,vertices,faces,group,mat=mat); obj.location=center
        if axis=='Y': obj.rotation_euler.x=math.pi/2
        elif axis=='X': obj.rotation_euler.y=math.pi/2
        return obj

    def cable(self,name,points,radius=.025,group='Crane',mat='Ink',sides=6):
        points=[Vector(p) for p in points]; vertices=[]
        for i,p in enumerate(points):
            t=(points[min(i+1,len(points)-1)]-points[max(0,i-1)]).normalized()
            q=t.to_track_quat('Z','Y')
            vertices.extend(p+q@Vector((radius*math.cos(j*math.tau/sides),radius*math.sin(j*math.tau/sides),0)) for j in range(sides))
        faces=[tuple(reversed(range(sides))),tuple(range((len(points)-1)*sides,len(points)*sides))]
        for i in range(len(points)-1):
            for j in range(sides): faces.append((i*sides+j,i*sides+(j+1)%sides,(i+1)*sides+(j+1)%sides,(i+1)*sides+j))
        return self.mesh(name,vertices,faces,group,mat=mat)

    def sign(self,name,center,width,height,rect,group):
        x,y,z=center
        self.box(name+'Frame',(x,y+.055,z),(width+.15,.16,height+.15),group,mat='Ink')
        self.box(name+'InsetRim',(x,y-.025,z),(width+.06,.06,height+.06),group,mat='SteelLight')
        obj=self.box(name+'LetterFace',(x,y-.075,z),(width,.035,height),group,mat='Signs')
        obj.data.update()
        layer=obj.data.uv_layers['PixelUV']; left,top,right,bottom=rect
        for face in obj.data.polygons:
            for i in face.loop_indices:
                p=obj.data.vertices[obj.data.loops[i].vertex_index].co
                layer.data[i].uv=((left+(p.x/width+.5)*(right-left))/512,1-(top+(.5-p.z/height)*(bottom-top))/128) if face.normal.y<-.9 else (.5,.1)
        obj['bitmap_sign']=name
        return obj

    def window(self,name,x,y,z,width,height,back=False,small=False):
        side=1 if back else -1
        self.box(name+'Recess',(x,y+side*.02,z),(width+.13,.15,height+.15),'Office',mat='Ink')
        self.box(name+'Glass',(x,y+side*.11,z),(width-.12,.025,height-.12),'Office',mat='Glass')
        self.box(name+'Reflect',(x-width*.1,y+side*.131,z+height*.23),(width*.64,.018,.08),'Office',mat='GlassLight')
        for sign in [-1,1]:
            self.box(name+'Jamb'+str(sign),(x+sign*width/2,y+side*.14,z),(.09,.12,height+.16),'Office',mat='Wood')
            self.box(name+'Rail'+str(sign),(x,y+side*.14,z+sign*height/2),(width+.18,.12,.10),'Office',mat='WoodLight' if sign==1 else 'WoodDark')
        if small:
            for index in [-1,0,1]: self.box(name+'Slat'+str(index),(x,y+side*.15,z+index*height*.23),(width-.10,.055,.065),'Office',mat='Wood')
        else:
            self.box(name+'Mullion',(x,y+side*.15,z),(.045,.055,height-.1),'Office',mat='WoodDark')


def current_model():
    return bpy.app.driver_namespace['insurance_r2_builder']
