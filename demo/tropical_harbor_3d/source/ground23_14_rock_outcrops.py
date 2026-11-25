"""Create interlocking exposed rock shoulders through the owned Blender MCP.

Fifteen designed broad wedges, one mesh, one collection, under 2,000 triangles.
Horizontal rays locate each actual rock face. Rear vertices are deeply inside
the terrain; exposed fronts turn through unequal planar faces. No terrain or
existing object is moved. This script intentionally does not export or save.
"""
import json
from pathlib import Path
import bpy
import bmesh
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree


ROOT=Path(bpy.data.filepath).parent.parent
LOG=ROOT/'captures/ground_integration_20261123'
terrain=bpy.data.objects['C25_ContourBuiltCoast']
assert terrain.get('ground23_stronger_forms'), 'Expected the current stronger G23 terrain'
assert not terrain.get('ground23_rock_outcrops'), 'Already applied; do not replay'
assert bpy.data.collections.get('Reference_RockOutcrops') is None, 'Outcrop collection already exists'
assert bpy.data.objects.get('G23_EmbeddedRockOutcrops') is None
assert bpy.data.images.get('G23_Rock'), 'G23 rock material image must already be authored'
bpy.context.view_layer.update()
surface=BVHTree.FromObject(terrain,bpy.context.evaluated_depsgraph_get())
down=Vector((0,0,-1))
with np.load(str(LOG/'land_data.npz')) as raw:
    land=raw['land'].copy()


def ground(x,z):
    hit=surface.ray_cast(Vector((float(x),-float(z),50)),down,150)[0]
    return None if hit is None else float(hit.z)


def wall_x(z,h,xmin,xmax):
    hit,normal,_,_=surface.ray_cast(Vector((float(xmin),-float(z),float(h))),Vector((1,0,0)),float(xmax-xmin))
    if hit is None or abs(normal.x)<.20:
        return None
    return float(hit.x)


def path_occupation(x,z):
    row=min(2047,max(0,int((z+15)/97*2048)))
    col=min(2047,max(0,int((x+4)/48*2048)))
    return float(land[row,col,2])


def world_vertices(obj):
    points=np.empty((len(obj.data.vertices),3),np.float32)
    obj.data.vertices.foreach_get('co',points.ravel())
    mat=np.asarray(obj.matrix_world,float)
    return points.astype(float)@mat[:3,:3].T+mat[:3,3]


# Protect occupied ground and the real height of props. Crown/leaf/grass bounds
# are not roots. Building floor footprints also protect their usable volume.
occupied=[];seen=set()
for cname in ('Reference_Town','Reference_Coast','Reference_Foliage'):
    for obj in bpy.data.collections[cname].all_objects:
        if obj.type!='MESH' or obj.name in seen or obj.hide_render:
            continue
        seen.add(obj.name)
        if any(word in obj.name for word in ('Grass','Tuft','Blade','Crown','Frond','Leaf','Coconut','Roof','Eave','Sign','Bargeboard')):
            continue
        p=world_vertices(obj)
        if not len(p):continue
        lo,hi=p.min(0),p.max(0)
        if hi[0]<13 or lo[0]>26 or -lo[1]<-7 or -hi[1]>50:
            continue
        floor=obj.name.startswith(('Town_Floor','Hut_Floor'))
        step=obj.name.startswith(('Town_Step','Hut_EntrySteps','Hut_StairStringer'))
        trunk=obj.name.startswith(('Palm_Trunk','Tree_Trunk','Palm_Root','Tree_Root'))
        if trunk:
            roots=p[p[:,2]<=lo[2]+max(.3,(hi[2]-lo[2])*.17)]
            if len(roots)>2:lo,hi=roots.min(0),roots.max(0)
            hi[2]+=1.4
        center=(lo+hi)*.5
        sample=ground(center[0],-center[1])
        touching=sample is not None and -.9<lo[2]-sample<.30
        if not (floor or step or trunk or touching):continue
        if floor:
            lo[2]-=.38;hi[2]+=5.0
        pad=np.array([.12,.12,.07]) if floor or step or trunk else np.array([.07,.07,.035])
        occupied.append((lo-pad,hi+pad,obj.name))


# Segment group, desired z/height, alongshore width, visible height, outward
# projection, slant of the shoulder across z. Closely paired stones overlap
# within six irregular groups; they do not follow an equally spaced necklace.
SPECS=[
    ('trade_south',-3.6,2.16,2.65,1.05,.62, .26),
    ('trade_south',-2.8,2.85,1.92,.80,.48,-.22),
    ('trade_south',-4.6,1.72,1.72,.62,.44, .18),
    ('trade_north', 5.3,2.38,2.70,1.10,.67,-.25),
    ('trade_north', 6.4,3.10,1.82,.76,.50, .30),
    ('trade_north', 4.25,1.83,1.76,.63,.43,-.15),
    ('clinic_south',23.3,2.34,2.70,1.16,.69, .32),
    ('clinic_south',24.3,3.02,2.02,.81,.52,-.22),
    ('clinic_south',22.5,1.72,1.80,.65,.46, .16),
    ('clinic_north',29.0,2.47,2.70,1.18,.68,-.34),
    ('clinic_north',29.8,3.21,1.92,.83,.48, .25),
    ('travel_south',42.0,2.10,2.48,.99,.68, .28),
    ('travel_south',42.8,2.73,1.78,.70,.49,-.25),
    ('travel_north',45.5,2.05,2.52,1.02,.64,-.32),
    ('travel_north',46.2,2.77,1.83,.74,.47, .20),
]
# A clipped six-sided outline in the alongshore/height plane. Its top rises
# diagonally while its lower end breaks back into the cliff. It is neither a
# sphere nor an identical rectangular course.
OUTLINE=np.array([[-.51,-.29],[-.21,-.49],[.39,-.35],
                  [.52,.11],[.19,.47],[-.43,.34]],float)
EXPOSURE=np.array([.25,.56,.43,.57,.82,.66])


def make_wedge(spec,index,zshift=0,hshift=0,projection_scale=1):
    group,z,h,width,tall,reach,slant=spec
    z+=zshift;h+=hshift;reach*=projection_scale
    xmin,xmax=(13.7,24.8) if group.startswith('trade') else ((17.4,25) if group.startswith('clinic') else (14.5,24.3))
    outline=OUTLINE.copy()
    # Three bounded asymmetries preserve the broad authored silhouette.
    outline[0,1]+=(-.035,.015,.045)[index%3]
    outline[3,0]+=(.025,-.04,.012)[index%3]
    outline[4,1]+=(0,.055,-.035)[index%3]
    front=[];back=[];wall_positions=[]
    for j,(u,v) in enumerate(outline):
        zz=z+u*width+slant*v
        hh=h+v*tall
        face=wall_x(zz,hh,xmin,xmax)
        if face is None:return None,'no_rock_face'
        # Front edges are partly buried and partly proud; the broad front
        # centre below creates the readable outward shoulder/shadow.
        front.append((face-reach*EXPOSURE[j],-zz,hh))
        bury=.38+(.12 if j in (2,3,4) else .04)
        rear=(face+bury,-zz,hh)
        support=ground(rear[0],zz)
        if support is None or support-hh<.10:return None,'back_not_embedded'
        back.append(rear);wall_positions.append(face)
    center_face=wall_x(z+.06*width,h+.015*tall,xmin,xmax)
    if center_face is None:return None,'no_centre_face'
    # The forward face centre is offset both in width and height so its facets
    # have unequal areas rather than meeting as a symmetric six-sided jewel.
    center=(center_face-reach,-(z+.06*width),h+.015*tall)
    verts=front+back+[center]
    faces=[]
    for j in range(6):
        nxt=(j+1)%6
        faces.append((j,nxt,12))
        faces.append((j,6+j,6+nxt,nxt))
    faces.append(tuple(range(11,5,-1)))
    coords=np.asarray(verts)
    lo,hi=coords.min(0),coords.max(0)
    conflicts=[name for a,b,name in occupied if np.all(hi>a) and np.all(lo<b)]
    if conflicts:return None,'occupied:'+','.join(conflicts[:3])
    # Rear vertices and their centre must lie inside the continuous terrain.
    rear_center=np.asarray(back).mean(0)
    rear_height=ground(rear_center[0],-rear_center[1])
    if rear_height is None or rear_height-rear_center[2]<.08:return None,'rear_centre_not_embedded'
    embedded=[ground(p[0],-p[1])-p[2] for p in back]
    exposed=[p[2]-ground(p[0],-p[1]) for p in front+[center]]
    if max(exposed)<.10:return None,'no_visible_projection'
    for point,gap in zip(front+[center],exposed):
        if path_occupation(point[0],-point[1])>.35 and gap<2.2:
            return None,'walkway_clearance'
    report={'group':group,'spec_index':index,'center_godot':[center[0],center[2],-center[1]],
            'alongshore_width_m':width,'visible_height_design_m':tall,
            'outward_projection_m':reach,'z_adjustment_m':zshift,'height_adjustment_m':hshift,
            'bounds_blender_xyz':[lo.tolist(),hi.tolist()],
            'back_vertical_burial_range_m':[float(min(embedded)),float(max(embedded))],
            'front_max_vertical_exposure_m':float(max(exposed)),
            'building_step_root_bbox_conflicts':[],'terrain_surface_x':wall_positions}
    return (verts,faces,report),None


vertices=[];faces=[];reports=[];rejections=[]
for index,spec in enumerate(SPECS):
    result=None
    # Small bounded placement adjustments resolve local roots/steps while
    # retaining each designed group and never editing an existing object.
    for zshift,hshift,projection_scale in [(0,0,1),(.22,0,1),(-.22,0,1),
                                           (0,.16,1),(0,-.16,1),(.35,.15,.9),
                                           (-.35,.15,.9),(0,.22,.8)]:
        result,reason=make_wedge(spec,index,zshift,hshift,projection_scale)
        if result:break
    if result is None:
        rejections.append({'spec':index,'group':spec[0],'last_reason':reason})
        continue
    verts,local_faces,report=result
    offset=len(vertices);vertices.extend(verts)
    faces.extend(tuple(offset+i for i in face) for face in local_faces)
    reports.append(report)
assert 12<=len(reports)<=18, 'Cannot safely fit twelve designed outcrops: '+str(rejections)
assert all(any(r['group']==group for r in reports) for group in {s[0] for s in SPECS}), 'An entire designed group was blocked'

# Build and verify the mesh before attaching it to the scene. Every independent
# wedge is closed. Their deliberate terrain/inter-wedge intersections are solid
# embedment, not open cracks or nonmanifold shared edges.
mesh=bpy.data.meshes.new('G23_EmbeddedRockOutcropsMesh')
mesh.from_pydata(vertices,[],faces);mesh.update()
bm=bmesh.new();bm.from_mesh(mesh)
try:
    bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
    assert all(e.is_manifold for e in bm.edges), 'Outcrop has open/nonmanifold edges'
    assert all(f.calc_area()>1e-8 for f in bm.faces), 'Degenerate rock face'
    # Two centimetre single-segment bevels keep an edged rock character and
    # catch light on exposed corners, without smoothing the volumes into balls.
    bmesh.ops.bevel(bm,geom=list(bm.edges),offset=.020,segments=1,
                    affect='EDGES',profile=.5,clamp_overlap=True)
    bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
    assert all(e.is_manifold for e in bm.edges)
    assert all(f.calc_area()>1e-10 for f in bm.faces)
    bm.to_mesh(mesh)
finally:bm.free()
mesh.update();mesh.calc_loop_triangles()
assert len(mesh.loop_triangles)<2000, 'Outcrop triangle budget exceeded'
assert all(not p.use_smooth for p in mesh.polygons)

# One existing G23 rock image, no baked face shadows and no floating grass cap.
# Texture UVs are world projected by each geometric face's main orientation.
uv=mesh.uv_layers.new(name='RockWorldUV')
for poly in mesh.polygons:
    normal=poly.normal
    for loop_id in poly.loop_indices:
        p=mesh.vertices[mesh.loops[loop_id].vertex_index].co
        if abs(normal.z)>.68:pair=(p.x/8,-p.y/8)
        elif abs(normal.y)>abs(normal.x):pair=(p.x/8,p.z/8)
        else:pair=(-p.y/8,p.z/8)
        uv.data[loop_id].uv=pair
material=bpy.data.materials.new('G23_ExposedRockShoulders')
material.use_nodes=True
nodes=material.node_tree.nodes;links=material.node_tree.links
principled=next(n for n in nodes if n.type=='BSDF_PRINCIPLED')
principled.inputs['Roughness'].default_value=.94
principled.inputs['Specular IOR Level'].default_value=.18
texture=nodes.new('ShaderNodeTexImage');texture.name='G23 existing rock surface';texture.image=bpy.data.images['G23_Rock']
uvnode=nodes.new('ShaderNodeUVMap');uvnode.uv_map='RockWorldUV'
links.new(uvnode.outputs['UV'],texture.inputs['Vector'])
links.new(texture.outputs['Color'],principled.inputs['Base Color'])
mesh.materials.append(material)
collection=bpy.data.collections.new('Reference_RockOutcrops')
bpy.context.scene.collection.children.link(collection)
obj=bpy.data.objects.new('G23_EmbeddedRockOutcrops',mesh);collection.objects.link(obj)
obj['ground23_outcrops']='Fifteen requested broad shoulder wedges; terrain embedded; no terrain modification'
terrain['ground23_rock_outcrops']=True
report={'created':True,'visual_accepted':False,'collection':collection.name,'object':obj.name,
        'wedges':len(reports),'vertices':len(mesh.vertices),'triangles':len(mesh.loop_triangles),
        'closed_components':len(reports),'open_edges':0,'nonmanifold_edges':0,
        'bevel_m':.020,'flat_faces':True,'planned_asset':'assets/reference/ground_rock.glb',
        'exported_assets':False,'saved_blend':False,'occupied_boxes_checked':len(occupied),
        'rocks':reports,'rejected_specs':rejections}
(LOG/'rock_outcrops.json').write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf8')
print(json.dumps({k:v for k,v in report.items() if k not in ('rocks',)},ensure_ascii=False))

