import bpy
exec(compile('''
assert not (LOG/'right_stair_fix.json').exists(),'Do not replay stair adjustment'
shift=-.70
steps=[o for o in C.objects if o.name.startswith('TN25_WideEntryStep') and abs(o.location.x-1.65)<.01]
bearings=[o for o in C.objects if o.name.startswith('TN25_StepBearing') and o.location.x>.5]
assert len(steps)==5 and len(bearings)==10
for o in steps+bearings:o.location.y+=shift
# Continuous top landing now spans the moved stairs and the main porch.
for j in range(7):
 o=B('RightStairLanding',(.65+(j+.5)*2/7,22.47,1.79),(2/7-.008,.66,.12),'deck',.008)
 o['terminal25_walk_support']=True
for xx in [.78,2.52]:B('RightLandingBearer',(xx,22.47,1.65),(.14,.76,.16),'beam',.009)
for xx in [.78,2.52]:
 for yy in [22.19,22.74]:
  bottom=min(.88,h_at(xx,yy,bvh)-.12);top=1.74
  B('RightLandingPier',(xx,yy,(bottom+top)/2),(.16,.16,top-bottom),'beam',.009)
# Visible stringers give each relocated stair a complete bearing path.
for xx in [.77,2.53]:L('RightStairStringer',(xx,20.82,.94),(xx,22.15,1.70),.12,'beam')
bpy.context.view_layer.update()
(LOG/'right_stair_fix.json').write_text(json.dumps({'steps':[o.name for o in steps],'bearings':[o.name for o in bearings],'delta':[0,shift,0],'top_landing_y':[22.14,22.80],'reason':'Existing slope intruded 0.1427m through first right tread; move complete run seaward on preserved apron and bridge its landing'},indent=2),encoding='utf8')
print('TN25_RIGHT_STAIRS_MOVED',len(steps),len(bearings))
''','terminal25_11_right_stairs.py','exec'),bpy.app.driver_namespace['terminal25'])
