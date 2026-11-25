"""Sculpt three integrated cliff masses from the immutable cliff25 baseline.

Run only through the verified owned GUI Blender MCP. Never run as external
Python. Repeatable: every revision derives from the new-round baseline,
never by layering another displacement onto the last sculpt result.
"""
import bpy, os, json, sys, importlib, hashlib, time
from pathlib import Path
import numpy as np

assert not bpy.app.background, 'Geometry authoring requires owned GUI Blender MCP'
ROOT=Path(bpy.data.filepath).parent.parent
LOG=ROOT/'captures/cliff_contacts_20261125'
session=json.loads((LOG/'session_start.json').read_text(encoding='utf-8-sig'))
assert os.getpid()==session['pid']==9864
assert bpy.types.blendermcp_server.port==session['port']==9881
assert Path(bpy.data.filepath).resolve()==Path(session['file']).resolve()
assert Path(bpy.data.filepath).name=='harbor_shore_control_mcp.blend'
started=time.perf_counter()
sys.path.insert(0,str(ROOT/'source'))
import structure23_common as util
import cliff25_geometry_common as forms
importlib.reload(forms)
import cliff25_relief_common as relief_forms
importlib.reload(relief_forms)

baseline=np.load(LOG/'baseline.npz')
base=baseline['positions'].astype(float); tri=baseline['triangles'].astype(np.int32)
ob=bpy.data.objects['C25_ContourBuiltCoast']; mesh=ob.data
assert len(mesh.vertices)==len(base) and len(mesh.polygons)==len(tri)
loop_indices=np.empty(len(mesh.loops),np.int32)
mesh.loops.foreach_get('vertex_index',loop_indices)
assert np.array_equal(loop_indices.reshape(-1,3),tri), 'Topology changed from cliff25 baseline'
assert np.max(np.abs(np.asarray(ob.matrix_world)-np.eye(4)))<1e-6, 'Expected identity terrain transform'
p=base.copy(); x=base[:,0]; z=-base[:,1]
q=np.column_stack([x,z]); qt=q[tri]
locks=np.load(LOG/'protected_terrain_faces.npz')
assert np.max(np.abs(base[locks['vertex_ids']]-locks['positions']))<1e-6
locked=np.zeros(len(p),bool); locked[locks['vertex_ids']]=True
lock_records=[{'kind':'retained_road_court_junction_faces','faces':int(len(locks['face_ids'])),
               'vertices':int(len(locks['vertex_ids']))}]

def protect_hull(name,hull,pad,fade):
    if len(hull)<3:return
    hull=np.asarray(hull,float)
    near=(q[:,0]>=hull[:,0].min()-pad-fade-.3)&(q[:,0]<=hull[:,0].max()+pad+fade+.3)&(q[:,1]>=hull[:,1].min()-pad-fade-.3)&(q[:,1]<=hull[:,1].max()+pad+fade+.3)
    d=np.full(len(q),1e6);d[near]=util.polygon_distance(x[near],z[near],hull)
    hit=util.intersections(qt,hull)
    ids=np.unique(tri[hit])
    locked[ids]=True;locked[d<=pad]=True
    extra_protection[:] = np.maximum(extra_protection,1-forms.smoothstep(pad,pad+fade,d))
    lock_records.append({'kind':name,'hull_xz':hull.tolist(),'faces':int(hit.sum()),'vertices_in_exact_faces':len(ids),'pad_m':pad,'fade_m':fade})

extra_protection=np.zeros(len(p))
known={row['name']:row for row in json.loads((LOG/'objects_before.json').read_text(encoding='utf-8-sig'))}
for obj in bpy.data.objects:
    if obj.type!='MESH' or obj.name not in known or obj.hide_render:continue
    if any(c.name.startswith('Archive_') or c.hide_render for c in obj.users_collection):continue
    structure=obj.name.startswith(('Town_Floor','Hut_Floor','Town_TavernPorch'))
    rooted=obj.name.startswith(('Tree_Trunk','Palm_Trunk','Bank_Boulder','S20_BankOutcrop_Bank_Boulder'))
    if not structure and not rooted:continue
    row=known[obj.name]; b=np.array(row['bounds']); bounds_xz=[b[0,0],-b[1,1],b[1,0],-b[0,1]]
    if bounds_xz[2]<15.1 or bounds_xz[0]>24.0 or bounds_xz[3]<21.3 or bounds_xz[1]>45.7:continue
    matrix=np.asarray(obj.matrix_world,float)
    assert np.max(abs(matrix-np.asarray(row['matrix'])))<2e-5,'Protected object moved: '+obj.name
    local=np.empty((len(obj.data.vertices),3),np.float32);obj.data.vertices.foreach_get('co',local.ravel())
    world=local@matrix[:3,:3].T+matrix[:3,3]
    if rooted:
        height=world[:,2].max()-world[:,2].min()
        # The root/base silhouette rather than the canopy or full tall trunk.
        take=world[:,2]<=world[:,2].min()+min(.32,max(.10,height*.16))
        root=world[take]
        if len(root)<3:root=world
        hull=util.convex_hull(np.column_stack([root[:,0],-root[:,1]]))
        protect_hull('root:'+obj.name,hull,.10,.38)
    else:
        hull=util.convex_hull(np.column_stack([world[:,0],-world[:,1]]))
        protect_hull('floor:'+obj.name,hull,.16,.40)

# Complete original boundary and low sea remain fixed independently of scope.
edges=np.sort(np.concatenate([tri[:,[0,1]],tri[:,[1,2]],tri[:,[2,0]]]),axis=1)
unique_edges,edge_counts=np.unique(edges,axis=0,return_counts=True)
boundary_vertices=np.unique(unique_edges[edge_counts==1])
locked[boundary_vertices]=True;locked[base[:,2]<=.10]=True

fields=forms.cliff25_fields(x,z)
weights=np.stack([v[1] for v in fields.values()])
targets=np.stack([v[0] for v in fields.values()])
den=weights.sum(axis=0)
target=np.divide((weights*targets).sum(axis=0),den,out=base[:,2].copy(),where=den>1e-10)
strength=np.clip(den,0,1)
candidate=(strength>0)&(x>15.8)&(x<23)&(z>21.8)&(z<45.2)
strength[~candidate]=0

# Fade from actual locked vertices as well as analytic footprints. This keeps
# full intersecting triangle protection from becoming a zero-width hard seam.
locked_ids=np.flatnonzero(locked)
relevant=locked_ids[(x[locked_ids]>14.8)&(x[locked_ids]<24)&(z[locked_ids]>20.8)&(z[locked_ids]<46.2)]
distance=np.full(len(q),1e6)
ids=np.flatnonzero(candidate)
for start in range(0,len(ids),256):
    ii=ids[start:start+256]
    sq=((q[ii,None,:]-q[relevant][None,:,:])**2).sum(axis=2)
    distance[ii]=np.sqrt(sq.min(axis=1))
freedom=forms.smoothstep(.08,.52,distance)*(1-extra_protection)
freedom[locked]=0
applied=strength*freedom
p[:,2]=base[:,2]+(target-base[:,2])*applied

# A single integrated debris apron under the primary projection; never a row
# of new rocks. The profile's outer toe is the controlling low bank height.
apron=np.exp(-((x-17.35)/.76)**4-((z-29.0)/1.30)**4)
apron*=forms.smoothstep(16.4,16.9,x)*(1-forms.smoothstep(18.3,18.7,x))
apron*=freedom*candidate
p[:,2]+=.085*apron

# Small non-periodic relief on broad soil/grass shoulders only. This is less
# than 4cm and cannot move retained road/court/floor/root triangles.
tv=base[tri]
normal=np.cross(tv[:,1]-tv[:,0],tv[:,2]-tv[:,0])
normal/=np.maximum(np.linalg.norm(normal,axis=1,keepdims=True),1e-12)
vert_z=np.zeros(len(p));vert_n=np.zeros(len(p))
np.add.at(vert_z,tri.ravel(),np.repeat(np.abs(normal[:,2]),3))
np.add.at(vert_n,tri.ravel(),1)
nz=np.divide(vert_z,vert_n,out=np.ones_like(vert_z),where=vert_n>0)
soft=(1-forms.smoothstep(.70,.93,strength))*forms.smoothstep(.50,.83,nz)
rough=.022*np.sin(x*2.1+z*.83)+.012*np.sin(x*4.7-z*1.73+.5)
p[:,2]+=rough*soft*strength*freedom
p[locked]=base[locked]
# Preserve the already-reviewed 1443-vertex main form exactly. Revision 3
# adds only ten finite mid-face cuts; it never accumulates a second sculpt.
primary=p.copy()
relief_delta,relief_features,relief_components=relief_forms.midscale_relief(primary,weights,freedom,locked)
assert np.max(np.abs(relief_delta))<=.200001
assert not np.any(relief_delta[locked])
p[:,2]+=relief_delta
p[locked]=base[locked]
assert np.array_equal(p[:,:2],base[:,:2])
assert np.max(abs(p[locks['vertex_ids']]-base[locks['vertex_ids']]))==0
assert np.isfinite(p).all()

delta=p[:,2]-base[:,2]
local_edges=unique_edges[np.any(candidate[unique_edges],axis=1)]
projected_edge=np.linalg.norm(base[local_edges[:,0],:2]-base[local_edges[:,1],:2],axis=1)
new_t=p[tri];new_norm=np.cross(new_t[:,1]-new_t[:,0],new_t[:,2]-new_t[:,0])
old_norm=np.cross(base[tri[:,1]]-base[tri[:,0]],base[tri[:,2]]-base[tri[:,0]])
assert np.all(new_norm[:,2]*old_norm[:,2]>0), 'Projected winding changed'
area=np.linalg.norm(new_norm,axis=1)*.5
assert area.min()>1e-10
slopes=np.rad2deg(np.arctan2(np.linalg.norm(new_norm[:,:2],axis=1),np.abs(new_norm[:,2])))
changed_faces=np.any(abs(delta[tri])>1e-6,axis=1)
per_mass=[]
for mass,(mh,mw,mcross) in zip(forms.MASSES,fields.values()):
    hit=mw>.01
    per_mass.append({'name':mass['name'],'candidate_vertices':int(hit.sum()),
                     'changed_vertices':int(np.count_nonzero(hit&(abs(delta)>1e-6))),
                     'max_abs_height_change_m':float(np.max(abs(delta[hit]),initial=0)),
                     'protected_or_faded_fraction':float(np.mean(freedom[hit]<.95)) if hit.any() else 0.0})
report={'status':'completed','visual_accepted':False,'source_baseline':'baseline.npz',
        'revision':3,'primary_form_changed_vertices':int(np.count_nonzero(abs(primary[:,2]-base[:,2])>1e-6)),
        'midscale':{'feature_count':len(relief_features),
                    'changed_vertices':int(np.count_nonzero(abs(relief_delta)>1e-6)),
                    'vertices_over_4cm':int(np.count_nonzero(abs(relief_delta)>.04)),
                    'newly_changed_outside_primary':int(np.count_nonzero((abs(relief_delta)>1e-6)&(abs(primary[:,2]-base[:,2])<=1e-6))),
                    'max_raise_m':float(relief_delta.max()),'max_lower_m':float(-relief_delta.min()),
                    'locked_vertex_change_m':float(np.max(abs(relief_delta[locked]))),
                    'features':relief_features},
        'pid':os.getpid(),'vertices':len(p),'triangles':len(tri),
        'changed_vertices':int(np.count_nonzero(abs(delta)>1e-6)),
        'max_raise_m':float(delta.max()),'max_lower_m':float(-delta.min()),
        'xy_unchanged':True,'topology_unchanged':True,'road_court_locked_vertices':int(len(locks['vertex_ids'])),
        'all_locked_vertices':int(locked.sum()),'max_locked_coordinate_change_m':float(np.max(abs(p[locked]-base[locked]))),
        'boundary_edges':int(np.count_nonzero(edge_counts==1)),'nonmanifold_edges':int(np.count_nonzero(edge_counts>2)),
        'minimum_triangle_area_m2':float(area.min()),
        'changed_face_slopes_deg':{'max':float(slopes[changed_faces].max(initial=0)),
                                  'p95':float(np.percentile(slopes[changed_faces],95)) if changed_faces.any() else 0},
        'local_projected_edge_m':{'min':float(projected_edge.min()),'p25':float(np.percentile(projected_edge,25)),
                                 'median':float(np.median(projected_edge)),'p95':float(np.percentile(projected_edge,95))},
        'regions':per_mass,'protected_objects':lock_records,
        'elapsed_seconds':time.perf_counter()-started,
        'limits':'No live export, no material edits, no automatic object relocation; final visual/structural audit required.'}

mesh.vertices.foreach_set('co',p.astype(np.float32).ravel())
mesh.update();bpy.context.view_layer.update()
np.savez_compressed(LOG/'sculpt.npz',positions=p.astype(np.float32),triangles=tri,
                    region_weight=strength.astype(np.float32),applied_weight=applied.astype(np.float32),
                    freedom=freedom.astype(np.float32),locked_vertices=np.flatnonzero(locked),
                    mass_weights=weights.astype(np.float32),primary_positions=primary.astype(np.float32),
                    midscale_delta=relief_delta.astype(np.float32),midscale_components=relief_components.astype(np.float32))
(LOG/'sculpt.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
(LOG/'section_mapping.json').write_text(json.dumps(forms.cliff25_section_metadata(),indent=2),encoding='utf8')
print(json.dumps({k:v for k,v in report.items() if k!='protected_objects'},ensure_ascii=False))
