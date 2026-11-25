exec((Path(bpy.data.filepath).parent/'shore_21_context.py').read_text(encoding='utf8'),globals())
LOG=ROOT/'captures/rock_earth_rebuild_20261121';LOG.mkdir(exist_ok=True)
attr=mesh.color_attributes['LandUse']
groups={k:[] for k in ['rock','soil','grass','path','sand']}
for p in mesh.polygons:
    col=np.mean([attr.data[i].color for i in p.loop_indices],axis=0)
    role=['grass','rock','path','soil'][int(np.argmax(col))] if max(col)>.45 else 'sand'
    if p.center.z>.18 and -15<-p.center.y<85:
        groups[role].append({'i':p.index,'center':list(p.center),'normal':list(p.normal),'area':p.area,'vertices':list(p.vertices)})
np.savez_compressed(str(LOG/'terrain_before.npz'),positions=np.array([v.co for v in mesh.vertices]),loops=np.array([l.vertex_index for l in mesh.loops]),starts=np.array([p.loop_start for p in mesh.polygons]),sizes=np.array([p.loop_total for p in mesh.polygons]),colors=np.array([c.color for c in attr.data]))
(LOG/'face_groups.json').write_text(json.dumps(groups),encoding='utf8')
buildings=[]
for o in bpy.data.collections['Reference_Town'].objects:
    if o.name.startswith('Town_Floor'):
        buildings.append({'name':o.get('town_building'),'bounds':bounds(o),'corners':[list(o.matrix_world@v.co) for v in o.data.vertices]})
(LOG/'foundations.json').write_text(json.dumps(buildings),encoding='utf8')
print(json.dumps({k:{'count':len(v),'area':sum(p['area'] for p in v),'z': [min(-p['center'][1] for p in v),max(-p['center'][1] for p in v)] if v else []} for k,v in groups.items()}))
