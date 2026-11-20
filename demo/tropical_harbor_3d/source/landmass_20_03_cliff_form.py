# Sharpen the major masses before surface work. Blender MCP only.
before_bvh=BVHTree.FromObject(terrain,bpy.context.evaluated_depsgraph_get())
HIGH_TOE[4]=(11.1,7)
HIGH_TOE[5]=(10.7,9.5)
HIGH_TOE[6]=(6.7,11.7)
d=dd.ravel();z=zz.ravel();x=shore(z)+d
def mass_fraction(d,z,toe,crown):
    a=signed_distance(d,z,toe);b=signed_distance(d,z,crown)
    t=np.clip(a/(np.maximum(a,0)+np.maximum(-b,0)+1e-5),0,1)
    f=np.interp(t,[0,.15,.26,.64,.74,1],[0,.025,.09,.93,.98,1])
    return np.where(b>=0,1,f),a,b
h,road,lower,upper=shape(d,z)
for i in np.where(keep)[0]:h[i]=old_ground(float(x[i]),float(z[i]))
for i in np.where((rim>0)&~keep)[0]:h[i]=h[i]*(1-rim[i])+old_ground(float(x[i]),float(z[i]))*rim[i]
# Quiet, broad upper court surfaces and existing building bearing footprints.
# The grading stays inside the highland rather than adding floating pads.
for s in SITES:
    cx,cz=s['center'][0],s['gz'];depth=s['depth'];widthsite=s['w']
    target=float(shape(np.array([cx-float(shore(cz))]),np.array([cz]))[0][0])
    localx=np.abs(x-cx);localz=np.abs(z-cz)
    w=(1-smooth(depth*.5+.15,depth*.5+.8,localx))*(1-smooth(widthsite*.5+.15,widthsite*.5+.8,localz))
    if s['name']=='IslaTradingPost':w*=smooth(0,.4,signed_distance(d,z,HIGH_TOE)*-1)
    h=h*(1-w)+target*w
vv[:,2]=h
terrain.data.vertices.foreach_set('co',vv.ravel());terrain.data.update()
terrain.data.set_sharp_from_angle(angle=math.radians(40))
bpy.context.view_layer.update();ground_bvh=BVHTree.FromObject(terrain,bpy.context.evaluated_depsgraph_get())
for item in moves:
    cx,cz=item['x'],item['z'];hit,*_=before_bvh.ray_cast(Vector((cx,-cz,80)),Vector((0,0,-1)),300)
    if hit:
        delta=ground(cx,cz)-hit.z
        for name in item['objects']:
            ob=bpy.data.objects.get(name)
            if ob:ob.location.z+=delta
refresh_height();export_land()
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'source/harbor_landform_mass_mcp.blend'))
print('CLIFF_FORM steep central faces and supported courts saved')
