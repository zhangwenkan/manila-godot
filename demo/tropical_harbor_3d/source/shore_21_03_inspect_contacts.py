exec((Path(bpy.data.filepath).parent/'shore_21_context.py').read_text(encoding='utf8'),globals())
import bmesh
bm=bmesh.new();bm.from_mesh(mesh)
bad=[(f.index,[round(v,3) for v in f.calc_center_median()],round(f.normal.z,3)) for f in bm.faces if f.normal.z<-.0001]
boundary=[tuple(e.verts[0].co) for e in bm.edges if e.is_boundary]
print('TOPOLOGY',json.dumps({'negative':bad[:40],'negative_count':len(bad),'boundary_count':len(boundary),'nonmanifold':sum(not e.is_manifold and not e.is_boundary for e in bm.edges),'degenerate':sum(f.calc_area()<1e-10 for f in bm.faces)}));bm.free()
out={}
for cname in ['Reference_Coast','Reference_Foliage','Reference_Rocks']:
    obs=[]
    for o in bpy.data.collections[cname].objects:
        c=center(o)
        if 42<-c.y<56 and c.x<22 and o.type=='MESH':
            if cname=='Reference_Foliage' and not any(s in o.name for s in ['Trunk','Shrub']):continue
            if cname=='Reference_Coast' and o.name.startswith(('Hut_','D19_Hut','D19_Thatch','D19_Reed','Pier_','D19_Deck','D19_Pile')):continue
            obs.append((o.name,[round(v,3) for v in c],[round(v,3) for v in o.dimensions],round(bounds(o)[2][0],3),round(ground(c.x,-c.y),3)))
    out[cname]=obs
(LOG/'local_objects.json').write_text(json.dumps(out,indent=2),encoding='utf8')
print('LOCAL_OBJECTS',json.dumps(out))
