exec((Path(bpy.data.filepath).parent/'shore_21_context.py').read_text(encoding='utf8'),globals())
import bmesh
assert not terrain.get('shore21_corrected'),'Already applied'
bm=bmesh.new();bm.from_mesh(mesh)
holes=[e for e in bm.edges if e.is_boundary and all(5<v.co.x<30 and 38<-v.co.y<57 for v in e.verts)]
print('LOCAL_HOLE',[[list(v.co) for v in e.verts] for e in holes])
assert len(holes)==5,'Inspect unexpected boundary before filling'
result=bmesh.ops.holes_fill(bm,edges=holes,sides=8)
layer=bm.loops.layers.float_color.get('LandUse')
for f in result['faces']:
    if f.normal.z<0:f.normal_flip()
    for l in f.loops:l[layer]=(1,0,0,0)
bm.to_mesh(mesh);bm.free();mesh.update()
# Re-establish a level bearing apron before the travel-office front corners.
for v in mesh.vertices:
    x,y,h=v.co;z=-y
    if 21.25<x<27.5 and 43.35<z<48.8 and h>3.5:
        w=float(smooth(21.25,21.85,x))*float(smooth(43.35,43.6,z))*(1-float(smooth(48.45,48.8,z)))
        v.co.z=h*(1-w)+4.14*w
mesh.update();bpy.context.view_layer.update();ground_bvh=BVHTree.FromObject(terrain,bpy.context.evaluated_depsgraph_get())
# Source components store world-positioned mesh coordinates. Recenter AFTER scaling.
# Scaling is already complete; this correction only seats the intended centers.
targets=[('S20_CourtyardShrub.036',17.75,44.10,.08),('S20_CourtyardShrub.037',18.45,44.95,.08),
 ('S20_CourtyardShrub.038',18.10,44.55,.08),('S20_CourtyardShrub.039',17.25,43.90,.08),
 ('Bank_Boulder.008',17.15,43.65,.32),('Bank_Boulder.025',17.80,45.1,.20),('Bank_Boulder.007',16.65,44.2,.20)]
for name,x,z,embed in targets:
    o=bpy.data.objects[name];p=center(o);o.location.x+=x-p.x;o.location.y+=-z-p.y;bpy.context.view_layer.update()
    o.location.z+=ground(x,z)-bounds(o)[2][0]-embed
terrain['shore21_corrected']=True
refresh_height();export_land();export_collection('Reference_Foliage','foliage.glb');export_collection('Reference_Rocks','rocks.glb')
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'source/harbor_shore_control_mcp.blend'))
print('CORRECTED boundary, bearing apron, scaled component centers')
