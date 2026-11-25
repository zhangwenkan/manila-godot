exec((Path(bpy.data.filepath).parent/'shore_21_context.py').read_text(encoding='utf8'),globals())
LOG=ROOT/'captures/rock_earth_rebuild_20261121'
result=[]
for c in bpy.data.collections:
    if not c.name.startswith('Reference'):continue
    for o in c.objects:
        if o.type!='MESH':continue
        b=bounds(o)
        if b[0][0]<22 and b[0][1]>14.6 and b[1][0]<-41 and b[1][1]>-47 and b[2][0]<3.9:
            result.append({'name':o.name,'collection':c.name,'bounds':b,'hidden':o.hide_render,'verts':len(o.data.vertices)})
(LOG/'obstructions.json').write_text(json.dumps(result,indent=2),encoding='utf8')
print(json.dumps(result))
