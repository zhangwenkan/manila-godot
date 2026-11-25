# Repair the unsaved trial's horizontal displacement only, preserving wide shoulders.
import bpy,json,numpy as np
from pathlib import Path
ROOT=Path(bpy.data.filepath).parent.parent;LOG=ROOT/'captures/rock_path_sample_20261123'
terrain=bpy.data.objects['C25_ContourBuiltCoast'];mesh=terrain.data
assert not terrain.get('sample23_forms')
base=np.load(str(LOG/'terrain_baseline.npz'));loops=base['loops']
pos=np.array([v.co[:] for v in mesh.vertices],np.float32)
pos[:,:2]=base['positions'][:,:2]
mesh.vertices.foreach_set('co',pos.ravel());mesh.update();mesh.calc_loop_triangles()
bad=[t.index for t in mesh.loop_triangles if (mesh.vertices[t.vertices[1]].co-mesh.vertices[t.vertices[0]].co).cross(mesh.vertices[t.vertices[2]].co-mesh.vertices[t.vertices[0]].co).z < -1e-7]
assert not bad
mesh.uv_layers[0].data.foreach_set('uv',np.column_stack(((pos[loops,0]-8)/26,(-pos[loops,1]-10)/37)).astype(np.float32).ravel())
uv1=mesh.uv_layers.get('RockRegion') or mesh.uv_layers.new(name='RockRegion')
uv1.data.foreach_set('uv',np.column_stack(((-pos[loops,1]-10)/37,(pos[loops,2]-.7)/4.4)).astype(np.float32).ravel())
terrain['sample23_forms']=True
terrain['sample23_rock_region']='Godot z10..47, height0.7..5.1; no repeat'
np.savez_compressed(str(LOG/'terrain_after_forms.npz'),positions=pos)
(LOG/'forms.json').write_text(json.dumps({'changed_vertices':int(np.sum(np.max(abs(pos-base['positions']),axis=1)>.0001)),'max_position_delta':np.max(np.abs(pos-base['positions']),axis=0).tolist(),'planar_folds':len(bad),'new_triangles':0,'trial_horizontal_displacement_removed':True},indent=2),encoding='utf8')
print((LOG/'forms.json').read_text())
