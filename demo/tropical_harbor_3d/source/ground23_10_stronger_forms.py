"""Second, deliberately larger connected landform pass; owned Blender MCP only.

Makes broad, offset shoulder/foot faces and recesses. No periodic sculpt noise,
object movement, topology editing, material edits, export, or source save.
The current G23 surface, not the earlier unmodified C25, is the input baseline.
"""
import json
import time
from pathlib import Path
import numpy as np


def smooth(a, b, v):
    q = np.clip((v-a)/(b-a), 0, 1)
    return q*q*(3-2*q)


def signed_area(p, tri):
    a, b = p[tri[:, 1]]-p[tri[:, 0]], p[tri[:, 2]]-p[tri[:, 0]]
    return a[:, 0]*b[:, 1]-a[:, 1]*b[:, 0]


def band(v, a, b, c, d):
    return smooth(a, b, v)*(1-smooth(c, d, v))


def linear_lobe(v, knots):
    return np.interp(v, [k[0] for k in knots], [k[1] for k in knots], left=0, right=0)


def design_positions(p, roles, freedom):
    x, z, h = p[:, 0], -p[:, 1], p[:, 2]
    displacement = np.zeros_like(p)
    pieces = []
    # The two sections use independently sampled foot/crown x positions. The
    # broad influence extends onto the immediate apron so a 0.9m shoulder does
    # not shear against an immobile toe only centimetres away.
    for title, zs, zwin, lower, upper, definitions in [
        ('clinic', np.arange(20.5, 32, .5), (20.7,21.7,30.3,31.4), 1.22,4.30,
         [(23.4,1.00,.85,[(20.9,0),(22.0,.78),(23.5,1),(24.6,.88),(26.0,0)]),
          (29.1,.94,-.70,[(26.0,0),(27.4,.82),(29.0,1),(30.1,.83),(31.4,0)])]),
        ('travel', np.arange(40,48,.5), (40.5,41.2,46.4,47.2), 1.47,3.48,
         [(42.2,.96,-.70,[(40.4,0),(41.35,.83),(42.3,1),(43.1,.86),(44.0,0)]),
          (45.6,.88,.55,[(43.6,0),(44.6,.76),(45.7,1),(46.4,.81),(47.4,0)])])]:
        sample_z, face_x = [], []
        for zz in zs:
            ids = (abs(z-zz)<.6)&(roles[:,1]>.35)&(x>16)&(x<24)&(h>lower+.1)&(h<upper+.1)
            if np.count_nonzero(ids)>3:
                sample_z.append(float(zz));face_x.append(float(np.median(x[ids])))
        assert len(sample_z)>8, 'Cannot locate the current '+title+' rock face'
        centre_x = np.interp(z,sample_z,face_x)
        across = band(x-centre_x,-3.1,-1.65,1.30,2.55)
        q = np.clip((h-lower)/(upper-lower),-.5,1.5)
        # Lower shoulder protrudes at a different height from the upper turn.
        # Wide planar flank connections; no sine/gaussian balloon extrusion.
        vertical = linear_lobe(q,[(-.35,0),(-.05,.48),(.25,.92),(.64,1),(.93,.74),(1.18,.30),(1.43,0)])
        section = band(z,*zwin)*across*freedom
        if title=='clinic': section*=band(x,17.3,18.1,23.3,24.4)
        else: section*=band(x,16.0,16.7,22.4,23.3)
        outward = np.zeros(len(p));slide=np.zeros(len(p));lift=np.zeros(len(p))
        for center, reach, lean, knots in definitions:
            # Diagonal shoulder boundary moves along z as height increases.
            lobe = linear_lobe(z-lean*(q-.45),knots)
            weight = lobe*vertical
            take = weight*reach>outward
            outward[take]=(weight*reach)[take]
            slide[take]=(weight*(.12 if lean>0 else -.12))[take]
            lift[take]=(lobe*linear_lobe(q,[(-.35,0),(0,-.05),(.32,.18),(.68,.09),(1,-.08),(1.43,0)]))[take]
            pieces.append({'name':title+'_shoulder','center_z':center,'reach_m':reach,
                           'lean_m':lean,'alongshore_knots':knots})
        notch_center=26.15 if title=='clinic' else 43.95
        notch_width=1.40 if title=='clinic' else .92
        notch=linear_lobe((z-notch_center+.55*(q-.35))/notch_width,
                          [(-1,0),(-.45,.8),(.10,1),(.55,.78),(1,0)])
        notch*=linear_lobe(q,[(-.2,0),(.10,.45),(.45,1),(.80,.75),(1.15,0)])
        displacement[:,0]+=section*(-outward+(.42 if title=='clinic' else .36)*notch)
        displacement[:,1]+=section*(-slide+.07*notch)
        displacement[:,2]+=section*(lift-.12*notch)
        pieces.append({'name':title+'_recess','center_z':notch_center,
                       'half_width_m':notch_width,'inward_m':.42 if title=='clinic' else .36,
                       'material_note':'rock recess face; soil only in its lower concave foot'})

    # Exactly two lower shore edits. Water-side fringe and building support
    # remain fixed; upper grass/earth no longer ends in a continuous step.
    grass = (band(z,28.6,30.0,32.5,34.0)*band(x,9.2,10.2,12.2,13.6)
             *smooth(.32,.55,h)*(1-smooth(1.35,1.70,h))*freedom)
    # Restore a gently falling grass shoulder onto the upper sand; taper its
    # interior edge so a soil strip visibly terminates beside the grass tongue.
    target = .35 + .145*np.maximum(x-9.45,0)
    displacement[:,2]+=grass*np.clip(target-h,-.31,.12)
    displacement[:,0]-=.24*grass
    bay = (band(z,10.0,11.6,13.9,16.5)*band(x,10.1,11.5,14.5,15.8)
           *smooth(.30,.45,h)*(1-smooth(1.4,1.85,h))*freedom)
    bay_target=.30+.105*np.maximum(x-10.9,0)
    displacement[:,2]+=bay*np.clip(bay_target-h,-.40,0)
    displacement[:,0]+=.12*bay
    # All below/water-adjacent terrain is exactly unchanged.
    displacement[h<=.30]=0
    pieces.extend([
        {'name':'low_grass_tongue','bounds_xz':[9.2,28.6,13.6,34.0],
         'full_weight_xz':[10.2,30.0,12.2,32.5],
         'material_note':'grass reaches down to height~0.45; soil terminates at both sides; sand outside foot'},
        {'name':'extended_sand_cove','bounds_xz':[10.1,10.0,15.8,16.5],
         'full_weight_xz':[11.5,11.6,14.5,13.9],
         'material_note':'sand on lowered centre to x14.5; sparse soil at inner uphill end; grass banks to either side'}])
    return displacement,pieces


def safe_local_displacement(before, displacement, tri, fixed):
    minimum=np.maximum(signed_area(before,tri)*.12,1e-8)
    assert np.all(minimum>0)
    factor=np.ones(len(before));factor[fixed]=0;history=[]
    for iteration in range(100):
        after=(before+displacement*factor[:,None]).astype(np.float32).astype(float)
        bad=np.flatnonzero(signed_area(after,tri)<minimum)
        if not len(bad): return after,factor,history
        affected=np.unique(tri[bad]);factor[affected]*=.60
        # Limit the transition into a reduced patch to keep adjacent broad
        # faces coherent. The same reduction applies to XYZ, never just height.
        for _ in range(2):
            lim=np.ones(len(before))
            np.minimum.at(lim,tri.ravel(),np.repeat(np.minimum(1,np.min(factor[tri],axis=1)+.18),3))
            factor=np.minimum(factor,lim);factor[fixed]=0
        history.append({'iteration':iteration+1,'bad_before_reduction':len(bad)})
    raise RuntimeError('Local XY backtracking failed; mesh remains unchanged')


def run():
    import bpy
    from mathutils import Vector
    from mathutils.bvhtree import BVHTree
    root=Path(bpy.data.filepath).parent.parent;log=root/'captures/ground_integration_20261123'
    terrain=bpy.data.objects['C25_ContourBuiltCoast'];mesh=terrain.data
    assert terrain.get('ground23_forms') and not terrain.get('ground23_stronger_forms'), 'Wrong state or replay'
    assert np.max(abs(np.asarray(terrain.matrix_world)-np.eye(4)))<1e-8
    with np.load(str(log/'forms_before_after.npz')) as raw:
        before=raw['positions'].astype(float);tri=raw['triangles'].copy();boundary=raw['boundary'].copy()
    current=np.empty((len(mesh.vertices),3),np.float32);mesh.vertices.foreach_get('co',current.ravel())
    assert np.array_equal(current,before.astype(np.float32)), 'Current terrain differs from first G23 pass'
    loops=np.empty(len(mesh.loops),np.int32);mesh.loops.foreach_get('vertex_index',loops)
    assert np.array_equal(loops.reshape(-1,3),tri)
    colors=np.empty((len(mesh.loops),4),np.float32);mesh.color_attributes['LandUse'].data.foreach_get('color',colors.ravel())
    roles=np.zeros((len(before),4));counts=np.zeros(len(before));np.add.at(roles,loops,colors);np.add.at(counts,loops,1)
    roles/=np.maximum(counts,1)[:,None]
    old_bvh=BVHTree.FromPolygons(before.tolist(),tri.tolist(),all_triangles=True)
    down=Vector((0,0,-1))
    def height(bvh,x,y):
        hit=bvh.ray_cast(Vector((float(x),float(y),50)),down,200)[0]
        return None if hit is None else float(hit.z)
    def coordinates(obj):
        a=np.empty((len(obj.data.vertices),3),np.float32);obj.data.vertices.foreach_get('co',a.ravel())
        mat=np.asarray(obj.matrix_world,float);return a.astype(float)@mat[:3,:3].T+mat[:3,3]
    footprints=[];contacts=[];seen=set()
    mandatory=('Town_Floor','Town_Step','Hut_Floor','Hut_EntrySteps','Hut_StairStringer','Town_TavernPorch')
    root_names=('Tree_Trunk','Palm_Trunk','Tree_Root','Palm_Root')
    for cname in ('Reference_Town','Reference_Coast','Reference_Foliage','Reference_Rocks'):
        for obj in bpy.data.collections[cname].all_objects:
            if obj.type!='MESH' or obj.name in seen or obj.hide_render or any(w in obj.name for w in ('Grass','Blade','Tuft','Crown','Frond','Leaf','Coconut','Canopy','Roof','Rafter','Eave','Bargeboard','Sign','DoorHandle')):continue
            seen.add(obj.name);p=coordinates(obj)
            if not len(p):continue
            lo,hi=p.min(0),p.max(0);required=obj.name.startswith(mandatory)
            if not required and not(hi[0]>8 and lo[0]<25 and -lo[1]>9 and -hi[1]<48):continue
            tree=obj.name.startswith(root_names)
            if tree:
                low=p[p[:,2]<lo[2]+max(.20,(hi[2]-lo[2])*.12)]
                if len(low)>=3:lo,hi=low.min(0),low.max(0)
            samples=[(lo[0],lo[1]),(lo[0],hi[1]),(hi[0],lo[1]),(hi[0],hi[1]),((lo[0]+hi[0])*.5,(lo[1]+hi[1])*.5)]
            hs=[height(old_bvh,x,y) for x,y in samples]
            gaps=[lo[2]-h for h in hs if h is not None]
            # Compact actual low contacts, not the projection of an unrelated
            # high fixture. Root/stair/floor semantics independently protected.
            touching=any(-1.1<gap<.28 for gap in gaps)
            if not(required or tree or touching):continue
            footprints.append((lo[:2]-.10,hi[:2]+.10,obj.name))
            contacts.append({'object':obj.name,'samples_xy':samples,'before_heights':hs})
    assert sum(r['object'].startswith('Town_Floor') for r in contacts)==9
    assert all(any(r['object']==name for r in contacts) for name in ['Town_Step.001','Town_Step.002','Town_Step.003','Town_Step.004','Town_Step.005','Town_Step.008'])
    fixed=np.zeros(len(before),bool);fixed[boundary]=True;freedom=np.ones(len(before))
    xy=before[tri,:2];lo_tri,hi_tri=xy.min(1),xy.max(1)
    for lo,hi,_ in footprints:
        hit=np.all(hi_tri>=lo,1)&np.all(lo_tri<=hi,1);fixed[np.unique(tri[hit])]=True
        dx=np.maximum(np.maximum(lo[0]-before[:,0],before[:,0]-hi[0]),0)
        dy=np.maximum(np.maximum(lo[1]-before[:,1],before[:,1]-hi[1]),0)
        freedom=np.minimum(freedom,smooth(.02,.52,np.hypot(dx,dy)))
    freedom[fixed]=0
    displacement,pieces=design_positions(before,roles,freedom);displacement[fixed]=0
    after,factors,backtrack=safe_local_displacement(before,displacement,tri,fixed)
    delta=after-before
    assert np.array_equal(after[boundary],before[boundary])
    assert np.array_equal(after[before[:,2]<=.30],before[before[:,2]<=.30])
    assert np.all(signed_area(after,tri)>0)
    new_bvh=BVHTree.FromPolygons(after.tolist(),tri.tolist(),all_triangles=True)
    maximum_support_delta=0
    for row in contacts:
        new=[height(new_bvh,x,y) for x,y in row['samples_xy']]
        changes=[]
        for a,b in zip(row['before_heights'],new):
            assert (a is None)==(b is None)
            if a is not None:changes.append(abs(a-b))
        row['max_height_delta_m']=max(changes,default=0)
        maximum_support_delta=max(maximum_support_delta,row['max_height_delta_m'])
    assert maximum_support_delta<=2e-5,'A protected support changed'
    changed=np.flatnonzero(np.linalg.norm(delta,axis=1)>1e-6)
    report={'applied':True,'visual_accepted':False,'design':pieces,'changed_vertices':len(changed),
            'max_abs_xyz_delta_m':abs(delta).max(0).tolist(),
            'outward_over_0_6m':int(np.count_nonzero(delta[:,0]<-.60)),
            'outward_over_0_3m':int(np.count_nonzero(delta[:,0]<-.30)),
            'inward_over_0_15m':int(np.count_nonzero(delta[:,0]>.15)),
            'negative_xy_triangles':0,'fixed_boundary':True,'fixed_water':True,
            'protected_contact_count':len(contacts),'max_support_delta_m':maximum_support_delta,
            'backtracking':backtrack,'contacts':contacts,'saved_blend':False,'exported_assets':False}
    np.savez_compressed(str(log/'stronger_forms_before_after.npz'),before=before.astype(np.float32),positions=after.astype(np.float32),
                        proposed=displacement.astype(np.float32),delta=delta.astype(np.float32),triangles=tri,
                        boundary=boundary,changed=changed,fixed=np.flatnonzero(fixed),scales=factors.astype(np.float32))
    try:
        mesh.vertices.foreach_set('co',after.astype(np.float32).ravel());mesh.update()
        terrain['ground23_stronger_forms']=True
        (log/'stronger_forms.json').write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf8')
    except Exception:
        mesh.vertices.foreach_set('co',before.astype(np.float32).ravel());mesh.update()
        if 'ground23_stronger_forms' in terrain:del terrain['ground23_stronger_forms']
        raise
    print(json.dumps({k:v for k,v in report.items() if k not in ('contacts','design')},ensure_ascii=False))


run()
