import bpy
exec(compile('''
assert not (LOG/'finish_details.json').exists(),'Do not replay detail offset'
rows=[]
for o in C.objects:
 if not o.name.startswith('TN25_GalleryRoofTile'):continue
 row=round((min(v.co.y for v in o.data.vertices)-23.84)/.50)
 o.location.z+=.012*(row+1)
 rows.append([o.name,row,float(o.location.z)])
# One moved palm tip touched the rear wall. Move its leaf-bearing tree as a whole.
names=plan['foliage_groups']['palm_17']['names']
for name in names:bpy.data.objects[name].location.y+=.35
connections=json.loads((LOG/'connections.json').read_text())
connections['palm_additional_delta']=[0,.35,0]
(LOG/'connections.json').write_text(json.dumps(connections,indent=2),encoding='utf8')
bpy.context.view_layer.update()
(LOG/'finish_details.json').write_text(json.dumps({'gallery_tile_offsets':rows,'palm_additional_delta':[0,.35,0]},indent=2),encoding='utf8')
print('TN25_FINISH',len(rows))
''','terminal25_10_finish.py','exec'),bpy.app.driver_namespace['terminal25'])
