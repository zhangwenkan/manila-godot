"""Replace the owned G23 pointed wedges with broad planar rock faces.

Run once in the owned live Blender MCP. Keeps the fourteen existing placements,
their material and object transform. Each new rock has one coplanar six-sided
front, a deeply embedded rear ring and thick diagonal side faces. No forward
centre vertex or triangle fan. Existing scene objects/terrain are untouched.
No export or source save is performed; the prior mesh is preserved locally.
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
obj=bpy.data.objects['G23_EmbeddedRockOutcrops']
assert terrain.get('ground23_rock_outcrops') and terrain.get('ground23_stronger_forms')
assert not obj.get('ground23_planar_outcrops'), 'Already revised; do not replay'
assert np.max(abs(np.asarray(obj.matrix_world)-np.eye(4)))<1e-8
prior=json.loads((LOG/'rock_outcrops.json').read_text(encoding='utf8'))
assert prior['wedges']==14 and len(prior['rocks'])==14
assert len(obj.data.materials)==1
bpy.context.view_layer.update()
surface=BVHTree.FromObject(terrain,bpy.context.evaluated_depsgraph_get())
with np.load(str(LOG/'land_data.npz')) as raw:land=raw['land'].copy()

def height(x,z):
    p=surface.ray_cast(Vector((float(x),-float(z),50)),Vector((0,0,-1)),150)[0]
    return None if p is None else float(p.z)

def face_x(z,h,group):
    xmin,xmax=(13.7,24.8) if group.startswith('trade') else ((17.4,25) if group.startswith('clinic') else (14.5,24.3))
    p,n,_,_=surface.ray_cast(Vector((xmin,-float(z),float(h))),Vector((1,0,0)),xmax-xmin)
    return None if p is None or abs(n.x)<.20 else float(p.x)

def path_weight(x,z):
    iz=min(2047,max(0,int((z+15)/97*2048)))
    ix=min(2047,max(0,int((x+4)/48*2048)))
    return float(land[iz,ix,2])

def coordinates(ob):
    p=np.empty((len(ob.data.vertices),3),np.float32);ob.data.vertices.foreach_get('co',p.ravel())
    m=np.asarray(ob.matrix_world,float);return p.astype(float)@m[:3,:3].T+m[:3,3]

occupied=[];seen=set()
for cname in ('Reference_Town','Reference_Coast','Reference_Foliage'):
    for ob in bpy.data.collections[cname].all_objects:
        if ob.type!='MESH' or ob.name in seen or ob.hide_render:continue
        seen.add(ob.name)
        if any(s in ob.name for s in ('Grass','Tuft','Blade','Crown','Frond','Leaf','Coconut','Roof','Eave','Sign','Bargeboard')):continue
        p=coordinates(ob)
        if not len(p):continue
        lo,hi=p.min(0),p.max(0)
        if hi[0]<13 or lo[0]>26 or -lo[1]<-7 or -hi[1]>50:continue
        floor=ob.name.startswith(('Town_Floor','Hut_Floor'))
        step=ob.name.startswith(('Town_Step','Hut_EntrySteps','Hut_StairStringer'))
        trunk=ob.name.startswith(('Palm_Trunk','Tree_Trunk','Palm_Root','Tree_Root'))
        if trunk:
            low=p[p[:,2]<=lo[2]+max(.3,(hi[2]-lo[2])*.17)]
            if len(low)>2:lo,hi=low.min(0),low.max(0)
            hi[2]+=1.4
        c=(lo+hi)*.5;h=height(c[0],-c[1]);contact=h is not None and -.9<lo[2]-h<.30
        if not(floor or step or trunk or contact):continue
        if floor:lo[2]-=.38;hi[2]+=5
        pad=np.array([.12,.12,.07]) if floor or step or trunk else np.array([.07,.07,.035])
        occupied.append((lo-pad,hi+pad,ob.name))

# A broad clipped quadrilateral with two unequal corner cuts. The front width
# persists at its bottom and top: it cannot collapse into an upward blade.
OUTLINE=np.array([[-.48,-.28],[-.25,-.48],[.37,-.39],
                  [.49,.21],[.27,.43],[-.39,.38]],float)

def block(row,outline_scale=1.0,reach=.40,zshift=0,hshift=0,height_scale=1.0):
    width=row['alongshore_width_m']*outline_scale
    tall=row['visible_height_design_m']*height_scale
    # Report centre was the old forward point, offset from the designed centre.
    cz=row['center_godot'][2]-.06*row['alongshore_width_m']+zshift
    ch=row['center_godot'][1]-.015*row['visible_height_design_m']+hshift
    group=row['group'];idx=row['spec_index']
    outline=OUTLINE.copy();outline[:,0]+=(outline[:,1]*[.10,-.08,.04][idx%3])
    zz=cz+outline[:,0]*width
    hh=ch+outline[:,1]*tall
    samples=[face_x(z,h,group) for z,h in zip(zz,hh)]
    center=face_x(cz,ch,group)
    if center is None or any(v is None for v in samples):return None,'missing_wall'
    # One least-squares plane for the entire front. Any variation of the source
    # terrain is absorbed into the buried body, never into a faceted front fan.
    design=np.column_stack((zz-cz,hh-ch,np.ones(6)))
    fit=np.linalg.lstsq(np.vstack((design,[0,0,1])),np.asarray(samples+[center]),rcond=None)[0]
    fitted=design@fit
    residual=np.asarray(samples)-fitted
    if float(residual.max()-residual.min())>.44:return None,'wall_curvature_too_high'
    # Place the fitted plane so its furthest corner projects at most 0.45m.
    # The nominal reach stays near 0.4m on planar source faces; curved source
    # sections absorb their residual into burial, not into a pointed corner.
    effective_reach=min(reach,.45-float(residual.max()))
    if effective_reach<.22:return None,'source_plane_needs_smaller_footprint'
    front_x=fitted-effective_reach
    # Keep all front corners sufficiently exposed to show one broad planar
    # face, while limiting every corner to 0.45m horizontal protrusion.
    exposure=np.asarray(samples)-front_x
    if exposure.min()<.16 or exposure.max()>.450001:return None,'plane_exposure_out_of_range'
    front=np.column_stack((front_x,-zz,hh))
    # A parallel rear plane maintains substantial thickness at every corner.
    # It lies behind the furthest local source surface by at least 0.42m.
    depth=effective_reach+float(residual.max())+.44
    back=np.column_stack((front_x+depth,-zz,hh))
    buried=[height(p[0],-p[1])-p[2] for p in back]
    if min(buried)<.12:return None,'back_not_buried'
    verts=np.vstack((front,back));lo,hi=verts.min(0),verts.max(0)
    conflicts=[name for a,b,name in occupied if np.all(hi>a) and np.all(lo<b)]
    if conflicts:return None,'occupied:'+','.join(conflicts[:3])
    for p in list(front)+[front.mean(0)]:
        ground=height(p[0],-p[1])
        if ground is None:return None,'missing_front_ground'
        if path_weight(p[0],-p[1])>.35 and p[2]-ground<2.2:return None,'walkway_clearance'
    # Two simple NGons and six broad side quads. The runtime triangulates the
    # front in one plane; no artificial radial lighting gradients can result.
    faces=[tuple(range(6)),tuple(range(11,5,-1))]
    for j in range(6):faces.append((j,6+j,6+(j+1)%6,(j+1)%6))
    normal=np.cross(front[1]-front[0],front[2]-front[0]);normal/=np.linalg.norm(normal)
    plane_error=float(np.max(abs((front-front[0])@normal)))
    assert plane_error<1e-8
    report={'spec_index':idx,'group':group,'center_godot':[float(front[:,0].mean()),ch,cz],
            'outline_scale':outline_scale,'width_m':width,'height_m':tall,
            'z_adjustment_m':zshift,'height_adjustment_m':hshift,'height_scale':height_scale,
            'nominal_projection_m':reach,'fitted_plane_offset_m':effective_reach,
            'horizontal_projection_range_m':exposure.tolist(),
            'body_depth_m':depth,'back_vertical_burial_range_m':[float(min(buried)),float(max(buried))],
            'front_plane_error_m':plane_error,'front_polygon_vertices':6,
            'bounds_blender_xyz':[lo.tolist(),hi.tolist()],'building_root_conflicts':[]}
    return (verts.tolist(),faces,report),None

vertices=[];faces=[];reports=[];omitted=[]
for row in prior['rocks']:
    accepted=None
    candidates=[(scale,reach,0,0,1) for scale,reach in
                [(1,.40),(1,.37),(.93,.40),(.93,.37),(.85,.40),(.85,.37),(.78,.38)]]
    if row['spec_index']==5:
        # The low trade_north stone conflicts with Town_Footing.006. Keep all
        # occupation tests; move only this authored stone within its group or
        # shorten its height. Narrowing a stone never increases its height.
        candidates.extend((scale,.37,zshift,hshift,height_scale)
                          for scale in (.93,.85,.78)
                          for height_scale in (.85,.70)
                          for zshift,hshift in [(0,.15),(0,.20),(0,-.15),(0,-.20),
                                               (.22,0),(-.22,0),(.35,.15),(-.35,.15),
                                               (.45,.20),(-.45,.20),(.35,-.15),(-.35,-.15)])
    for scale,reach,zshift,hshift,height_scale in candidates:
        accepted,why=block(row,scale,reach,zshift,hshift,height_scale)
        if accepted:break
    if accepted is None and row['spec_index']==5:
        omitted.append({'spec_index':5,'group':row['group'],'reason':why,
                        'candidates_checked':len(candidates)})
        continue
    assert accepted is not None, 'Cannot retain rock '+str(row['spec_index'])+': '+str(why)
    vv,ff,report=accepted;offset=len(vertices);vertices.extend(vv)
    faces.extend(tuple(offset+i for i in face) for face in ff);reports.append(report)
assert len(reports) in (13,14)
assert {r['group'] for r in reports}=={r['group'] for r in prior['rocks']}, 'Every original group must remain'

# Create an unattached candidate; verify it fully before replacing the owned
# object. The existing fourteen-rock mesh remains available on every failure.
candidate=bpy.data.meshes.new('G23_PlanarRockOutcropsMesh')
try:
    candidate.from_pydata(vertices,[],faces);candidate.update()
    bm=bmesh.new();bm.from_mesh(candidate)
    try:
        bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
        assert all(e.is_manifold for e in bm.edges)
        assert all(f.calc_area()>1e-8 for f in bm.faces)
        bmesh.ops.bevel(bm,geom=list(bm.edges),offset=.018,segments=1,
                        affect='EDGES',profile=.5,clamp_overlap=True)
        bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
        assert all(e.is_manifold for e in bm.edges)
        assert all(f.calc_area()>1e-10 for f in bm.faces)
        bm.to_mesh(candidate)
    finally:bm.free()
    candidate.update();candidate.calc_loop_triangles()
    assert len(candidate.loop_triangles)<=2000
    uv=candidate.uv_layers.new(name='RockWorldUV')
    for poly in candidate.polygons:
        poly.use_smooth=False
        for li in poly.loop_indices:
            p=candidate.vertices[candidate.loops[li].vertex_index].co;n=poly.normal
            uv.data[li].uv=(p.x/8,-p.y/8) if abs(n.z)>.68 else ((p.x/8,p.z/8) if abs(n.y)>abs(n.x) else (-p.y/8,p.z/8))
    candidate.materials.append(obj.data.materials[0])
    # Save a compact exact geometry backup and keep the original mesh datablock
    # with a fake user. Restoring obj.data is a reversible local operation.
    previous=obj.data
    coords=np.empty((len(previous.vertices),3),np.float32);previous.vertices.foreach_get('co',coords.ravel())
    loops=np.empty(len(previous.loops),np.int32);previous.loops.foreach_get('vertex_index',loops)
    starts=np.array([p.loop_start for p in previous.polygons],np.int32)
    sizes=np.array([p.loop_total for p in previous.polygons],np.int32)
    np.savez_compressed(str(LOG/'rock_outcrops_v4_mesh_backup.npz'),positions=coords,loops=loops,starts=starts,sizes=sizes)
    previous.use_fake_user=True
    previous.name='G23_EmbeddedRockOutcropsMesh_V4_BACKUP'
    obj.data=candidate
    obj['ground23_planar_outcrops']=True
except Exception:
    if candidate.users==0:bpy.data.meshes.remove(candidate)
    raise
report={'replaced':True,'visual_accepted':False,'rocks':reports,'count':len(reports),'omitted':omitted,
        'vertices':len(candidate.vertices),'triangles':len(candidate.loop_triangles),
        'closed_components':len(reports),'open_edges':0,'nonmanifold_edges':0,
        'front_construction':'one coplanar six-sided face per rock, no forward centre vertex',
        'bevel_m':.018,'backup_mesh':previous.name,
        'backup_file':'rock_outcrops_v4_mesh_backup.npz','saved_blend':False,'exported_assets':False}
(LOG/'rock_outcrops_revised.json').write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf8')
print(json.dumps({k:v for k,v in report.items() if k!='rocks'},ensure_ascii=False))

