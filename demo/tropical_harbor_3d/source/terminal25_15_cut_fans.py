"""Correct the interpolation of newly appended fan centers beside the terminal cut."""
import bpy,os,json,hashlib,shutil
import numpy as np
from pathlib import Path
assert os.getpid()==13812 and bpy.types.blendermcp_server.port==9881
root=Path(bpy.data.filepath).parent.parent
log=root/'captures/terminal_rebuild_20261125'
assert not (log/'cut_fan_fix.json').exists(),'Do not replay cut fan repair'
ob=bpy.data.objects['C25_ContourBuiltCoast'];m=ob.data
cert=json.loads((log/'ground_fix.json').read_text(encoding='utf8'))
prior=np.load(log/'terrain_after.npz');p=prior['positions'].copy();tri=prior['triangles']
current=np.empty_like(p);m.vertices.foreach_get('co',current.ravel())
assert np.array_equal(p,current)
start=cert['before_vertices']+cert['shared_intersection_vertices']
assert start==66367
adj={i:set() for i in range(start,len(p))}
for face in tri:
 for i in face:
  if i>=start:adj[int(i)].update(int(n) for n in face if n!=i)
changes=[]
for i,neighbors in adj.items():
 assert not any(n>=start for n in neighbors), 'centroids must not be adjacent'
 x,y,z=p[i]
 ns=sorted(neighbors)
 assert np.max(np.abs(p[ns,:2].astype(float).mean(0)-p[i,:2]))<3e-6
 target=float(p[ns,2].astype(float).mean())
 if abs(target-float(z))<2e-6:continue
 assert target<float(z)+2e-6,'repair must not introduce peaks'
 changes.append({'vertex':i,'neighbors':ns,'before':float(z),'after':target,'lowering':float(z)-target,'xy':[float(x),float(y)]})
 p[i,2]=target
assert changes
assert np.array_equal(p[:start],current[:start]) and np.array_equal(p[:,:2],current[:,:2])
v=p[tri].astype(float);cr=np.cross(v[:,1]-v[:,0],v[:,2]-v[:,0])
assert np.all(cr[:,2]>1e-10) and np.all(np.linalg.norm(cr,axis=1)>1e-10)
report={'status':'dryrun','rule':'Each appended fan centroid is the mean height of its unique fan-boundary vertices after core lowering. Original vertices and shared intersections do not move.',
 'first_centroid':start,'changes':changes,'changed_count':len(changes),'max_lowering':max(r['lowering'] for r in changes),
 'topology_unchanged':True,'all_xy_unchanged':True,'original_and_shared_vertices_unchanged':True,
 'scope_min':[min(r['xy'][a] for r in changes) for a in range(2)],'scope_max':[max(r['xy'][a] for r in changes) for a in range(2)]}
(log/'cut_fan_dryrun.json').write_text(json.dumps(report,indent=2),encoding='utf8')
if globals().get('TN25_FAN_APPLY',False):
 archive=log/'before_cut_fan_fix';archive.mkdir(exist_ok=False)
 for name in ['ground_fix.json','terrain_after.npz','export.json','final_source_check.json']:
  shutil.copy2(log/name,archive/name)
 m.vertices.foreach_set('co',p.ravel());m.update();bpy.context.view_layer.update()
 digest=hashlib.sha256(p.astype(np.float32).tobytes()+tri.astype(np.int32).ravel().tobytes()).hexdigest()
 report.update(status='applied',terrain_before_sha256=cert['terrain_after_sha256'],terrain_after_sha256=digest)
 np.savez_compressed(log/'terrain_after.npz',positions=p,triangles=tri)
 cert['terrain_after_sha256']=digest
 cert['fan_centroid_refinement']={'report':'cut_fan_fix.json','previous_certificate':'before_cut_fan_fix/ground_fix.json','changed_count':len(changes),'all_original_and_shared_vertices_unchanged':True}
 (log/'ground_fix.json').write_text(json.dumps(cert,indent=2),encoding='utf8')
 (log/'cut_fan_fix.json').write_text(json.dumps(report,indent=2),encoding='utf8')
print(json.dumps({k:v for k,v in report.items() if k!='changes'}))
