"""Export reviewed embedded shoulders through the owned Blender MCP."""
import bpy,json
from pathlib import Path
ROOT=Path(bpy.data.filepath).parent.parent
ob=bpy.data.objects['G23_EmbeddedRockOutcrops']
assert bpy.data.objects['C25_ContourBuiltCoast'].get('ground23_rock_outcrops')
bpy.ops.object.select_all(action='DESELECT')
ob.hide_set(False);ob.hide_render=False;ob.select_set(True)
bpy.context.view_layer.objects.active=ob
bpy.ops.export_scene.gltf(filepath=str(ROOT/'assets/reference/ground_rock.glb'),export_format='GLB',use_selection=True,export_apply=True,export_yup=True,export_materials='EXPORT',export_normals=True)
(ROOT/'captures/ground_integration_20261123/rock_export.json').write_text(json.dumps({'object':ob.name,'asset':'assets/reference/ground_rock.glb','vertices':len(ob.data.vertices),'triangles':len(ob.data.loop_triangles),'runtime_material':'G23 shared world rock, 8m tile, independent height alpha'},indent=2),encoding='utf8')
print('Exported grounded rock shoulders')
