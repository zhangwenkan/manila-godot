"""Six continuous terrain shoulders replacing the isolated G23 rock plates.

Execute only through the owned live Blender MCP. No historical modeling body
is executed. The C25 mesh retains its vertices, triangles, boundary and object
transform. All construction and support checks precede mesh modification.
The old plates are hidden and archived only after a successful terrain commit.
No assets are exported and the source is not saved by this script.
"""
import json
from pathlib import Path
import numpy as np


def smooth(a,b,x):
    t=np.clip((x-a)/(b-a),0,1)
    return t*t*(3-2*t)


def band(x,a,b,c,d):
    return smooth(a,b,x)*(1-smooth(c,d,x))


def signed_area(p,t):
    a,b=p[t[:,1]]-p[t[:,0]],p[t[:,2]]-p[t[:,0]]
    return a[:,0]*b[:,1]-a[:,1]*b[:,0]


def land_samples(a,x,z):
    rows,cols=a.shape[:2]
    u=np.clip((x+4)/48*cols-.5,0,cols-1.0001)
    v=np.clip((z+15)/97*rows-.5,0,rows-1.0001)
    ix,iy=u.astype(int),v.astype(int);fx,fy=(u-ix)[:,None],(v-iy)[:,None]
    return ((a[iy,ix]*(1-fx)+a[iy,ix+1]*fx)*(1-fy)
            +(a[iy+1,ix]*(1-fx)+a[iy+1,ix+1]*fx)*fy)


def designs(before,vertex_roles,freedom,previous_rocks):
    """One asymmetric primary shoulder per group, never one bump per rock."""
    x,z,h=before[:,0],-before[:,1],before[:,2]
    delta=np.zeros_like(before);winner=np.full(len(before),-1,np.int32)
    reports=[]
    # group, centre, left/core-left/core-right/right offsets, target reach,
    # diagonal lean of shoulder ends. Secondary groups are deliberately smaller.
    groups=[('trade_south',-3.7,(-2.05,-.95,.80,1.85),.68,.35),
            ('trade_north',5.30,(-1.80,-.75,.90,2.05),.56,-.30),
            ('clinic_south',23.65,(-2.10,-.95,.95,2.00),.76,.42),
            ('clinic_north',29.15,(-1.85,-.80,.75,1.90),.62,-.35),
            ('travel_south',42.25,(-2.00,-.90,.80,1.85),.72,-.38),
            ('travel_north',46.15,(-1.75,-.70,.75,1.90),.52,.28)]
    for index,(name,center,ends,reach,lean) in enumerate(groups):
        old=[row for row in previous_rocks if row['group']==name]
        assert old,'Missing historical group placement '+name
        estimated_x=float(np.mean([row['center_godot'][0] for row in old]))
        seeds=(abs(z-center)<2.25)&(abs(x-estimated_x)<3.0)&(vertex_roles[:,1]>.48)&(h>.6)
        assert seeds.sum()>12,'Insufficient exposed rock vertices for '+name
        foot,crown=np.quantile(h[seeds],[.035,.965])
        assert crown-foot>.85,'Insufficient continuous relief for '+name
        mid=(foot+crown)*.5
        # Fit the existing whole slope, then author one broad slanted plane.
        # Only the selected primary face flattens fully to it. Its apron and
        # end faces smoothly inherit the shift and turn back into the cliff.
        A=np.column_stack((z[seeds]-center,h[seeds]-mid,np.ones(seeds.sum())))
        coefficients=np.linalg.lstsq(A,x[seeds],rcond=None)[0]
        coefficients[0]=np.clip(coefficients[0],-.70,.70)
        coefficients[1]=np.clip(coefficients[1],.25,.85)
        plane=coefficients[2]+coefficients[0]*(z-center)+coefficients[1]*(h-mid)
        q=(h-foot)/(crown-foot)
        longitudinal=z-center-lean*(q-.5)
        along=band(longitudinal,*ends)
        # Keep the full rock body and its toe moving together. Tapering within
        # the steep face would compress tiny XY triangles into a thin bulge.
        # Heights never change; floor, root and walking contacts stay locked.
        vertical=band(q,-.55,-.15,1.05,1.45)
        across=band(x-plane,-2.2,-1.05,1.0,2.15)
        support=along*vertical*across*freedom
        core=band(longitudinal,ends[1]-.15,ends[1]+.12,ends[2]-.12,ends[2]+.15)
        core*=band(q,.12,.30,.66,.83)
        # The wide support translation preserves continuity. Core correction
        # gently straightens the exposed face into the intended broad plane;
        # there is no displaced central point or radial triangle-fan peak.
        target=(plane-reach)-x
        local=support*((1-.20*core)*(-reach)+.20*core*np.clip(target,-1.05,-.10))
        take=local<delta[:,0]
        delta[take,0]=local[take];winner[take]=index
        reports.append({'group':name,'center_godot_z':center,
                        'support_z_offsets':list(ends),'nominal_outward_m':reach,
                        'diagonal_end_lean_m':lean,'estimated_current_x':estimated_x,
                        'foot_crown_height_m':[float(foot),float(crown)],
                        'target_plane_x_coefficients_z_h_constant':coefficients.tolist(),
                        'seed_vertices':int(seeds.sum()),
                        'material_guidance':'exposed continuous rock face; preserve grass crown and grass/soil toe occupancy'})
    delta[(h<=.30)|(z>49)|(z<-7)]=0
    return delta,winner,reports


def local_backtrack(before,proposed,tri,fixed):
    old=signed_area(before,tri);assert np.all(old>0)
    minimum=np.maximum(old*.15,1e-8)
    old_n=np.cross(before[tri[:,1]]-before[tri[:,0]],before[tri[:,2]]-before[tri[:,0]])
    factor=np.ones(len(before));factor[fixed]=0;history=[]
    for k in range(100):
        after=(before+proposed*factor[:,None]).astype(np.float32).astype(float)
        n=np.cross(after[tri[:,1]]-after[tri[:,0]],after[tri[:,2]]-after[tri[:,0]])
        bad=np.flatnonzero((n[:,2]<minimum)|(np.einsum('ij,ij->i',old_n,n)<=0))
        if not len(bad):return after,factor,history
        affected=np.unique(tri[bad]);factor[affected]*=.62
        for _ in range(2):
            limits=np.ones(len(before))
            np.minimum.at(limits,tri.ravel(),np.repeat(np.minimum(1,np.min(factor[tri],1)+.20),3))
            factor=np.minimum(factor,limits);factor[fixed]=0
        history.append({'iteration':k+1,'faces_before_reduction':len(bad)})
    raise RuntimeError('Continuous shoulder backtracking failed; mesh unchanged')


def run(diagnose_only=False):
    import bpy
    from mathutils import Vector
    from mathutils.bvhtree import BVHTree
    assert not bpy.app.background,'Use owned GUI Blender MCP'
    root=Path(bpy.data.filepath).parent.parent;log=root/'captures/ground_integration_20261123'
    terrain=bpy.data.objects['C25_ContourBuiltCoast'];mesh=terrain.data
    plates=bpy.data.objects['G23_EmbeddedRockOutcrops']
    assert terrain.get('ground23_low_shoulder_18') and plates.get('ground23_planar_outcrops')
    assert not terrain.get('ground23_integrated_shoulders'),'One-time pass already applied'
    assert np.max(abs(np.asarray(terrain.matrix_world)-np.eye(4)))<1e-8
    with np.load(log/'low_shoulder_18_before_after.npz') as raw:
        before=raw['positions'].astype(float);tri=raw['triangles'].copy();boundary=raw['boundary'].copy()
    current=np.empty((len(mesh.vertices),3),np.float32);mesh.vertices.foreach_get('co',current.ravel())
    assert np.array_equal(current,before.astype(np.float32)),'Stale pre-shoulder baseline'
    loops=np.empty(len(mesh.loops),np.int32);mesh.loops.foreach_get('vertex_index',loops)
    assert np.array_equal(loops.reshape(-1,3),tri)
    colors=np.empty((len(loops),4),np.float32);mesh.color_attributes['LandUse'].data.foreach_get('color',colors.ravel())
    roles=np.zeros((len(before),4));counts=np.zeros(len(before));np.add.at(roles,loops,colors);np.add.at(counts,loops,1)
    roles/=np.maximum(counts,1)[:,None]
    with np.load(log/'land_data.npz') as raw:land=land_samples(raw['land'],before[:,0],-before[:,1])
    old_bvh=BVHTree.FromPolygons(before.tolist(),tri.tolist(),all_triangles=True)
    def height(bvh,x,y):
        hit=bvh.ray_cast(Vector((float(x),float(y),60)),Vector((0,0,-1)),250)[0]
        return None if hit is None else float(hit.z)
    def coordinates(ob):
        p=np.empty((len(ob.data.vertices),3),np.float32);ob.data.vertices.foreach_get('co',p.ravel())
        m=np.asarray(ob.matrix_world,float);return p.astype(float)@m[:3,:3].T+m[:3,3]
    mandatory=('Town_Floor','Town_Step','Hut_Floor','Hut_EntrySteps','Hut_StairStringer','Town_TavernPorch')
    root_names=('Tree_Trunk','Palm_Trunk','Tree_Root','Palm_Root')
    ignore=('Grass','Blade','Tuft','Crown','Frond','Leaf','Coconut','Canopy','Roof','Rafter','Eave','Bargeboard','Sign','DoorHandle')
    contacts=[];footprints=[];footprint_metadata=[]
    # Only current exported asset collections define real support contacts.
    # Archived objects may have hide_render=False while an owning collection
    # hides the whole historical layout, so scanning scene.objects is unsafe.
    active_objects={}
    def collect_active(collection):
        if collection.hide_render or collection.name.startswith('Archive_'):return
        for ob in collection.objects:
            if not ob.hide_render:active_objects[ob.name]=ob
        for child in collection.children:collect_active(child)
    active_collection_names=('Reference_Town','Reference_Coast','Reference_Foliage','Reference_Rocks')
    for collection_name in active_collection_names:
        assert collection_name in bpy.data.collections,'Missing current asset collection '+collection_name
        collect_active(bpy.data.collections[collection_name])
    for ob in active_objects.values():
        if ob.type!='MESH' or ob==terrain or ob==plates or ob.hide_render:continue
        # The parent rebuilds these small ground accents from the new terrain
        # with pass 04. They must not pin the old surface to their former shape.
        if ob.name.startswith('G23_EmbeddedSlopeFragments'):continue
        required=ob.name.startswith(mandatory);tree=ob.name.startswith(root_names)
        if not required and any(s in ob.name for s in ignore):continue
        b=np.array([ob.matrix_world@Vector(corner) for corner in ob.bound_box]);lo,hi=b.min(0),b.max(0)
        if not required and not(hi[0]>13 and lo[0]<26 and -lo[1]>-7 and -hi[1]<49):continue
        p=coordinates(ob)
        if not len(p):continue
        lo,hi=p.min(0),p.max(0)
        if tree:
            low=p[p[:,2]<lo[2]+max(.20,(hi[2]-lo[2])*.12)]
            if len(low)>2:lo,hi=low.min(0),low.max(0)
        samples=[(float(x),float(y)) for x in np.linspace(lo[0],hi[0],3) for y in np.linspace(lo[1],hi[1],3)]
        hs=[height(old_bvh,x,y) for x,y in samples]
        touching=any(-1.1<lo[2]-h<.28 for h in hs if h is not None)
        if not(required or tree or touching):continue
        if not required and not tree and max(hi[:2]-lo[:2])>8:continue
        footprints.append((lo[:2]-.10,hi[:2]+.10,ob.name))
        contacts.append({'object':ob.name,'samples_xy':samples,'before_heights':hs})
        footprint_metadata.append({'object':ob.name,'required':required,'tree':tree,
            'collections':[c.name for c in ob.users_collection],
            'collection_hide_render':[c.hide_render for c in ob.users_collection],
            'object_hide_get':ob.hide_get(),'bounds_world': [lo.tolist(),hi.tolist()],
            'sample_base_minus_terrain_m':[None if h is None else float(lo[2]-h) for h in hs]})
    assert sum(r['object'].startswith('Town_Floor') for r in contacts)==9
    for name in ('Town_Step','Town_Step.001','Town_Step.002','Town_Step.003','Town_Step.004','Town_Step.005','Town_Step.007','Town_Step.008','Hut_EntrySteps.043','Hut_EntrySteps.051'):
        assert any(r['object']==name for r in contacts),'Missing protected entrance '+name
    xy=before[tri,:2];tlo,thi=xy.min(1),xy.max(1)
    fixed=before[:,2]<=.30;fixed[boundary]=True;freedom=np.ones(len(before));footprint_vertex_ids=[]
    for lo,hi,_ in footprints:
        hit=np.all(thi>=lo,1)&np.all(tlo<=hi,1);locked=np.unique(tri[hit]);fixed[locked]=True
        footprint_vertex_ids.append(locked)
        dx=np.maximum(np.maximum(lo[0]-before[:,0],before[:,0]-hi[0]),0)
        dy=np.maximum(np.maximum(lo[1]-before[:,1],before[:,1]-hi[1]),0)
        freedom=np.minimum(freedom,smooth(.02,.90,np.hypot(dx,dy)))
    # Keep every triangle touching a real strongly occupied walking surface.
    # Mesh roles alone do not represent the revised G23 path network.
    path_vertices=land[:,2]>.48
    path_fixed=np.zeros(len(before),bool)
    path_fixed[np.unique(tri[np.any(path_vertices[tri],axis=1)])]=True
    fixed[path_fixed]=True
    freedom*=1-smooth(.10,.48,land[:,2]);freedom[fixed]=0
    previous=json.loads((log/'rock_outcrops_revised.json').read_text(encoding='utf8'))['rocks']
    proposed,labels,group_reports=designs(before,roles,freedom,previous);proposed[fixed]=0
    after,scales,history=local_backtrack(before,proposed,tri,fixed)
    delta=after-before;changed=np.flatnonzero(np.linalg.norm(delta,axis=1)>1e-6)
    for i,row in enumerate(group_reports):
        ids=(labels==i)&(abs(delta[:,0])>1e-6)
        row['changed_vertices']=int(ids.sum())
        row['maximum_outward_m']=float(-delta[ids,0].min()) if ids.any() else 0
        row['vertices_outward_over_0_25m']=int(np.count_nonzero(ids&(delta[:,0]<-.25)))
    # Persist the exact current scene constraints before testing effectiveness.
    # Diagnose-only calls return here without writing any Blender data.
    ideal,ideal_labels,_=designs(before,roles,np.ones(len(before)),previous)
    for i,row in enumerate(group_reports):
        region=(ideal_labels==i)&(abs(ideal[:,0])>.05)
        row['unconstrained_candidate_vertices']=int(region.sum())
        row['candidate_fixed_vertices']=int(np.count_nonzero(region&fixed))
        row['candidate_path_fixed_vertices']=int(np.count_nonzero(region&path_fixed))
        row['maximum_before_backtracking_m']=float(-proposed[region,0].min()) if region.any() else 0
        row['candidate_freedom_quantiles']=np.quantile(freedom[region],[0,.25,.5,.75,1]).tolist() if region.any() else []
        blocking=[]
        for metadata,locked in zip(footprint_metadata,footprint_vertex_ids):
            count=int(np.count_nonzero(region[locked]))
            if count:
                item=dict(metadata);item['locked_candidate_vertices']=count;blocking.append(item)
        row['locking_footprints']=sorted(blocking,key=lambda r:r['locked_candidate_vertices'],reverse=True)
    failures=[r['group'] for r in group_reports if r['changed_vertices']<12 or r['maximum_outward_m']<.24]
    diagnostic={'diagnose_only':diagnose_only,'mesh_modified':False,'groups':group_reports,
                'active_collection_names':list(active_collection_names),
                'failed_meaningful_groups':failures,'protected_contacts':len(contacts),
                'footprint_metadata':footprint_metadata,'backtracking':history}
    (log/'integrated_shoulders_precommit_diagnostic.json').write_text(json.dumps(diagnostic,indent=2,ensure_ascii=False),encoding='utf8')
    np.savez_compressed(log/'integrated_shoulders_precommit_diagnostic.npz',before=before.astype(np.float32),
        proposed_after=after.astype(np.float32),proposed=proposed.astype(np.float32),ideal=ideal.astype(np.float32),
        triangles=tri,boundary=boundary,roles=roles,land=land,freedom=freedom,fixed=fixed,path_fixed=path_fixed,
        scales=scales,group_labels=labels,ideal_group_labels=ideal_labels,
        footprint_lows=np.array([f[0] for f in footprints]),footprint_highs=np.array([f[1] for f in footprints]),
        footprint_names=np.array([f[2] for f in footprints]))
    if diagnose_only:
        print(json.dumps({'diagnose_only':True,'mesh_modified':False,'protected_contacts':len(contacts),
            'failed_meaningful_groups':failures,'groups':[{k:r[k] for k in
            ('group','changed_vertices','maximum_outward_m','maximum_before_backtracking_m',
             'unconstrained_candidate_vertices','candidate_fixed_vertices','candidate_path_fixed_vertices')} for r in group_reports]},ensure_ascii=False))
        return
    assert not failures,'No meaningful continuous shoulder: '+', '.join(failures)
    # Detailed per-object locks remain in the standalone diagnostic; keep the
    # successful execution result small enough for the MCP transport.
    for row in group_reports:row.pop('locking_footprints',None)
    assert np.array_equal(after[fixed],before[fixed]) and np.array_equal(after[boundary],before[boundary])
    assert np.array_equal(after[:,1:],before[:,1:]),'Shoulder pass must only move terrain X'
    assert np.all(signed_area(after,tri)>0)
    final_bvh=BVHTree.FromPolygons(after.tolist(),tri.tolist(),all_triangles=True)
    max_support=0
    for row in contacts:
        hs=[height(final_bvh,x,y) for x,y in row['samples_xy']];changes=[]
        for a,b in zip(row['before_heights'],hs):
            assert (a is None)==(b is None)
            if a is not None:changes.append(abs(a-b))
        row['max_support_delta_m']=max(changes,default=0);max_support=max(max_support,row['max_support_delta_m'])
    assert max_support<2e-5,'A protected support changed'
    np.savez_compressed(log/'integrated_shoulders_before_after.npz',before=before.astype(np.float32),positions=after.astype(np.float32),
                        proposed=proposed.astype(np.float32),delta=delta.astype(np.float32),triangles=tri,boundary=boundary,
                        fixed=np.flatnonzero(fixed),changed=changed,scales=scales.astype(np.float32),group_labels=labels)
    report={'applied':True,'visual_accepted':False,'groups':group_reports,'changed_vertices':len(changed),
            'max_abs_xyz_delta_m':abs(delta).max(0).tolist(),'negative_xy_triangles':0,'topology_unchanged':True,
            'fixed_boundary':True,'protected_contacts':len(contacts),'max_support_delta_m':max_support,
            'path_triangles_fixed':int(np.count_nonzero(np.any(path_vertices[tri],axis=1))),
            'backtracking':history,'plate_archive_object':plates.name,'exported_assets':False,'saved_blend':False,
            'follow_up':'Refresh land occupancy/UV/cache, re-root grasses and remove ground_rock runtime loading before final captures'}
    old_hide_render=plates.hide_render;old_hide=plates.hide_get();old_collections=list(plates.users_collection)
    archive=None
    try:
        mesh.vertices.foreach_set('co',after.astype(np.float32).ravel());mesh.update()
        actual=np.empty_like(current);mesh.vertices.foreach_get('co',actual.ravel())
        assert np.array_equal(actual,after.astype(np.float32))
        archive=bpy.data.collections.new('Archive_G23_V5_RockPlates')
        bpy.context.scene.collection.children.link(archive);archive.objects.link(plates)
        for col in old_collections:col.objects.unlink(plates)
        plates.hide_render=True;plates.hide_set(True);archive.hide_render=True
        terrain['ground23_integrated_shoulders']=True
        (log/'integrated_shoulders.json').write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf8')
    except Exception:
        mesh.vertices.foreach_set('co',before.astype(np.float32).ravel());mesh.update()
        for col in old_collections:
            if plates.name not in col.objects:col.objects.link(plates)
        if archive:
            if plates.name in archive.objects:archive.objects.unlink(plates)
            bpy.data.collections.remove(archive)
        plates.hide_render=old_hide_render;plates.hide_set(old_hide)
        if 'ground23_integrated_shoulders' in terrain:del terrain['ground23_integrated_shoulders']
        raise
    print(json.dumps(report,ensure_ascii=False))


run()
