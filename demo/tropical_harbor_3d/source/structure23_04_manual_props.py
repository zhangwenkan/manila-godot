"""Specific reviewed placements only, in the owned GUI MCP after local courts.
Repeatable from objects_before.json; no search, export, save, or mesh mutation.
"""
import bpy,os,json,math,numpy as np,sys
from pathlib import Path
from mathutils import Matrix,Vector
from mathutils.bvhtree import BVHTree
ROOT=Path(bpy.data.filepath).parent.parent
LOG=ROOT/'captures/terrain_structure_20261123'
assert not bpy.app.background
session=json.loads((LOG/'session_start.json').read_text(encoding='utf8'))
assert os.getpid()==session['pid'] and bpy.types.blendermcp_server.port==session['port']
sys.path.insert(0,str(ROOT/'source'))
import importlib,structure23_common as util
importlib.reload(util)
records={r['name']:r for r in json.loads((LOG/'objects_before.json').read_text(encoding='utf8'))}
report=json.loads((LOG/'props.json').read_text(encoding='utf8'))
groups={g['group']:g for g in report['groups']}
design=json.loads((LOG/'design.json').read_text(encoding='utf8'))
terrain=bpy.data.objects['C25_ContourBuiltCoast'];mesh=terrain.data
assert terrain.get('structure23_grade') and terrain.get('structure23_land')
bvh=BVHTree.FromPolygons([v.co.copy() for v in mesh.vertices],[list(p.vertices) for p in mesh.polygons],all_triangles=True)
baseline={n:Matrix(r['matrix']) for n,r in records.items()}
cache={}
def xyz(name):
    if name not in cache:
        o=bpy.data.objects[name]
        assert len(o.data.vertices)==records[name]['vertices'],'Unexpected geometry change: '+name
        raw=np.empty(len(o.data.vertices)*3);o.data.vertices.foreach_get('co',raw)
        mat=np.array(baseline[name]);cache[name]=raw.reshape(-1,3)@mat[:3,:3].T+mat[:3,3]
    return cache[name]
def prefix(name):
    a=name.rsplit('.',1);return a[0] if len(a)==2 and a[1].isdigit() else name
def ray(q):
    hit,normal,index,distance=bvh.ray_cast(Vector((float(q[0]),float(q[1]),80)),Vector((0,0,-1)),200)
    assert hit is not None,'No ground under authored location'
    return float(hit.z)
def group(key):
    return groups[key]['objects'][:]
def centered(body,target):
    b=np.array(records[body]['bounds']);centre=np.array([(b[0,0]+b[1,0])/2,-(b[0,1]+b[1,1])/2])
    return (np.array(target)-centre).tolist()
def series(stem,indices):
    return [stem+'.'+str(i).zfill(3) for i in indices]
def entry(name,objects,supports,pivot,shift,angle,gap,why):
    return dict(name=name,objects=objects,supports=supports,pivot=pivot,shift=shift,angle=angle,gap=gap,reason=why)

jobs=[
 entry('second_fish_stall',group('market_stall:Town_MarketPost.004'),series('Town_MarketPost',range(4,8)),[0,0],[0,-2.2],0,.008,'Keep the complete stall beside the lower road, ahead of the north ramp, on the new local market court.'),
 entry('restaurant_north_seating',group('seating:Town_TableLeg.008'),series('Town_TableLeg',range(8,12))+series('Town_ChairLeg',range(16,24)),[13.885,22.064],[.55,-.09],90,.005,'Turn the complete table and two chairs along the facade, keeping road, entry and awning post clear.'),
 entry('restaurant_north_planter',group('planter:Town_Planter.005'),['Town_Planter.005'],[0,0],centered('Town_Planter.005',[15.95,20.65]),0,.005,'Move the complete planter into the same restaurant north court corner, beside the supply group.'),
 entry('shore_net',group('coast_prop:S20_NetPost'),['S20_NetPost'],[8.044841766357422,41.97568702697754],[-.25,-2.2],90,-.025,'Place the complete net parallel to the shore on the existing dry sand strip.'),
 entry('shore_timber',group('coast_prop:S20_StackBearers'),['S20_StackBearers','S20_StackBearers.001'],[7.767475605010986,42.085968017578125],[-.05,.7],90,-.012,'Rotate the complete timber stack and its bearers along the shore, clear of the net and existing crate.'),
]
crate_a=['S20_fishing_Prop_Crate.002']+series('S20_fishing_Crate_Frame',range(5,9))+series('S20_fishing_Crate_Rail',range(5,9))+series('S20_fishing_Crate_Diagonal',range(3,5))
crate_b=['S20_fishing_Prop_Crate.003']+series('S20_fishing_Crate_Frame',range(9,13))+series('S20_fishing_Crate_Rail',range(9,13))+series('S20_fishing_Crate_Diagonal',range(5,7))
barrel=['S20_fishing_Prop_Barrel.001']+series('S20_fishing_Barrel_IronHoop',range(1,3))+['S20_fishing_Barrel_Lid.001']
assert set(crate_a+crate_b+barrel)==set(group('coast_prop:S20_fishing_Crate_Frame.005')),'The supply cluster partition changed'
for name,names,body,target in [('shore_crate_a',crate_a,crate_a[0],[7.15,39.3]),('shore_crate_b',crate_b,crate_b[0],[7.15,40.35]),('shore_barrel',barrel,barrel[0],[7.1,41.4])]:
    jobs.append(entry(name,names,[body],[0,0],centered(body,target),0,-.008,'Place this complete individual supply object beside the shore net, avoiding the new slope.'))
assert len([n for j in jobs for n in j['objects']])==len({n for j in jobs for n in j['objects']})

def hull_hit(a,b,padding=.015):
    if np.any(a.max(0)+padding<b.min(0)) or np.any(b.max(0)+padding<a.min(0)):return False
    for p in (a,b):
        for edge in np.roll(p,-1,axis=0)-p:
            axis=np.array([-edge[1],edge[0]]);length=np.linalg.norm(axis)
            if length<1e-9:continue
            axis/=length;aa,bb=a@axis,b@axis
            if aa.max()+padding<bb.min() or bb.max()+padding<aa.min():return False
    return True

struct=[]
for name in records:
    if prefix(name) in ('Town_Floor','Town_Footing','Town_Step','Town_AwningPost','Town_SchoolPorchPost','Hut_Floor','Hut_EntrySteps') or name.startswith('Town_TavernPorch'):
        q=xyz(name);hull=util.convex_hull(q[:,:2])
        if len(hull)>2:struct.append((name,hull))
targets={};results=[];proposed_hulls={};problems=[]
for job in jobs:
    px,pz=job['pivot'];dx,dz=job['shift'];pivot=Vector((px,-pz,0))
    transform=Matrix.Translation(pivot+Vector((dx,-dz,0)))@Matrix.Rotation(-math.radians(job['angle']),4,'Z')@Matrix.Translation(-pivot)
    contacts=[]
    for name in job['supports']:
        pp=xyz(name);low=pp[pp[:,2]<=pp[:,2].min()+.025]
        contacts.extend(np.array(transform@Vector(q)) for q in low)
    contacts=np.array(contacts)
    needed=np.array([ray(q)+job['gap']-q[2] for q in contacts])
    vertical=float(np.median(needed))
    # A shallow beach crossfall can partially bury feet; do not raise every
    # object to the highest sand point and leave its other side floating.
    final_gaps=np.array([q[2]+vertical-ray(q) for q in contacts])
    if final_gaps.min()<-.075 or final_gaps.max()>.075:
        problems.append({'job':job['name'],'reason':'support_spread_requires_court_or_adjustment','gap_range':[float(final_gaps.min()),float(final_gaps.max())]})
    transform=Matrix.Translation(Vector((0,0,vertical)))@transform
    low=[];afterpoints=[]
    bottom=min(float(xyz(name)[:,2].min()) for name in job['objects'])
    for name in job['objects']:
        q=xyz(name);qq=np.array([transform@Vector(p) for p in q]);afterpoints.append(qq)
        low.append(qq[q[:,2]<=bottom+1.15])
        targets[name]=transform@baseline[name]
    low=np.concatenate([p for p in low if len(p)]);hull=util.convex_hull(low[:,:2]);proposed_hulls[job['name']]=hull
    blocked=[name for name,bh in struct if hull_hit(hull,bh)]
    if blocked:problems.append({'job':job['name'],'reason':'structural_overlap','objects':blocked})
    # Dense perimeter and interior samples catch a route passing through an
    # object hull even when the hull's corners are outside that route.
    lo,hi=hull.min(0),hull.max(0);xx,yy=np.meshgrid(np.linspace(lo[0],hi[0],12),np.linspace(lo[1],hi[1],12));pp=np.c_[xx.ravel(),yy.ravel()]
    pp=pp[util.polygon_distance(pp[:,0],pp[:,1],hull)<=.001]
    route_clearance=[]
    for route in design['routes']:
        dd,_=util.route_profile(pp[:,0],-pp[:,1],route['points']);margin=float(dd.min()-route['halfwidth'])
        if margin<.2:route_clearance.append([route['name'],margin])
        if margin<.015:problems.append({'job':job['name'],'reason':'route_overlap','route':route['name'],'margin':margin})
    results.append({**job,'vertical_translation':vertical,'contact_gap_range':[float(final_gaps.min()),float(final_gaps.max())],
                    'near_route_margins':route_clearance,'after_hull_blender_xy':hull.tolist(),
                    'before_matrices':{name:records[name]['matrix'] for name in job['objects']},
                    'after_matrices':{name:np.array(targets[name]).tolist() for name in job['objects']}})
for i,a in enumerate(jobs):
    for b in jobs[i+1:]:
        if hull_hit(proposed_hulls[a['name']],proposed_hulls[b['name']],.035):
            problems.append({'job':a['name'],'reason':'manual_group_overlap','other':b['name']})
# Check current low footprints of all other complete props, excluding only the
# groups being replaced above. This catches a nearby moved planter or supply
# pile without treating a whole tree crown as a ground obstacle.
target_names=set(targets)
other_hulls=[]
for existing in groups.values():
    if set(existing['objects'])&target_names:continue
    names=[existing['support_object']] if existing['kind'] in ('tree','palm') else existing['objects']
    world=[]
    for name in names:
        ob=bpy.data.objects[name];world.append(np.array([ob.matrix_world@v.co for v in ob.data.vertices]))
    bottom=min(float(q[:,2].min()) for q in world)
    low=np.concatenate([q[q[:,2]<=bottom+(0.65 if existing['kind'] in ('tree','palm') else 1.15)] for q in world if np.any(q[:,2]<=bottom+(0.65 if existing['kind'] in ('tree','palm') else 1.15))])
    hull=util.convex_hull(low[:,:2])
    if len(hull)>2:other_hulls.append((existing['group'],hull))
for job in jobs:
    for name,hull in other_hulls:
        if hull_hit(proposed_hulls[job['name']],hull,.035):
            problems.append({'job':job['name'],'reason':'existing_prop_overlap','other':name})
summary={'stage':'structure23_04_manual_props','source':'objects_before.json','jobs':results,'problems':problems,'applied':False,'saved':False,'exported':False,'visual_accepted':False}
(LOG/'manual_props_plan.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf8')
assert not problems,'Authored manual placement needs review: '+json.dumps(problems,ensure_ascii=False)
if globals().get('STRUCTURE23_MANUAL_PROPS_APPLY',True):
    preserve={name:bpy.data.objects[name].matrix_world.copy() for name in records if name not in targets}
    def depth(name):
        n=0;o=bpy.data.objects[name]
        while o.parent is not None:n+=1;o=o.parent
        return n
    for name in sorted(targets,key=depth):bpy.data.objects[name].matrix_world=targets[name]
    bpy.context.view_layer.update()
    assert all(np.max(np.abs(np.array(bpy.data.objects[name].matrix_world)-np.array(mat)))<3e-5 for name,mat in targets.items())
    assert all(np.max(np.abs(np.array(bpy.data.objects[name].matrix_world)-np.array(mat)))<3e-5 for name,mat in preserve.items())
    terrain['structure23_manual_props']=True;summary['applied']=True
    (LOG/'manual_props.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps({'jobs':len(jobs),'components':len(targets),'applied':summary['applied'],'problems':problems},ensure_ascii=False))
