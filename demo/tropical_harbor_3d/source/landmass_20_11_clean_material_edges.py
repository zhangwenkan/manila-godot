# Use crown/toe distances rather than per-triangle slope to remove triangular turf teeth.
coords=np.empty((len(terrain.data.vertices),3),np.float32);terrain.data.vertices.foreach_get('co',coords.ravel())
mx=coords[:,0];mz=-coords[:,1];md=mx-shore(mz);my=coords[:,2]
lt=signed_distance(md,mz,LOW_TOP);lb=signed_distance(md,mz,LOW_TOE)
ht=signed_distance(md,mz,HIGH_TOP);hb=signed_distance(md,mz,HIGH_TOE)
attr=terrain.data.color_attributes['LandUse'];weights=np.empty((len(coords),4),np.float32);attr.data.foreach_get('color',weights.ravel());path=weights[:,2]
lc=smooth(-.30,-.06,lt);hc=smooth(-.30,-.06,ht)
lowface=smooth(.12,.35,lb)*(1-lc)
highface=smooth(.12,.35,hb)*(1-hc)
road=path
grain=.05*np.sin(mx*1.13+mz*.79)
grassline=np.interp(mz,[-70,0,8,16,23,30,36,41,46,52,58,65,75,110],[1.8,2.4,2.0,3.6,2.4,3.5,5.4,1.5,2.2,3.7,2.5,3,2,2])
vegetated=smooth(grassline-.14,grassline+.14,md+grain)*smooth(.18,.36,my)
rock=highface*(1-road)
soil=lowface*(1-smooth(.05,.3,hb))*(1-road)
grass=vegetated*(1-np.maximum(highface,lowface))*(1-road)
weights=np.column_stack([grass,rock,road,soil]).astype(np.float32);weights/=np.maximum(weights.sum(1),1)[:,None]
attr.data.foreach_set('color',weights.ravel());terrain.data.update();export_land()
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'source/harbor_landform_mass_mcp.blend'))
print('CLEAN_MATERIAL_EDGES crown/toe distances; no per-triangle turf boundary')
