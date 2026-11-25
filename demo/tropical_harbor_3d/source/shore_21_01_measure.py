exec((Path(bpy.data.filepath).parent/'shore_21_context.py').read_text(encoding='utf8'),globals())
groups={}
for o in bpy.data.collections['Reference_Town'].objects:
    name=o.get('town_building')
    if not name or o.type!='MESH':continue
    groups.setdefault(name,[]).append(o)
report={}
for name,obs in groups.items():
    bb=[bounds(o) for o in obs]
    report[name]={'bounds':[[min(b[i][0] for b in bb),max(b[i][1] for b in bb)] for i in range(3)],'count':len(obs),
      'foot_objects':[(o.name,bounds(o)) for o in obs if any(s in o.name.lower() for s in ['foundation','floor','porch','step','plinth'])]}
(LOG/'buildings_before.json').write_text(json.dumps(report,indent=2),encoding='utf8')
positions=np.empty((len(mesh.vertices),3),np.float32);mesh.vertices.foreach_get('co',positions.ravel())
loops=np.empty(len(mesh.loops),np.int32);mesh.loops.foreach_get('vertex_index',loops)
starts=np.empty(len(mesh.polygons),np.int32);mesh.polygons.foreach_get('loop_start',starts)
sizes=np.empty(len(mesh.polygons),np.int32);mesh.polygons.foreach_get('loop_total',sizes)
colors=np.empty((len(mesh.loops),4),np.float32);mesh.color_attributes['LandUse'].data.foreach_get('color',colors.ravel())
np.savez_compressed(str(LOG/'terrain_before.npz'),positions=positions,loops=loops,starts=starts,sizes=sizes,colors=colors)
samples={str(z):[(d,round(ground(float(shore(z)+d),z),3)) for d in range(2,24)] for z in [38,40,42,44,46,48,50,52,54,56,58,60,62]}
print(json.dumps({'buildings':{k: {'bounds':v['bounds'],'count':v['count']} for k,v in report.items()},'height_cross_sections':samples},ensure_ascii=False))
