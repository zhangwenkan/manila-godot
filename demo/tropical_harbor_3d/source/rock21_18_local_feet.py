exec((Path(bpy.data.filepath).parent/'shore_21_context.py').read_text(encoding='utf8'),globals())
LOG=ROOT/'captures/rock_earth_rebuild_20261121'
data={'heights':[],'triangles':[]}
for z in np.arange(41.4,45.41,.4):
    data['heights'].append({'z':float(z),'points':[[round(float(x),2),round(ground(float(x),float(z)),3)] for x in np.arange(15.5,19.6,.25)]})
for p in mesh.polygons:
    x,y,h=p.center;z=-y
    if 15.9<x<18.4 and 41.9<z<44.2 and p.normal.z<.6 and h<2.15:
        data['triangles'].append({'id':p.index,'vertices':[[round(float(a),4) for a in mesh.vertices[i].co] for i in p.vertices]})
(LOG/'local_feet.json').write_text(json.dumps(data,indent=2),encoding='utf8')
print(json.dumps({'height_rows':len(data['heights']),'steep_low_faces':len(data['triangles'])}))
