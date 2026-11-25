import bpy
exec(compile('''
assert not (LOG/'connections.json').exists(),'Do not replay corrections'
# Repair side/rear window transforms after explicitly updating source matrices.
src=(ROOT/'source/terminal25_02_helpers.py').read_text(encoding='utf8')
definition=src[src.index('def window('):src.index('def roof(')]
definition=definition.replace(' if side:\\n',' bpy.context.view_layer.update()\\n if side:\\n')
exec(compile(definition,'TN25_window_matrix_fix','exec'),globals())
prefixes=['TN25_MainSideWindow','TN25_SmallSideWindow','TN25_MainRearWindow','TN25_SmallRearWindow','TN25_GalleryRearWindow']
removed=[o.name for o in C.objects if any(o.name.startswith(q) for q in prefixes)]
for name in removed:bpy.data.objects.remove(bpy.data.objects[name],do_unlink=True)
for name,x,y,w,d in [('Main',-4.9,25.35,3.7,3.3),('Small',1.45,25.275,2.7,3.15)]:
 for side in [-1,1]:window(name+'SideWindow',x+side*w/2,y,3.6,1.06,1.2,side=side)
 window(name+'RearWindow',x,y+d/2+.03,4.325,1.12,1.05,side=2)
window('GalleryRearWindow',-1.475,26.31,3.32,1.20,1.05,side=2)
# Split the low front facade rail at the main doorway.
cross=[o for o in C.objects if o.name.startswith('TN25_MainFacadeBeam') and abs(o.location.y-23.645)<.02 and abs(o.location.z-2.35)<.02]
assert len(cross)==1
bpy.data.objects.remove(cross[0],do_unlink=True)
for a,b in [(-6.85,-5.70),(-4.10,-2.95)]:B('DoorSideBaseRail',((a+b)/2,23.645,2.35),(b-a,.17,.17),'wood',.012)
# The porch and gallery share a continuous landing, including the service shelf.
for j in range(11):B('GalleryLanding',(-3.05+(j+.5)*3.15/11,23.85,1.79),(3.15/11-.008,.45,.12),'deck',.008)
for xx in [-2.97,-.02]:B('GalleryLandingBearer',(xx,23.85,1.65),(.15,.60,.16),'beam',.01)
# A practical side work deck carries the hoist, barrel and loading activity.
for j in range(9):B('WorkDeckPlank',(-9.25+(j+.5)*2.48/9,24.55,1.79),(2.48/9-.008,2.60,.12),'deck',.008)
for xx in [-9.07,-7.03]:
 for yy in [23.40,25.65]:
  bottom=h_at(xx,yy,bvh)-.14;top=1.74
  B('WorkDeckPier',(xx,yy,(bottom+top)/2),(.24,.24,max(.10,top-bottom)),'beam',.01)
 B('WorkDeckBearer',(xx,24.55,1.65),(.18,2.72,.18),'beam',.01)
for xx in [-9.18,-8.02,-6.86]:B('WorkBackPost',(xx,25.80,2.27),(.10,.10,.86),'wood',.009)
for zz in [2.04,2.63]:L('WorkBackRail',(-9.18,25.80,zz),(-6.86,25.80,zz),.065,'wood')
# Clear the right eave with the entire neighbouring tree, keeping the group intact.
names=plan['foliage_groups']['tree_3']['names']
tree=bpy.data.objects[names[0]]
oldrow=next(r for r in json.loads((LOG/'objects_before.json').read_text()) if r['name']==names[0])
base=(np.array(oldrow['bounds'][0])+np.array(oldrow['bounds'][1]))*.5
tdx=1.0;tdy=.5;tdz=h_at(base[0]+tdx,base[1]+tdy)-h_at(base[0],base[1])
for name in names:bpy.data.objects[name].location+=Vector((tdx,tdy,tdz))
bpy.context.view_layer.update()
report={'window_objects_replaced':removed,'door_crossbar_split':True,'landing_filled':True,'work_deck_added':True,'tree_group':names,'tree_delta':[tdx,tdy,tdz]}
(LOG/'connections.json').write_text(json.dumps(report,indent=2),encoding='utf8')
print(json.dumps(report))
''','terminal25_07_connections.py','exec'),bpy.app.driver_namespace['terminal25'])
