"""Reconcile existing plants with the reviewed road contacts, through GUI MCP."""
import bpy,bmesh,json,numpy as np
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT=Path(bpy.data.filepath).parent.parent;LOG=ROOT/'captures/road_contacts_20261123'
t=bpy.data.objects['C25_ContourBuiltCoast'];assert t.get('road23_contacts_grade')
assert not t.get('road23_grass_contacts'),'Already applied to the current grass population'
with np.load(str(LOG/'land_data.npz')) as f:land=f['land'].copy();scope=f['scope'].copy()
with np.load(str(LOG/'baseline.npz')) as f:oldp=f['positions'].copy();tri=f['loops'].reshape(-1,3).copy()
bpy.context.view_layer.update()
bvh=BVHTree.FromObject(t,bpy.context.evaluated_depsgraph_get())
oldbvh=BVHTree.FromPolygons(oldp.tolist(),tri.tolist(),all_triangles=True)
def sample(a,x,z):
    px=float(np.clip((x+4)/48*2048-.5,0,2046.999));pz=float(np.clip((z+15)/97*2048-.5,0,2046.999))
    ix,iz=int(px),int(pz);fx,fz=px-ix,pz-iz
    return ((a[iz,ix]*(1-fx)+a[iz,ix+1]*fx)*(1-fz)+(a[iz+1,ix]*(1-fx)+a[iz+1,ix+1]*fx)*fz)
def hit(b,x,y):
    h,n,_,_=b.ray_cast(Vector((float(x),float(y),40)),Vector((0,0,-1)),120)
    assert h is not None;return h,n
reports=[]
for name in ('L24_GrassTuftClusters','G23_RootedGrassMargins'):
    ob=bpy.data.objects[name];matrix=ob.matrix_world;inverse=matrix.to_3x3().inverted()
    bm=bmesh.new();bm.from_mesh(ob.data);bm.faces.ensure_lookup_table()
    before=len(bm.faces);remove=[];roots=[];bases=[];unchanged=0
    for face in bm.faces:
        assert len(face.verts)==3 and all(len(v.link_faces)==1 for v in face.verts)
        pp=[matrix@v.co for v in face.verts];root=(pp[0]+pp[1])*.5
        assert abs(pp[0].z-pp[1].z)<.003 and pp[2].z-max(pp[0].z,pp[1].z)>.025
        if not (9.5<root.x<26 and 8.5<-root.y<34.5):unchanged+=1;continue
        h,no=hit(bvh,root.x,root.y);oldh,_=hit(oldbvh,root.x,root.y)
        if sample(scope,root.x,-root.y)<.001 and abs(h.z-oldh.z)<1e-5:unchanged+=1;continue
        rr=[sample(land,p.x,-p.y) for p in [root,*pp[:2]]]
        # Keep actual roots out of both the compacted route and its thin margin.
        if any(r[2]>.20 or r[0]<.40 or r[1]>.45 or r[3]>.48 for r in rr) or no.z<.60:
            remove.append(face);continue
        hs=[hit(bvh,p.x,p.y)[0].z for p in pp[:2]]
        embed=.012 if name.startswith('L24') else .008
        delta=min(h.z-root.z,*(hh-p.z for hh,p in zip(hs,pp[:2])))-embed
        shift=inverse@Vector((0,0,delta))
        for vert in face.verts:vert.co+=shift
        roots.append(root.z+delta-h.z);bases.extend(p.z+delta-hh for p,hh in zip(pp[:2],hs))
    if remove:bmesh.ops.delete(bm,geom=[v for f in remove for v in f.verts],context='VERTS')
    original=ob.data;copy=original.copy();bm.to_mesh(copy);copy.update();bm.free();ob.data=copy
    assert len(copy.vertices)==len(copy.polygons)*3
    assert not bases or max(bases)<0
    reports.append({'name':name,'before_triangles':before,'after_triangles':len(copy.polygons),'removed':len(remove),
                    'regrounded':len(roots),'unchanged':unchanged,'root_gap_range':[min(roots),max(roots)] if roots else None,
                    'basal_gap_range':[min(bases),max(bases)] if bases else None})
ob=bpy.data.objects['G23_EmbeddedSlopeFragments'];bm=bmesh.new();bm.from_mesh(ob.data)
todo=set(bm.verts);remove=[];shifted=0;total=0
while todo:
    pending=[next(iter(todo))];group=set()
    while pending:
        vert=pending.pop()
        if vert in group:continue
        group.add(vert);pending.extend(e.other_vert(vert) for e in vert.link_edges)
    todo-=group;total+=1
    # Each final G23 fragment has 13 vertices, with its bottom six-vertex ring.
    assert len(group)==13
    points=[ob.matrix_world@q.co for q in group];x=sum(p.x for p in points)/len(points);y=sum(p.y for p in points)/len(points)
    h,_=hit(bvh,x,y);oh,_=hit(oldbvh,x,y)
    if not (9.5<x<26 and 8.5<-y<34.5):continue
    r=sample(land,x,-y)
    if sample(scope,x,-y)>.001 and r[2]>.25:remove.extend(group);continue
    delta=h.z-oh.z
    if abs(delta)>1e-5:
        shift=ob.matrix_world.to_3x3().inverted()@Vector((0,0,delta))
        for q in group:q.co+=shift
        shifted+=1
if remove:bmesh.ops.delete(bm,geom=remove,context='VERTS')
old=ob.data;copy=old.copy();bm.to_mesh(copy);copy.update();bm.free();ob.data=copy
t['road23_grass_contacts']=True
report={'grass':reports,'fragments_before':total,'fragments_removed':len(remove)//13,'fragments_shifted':shifted,'visual_accepted':False}
(LOG/'grass_contacts.json').write_text(json.dumps(report,indent=2),encoding='utf8');print(json.dumps(report))
