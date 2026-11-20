# Reuse existing group identity and move complete assemblies through Blender MCP.
script=(ROOT/'source/redesign_20_02_assemblies.py').read_text(encoding='utf8')
script=script[:script.index('# Small growth clusters')]
exec(script,globals())
for i,t in enumerate(trunks):
    p=foot(t);delta=ground(p.x,-p.y)-p.z-.09
    for ob in [t]+crowns[i*6:(i+1)*6]+branches[i*5:(i+1)*5]:ob.location.z+=delta
for i,t in enumerate(palms):
    p=foot(t);delta=ground(p.x,-p.y)-p.z-.07
    obs=[t]+parts['rachis'][i*8:(i+1)*8]+parts['leaves'][i*8:(i+1)*8]+parts['nuts'][i*3:(i+1)*3]+parts['rings'][i*12:(i+1)*12]
    for ob in obs:ob.location.z+=delta
for ob in list(fol.objects):
    if ob.name.startswith('Grass_Tuft'):
        archive.objects.link(ob);fol.objects.unlink(ob)
bpy.context.view_layer.update()
support=[]
for s in SITES:
    x,z=s['center'][0],s['gz'];d=x-shore(z)
    samples=[ground(x+dx,z+dz) for dx in [-s['depth']*.45,0,s['depth']*.45] for dz in [-s['w']*.45,0,s['w']*.45]]
    support.append({'name':s['name'],'height':ground(x,z),'spread':max(samples)-min(samples)})
(LOG/'building_support.json').write_text(json.dumps(support,indent=2),encoding='utf8')
print('BUILDING_SUPPORT',json.dumps(support))
for fn in ['reference_detail_01_materials.mcp.json']:
    code=json.loads((ROOT/'source'/fn).read_text(encoding='utf8'))['code']
    for n in ast.parse(code).body:
        if isinstance(n,ast.FunctionDef) and n.name=='export_collection':exec(compile(ast.Module(body=[n],type_ignores=[]),fn,'exec'),globals())
def export_land():
    bpy.ops.object.select_all(action='DESELECT');terrain.hide_set(False);terrain.select_set(True);bpy.context.view_layer.objects.active=terrain
    bpy.ops.export_scene.gltf(filepath=str(OUT/'terrain.glb'),export_format='GLB',use_selection=True,export_apply=True,export_yup=True,export_texcoords=True,export_normals=True,export_materials='EXPORT',export_vertex_color='ACTIVE')
export_land()
for col,file in [('Reference_Town','town.glb'),('Reference_Coast','coast.glb'),('Reference_Foliage','foliage.glb'),('Reference_Rocks','rocks.glb')]:export_collection(col,file)
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'source/harbor_landform_mass_mcp.blend'))
